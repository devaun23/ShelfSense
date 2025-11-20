from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Dict, Optional

from app.database import get_db
from app.models.models import QuestionAttempt, Question
from app.services.adaptive import (
    calculate_predicted_score,
    get_performance_by_source
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class UserStatsResponse(BaseModel):
    total_questions_answered: int
    overall_accuracy: float
    weighted_accuracy: float
    predicted_score: Optional[int]
    performance_by_source: Dict[str, Dict]


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

    # Performance by source
    performance = get_performance_by_source(db, user_id)

    return UserStatsResponse(
        total_questions_answered=total,
        overall_accuracy=round(overall_accuracy, 2),
        weighted_accuracy=round(weighted_accuracy, 2),
        predicted_score=predicted_score,
        performance_by_source=performance
    )
