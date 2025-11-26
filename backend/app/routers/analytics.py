from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import QuestionAttempt, Question
from app.services.adaptive import (
    calculate_predicted_score,
    get_performance_by_source
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def calculate_streak(db: Session, user_id: str) -> int:
    """
    Calculate user's current study streak (consecutive days with activity)
    """
    # Get all unique dates user has answered questions
    attempts = db.query(
        func.date(QuestionAttempt.created_at).label('date')
    ).filter(
        QuestionAttempt.user_id == user_id
    ).distinct().order_by(
        func.date(QuestionAttempt.created_at).desc()
    ).all()

    if not attempts:
        return 0

    # Convert to list of dates
    dates = [datetime.strptime(str(attempt.date), '%Y-%m-%d').date() for attempt in attempts]

    # Check if user studied today or yesterday (to maintain streak)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    if dates[0] not in [today, yesterday]:
        return 0  # Streak broken

    # Count consecutive days backward from most recent
    streak = 1
    for i in range(1, len(dates)):
        expected_date = dates[i-1] - timedelta(days=1)
        if dates[i] == expected_date:
            streak += 1
        else:
            break

    return streak


def calculate_score_confidence(total_questions: int) -> int:
    """
    Calculate confidence interval for predicted score based on sample size
    Larger sample = smaller confidence interval (more accurate prediction)
    """
    if total_questions < 50:
        return 20  # ±20 points
    elif total_questions < 100:
        return 15  # ±15 points
    elif total_questions < 250:
        return 10  # ±10 points
    elif total_questions < 500:
        return 7   # ±7 points
    else:
        return 5   # ±5 points (UWorld-level accuracy)


class UserStatsResponse(BaseModel):
    total_questions_answered: int
    overall_accuracy: float
    weighted_accuracy: float
    predicted_score: Optional[int]
    score_confidence: Optional[int]  # ± confidence interval
    performance_by_source: Dict[str, Dict]
    streak: int


@router.get("/stats", response_model=UserStatsResponse)
def get_user_stats(user_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive user statistics
    """
    # Total questions answered
    total = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id
    ).scalar() or 0

    # Overall accuracy
    correct = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    overall_accuracy = (correct / total * 100) if total > 0 else 0.0

    # Weighted accuracy
    attempts = db.query(
        QuestionAttempt.is_correct,
        Question.recency_weight
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).all()

    if attempts:
        total_weight = sum(w or 0.5 for _, w in attempts)
        weighted_correct = sum((w or 0.5) for c, w in attempts if c)
        weighted_accuracy = (weighted_correct / total_weight * 100) if total_weight > 0 else 0.0
    else:
        weighted_accuracy = 0.0

    # Predicted score
    predicted_score = calculate_predicted_score(db, user_id)

    # Score confidence interval
    score_confidence = calculate_score_confidence(total) if predicted_score else None

    # Performance by source
    performance = get_performance_by_source(db, user_id)

    # Calculate streak
    streak = calculate_streak(db, user_id)

    return UserStatsResponse(
        total_questions_answered=total,
        overall_accuracy=round(overall_accuracy, 2),
        weighted_accuracy=round(weighted_accuracy, 2),
        predicted_score=predicted_score,
        score_confidence=score_confidence,
        performance_by_source=performance,
        streak=streak
    )
