"""
AI Study Planner Service

Generates and adapts personalized study plans using AI.
Creates daily tasks based on:
- Exam date and target score
- Current performance and weak areas
- Available study time
- Spaced repetition schedule
- Learning velocity
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    User, StudyPlan, DailyStudyTask, QuestionAttempt, Question,
    ScheduledReview, LearningMetricsCache, generate_uuid
)
from app.services.study_plan import (
    get_specialty_performance, get_error_patterns, get_user_stats,
    determine_learning_phase, SPECIALTIES
)


def get_or_create_plan(
    db: Session,
    user_id: str,
    exam_date: datetime,
    target_score: int = 240,
    daily_hours: float = 3.0,
    study_days_per_week: int = 6
) -> StudyPlan:
    """Get existing plan or create a new one."""
    plan = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).first()

    if plan:
        # Update if exam date changed
        if plan.exam_date != exam_date or plan.target_score != target_score:
            plan.exam_date = exam_date
            plan.target_score = target_score
            plan.daily_hours_available = daily_hours
            plan.study_days_per_week = study_days_per_week
            plan.last_regenerated = datetime.utcnow()
            db.commit()
        return plan

    # Create new plan
    plan = StudyPlan(
        id=generate_uuid(),
        user_id=user_id,
        exam_date=exam_date,
        target_score=target_score,
        daily_hours_available=daily_hours,
        study_days_per_week=study_days_per_week,
        status="active"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan


def generate_daily_tasks(
    db: Session,
    user_id: str,
    days_ahead: int = 7
) -> List[DailyStudyTask]:
    """
    Generate daily study tasks for the next N days.
    Adapts based on user's performance and schedule.
    """
    # Get user and plan
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.exam_date:
        return []

    plan = get_or_create_plan(
        db, user_id, user.exam_date,
        target_score=user.target_score or 240
    )

    # Get performance data
    stats = get_user_stats(db, user_id)
    specialty_perf = get_specialty_performance(db, user_id)
    error_patterns = get_error_patterns(db, user_id)

    # Calculate days until exam
    days_until_exam = (user.exam_date - datetime.utcnow()).days

    # Get due reviews
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    due_reviews = db.query(func.count(ScheduledReview.id)).filter(
        ScheduledReview.user_id == user_id,
        ScheduledReview.scheduled_for <= today + timedelta(days=days_ahead)
    ).scalar() or 0

    # Identify weak areas (sorted by priority)
    weak_areas = []
    for spec, data in specialty_perf.items():
        if data["accuracy"] < 65 or data["total"] < 20:
            priority_score = (100 - data["accuracy"]) * SPECIALTIES.get(spec, 0.1)
            weak_areas.append({
                "specialty": spec,
                "accuracy": data["accuracy"],
                "total": data["total"],
                "priority": priority_score
            })
    weak_areas.sort(key=lambda x: x["priority"], reverse=True)

    # Generate tasks for each day
    tasks = []
    for day_offset in range(days_ahead):
        task_date = today + timedelta(days=day_offset)

        # Skip if tasks already exist for this day
        existing = db.query(DailyStudyTask).filter(
            DailyStudyTask.user_id == user_id,
            DailyStudyTask.date == task_date
        ).first()
        if existing:
            tasks.append(existing)
            continue

        # Determine phase
        remaining_days = days_until_exam - day_offset
        phase = determine_learning_phase(remaining_days)

        # Calculate daily targets based on phase and available time
        if phase == "foundation":
            base_questions = 20
            review_ratio = 0.2
        elif phase == "strengthening":
            base_questions = 30
            review_ratio = 0.3
        elif phase == "review":
            base_questions = 40
            review_ratio = 0.4
        else:  # final
            base_questions = 25
            review_ratio = 0.5

        # Adjust based on hours available (assuming ~2 min per question)
        questions_per_hour = 30
        max_questions = int(plan.daily_hours_available * questions_per_hour)
        target_questions = min(base_questions, max_questions)

        # Split between new and review
        review_questions = int(target_questions * review_ratio)
        new_questions = target_questions - review_questions

        # Create tasks for the day
        order = 1

        # Task 1: Spaced repetition reviews (if any due)
        if review_questions > 0:
            review_task = DailyStudyTask(
                id=generate_uuid(),
                plan_id=plan.id,
                user_id=user_id,
                date=task_date,
                task_type="review",
                description=f"Complete spaced repetition reviews ({review_questions} questions)",
                target_questions=review_questions,
                target_time_minutes=review_questions * 2,
                priority=1,
                order_in_day=order
            )
            db.add(review_task)
            tasks.append(review_task)
            order += 1

        # Task 2: Weak area focus (if any)
        if weak_areas and new_questions >= 10:
            focus_area = weak_areas[day_offset % len(weak_areas)]  # Rotate through weak areas
            weak_questions = min(new_questions // 2, 15)

            weak_task = DailyStudyTask(
                id=generate_uuid(),
                plan_id=plan.id,
                user_id=user_id,
                date=task_date,
                task_type="weak_area",
                specialty=focus_area["specialty"],
                description=f"Focus on {focus_area['specialty']} (current: {focus_area['accuracy']:.0f}%)",
                target_questions=weak_questions,
                target_time_minutes=weak_questions * 2,
                difficulty_mix={"easy": 30, "medium": 50, "hard": 20},
                priority=2,
                order_in_day=order
            )
            db.add(weak_task)
            tasks.append(weak_task)
            new_questions -= weak_questions
            order += 1

        # Task 3: New questions (mixed practice)
        if new_questions > 0:
            new_task = DailyStudyTask(
                id=generate_uuid(),
                plan_id=plan.id,
                user_id=user_id,
                date=task_date,
                task_type="new_questions",
                description=f"Mixed practice questions ({new_questions} questions)",
                target_questions=new_questions,
                target_time_minutes=new_questions * 2,
                difficulty_mix={"easy": 20, "medium": 50, "hard": 30},
                priority=3,
                order_in_day=order
            )
            db.add(new_task)
            tasks.append(new_task)

    # Update plan phase
    plan.current_phase = determine_learning_phase(days_until_exam)
    plan.focus_areas = [w["specialty"] for w in weak_areas[:3]]

    db.commit()

    return tasks


def get_today_tasks(db: Session, user_id: str) -> List[Dict]:
    """Get today's study tasks."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    tasks = db.query(DailyStudyTask).filter(
        DailyStudyTask.user_id == user_id,
        DailyStudyTask.date == today
    ).order_by(DailyStudyTask.order_in_day).all()

    # Generate if none exist
    if not tasks:
        generate_daily_tasks(db, user_id, days_ahead=1)
        tasks = db.query(DailyStudyTask).filter(
            DailyStudyTask.user_id == user_id,
            DailyStudyTask.date == today
        ).order_by(DailyStudyTask.order_in_day).all()

    return [
        {
            "id": t.id,
            "task_type": t.task_type,
            "specialty": t.specialty,
            "description": t.description,
            "target_questions": t.target_questions,
            "target_time_minutes": t.target_time_minutes,
            "status": t.status,
            "questions_completed": t.questions_completed,
            "time_spent_minutes": t.time_spent_minutes,
            "accuracy": t.accuracy,
            "priority": t.priority
        }
        for t in tasks
    ]


