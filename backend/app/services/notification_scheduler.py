"""
Notification Scheduler.
Runs hourly to send push notifications for daily reminders and streak alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import (
    User, UserSettings, UserEngagementScore, PushSubscription, ScheduledReview
)
from app.services.push_notification_service import get_push_notification_service

logger = logging.getLogger(__name__)


def get_users_for_push_reminder(db: Session, current_hour: int) -> List[Tuple[User, int, int, bool]]:
    """
    Get users who should receive a push reminder at this hour.

    Returns:
        List of (user, review_count, current_streak, streak_at_risk) tuples
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Find users with:
    # - daily_reminder = True
    # - reminder_time hour matches current UTC hour
    # - have at least one active push subscription
    users_with_settings = db.query(User, UserSettings).join(
        UserSettings, User.id == UserSettings.user_id
    ).filter(
        and_(
            UserSettings.daily_reminder == True,
            UserSettings.reminder_time.isnot(None)
        )
    ).all()

    matching_users = []

    for user, settings in users_with_settings:
        # Parse reminder_time "HH:MM" and check hour
        try:
            reminder_hour = int(settings.reminder_time.split(":")[0])
            if reminder_hour != current_hour:
                continue
        except (ValueError, AttributeError):
            continue

        # Check if user has active push subscriptions
        has_push = db.query(PushSubscription).filter(
            and_(
                PushSubscription.user_id == user.id,
                PushSubscription.is_active == True
            )
        ).first() is not None

        if not has_push:
            continue

        # Count reviews due today
        review_count = db.query(ScheduledReview).filter(
            and_(
                ScheduledReview.user_id == user.id,
                ScheduledReview.scheduled_for <= now
            )
        ).count()

        # Get streak info
        engagement = db.query(UserEngagementScore).filter(
            UserEngagementScore.user_id == user.id
        ).first()

        current_streak = 0
        streak_at_risk = False

        if engagement:
            current_streak = engagement.streak_current or 0

            # Check if streak is at risk
            if engagement.last_activity_at:
                last_activity_date = engagement.last_activity_at.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                days_since = (today_start - last_activity_date).days

                # Streak at risk if last activity was yesterday
                if days_since == 1 and current_streak > 0:
                    streak_at_risk = True

        matching_users.append((user, review_count, current_streak, streak_at_risk))

    return matching_users


async def send_push_reminders_for_hour(current_hour: int) -> int:
    """
    Send push notification reminders for all users scheduled at this hour.

    Args:
        current_hour: UTC hour to process

    Returns:
        Number of reminders sent
    """
    push_service = get_push_notification_service()

    if not push_service.is_configured():
        logger.info("Push notifications not configured, skipping reminders")
        return 0

    db = SessionLocal()
    sent_count = 0

    try:
        users = get_users_for_push_reminder(db, current_hour)
        logger.info(f"Found {len(users)} users due for push reminders at hour {current_hour}")

        for user, review_count, current_streak, streak_at_risk in users:
            # Get all active subscriptions for user
            subs = db.query(PushSubscription).filter(
                and_(
                    PushSubscription.user_id == user.id,
                    PushSubscription.is_active == True
                )
            ).all()

            for sub in subs:
                try:
                    subscription_info = {
                        "endpoint": sub.endpoint,
                        "keys": {
                            "p256dh": sub.p256dh_key,
                            "auth": sub.auth_key
                        }
                    }

                    success = await push_service.send_study_reminder(
                        subscription_info=subscription_info,
                        user_name=user.first_name or "there",
                        reviews_due=review_count,
                        streak_at_risk=streak_at_risk,
                        current_streak=current_streak
                    )

                    if success:
                        sent_count += 1
                        sub.last_used = datetime.utcnow()
                        sub.failed_attempts = 0
                    else:
                        sub.failed_attempts += 1
                        if sub.failed_attempts >= 3:
                            sub.is_active = False
                            logger.info(f"Deactivated subscription {sub.id} after 3 failures")

                except Exception as e:
                    logger.error(f"Failed to send push to {user.email}: {e}")
                    sub.failed_attempts += 1

        db.commit()
        logger.info(f"Sent {sent_count} push reminders for hour {current_hour}")

    except Exception as e:
        logger.error(f"Error in push reminder scheduler: {e}")

    finally:
        db.close()

    return sent_count


async def run_hourly_push_reminder_check():
    """
    Background task that runs every hour to send push reminders.
    Designed to run continuously within the FastAPI process.
    """
    logger.info("Push notification reminder scheduler started")

    while True:
        try:
            current_hour = datetime.utcnow().hour
            await send_push_reminders_for_hour(current_hour)

        except Exception as e:
            logger.error(f"Error in hourly push reminder check: {e}")

        # Wait 1 hour before next check
        await asyncio.sleep(3600)
