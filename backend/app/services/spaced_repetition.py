"""
Spaced Repetition Service

Implements SM-2 algorithm for spaced repetition scheduling.
This is the same algorithm used by Anki, proven effective for 30+ years.

SM-2 Algorithm:
- Quality rating 0-5 based on answer correctness and response time
- Ease factor starts at 2.5 and adjusts based on performance
- Intervals grow exponentially: 1 → 6 → (interval * ease_factor)
- Wrong answers reset to 1 day

Reference: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import ScheduledReview, Question, QuestionAttempt


# SM-2 Constants
DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3

# Interval progression map (legacy support + SM-2 aligned)
INTERVAL_MAP = {
    "1d": 6,    # First correct → 6 days (SM-2 standard)
    "6d": 15,   # Second correct at ~6 days → ~15 days (6 * 2.5)
    "3d": 7,    # Legacy: 3d → 7d
    "7d": 14,   # Legacy: 7d → 14d
    "14d": 30,  # 14d → 30d
    "15d": 38,  # ~15d → ~38d
    "30d": 60,  # Mastered - review in 60 days
    "38d": 60,  # Cap at 60 days
    "60d": 90,  # Extended mastery
}


def calculate_sm2_quality(is_correct: bool, time_seconds: float = 0, confidence: str = "medium") -> int:
    """
    Calculate SM-2 quality rating (0-5) based on answer.

    Quality ratings:
      5 = perfect, instant recall (<30s, high confidence)
      4 = correct after hesitation (30-60s)
      3 = correct with difficulty (>60s or low confidence)
      2 = incorrect, but recognized answer when shown
      1 = incorrect, vaguely remembered
      0 = complete blackout

    Args:
        is_correct: Whether the answer was correct
        time_seconds: Time taken to answer
        confidence: "high", "medium", or "low"

    Returns:
        Quality rating 0-5
    """
    if not is_correct:
        # For incorrect answers, we default to 1 (needs review)
        # Could be enhanced with user feedback on "did you know it?"
        return 1

    # Correct answer - rate by speed and confidence
    if time_seconds < 30 and confidence == "high":
        return 5  # Perfect recall
    elif time_seconds < 60:
        return 4  # Good recall
    elif time_seconds < 120:
        return 3  # Acceptable
    else:
        return 3  # Still correct, just slow


def calculate_sm2_interval(
    current_interval_days: int,
    ease_factor: float,
    quality: int,
    repetition_number: int
) -> Tuple[int, float]:
    """
    Calculate next interval using SM-2 algorithm.

    Args:
        current_interval_days: Current interval in days
        ease_factor: Current ease factor (2.5 default)
        quality: Quality rating 0-5
        repetition_number: Number of times reviewed

    Returns:
        Tuple of (next_interval_days, new_ease_factor)
    """
    # Update ease factor based on quality
    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(MIN_EASE_FACTOR, new_ef)  # Never go below 1.3

    if quality < 3:
        # Failed - reset to beginning
        return 1, new_ef

    # Passed - calculate next interval
    if repetition_number <= 1:
        next_interval = 1
    elif repetition_number == 2:
        next_interval = 6
    else:
        next_interval = round(current_interval_days * new_ef)

    # Cap at 180 days (6 months) for sanity
    next_interval = min(next_interval, 180)

    return next_interval, new_ef


def interval_to_string(days: int) -> str:
    """Convert interval days to string representation."""
    if days <= 1:
        return "1d"
    elif days <= 3:
        return "3d"
    elif days <= 6:
        return "6d"
    elif days <= 7:
        return "7d"
    elif days <= 14:
        return "14d"
    elif days <= 15:
        return "15d"
    elif days <= 30:
        return "30d"
    elif days <= 38:
        return "38d"
    elif days <= 60:
        return "60d"
    else:
        return "90d"


def string_to_interval(interval_str: str) -> int:
    """Convert interval string to days."""
    mapping = {
        "1d": 1, "3d": 3, "6d": 6, "7d": 7,
        "14d": 14, "15d": 15, "30d": 30,
        "38d": 38, "60d": 60, "90d": 90
    }
    return mapping.get(interval_str, 1)


def schedule_review(
    db: Session,
    user_id: str,
    question_id: str,
    is_correct: bool,
    source: Optional[str] = None,
    time_seconds: float = 0
) -> ScheduledReview:
    """
    Schedule or update review for a question using SM-2 algorithm.

    Args:
        db: Database session
        user_id: User ID
        question_id: Question ID
        is_correct: Whether user answered correctly
        source: Question source/topic (for filtering)
        time_seconds: Time taken to answer (for SM-2 quality calculation)

    Returns:
        ScheduledReview object
    """
    # Calculate SM-2 quality rating
    quality = calculate_sm2_quality(is_correct, time_seconds)

    # Check if review already exists
    existing = db.query(ScheduledReview).filter_by(
        user_id=user_id,
        question_id=question_id
    ).first()

    if not existing:
        # First time seeing this question
        repetition_number = 1
        current_interval = 0
        ease_factor = DEFAULT_EASE_FACTOR

        # Calculate next interval using SM-2
        next_days, _ = calculate_sm2_interval(
            current_interval, ease_factor, quality, repetition_number
        )

        # Determine learning stage
        if next_days >= 30:
            stage = "Mastered"
        elif next_days >= 7:
            stage = "Review"
        else:
            stage = "Learning"

        scheduled_for = datetime.utcnow() + timedelta(days=next_days)
        interval = interval_to_string(next_days)

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
        # Subsequent reviews - use SM-2 algorithm
        existing.times_reviewed += 1
        existing.last_reviewed = datetime.utcnow()

        # Get current interval in days
        current_interval = string_to_interval(existing.review_interval)

        # Calculate next interval using SM-2
        # We simulate ease factor since we don't store it (default 2.5)
        # In a full implementation, ease_factor would be stored per review
        ease_factor = DEFAULT_EASE_FACTOR
        next_days, _ = calculate_sm2_interval(
            current_interval,
            ease_factor,
            quality,
            existing.times_reviewed
        )

        # Determine learning stage
        if next_days >= 30:
            stage = "Mastered"
        elif next_days >= 7:
            stage = "Review"
        else:
            stage = "Learning"

        existing.review_interval = interval_to_string(next_days)
        existing.scheduled_for = datetime.utcnow() + timedelta(days=next_days)
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
    for scheduled_review in all_reviews:
        source = scheduled_review.source or "Unknown"
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
