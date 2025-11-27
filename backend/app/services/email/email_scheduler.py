"""
Email reminder scheduler.
Runs hourly to send daily review reminders to users at their preferred time.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import User, UserSettings, ScheduledReview

logger = logging.getLogger(__name__)


def get_users_for_reminder(db: Session, current_hour: int) -> List[Tuple[User, int]]:
    """
    Get users who should receive a reminder at this hour.

    Args:
        db: Database session
        current_hour: Current UTC hour (0-23)

    Returns:
        List of (user, review_count) tuples for users with due reviews
    """
    # Find users with:
    # - email_notifications = True
    # - daily_reminder = True
    # - reminder_time hour matches current UTC hour
    users_with_settings = db.query(User, UserSettings).join(
        UserSettings, User.id == UserSettings.user_id
    ).filter(
        and_(
            UserSettings.email_notifications == True,
            UserSettings.daily_reminder == True,
            UserSettings.reminder_time.isnot(None),
            User.email.isnot(None)
        )
    ).all()

    matching_users = []
    now = datetime.utcnow()

    for user, settings in users_with_settings:
        # Parse reminder_time "HH:MM" and check hour
        try:
            reminder_hour = int(settings.reminder_time.split(":")[0])
            if reminder_hour != current_hour:
                continue
        except (ValueError, AttributeError):
            continue

        # Count reviews due today
        review_count = db.query(ScheduledReview).filter(
            and_(
                ScheduledReview.user_id == user.id,
                ScheduledReview.scheduled_for <= now
            )
        ).count()

        # Only add users who have reviews due
        if review_count > 0:
            matching_users.append((user, review_count))

    return matching_users


async def send_reminders_for_hour(current_hour: int) -> int:
    """
    Send review reminders for all users scheduled at this hour.

    Args:
        current_hour: UTC hour to process

    Returns:
        Number of reminders sent
    """
    # Import here to avoid circular imports
    from app.services.email.email_service import get_email_service

    db = SessionLocal()
    sent_count = 0

    try:
        users = get_users_for_reminder(db, current_hour)
        logger.info(f"Found {len(users)} users due for reminders at hour {current_hour}")

        email_service = get_email_service()

        for user, review_count in users:
            try:
                success = await email_service.send_review_reminder(
                    db, user, review_count
                )
                if success:
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder to {user.email}: {e}")

        logger.info(f"Sent {sent_count}/{len(users)} reminders for hour {current_hour}")

    except Exception as e:
        logger.error(f"Error in reminder scheduler: {e}")

    finally:
        db.close()

    return sent_count


async def run_hourly_reminder_check():
    """
    Background task that runs every hour to check for and send reminders.
    Designed to run continuously within the FastAPI process.
    """
    logger.info("Email reminder scheduler started")

    while True:
        try:
            current_hour = datetime.utcnow().hour
            await send_reminders_for_hour(current_hour)

        except Exception as e:
            logger.error(f"Error in hourly reminder check: {e}")

        # Wait 1 hour before next check
        # Sleep for slightly less to account for processing time
        await asyncio.sleep(3600)
