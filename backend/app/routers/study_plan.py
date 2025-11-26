"""
Study Plan API Router

Provides endpoints for:
- Daily study plan generation
- Weekly study plan generation
- Exam countdown planning
- Personalized recommendations
- Study progress tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, date

from app.database import get_db
from app.services.study_plan_agent import (
    StudyPlanAgent,
    get_study_plan_agent,
    generate_daily_plan,
    generate_weekly_plan,
    get_exam_countdown
)
from app.models.models import User

router = APIRouter(prefix="/api/study-plan", tags=["study-plan"])


# =========================================================================
# Response Models
# =========================================================================

class DailyPlanResponse(BaseModel):
    date: str
    user_id: str
    total_questions: int
    estimated_time_minutes: int
    focus_areas: List[str]
    sessions: List[Dict[str, Any]]
    weak_area_focus: Dict[str, int]
    review_questions: int
    new_questions: int
    recommendations: List[str]


class WeeklyPlanResponse(BaseModel):
    week_start: str
    week_end: str
    user_id: str
    total_questions: int
    total_time_minutes: int
    daily_plans: List[Dict[str, Any]]
    weekly_goals: List[str]
    focus_rotation: List[str]
    summary: Dict[str, Any]


class ExamCountdownResponse(BaseModel):
    exam_date: str
    days_remaining: int
    current_phase: str
    phase_description: str
    weekly_plans: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]
    daily_targets: Dict[str, int]
    recommendations: List[str]


class RecommendationsResponse(BaseModel):
    user_id: str
    generated_at: str
    immediate_actions: List[Dict[str, Any]]
    focus_areas: List[Dict[str, Any]]
    study_habits: List[Dict[str, Any]]
    resource_suggestions: List[Dict[str, Any]]
    motivation: str


class StudyProgressResponse(BaseModel):
    user_id: str
    period: str
    questions_completed: int
    target_questions: int
    completion_rate: float
    accuracy: float
    time_spent_minutes: int
    areas_covered: List[str]
    streak_days: int
    on_track: bool


# =========================================================================
# Daily Plan Endpoints
# =========================================================================

@router.get("/daily/{user_id}", response_model=DailyPlanResponse)
async def get_daily_plan(
    user_id: str,
    target_questions: int = Query(40, ge=10, le=200, description="Target questions for the day"),
    available_hours: float = Query(4.0, ge=0.5, le=12.0, description="Available study hours"),
    focus_weak_areas: bool = Query(True, description="Prioritize weak areas"),
    include_reviews: bool = Query(True, description="Include spaced repetition reviews"),
    db: Session = Depends(get_db)
):
    """
    Generate a personalized daily study plan.

    The plan includes:
    - Optimal session breakdown
    - Focus area allocation
    - Review question scheduling
    - Time estimates
    - Personalized recommendations
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    plan = agent.generate_daily_plan(
        user_id=user_id,
        target_questions=target_questions,
        available_hours=available_hours,
        focus_weak_areas=focus_weak_areas,
        include_reviews=include_reviews
    )

    return plan


