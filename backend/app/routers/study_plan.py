"""
Study Plan API Router

Endpoints for personalized study plan recommendations.
Includes AI-powered adaptive daily task generation.

SECURITY: All endpoints require authentication and IDOR protection.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.database import get_db
from app.models.models import User, StudyPlan, DailyStudyTask
from app.dependencies.auth import get_current_user, verify_user_access
from app.services.study_plan import (
    generate_study_plan,
    get_quick_plan_summary,
    get_daily_recommendation,
    get_specialty_performance,
    get_error_patterns,
    get_days_until_exam
)
from app.services.ai_study_planner import (
    get_or_create_plan,
    generate_daily_tasks,
    get_today_tasks,
    get_weekly_overview,
    update_task_progress,
    adapt_plan,
    get_plan_dashboard
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
def get_study_plan(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive study plan with exam countdown.

    SECURITY: Requires authentication. Users can only access their own plan.

    Returns:
    - Overview: days remaining, phase, score gap
    - Weekly plan: targets and focus areas for each week
    - Today's recommendation: what to study now
    - Weak specialties: areas needing attention
    - Error patterns: common mistake types
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
    try:
        plan = generate_study_plan(db, user_id)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating study plan: {str(e)}")


@router.get("/{user_id}/summary")
def get_plan_summary(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get concise text summary of study plan (< 100 words).
    Useful for chat responses or quick display.

    SECURITY: Requires authentication. Users can only access their own plan.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
    try:
        summary = get_quick_plan_summary(db, user_id)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


@router.get("/{user_id}/today")
def get_today_recommendation(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get just today's study recommendation.
    Quick endpoint for daily focus without full plan.

    SECURITY: Requires authentication. Users can only access their own plan.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set or update user's exam date and target score.
    Required for generating exam countdown study plan.

    SECURITY: Requires authentication. Users can only modify their own data.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
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
def get_progress_check(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick progress check against study plan targets.
    Returns whether user is on track this week.

    SECURITY: Requires authentication. Users can only access their own data.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
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


# =============================================================================
# AI STUDY PLANNER ENDPOINTS
# =============================================================================

class CreatePlanRequest(BaseModel):
    """Request to create/update a study plan."""
    exam_date: datetime
    target_score: int = Field(default=240, ge=194, le=300)
    daily_hours: float = Field(default=3.0, ge=0.5, le=12)
    study_days_per_week: int = Field(default=6, ge=1, le=7)


class TaskProgressRequest(BaseModel):
    """Request to update task progress."""
    questions_completed: int = Field(ge=0, le=500)  # Max 500 questions per update
    time_spent_minutes: int = Field(ge=0, le=720)  # Max 12 hours per update
    accuracy: Optional[float] = Field(None, ge=0, le=100)


@router.get("/dashboard")
def get_dashboard(
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive study planner dashboard.

    SECURITY: Requires authentication. Users can only access their own dashboard.

    Returns:
    - Exam countdown and score predictions
    - Today's tasks with progress
    - Weekly schedule overview
    - Focus areas based on weak spots
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    return get_plan_dashboard(db, user_id)


@router.post("/create")
def create_study_plan(
    request: CreatePlanRequest,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update a personalized study plan.

    SECURITY: Requires authentication. Users can only create their own study plans.

    Generates daily tasks based on:
    - Time until exam
    - Target score and current performance
    - Available study hours
    - Weak areas and spaced repetition schedule
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    # Update user's exam date
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.exam_date = request.exam_date
    user.target_score = request.target_score
    db.commit()

    # Create plan
    plan = get_or_create_plan(
        db, user_id, request.exam_date,
        target_score=request.target_score,
        daily_hours=request.daily_hours,
        study_days_per_week=request.study_days_per_week
    )

    # Generate initial tasks
    generate_daily_tasks(db, user_id, days_ahead=7)

    return {
        "success": True,
        "plan_id": plan.id,
        "exam_date": request.exam_date.isoformat(),
        "target_score": request.target_score,
        "message": "Study plan created! Check your dashboard for daily tasks."
    }


@router.get("/today")
def get_todays_tasks(
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get today's study tasks.

    SECURITY: Requires authentication. Users can only access their own tasks.

    Returns prioritized list of tasks:
    - Spaced repetition reviews
    - Weak area focus
    - New practice questions
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    tasks = get_today_tasks(db, user_id)

    if not tasks:
        return {
            "status": "no_plan",
            "message": "Create a study plan to get daily tasks",
            "tasks": []
        }

    total_questions = sum(t["target_questions"] for t in tasks)
    completed_questions = sum(t["questions_completed"] for t in tasks)

    return {
        "status": "active",
        "tasks": tasks,
        "summary": {
            "total_tasks": len(tasks),
            "completed_tasks": len([t for t in tasks if t["status"] == "completed"]),
            "total_questions": total_questions,
            "completed_questions": completed_questions,
            "progress_percent": round(completed_questions / total_questions * 100, 1) if total_questions > 0 else 0
        }
    }


@router.get("/week")
def get_weekly_schedule(
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get weekly study schedule overview.

    SECURITY: Requires authentication. Users can only access their own schedule.

    Returns tasks for the next 7 days with:
    - Daily targets and progress
    - Task breakdown per day
    - Weekly totals
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    return get_weekly_overview(db, user_id)


@router.post("/task/{task_id}/progress")
def update_task(
    task_id: str,
    request: TaskProgressRequest,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update progress on a daily study task.

    SECURITY: Requires authentication. Users can only update their own tasks.

    Automatically marks task as completed when target is reached.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        task = update_task_progress(
            db, task_id, user_id,
            questions_completed=request.questions_completed,
            time_spent_minutes=request.time_spent_minutes,
            accuracy=request.accuracy
        )

        return {
            "success": True,
            "task_id": task.id,
            "status": task.status,
            "questions_completed": task.questions_completed,
            "target_questions": task.target_questions,
            "is_complete": task.status == "completed"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/task/{task_id}/complete")
def complete_task(
    task_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a task as completed manually.

    SECURITY: Requires authentication. Users can only complete their own tasks.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    task = db.query(DailyStudyTask).filter(
        DailyStudyTask.id == task_id,
        DailyStudyTask.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.commit()

    return {"success": True, "task_id": task_id, "status": "completed"}


@router.post("/task/{task_id}/skip")
def skip_task(
    task_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Skip a task (won't count toward completion).

    SECURITY: Requires authentication. Users can only skip their own tasks.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    task = db.query(DailyStudyTask).filter(
        DailyStudyTask.id == task_id,
        DailyStudyTask.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "skipped"
    db.commit()

    return {"success": True, "task_id": task_id, "status": "skipped"}


@router.post("/adapt")
def adapt_study_plan(
    user_id: str = Query(..., description="User ID"),
    reason: str = Query("manual", description="Reason for adaptation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger plan adaptation.

    SECURITY: Requires authentication. Users can only adapt their own plans.

    Regenerates future tasks based on current performance.
    Useful when user's availability or performance changes significantly.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    success = adapt_plan(db, user_id, reason=reason)

    if not success:
        raise HTTPException(status_code=404, detail="No active plan found")

    return {
        "success": True,
        "message": "Study plan adapted based on current performance",
        "reason": reason
    }


@router.get("/streak-check")
def check_daily_streak(
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user completed today's study plan tasks.

    SECURITY: Requires authentication. Users can only check their own streak.

    Used for streak tracking and notifications.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    tasks = get_today_tasks(db, user_id)

    if not tasks:
        return {"has_plan": False, "completed_today": False}

    completed = all(t["status"] == "completed" for t in tasks)
    partial = any(t["status"] == "completed" for t in tasks)

    return {
        "has_plan": True,
        "completed_today": completed,
        "partial_completion": partial and not completed,
        "tasks_completed": len([t for t in tasks if t["status"] == "completed"]),
        "tasks_total": len(tasks)
    }
