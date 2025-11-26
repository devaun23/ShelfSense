"""
Study Plan API Router

Endpoints for personalized study plan recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

from app.database import get_db
from app.models.models import User
from app.services.study_plan import (
    generate_study_plan,
    get_quick_plan_summary,
    get_daily_recommendation,
    get_specialty_performance,
    get_error_patterns,
    get_days_until_exam
)

router = APIRouter(prefix="/api/study-plan", tags=["study-plan"])


class WeeklyTarget(BaseModel):
    week: int
    days_from_now: int
    days_until_exam: int
    focus_areas: List[str]
    questions_target: int
    daily_target: int
    accuracy_milestone: float
    phase: str


class DailyRecommendation(BaseModel):
    focus_specialty: str
    focus_reason: str
    questions_recommended: int
    error_focus: Optional[str]
    error_advice: str
    phase: str


class StudyPlanOverview(BaseModel):
    days_remaining: int
    weeks_remaining: int
    current_phase: str
    target_score: int
    predicted_score: Optional[int]
    score_gap: Optional[int]
    on_track: bool


class WeakSpecialty(BaseModel):
    specialty: str
    accuracy: float
    total: int


class StudyPlanResponse(BaseModel):
    status: str
    overview: Optional[StudyPlanOverview] = None
    stats: Dict
    today: DailyRecommendation
    weekly_plan: Optional[List[WeeklyTarget]] = None
    weak_specialties: Optional[List[WeakSpecialty]] = None
    error_patterns: Optional[Dict[str, int]] = None
    message: Optional[str] = None


@router.get("/{user_id}", response_model=StudyPlanResponse)
def get_study_plan(user_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive study plan with exam countdown.

    Returns:
    - Overview: days remaining, phase, score gap
    - Weekly plan: targets and focus areas for each week
    - Today's recommendation: what to study now
    - Weak specialties: areas needing attention
    - Error patterns: common mistake types
    """
    try:
        plan = generate_study_plan(db, user_id)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating study plan: {str(e)}")


@router.get("/{user_id}/summary")
def get_plan_summary(user_id: str, db: Session = Depends(get_db)):
    """
    Get concise text summary of study plan (< 100 words).
    Useful for chat responses or quick display.
    """
    try:
        summary = get_quick_plan_summary(db, user_id)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


@router.get("/{user_id}/today")
def get_today_recommendation(user_id: str, db: Session = Depends(get_db)):
    """
    Get just today's study recommendation.
    Quick endpoint for daily focus without full plan.
    """
    try:
        days = get_days_until_exam(db, user_id) or 60
        specialty_perf = get_specialty_performance(db, user_id)
        errors = get_error_patterns(db, user_id)

        today = get_daily_recommendation(specialty_perf, errors, days)
        return {"today": today}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendation: {str(e)}")


class SetExamDateRequest(BaseModel):
    exam_date: datetime
    target_score: Optional[int] = None


@router.post("/{user_id}/exam-date")
def set_exam_date(
    user_id: str,
    request: SetExamDateRequest,
    db: Session = Depends(get_db)
):
    """
    Set or update user's exam date and target score.
    Required for generating exam countdown study plan.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.exam_date = request.exam_date
    if request.target_score:
        user.target_score = request.target_score

    db.commit()

    return {
        "success": True,
        "exam_date": request.exam_date.isoformat(),
        "target_score": user.target_score,
        "days_remaining": (request.exam_date - datetime.utcnow()).days
    }


@router.get("/{user_id}/progress")
def get_progress_check(user_id: str, db: Session = Depends(get_db)):
    """
    Quick progress check against study plan targets.
    Returns whether user is on track this week.
    """
    plan = generate_study_plan(db, user_id)

    if plan["status"] == "no_exam_date":
        return {"status": "no_exam_date", "message": "Set exam date first"}

    stats = plan["stats"]
    overview = plan["overview"]

    # Check weekly progress
    weekly_target = plan["weekly_plan"][0]["questions_target"] if plan["weekly_plan"] else 100
    weekly_progress = stats["weekly_questions"]
    weekly_percentage = round((weekly_progress / weekly_target) * 100, 1)

    return {
        "status": "ok",
        "weekly_progress": {
            "target": weekly_target,
            "completed": weekly_progress,
            "percentage": weekly_percentage,
            "on_track": weekly_percentage >= 70
        },
        "overall": {
            "days_remaining": overview["days_remaining"],
            "predicted_score": overview["predicted_score"],
            "target_score": overview["target_score"],
            "on_track": overview["on_track"]
        }
    }