@router.get("/daily/quick/{user_id}")
async def get_quick_daily_plan(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a quick daily plan with default settings.

    Uses sensible defaults for a typical study day.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    return agent.generate_daily_plan(user_id)


@router.post("/daily/{user_id}/adjust")
async def adjust_daily_plan(
    user_id: str,
    completed_questions: int = Query(0, ge=0, description="Questions already completed today"),
    remaining_hours: float = Query(2.0, ge=0.5, le=8.0, description="Remaining study hours"),
    energy_level: str = Query("medium", description="Current energy: low, medium, high"),
    db: Session = Depends(get_db)
):
    """
    Adjust today's plan based on current progress and energy.

    Useful for mid-day recalibration of study goals.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if energy_level not in ["low", "medium", "high"]:
        raise HTTPException(status_code=400, detail="Invalid energy level")

    agent = get_study_plan_agent(db)

    # Adjust target based on energy
    energy_multiplier = {"low": 0.6, "medium": 1.0, "high": 1.3}
    base_target = int(remaining_hours * 10)  # ~10 questions per hour
    adjusted_target = int(base_target * energy_multiplier[energy_level])

    plan = agent.generate_daily_plan(
        user_id=user_id,
        target_questions=adjusted_target,
        available_hours=remaining_hours,
        focus_weak_areas=(energy_level != "low"),  # Easy content when tired
        include_reviews=True
    )

    plan["adjusted_for"] = {
        "completed_today": completed_questions,
        "energy_level": energy_level,
        "original_estimate": base_target,
        "adjusted_target": adjusted_target
    }

    return plan


# =========================================================================
# Weekly Plan Endpoints
# =========================================================================

@router.get("/weekly/{user_id}", response_model=WeeklyPlanResponse)
async def get_weekly_plan(
    user_id: str,
    daily_target: int = Query(40, ge=10, le=200, description="Target questions per day"),
    study_days: int = Query(6, ge=1, le=7, description="Study days per week"),
    rest_day: str = Query("sunday", description="Preferred rest day"),
    db: Session = Depends(get_db)
):
    """
    Generate a comprehensive weekly study plan.

    Includes:
    - Daily breakdown with rotating focus areas
    - Weekly goals and milestones
    - Rest day scheduling
    - Progress checkpoints
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if rest_day.lower() not in valid_days:
        raise HTTPException(status_code=400, detail="Invalid rest day")

    agent = get_study_plan_agent(db)
    plan = agent.generate_weekly_plan(
        user_id=user_id,
        daily_target=daily_target,
        study_days=study_days,
        rest_day=rest_day.lower()
    )

    return plan


@router.get("/weekly/{user_id}/summary")
async def get_weekly_summary(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a summary of this week's study progress.

    Compares planned vs actual performance.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    return agent.get_weekly_progress_summary(user_id)


# =========================================================================
# Exam Countdown Endpoints
# =========================================================================

@router.get("/exam-countdown/{user_id}", response_model=ExamCountdownResponse)
async def get_exam_countdown_plan(
    user_id: str,
    exam_date: str = Query(..., description="Exam date (YYYY-MM-DD)"),
    daily_hours: float = Query(6.0, ge=2.0, le=14.0, description="Daily study hours"),
    db: Session = Depends(get_db)
):
    """
    Generate a comprehensive exam countdown study plan.

    Creates a phased approach:
    - Foundation phase (early): Cover all content
    - Intensification phase (middle): Focus on weak areas
    - Consolidation phase (final weeks): Review and practice
    - Peak phase (final days): Light review, confidence building
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        exam_date_parsed = datetime.strptime(exam_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if exam_date_parsed <= date.today():
        raise HTTPException(status_code=400, detail="Exam date must be in the future")

    agent = get_study_plan_agent(db)
    plan = agent.generate_exam_countdown_plan(
        user_id=user_id,
        exam_date=exam_date_parsed,
        daily_hours=daily_hours
    )

    return plan


@router.get("/exam-countdown/{user_id}/today")
async def get_today_from_countdown(
    user_id: str,
    exam_date: str = Query(..., description="Exam date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get today's specific plan from exam countdown context.

    Returns what you should focus on today given your exam date.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        exam_date_parsed = datetime.strptime(exam_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    days_until = (exam_date_parsed - date.today()).days

    if days_until <= 0:
        raise HTTPException(status_code=400, detail="Exam date must be in the future")

    agent = get_study_plan_agent(db)

    # Determine phase and adjust plan accordingly
    if days_until <= 3:
        phase = "peak"
        target = 20
        focus = "light_review"
    elif days_until <= 14:
        phase = "consolidation"
        target = 60
        focus = "practice_tests"
    elif days_until <= 30:
        phase = "intensification"
        target = 80
        focus = "weak_areas"
    else:
        phase = "foundation"
        target = 50
        focus = "coverage"

    daily_plan = agent.generate_daily_plan(
        user_id=user_id,
        target_questions=target,
        focus_weak_areas=(focus == "weak_areas"),
        include_reviews=True
    )

    daily_plan["exam_context"] = {
        "days_until_exam": days_until,
        "current_phase": phase,
        "phase_focus": focus,
        "exam_date": exam_date
    }

    return daily_plan


# =========================================================================
# Recommendations Endpoints
# =========================================================================

@router.get("/recommendations/{user_id}", response_model=RecommendationsResponse)
async def get_personalized_recommendations(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get AI-powered personalized study recommendations.

    Analyzes your performance patterns and provides:
    - Immediate action items
    - Focus area suggestions
    - Study habit improvements
    - Resource recommendations
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    return agent.get_personalized_recommendations(user_id)


@router.get("/recommendations/{user_id}/quick")
async def get_quick_recommendations(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get quick, actionable recommendations.

    Returns top 3 things to focus on right now.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    full_recs = agent.get_personalized_recommendations(user_id)

    return {
        "user_id": user_id,
        "top_actions": full_recs.get("immediate_actions", [])[:3],
        "primary_focus": full_recs.get("focus_areas", [{}])[0] if full_recs.get("focus_areas") else None,
        "motivation": full_recs.get("motivation", "Keep pushing forward!")
    }


# =========================================================================
# Progress Tracking Endpoints
# =========================================================================

@router.get("/progress/{user_id}", response_model=StudyProgressResponse)
async def get_study_progress(
    user_id: str,
    period: str = Query("today", description="Period: today, week, month"),
    db: Session = Depends(get_db)
):
    """
    Get study progress for a given period.

    Shows completion rates, accuracy, and whether you're on track.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if period not in ["today", "week", "month"]:
        raise HTTPException(status_code=400, detail="Invalid period")

    agent = get_study_plan_agent(db)
    return agent.get_study_progress(user_id, period)


@router.get("/progress/{user_id}/streak")
async def get_study_streak(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get current study streak information.

    Tracks consecutive days of meeting study goals.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    return agent.get_streak_info(user_id)


@router.get("/progress/{user_id}/milestones")
async def get_milestones(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get upcoming and completed milestones.

    Tracks achievements like questions answered, accuracy targets, etc.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    return agent.get_milestones(user_id)


# =========================================================================
# Quick Actions
# =========================================================================

@router.post("/start-session/{user_id}")
async def start_study_session(
    user_id: str,
    duration_minutes: int = Query(60, ge=15, le=240, description="Session duration"),
    session_type: str = Query("mixed", description="Type: mixed, weak_areas, review, new_content"),
    db: Session = Depends(get_db)
):
    """
    Start a focused study session.

    Returns a curated set of questions for the session duration.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if session_type not in ["mixed", "weak_areas", "review", "new_content"]:
        raise HTTPException(status_code=400, detail="Invalid session type")

    agent = get_study_plan_agent(db)

    # Calculate questions based on duration (~1.5 min per question)
    question_count = int(duration_minutes / 1.5)

    session = agent.create_study_session(
        user_id=user_id,
        question_count=question_count,
        session_type=session_type
    )

    session["duration_minutes"] = duration_minutes
    session["session_type"] = session_type

    return session


@router.get("/what-next/{user_id}")
async def what_should_i_study_next(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Simple endpoint: What should I study next?

    Returns the single most important thing to focus on right now.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    agent = get_study_plan_agent(db)
    return agent.get_next_priority(user_id)