def get_weekly_overview(db: Session, user_id: str) -> Dict:
    """Get overview of tasks for the current week."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today + timedelta(days=7)

    # Get or generate tasks
    generate_daily_tasks(db, user_id, days_ahead=7)

    tasks = db.query(DailyStudyTask).filter(
        DailyStudyTask.user_id == user_id,
        DailyStudyTask.date >= today,
        DailyStudyTask.date < week_end
    ).order_by(DailyStudyTask.date, DailyStudyTask.order_in_day).all()

    # Group by day
    days = {}
    for task in tasks:
        day_key = task.date.strftime("%Y-%m-%d")
        if day_key not in days:
            days[day_key] = {
                "date": day_key,
                "day_name": task.date.strftime("%A"),
                "tasks": [],
                "total_questions": 0,
                "total_time": 0,
                "completed": 0
            }
        days[day_key]["tasks"].append({
            "id": task.id,
            "type": task.task_type,
            "description": task.description,
            "target_questions": task.target_questions,
            "status": task.status
        })
        days[day_key]["total_questions"] += task.target_questions
        days[day_key]["total_time"] += task.target_time_minutes
        if task.status == "completed":
            days[day_key]["completed"] += 1

    # Calculate week totals
    total_questions = sum(d["total_questions"] for d in days.values())
    total_time = sum(d["total_time"] for d in days.values())
    completed_tasks = sum(d["completed"] for d in days.values())
    total_tasks = sum(len(d["tasks"]) for d in days.values())

    return {
        "week_start": today.strftime("%Y-%m-%d"),
        "week_end": (week_end - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_questions": total_questions,
        "total_time_minutes": total_time,
        "tasks_completed": completed_tasks,
        "tasks_total": total_tasks,
        "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
        "days": list(days.values())
    }


def update_task_progress(
    db: Session,
    task_id: str,
    user_id: str,
    questions_completed: int,
    time_spent_minutes: int,
    accuracy: Optional[float] = None
) -> DailyStudyTask:
    """Update progress on a daily task."""
    task = db.query(DailyStudyTask).filter(
        DailyStudyTask.id == task_id,
        DailyStudyTask.user_id == user_id
    ).first()

    if not task:
        raise ValueError("Task not found")

    task.questions_completed = questions_completed
    task.time_spent_minutes = time_spent_minutes
    if accuracy is not None:
        task.accuracy = accuracy

    # Update status
    if task.status == "pending":
        task.status = "in_progress"
        task.started_at = datetime.utcnow()

    if questions_completed >= task.target_questions:
        task.status = "completed"
        task.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    return task


def adapt_plan(db: Session, user_id: str, reason: str = "performance_change") -> bool:
    """
    Adapt the study plan based on recent performance.
    Called when user's performance significantly changes.
    """
    plan = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).first()
    if not plan:
        return False

    # Delete future incomplete tasks
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    db.query(DailyStudyTask).filter(
        DailyStudyTask.plan_id == plan.id,
        DailyStudyTask.date > today,
        DailyStudyTask.status == "pending"
    ).delete()

    # Track adaptation
    plan.times_adapted += 1
    reasons = plan.adaptation_reasons or []
    reasons.append({
        "date": datetime.utcnow().isoformat(),
        "reason": reason
    })
    plan.adaptation_reasons = reasons[-10:]  # Keep last 10
    plan.last_regenerated = datetime.utcnow()

    db.commit()

    # Regenerate tasks
    generate_daily_tasks(db, user_id, days_ahead=7)

    return True


def get_plan_dashboard(db: Session, user_id: str) -> Dict:
    """Get comprehensive dashboard data for the study planner."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    # Check for exam date
    if not user.exam_date:
        return {
            "status": "no_exam_date",
            "message": "Set your exam date to get a personalized study plan"
        }

    plan = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).first()

    # Get performance stats
    stats = get_user_stats(db, user_id)
    specialty_perf = get_specialty_performance(db, user_id)

    # Days until exam
    days_remaining = (user.exam_date - datetime.utcnow()).days
    phase = determine_learning_phase(days_remaining)

    # Today's tasks
    today_tasks = get_today_tasks(db, user_id)

    # Weekly overview
    weekly = get_weekly_overview(db, user_id)

    # Calculate predicted vs target
    target_score = user.target_score or 240
    predicted_score = None
    if stats["total_questions"] >= 20:
        predicted_score = int(194 + (stats["accuracy"] / 100 - 0.6) * 265)
        predicted_score = max(194, min(300, predicted_score))

    # Identify top focus areas
    weak_areas = sorted(
        [{"specialty": s, **d} for s, d in specialty_perf.items() if d["accuracy"] < 65],
        key=lambda x: x["accuracy"]
    )[:3]

    return {
        "status": "active",
        "exam_date": user.exam_date.isoformat(),
        "days_remaining": days_remaining,
        "weeks_remaining": days_remaining // 7,
        "current_phase": phase,
        "target_score": target_score,
        "predicted_score": predicted_score,
        "score_gap": target_score - predicted_score if predicted_score else None,
        "on_track": predicted_score and predicted_score >= target_score - 5 if predicted_score else False,
        "stats": stats,
        "today": {
            "tasks": today_tasks,
            "total_questions": sum(t["target_questions"] for t in today_tasks),
            "completed_questions": sum(t["questions_completed"] for t in today_tasks),
            "tasks_completed": len([t for t in today_tasks if t["status"] == "completed"]),
            "tasks_total": len(today_tasks)
        },
        "weekly": weekly,
        "focus_areas": weak_areas,
        "plan_id": plan.id if plan else None
    }
