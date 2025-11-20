"""
Reviews Router

Provides endpoints for spaced repetition review system.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.models import Question, ScheduledReview
from app.services.spaced_repetition import (
    get_todays_reviews,
    get_upcoming_reviews,
    get_review_stats,
    get_questions_for_todays_reviews
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class QuestionResponse(BaseModel):
    id: str
    vignette: str
    choices: List[str]
    source: str
    recency_weight: float
    review_info: dict  # Additional review metadata

    class Config:
        from_attributes = True


class ReviewStatsResponse(BaseModel):
    total_reviews: int
    due_today: int
    learning: int
    review: int
    mastered: int
    by_source: dict


class UpcomingReviewsResponse(BaseModel):
    calendar: dict  # Date strings -> count
    total: int


@router.get("/today", response_model=List[QuestionResponse])
def get_todays_review_questions(user_id: str, db: Session = Depends(get_db)):
    """
    Get all questions scheduled for review today.
    """
    # Get today's review schedule
    reviews = get_todays_reviews(db, user_id)

    if not reviews:
        return []

    # Get questions
    question_ids = [review.question_id for review in reviews]
    questions = db.query(Question).filter(Question.id.in_(question_ids)).all()

    # Build response with review metadata
    review_map = {review.question_id: review for review in reviews}

    return [
        QuestionResponse(
            id=q.id,
            vignette=q.vignette,
            choices=q.choices,
            source=q.source or "Unknown",
            recency_weight=q.recency_weight or 0.5,
            review_info={
                "scheduled_for": review_map[q.id].scheduled_for.isoformat(),
                "interval": review_map[q.id].review_interval,
                "times_reviewed": review_map[q.id].times_reviewed,
                "learning_stage": review_map[q.id].learning_stage
            }
        )
        for q in questions
    ]


@router.get("/upcoming", response_model=UpcomingReviewsResponse)
def get_upcoming_review_calendar(
    user_id: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get upcoming reviews for the next N days, grouped by date.
    """
    calendar_data = get_upcoming_reviews(db, user_id, days=days)

    # Convert to counts for frontend
    calendar_counts = {
        date: len(reviews)
        for date, reviews in calendar_data.items()
    }

    total = sum(calendar_counts.values())

    return UpcomingReviewsResponse(
        calendar=calendar_counts,
        total=total
    )


@router.get("/stats", response_model=ReviewStatsResponse)
def get_user_review_stats(user_id: str, db: Session = Depends(get_db)):
    """
    Get review statistics for user.
    """
    stats = get_review_stats(db, user_id)

    return ReviewStatsResponse(
        total_reviews=stats['total_reviews'],
        due_today=stats['due_today'],
        learning=stats['learning'],
        review=stats['review'],
        mastered=stats['mastered'],
        by_source=stats['by_source']
    )


@router.get("/next", response_model=QuestionResponse)
def get_next_review_question(user_id: str, db: Session = Depends(get_db)):
    """
    Get the next question to review (earliest scheduled).
    """
    reviews = get_todays_reviews(db, user_id)

    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews due today")

    # Get the earliest scheduled review
    next_review = reviews[0]

    # Get question
    question = db.query(Question).filter(Question.id == next_review.question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return QuestionResponse(
        id=question.id,
        vignette=question.vignette,
        choices=question.choices,
        source=question.source or "Unknown",
        recency_weight=question.recency_weight or 0.5,
        review_info={
            "scheduled_for": next_review.scheduled_for.isoformat(),
            "interval": next_review.review_interval,
            "times_reviewed": next_review.times_reviewed,
            "learning_stage": next_review.learning_stage
        }
    )
