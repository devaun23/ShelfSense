from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import QuestionAttempt, Question
from app.services.adaptive import (
    calculate_predicted_score,
    get_performance_by_source,
    get_weak_areas
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


class SpecialtyBreakdown(BaseModel):
    specialty: str
    total_questions: int
    correct: int
    accuracy: float
    avg_time_seconds: float
    is_weak_area: bool


@router.get("/specialty-breakdown", response_model=List[SpecialtyBreakdown])
def get_specialty_breakdown(user_id: str, db: Session = Depends(get_db)):
    """
    Get detailed performance breakdown by medical specialty

    Returns accuracy, question count, and avg time per specialty
    """
    # Get weak areas for this user
    weak_areas = get_weak_areas(db, user_id, threshold=0.6)

    # Define specialties to analyze
    specialties = [
        "Internal Medicine",
        "Surgery",
        "Pediatrics",
        "Psychiatry",
        "Obstetrics and Gynecology",
        "Family Medicine",
        "Emergency Medicine",
        "Preventive Medicine"
    ]

    results = []

    for specialty in specialties:
        # Get all attempts for this specialty
        attempts = db.query(
            QuestionAttempt.is_correct,
            QuestionAttempt.time_spent_seconds
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id,
            Question.source.like(f"%{specialty}%")
        ).all()

        if not attempts:
            continue

        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        accuracy = (correct / total * 100) if total > 0 else 0.0

        # Calculate average time
        times = [a.time_spent_seconds for a in attempts if a.time_spent_seconds]
        avg_time = sum(times) / len(times) if times else 0.0

        # Check if this is a weak area
        is_weak = any(specialty in source for source in weak_areas)

        results.append(SpecialtyBreakdown(
            specialty=specialty,
            total_questions=total,
            correct=correct,
            accuracy=round(accuracy, 2),
            avg_time_seconds=round(avg_time, 1),
            is_weak_area=is_weak
        ))

    # Sort by accuracy (weakest first)
    results.sort(key=lambda x: x.accuracy)

    return results


class PerformanceTrend(BaseModel):
    date: str
    questions_answered: int
    accuracy: float
    avg_time_seconds: float


@router.get("/performance-trend", response_model=List[PerformanceTrend])
def get_performance_trend(user_id: str, days: int = 30, db: Session = Depends(get_db)):
    """
    Get performance trend over time

    Args:
        user_id: User ID
        days: Number of days to look back (default 30)

    Returns:
        Daily performance data
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get all attempts in the time period
    attempts = db.query(
        QuestionAttempt.attempted_at,
        QuestionAttempt.is_correct,
        QuestionAttempt.time_spent_seconds
    ).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= cutoff_date
    ).all()

    # Group by date
    daily_stats = {}

    for attempt in attempts:
        date_key = attempt.attempted_at.date().isoformat()

        if date_key not in daily_stats:
            daily_stats[date_key] = {
                "correct": 0,
                "total": 0,
                "times": []
            }

        daily_stats[date_key]["total"] += 1
        if attempt.is_correct:
            daily_stats[date_key]["correct"] += 1
        if attempt.time_spent_seconds:
            daily_stats[date_key]["times"].append(attempt.time_spent_seconds)

    # Convert to response format
    results = []
    for date, stats in sorted(daily_stats.items()):
        accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
        avg_time = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0.0

        results.append(PerformanceTrend(
            date=date,
            questions_answered=stats["total"],
            accuracy=round(accuracy, 2),
            avg_time_seconds=round(avg_time, 1)
        ))

    return results


class WeakArea(BaseModel):
    source: str
    total_questions: int
    accuracy: float
    recommendation: str


@router.get("/weak-areas", response_model=List[WeakArea])
def get_user_weak_areas(user_id: str, threshold: float = 0.6, db: Session = Depends(get_db)):
    """
    Identify weak areas where user needs improvement

    Args:
        user_id: User ID
        threshold: Accuracy threshold for weak areas (default 60%)

    Returns:
        List of weak areas with recommendations
    """
    weak_sources = get_weak_areas(db, user_id, threshold)

    results = []

    for source in weak_sources:
        # Get stats for this source
        attempts = db.query(QuestionAttempt).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id,
            Question.source == source
        ).all()

        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        accuracy = (correct / total * 100) if total > 0 else 0.0

        # Generate recommendation based on accuracy
        if accuracy < 40:
            recommendation = "Critical: Review fundamentals and practice more questions"
        elif accuracy < 50:
            recommendation = "Needs improvement: Focus on common patterns and decision-making"
        elif accuracy < 60:
            recommendation = "Below target: Review key concepts and practice applications"
        else:
            recommendation = "Minor weakness: Fine-tune understanding with practice"

        results.append(WeakArea(
            source=source,
            total_questions=total,
            accuracy=round(accuracy, 2),
            recommendation=recommendation
        ))

    # Sort by accuracy (weakest first)
    results.sort(key=lambda x: x.accuracy)

    return results


class RecentPerformance(BaseModel):
    question_id: str
    vignette_preview: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    time_spent_seconds: int
    attempted_at: datetime
    specialty: str


@router.get("/recent-performance", response_model=List[RecentPerformance])
def get_recent_performance(user_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """
    Get user's recent question attempts

    Args:
        user_id: User ID
        limit: Number of recent attempts to return (default 20)

    Returns:
        List of recent attempts with details
    """
    attempts = db.query(
        QuestionAttempt,
        Question
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).order_by(
        desc(QuestionAttempt.attempted_at)
    ).limit(limit).all()

    results = []

    for attempt, question in attempts:
        # Extract specialty from source
        specialty = "Unknown"
        if question.source:
            for spec in ["Internal Medicine", "Surgery", "Pediatrics", "Psychiatry",
                        "Obstetrics and Gynecology", "Family Medicine", "Emergency Medicine", "Preventive Medicine"]:
                if spec in question.source:
                    specialty = spec
                    break

        results.append(RecentPerformance(
            question_id=attempt.question_id,
            vignette_preview=question.vignette[:100] + "..." if len(question.vignette) > 100 else question.vignette,
            user_answer=attempt.user_answer,
            correct_answer=question.answer_key,
            is_correct=attempt.is_correct,
            time_spent_seconds=attempt.time_spent_seconds or 0,
            attempted_at=attempt.attempted_at,
            specialty=specialty
        ))

    return results


class StudyTimeStats(BaseModel):
    total_study_time_minutes: float
    avg_time_per_question_seconds: float
    fastest_question_seconds: float
    slowest_question_seconds: float
    questions_this_week: int
    questions_this_month: int


@router.get("/study-time", response_model=StudyTimeStats)
def get_study_time_stats(user_id: str, db: Session = Depends(get_db)):
    """
    Get study time statistics for the user

    Includes total time, averages, and recent activity
    """
    # Get all attempts with time data
    attempts = db.query(QuestionAttempt.time_spent_seconds, QuestionAttempt.attempted_at).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.time_spent_seconds != None
    ).all()

    if not attempts:
        return StudyTimeStats(
            total_study_time_minutes=0,
            avg_time_per_question_seconds=0,
            fastest_question_seconds=0,
            slowest_question_seconds=0,
            questions_this_week=0,
            questions_this_month=0
        )

    times = [a.time_spent_seconds for a in attempts]
    total_seconds = sum(times)
    avg_seconds = total_seconds / len(times)

    # Recent activity
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    questions_this_week = sum(1 for a in attempts if a.attempted_at >= week_ago)
    questions_this_month = sum(1 for a in attempts if a.attempted_at >= month_ago)

    return StudyTimeStats(
        total_study_time_minutes=round(total_seconds / 60, 1),
        avg_time_per_question_seconds=round(avg_seconds, 1),
        fastest_question_seconds=min(times),
        slowest_question_seconds=max(times),
        questions_this_week=questions_this_week,
        questions_this_month=questions_this_month
    )
