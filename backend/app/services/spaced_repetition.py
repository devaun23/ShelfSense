"""
Spaced Repetition Service

Implements Anki-style spaced repetition scheduling for questions.
Uses SM-2 algorithm for review intervals.

Review intervals:
- Wrong answer: 1 day
- 1st correct: 3 days
- 2nd correct: 7 days
- 3rd correct: 14 days
- 4th+ correct: 30 days
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import ScheduledReview, Question, QuestionAttempt


# Interval progression map
INTERVAL_MAP = {
    "1d": 3,    # After reviewing 1d item correctly, next review in 3 days
    "3d": 7,    # After reviewing 3d item correctly, next review in 7 days
    "7d": 14,   # After reviewing 7d item correctly, next review in 14 days
    "14d": 30,  # After reviewing 14d item correctly, next review in 30 days
    "30d": 60,  # Mastered - review in 60 days
}


def schedule_review(
    db: Session,
    user_id: str,
    question_id: str,
    is_correct: bool,
    source: Optional[str] = None
) -> ScheduledReview:
    """
    Schedule or update review for a question based on user's answer.

    Args:
        db: Database session
        user_id: User ID
        question_id: Question ID
        is_correct: Whether user answered correctly
        source: Question source/topic (for filtering)

    Returns:
        ScheduledReview object
    """
    # Check if review already exists
    existing = db.query(ScheduledReview).filter_by(
        user_id=user_id,
        question_id=question_id
    ).first()

    if not existing:
        # First time seeing this question
        if is_correct:
            # Got it right first try - schedule for 3 days
            interval = "3d"
            days = 3
            stage = "Learning"
        else:
            # Got it wrong - schedule for tomorrow
            interval = "1d"
            days = 1
            stage = "Learning"

        scheduled_for = datetime.utcnow() + timedelta(days=days)

        review = ScheduledReview(
            user_id=user_id,
            question_id=question_id,
            scheduled_for=scheduled_for,
            review_interval=interval,
            times_reviewed=1,
            learning_stage=stage,
            source=source,
            last_reviewed=datetime.utcnow()
        )

        db.add(review)
        db.commit()
        return review

    else:
        # Subsequent reviews - update schedule
        existing.times_reviewed += 1
        existing.last_reviewed = datetime.utcnow()

        if not is_correct:
            # Got it wrong - reset to 1 day
            interval = "1d"
            days = 1
            stage = "Learning"
        else:
            # Got it right - increase interval
            current_interval = existing.review_interval
            next_days = INTERVAL_MAP.get(current_interval, 30)
            days = next_days

            # Update interval string
            if days == 1:
                interval = "1d"
            elif days == 3:
                interval = "3d"
            elif days == 7:
                interval = "7d"
            elif days == 14:
                interval = "14d"
            elif days == 30:
                interval = "30d"
            else:
                interval = "60d"

            # Update learning stage
            if days >= 30:
                stage = "Mastered"
            elif days >= 7:
                stage = "Review"
            else:
                stage = "Learning"

        existing.review_interval = interval
        existing.scheduled_for = datetime.utcnow() + timedelta(days=days)
        existing.learning_stage = stage

        db.commit()
        return existing


def get_todays_reviews(db: Session, user_id: str) -> List[ScheduledReview]:
    """
    Get all reviews scheduled for today or earlier.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        List of ScheduledReview objects
    """
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    reviews = db.query(ScheduledReview).filter(
        ScheduledReview.user_id == user_id,
        ScheduledReview.scheduled_for < tomorrow
    ).order_by(
        ScheduledReview.scheduled_for.asc()
    ).all()

    return reviews


def get_upcoming_reviews(db: Session, user_id: str, days: int = 7) -> dict:
    """
    Get reviews scheduled in the next N days, grouped by date.

    Args:
        db: Database session
        user_id: User ID
        days: Number of days to look ahead (default 7)

    Returns:
        Dict mapping date strings to lists of ScheduledReview objects
        {
            "2025-11-21": [ScheduledReview, ScheduledReview, ...],
            "2025-11-22": [ScheduledReview, ...],
            ...
        }
    """
    today = datetime.utcnow().date()
    end_date = today + timedelta(days=days)

    reviews = db.query(ScheduledReview).filter(
        ScheduledReview.user_id == user_id,
        ScheduledReview.scheduled_for >= today,
        ScheduledReview.scheduled_for <= end_date
    ).order_by(
        ScheduledReview.scheduled_for.asc()
    ).all()

    # Group by date
    calendar = {}
    for review in reviews:
        date_str = review.scheduled_for.strftime("%Y-%m-%d")
        if date_str not in calendar:
            calendar[date_str] = []
        calendar[date_str].append(review)

    return calendar


def get_review_stats(db: Session, user_id: str, specialty: Optional[str] = None) -> dict:
    """
    Get review statistics for user.

    Args:
        db: Database session
        user_id: User ID
        specialty: Optional specialty filter (e.g., 'Internal Medicine')

    Returns:
        Dict with review stats:
        {
            "total_reviews": 123,
            "due_today": 5,
            "learning": 10,
            "review": 50,
            "mastered": 63,
            "by_source": {...}
        }
    """
    # Build base query for all reviews
    base_query = db.query(ScheduledReview).filter(ScheduledReview.user_id == user_id)

    # Add specialty filter if provided (join with Question table)
    if specialty:
        base_query = base_query.join(
            Question, ScheduledReview.question_id == Question.id
        ).filter(Question.specialty == specialty)

    all_reviews = base_query.all()

    # Count by stage
    learning = sum(1 for r in all_reviews if r.learning_stage == "Learning")
    review = sum(1 for r in all_reviews if r.learning_stage == "Review")
    mastered = sum(1 for r in all_reviews if r.learning_stage == "Mastered")

    # Count due today
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    due_today = sum(1 for r in all_reviews if r.scheduled_for.date() < tomorrow)

    # Count by source
    by_source = {}
    for review in all_reviews:
        source = review.source or "Unknown"
        if source not in by_source:
            by_source[source] = 0
        by_source[source] += 1

    return {
        "total_reviews": len(all_reviews),
        "due_today": due_today,
        "learning": learning,
        "review": review,
        "mastered": mastered,
        "by_source": by_source
    }


def get_questions_for_todays_reviews(db: Session, user_id: str) -> List[Question]:
    """
    Get Question objects for today's reviews.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        List of Question objects scheduled for review today
    """
    reviews = get_todays_reviews(db, user_id)
    question_ids = [review.question_id for review in reviews]

    questions = db.query(Question).filter(
        Question.id.in_(question_ids)
    ).all()

    return questions
