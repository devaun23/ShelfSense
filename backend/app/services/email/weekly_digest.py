"""
Weekly Email Digest Service.
Sends weekly progress reports to users every Sunday.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import (
    User, UserSettings, QuestionAttempt, ScheduledReview,
    UserEngagementScore, UserPerformance, ScorePredictionHistory
)
from app.services.email.email_service import get_email_service
from app.services.email.email_templates import render_template

logger = logging.getLogger(__name__)


def get_weekly_stats(db: Session, user_id: str, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
    """
    Calculate weekly statistics for a user.

    Returns:
        Dict with questions_answered, accuracy, study_days, etc.
    """
    # Get all attempts for the week
    attempts = db.query(QuestionAttempt).filter(
        and_(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= week_start,
            QuestionAttempt.attempted_at < week_end
        )
    ).all()

    if not attempts:
        return {
            "questions_answered": 0,
            "accuracy": 0,
            "study_days": 0,
            "correct_count": 0
        }

    correct_count = sum(1 for a in attempts if a.is_correct)
    accuracy = round((correct_count / len(attempts)) * 100) if attempts else 0

    # Count unique study days
    study_days = len(set(a.attempted_at.date() for a in attempts))

    return {
        "questions_answered": len(attempts),
        "accuracy": accuracy,
        "study_days": study_days,
        "correct_count": correct_count
    }


def get_weak_areas(db: Session, user_id: str, week_start: datetime, week_end: datetime) -> List[Dict[str, Any]]:
    """
    Get weak areas from the past week based on accuracy by specialty.

    Returns:
        List of {name, accuracy, attempts} dicts sorted by accuracy ascending
    """
    from app.models.models import Question

    # Get attempts with questions to get specialty
    attempts = db.query(
        QuestionAttempt, Question
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        and_(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= week_start,
            QuestionAttempt.attempted_at < week_end
        )
    ).all()

    # Group by specialty
    specialty_stats = {}
    for attempt, question in attempts:
        specialty = question.specialty or question.source or "Unknown"
        if specialty not in specialty_stats:
            specialty_stats[specialty] = {"correct": 0, "total": 0}
        specialty_stats[specialty]["total"] += 1
        if attempt.is_correct:
            specialty_stats[specialty]["correct"] += 1

    # Calculate accuracy and filter weak areas (< 70% with at least 5 attempts)
    weak_areas = []
    for specialty, stats in specialty_stats.items():
        if stats["total"] >= 5:
            accuracy = round((stats["correct"] / stats["total"]) * 100)
            if accuracy < 70:
                weak_areas.append({
                    "name": specialty.replace("_", " ").title(),
                    "accuracy": accuracy,
                    "attempts": stats["total"]
                })

    # Sort by accuracy ascending (weakest first)
    weak_areas.sort(key=lambda x: x["accuracy"])
    return weak_areas[:5]  # Top 5 weak areas


def get_score_change(db: Session, user_id: str) -> Optional[int]:
    """
    Get the change in predicted score from last week.

    Returns:
        Score change (positive or negative) or None if not enough data
    """
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # Get most recent prediction
    current = db.query(ScorePredictionHistory).filter(
        and_(
            ScorePredictionHistory.user_id == user_id,
            ScorePredictionHistory.calculated_at >= week_ago
        )
    ).order_by(ScorePredictionHistory.calculated_at.desc()).first()

    # Get prediction from a week ago
    previous = db.query(ScorePredictionHistory).filter(
        and_(
            ScorePredictionHistory.user_id == user_id,
            ScorePredictionHistory.calculated_at >= two_weeks_ago,
            ScorePredictionHistory.calculated_at < week_ago
        )
    ).order_by(ScorePredictionHistory.calculated_at.desc()).first()

    if current and previous:
        return current.predicted_score - previous.predicted_score

    return None


async def send_weekly_digest(db: Session, user: User) -> bool:
    """
    Send weekly digest email to a user.

    Returns:
        True if sent successfully
    """
    # Check if user has email notifications enabled
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == user.id
    ).first()

    if settings and not settings.email_notifications:
        return False

    if not user.email:
        return False

    email_service = get_email_service()

    # Calculate week range (last 7 days)
    now = datetime.utcnow()
    week_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = week_end - timedelta(days=7)

    # Get weekly stats
    stats = get_weekly_stats(db, user.id, week_start, week_end)

    # Skip if user didn't study at all
    if stats["questions_answered"] == 0:
        logger.info(f"Skipping digest for {user.email} - no activity")
        return False

    # Get engagement data
    engagement = db.query(UserEngagementScore).filter(
        UserEngagementScore.user_id == user.id
    ).first()

    current_streak = engagement.streak_current if engagement else 0
    best_streak = engagement.streak_best if engagement else 0
    streak_at_risk = False

    if engagement and engagement.last_activity_at:
        days_since = (now - engagement.last_activity_at).days
        streak_at_risk = days_since >= 1 and current_streak > 0

    # Get performance data for predicted score
    performance = db.query(UserPerformance).filter(
        UserPerformance.user_id == user.id
    ).order_by(UserPerformance.calculated_at.desc()).first()

    predicted_score = performance.predicted_score if performance else None
    score_change = get_score_change(db, user.id)

    # Get weak areas
    weak_areas = get_weak_areas(db, user.id, week_start, week_end)

    # Count reviews due
    reviews_due = db.query(ScheduledReview).filter(
        and_(
            ScheduledReview.user_id == user.id,
            ScheduledReview.scheduled_for <= now
        )
    ).count()

    # Generate unsubscribe token
    unsub_token = email_service._generate_unsubscribe_token(db, user.id, "digest")
    unsubscribe_url = email_service._get_unsubscribe_url(unsub_token)

    # Render template
    context = {
        "first_name": user.first_name or "there",
        "week_start": week_start.strftime("%b %d"),
        "week_end": (week_end - timedelta(days=1)).strftime("%b %d"),
        "questions_answered": stats["questions_answered"],
        "accuracy": stats["accuracy"],
        "current_streak": current_streak,
        "best_streak": best_streak,
        "streak_at_risk": streak_at_risk,
        "predicted_score": predicted_score,
        "score_change": score_change,
        "weak_areas": weak_areas,
        "reviews_due": reviews_due,
        "study_url": f"{email_service.frontend_url}/study",
        "unsubscribe_url": unsubscribe_url
    }

    html_content = render_template("weekly_digest.html", context)
    subject = f"Your Weekly Progress: {stats['questions_answered']} questions, {stats['accuracy']}% accuracy"

    return await email_service._send_and_log(
        db=db,
        user_id=user.id,
        email_type="digest",
        to_email=user.email,
        subject=subject,
        html_content=html_content
    )


async def send_weekly_digests() -> int:
    """
    Send weekly digests to all eligible users.
    Should be called once per week (e.g., Sunday morning).

    Returns:
        Number of digests sent
    """
    db = SessionLocal()
    sent_count = 0

    try:
        # Get all users with email notifications enabled
        users = db.query(User).join(
            UserSettings, User.id == UserSettings.user_id, isouter=True
        ).filter(
            User.email.isnot(None)
        ).all()

        logger.info(f"Sending weekly digests to {len(users)} users")

        for user in users:
            try:
                success = await send_weekly_digest(db, user)
                if success:
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send digest to {user.email}: {e}")

        logger.info(f"Sent {sent_count} weekly digests")

    except Exception as e:
        logger.error(f"Error in weekly digest job: {e}")

    finally:
        db.close()

    return sent_count


async def run_weekly_digest_scheduler():
    """
    Background task that runs weekly to send digests.
    Sends on Sunday at 9 AM UTC.
    """
    logger.info("Weekly digest scheduler started")

    while True:
        try:
            now = datetime.utcnow()

            # Check if it's Sunday at 9 AM UTC
            if now.weekday() == 6 and now.hour == 9:
                await send_weekly_digests()
                # Sleep for 2 hours to avoid re-sending
                await asyncio.sleep(7200)
            else:
                # Sleep for 1 hour and check again
                await asyncio.sleep(3600)

        except Exception as e:
            logger.error(f"Error in weekly digest scheduler: {e}")
            await asyncio.sleep(3600)
