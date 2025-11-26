from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import QuestionAttempt, Question
from app.services.adaptive import (
    calculate_predicted_score,
    get_performance_by_source
)
from app.services.analytics_agent import (
    get_dashboard_data,
    get_performance_trends,
    analyze_behavioral_patterns,
    get_error_distribution,
    get_detailed_weak_areas,
    calculate_predicted_score_detailed
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


# =============================================================================
# NEW COMPREHENSIVE ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/dashboard")
def get_analytics_dashboard(user_id: str, db: Session = Depends(get_db)):
    """
    Get complete dashboard data in a single call.
    Returns all analytics data for the comprehensive dashboard.
    """
    try:
        dashboard_data = get_dashboard_data(db, user_id)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard data: {str(e)}")


@router.get("/trends")
def get_trends(
    user_id: str,
    days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """
    Get performance trends over specified time period.

    Args:
        user_id: User identifier
        days: Number of days to analyze (7-90, default 30)

    Returns:
        Daily data, weekly summary, and overall trend direction
    """
    try:
        trends = get_performance_trends(db, user_id, days)
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trends: {str(e)}")


@router.get("/behavioral")
def get_behavioral_insights(user_id: str, db: Session = Depends(get_db)):
    """
    Get behavioral pattern analysis.

    Returns:
        - Time analysis (avg time by outcome)
        - Hover patterns (uncertainty indicators)
        - Confidence vs accuracy correlation
        - Optimal study conditions (best time of day)
    """
    try:
        behavioral = analyze_behavioral_patterns(db, user_id)
        return behavioral
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching behavioral data: {str(e)}")


@router.get("/errors")
def get_error_analysis(user_id: str, db: Session = Depends(get_db)):
    """
    Get error type distribution and trends.

    Returns:
        - Error counts by type
        - Most common error type
        - Improvement trends per error type
    """
    try:
        errors = get_error_distribution(db, user_id)
        return errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching error data: {str(e)}")


@router.get("/weak-areas")
def get_weak_areas_detailed(user_id: str, db: Session = Depends(get_db)):
    """
    Get detailed weak and strong area analysis.

    Returns:
        - Weak areas sorted by priority
        - Strong areas (mastered topics)
        - Focus recommendations (top 3 areas)
    """
    try:
        areas = get_detailed_weak_areas(db, user_id)
        return areas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching weak areas: {str(e)}")


@router.get("/score-details")
def get_score_breakdown(user_id: str, db: Session = Depends(get_db)):
    """
    Get detailed predicted score breakdown.

    Returns:
        - Current predicted score (194-300)
        - Confidence interval
        - Score trajectory (improving/declining/stable)
        - Breakdown by specialty
    """
    try:
        score_data = calculate_predicted_score_detailed(db, user_id)
        return score_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching score details: {str(e)}")


@router.get("/activity-heatmap")
def get_activity_heatmap(
    user_id: str,
    days: int = Query(default=365, ge=30, le=365),
    db: Session = Depends(get_db)
):
    """
    Get daily activity data for calendar heatmap visualization.

    Args:
        user_id: User identifier
        days: Number of days to include (30-365, default 365)

    Returns:
        Array of daily data with date, count (questions answered), and accuracy
    """
    from sqlalchemy import Integer

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Get daily activity data
    daily_data = db.query(
        func.date(QuestionAttempt.created_at).label('date'),
        func.count(QuestionAttempt.id).label('count'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).filter(
        QuestionAttempt.user_id == user_id,
        func.date(QuestionAttempt.created_at) >= start_date,
        func.date(QuestionAttempt.created_at) <= end_date
    ).group_by(
        func.date(QuestionAttempt.created_at)
    ).order_by(
        func.date(QuestionAttempt.created_at)
    ).all()

    # Format response
    heatmap_data = []
    for row in daily_data:
        accuracy = round((row.correct or 0) / row.count * 100, 1) if row.count > 0 else 0
        heatmap_data.append({
            "date": str(row.date),
            "count": row.count,
            "accuracy": accuracy
        })

    # Calculate summary stats
    total_days_active = len(daily_data)
    total_questions = sum(d["count"] for d in heatmap_data)
    avg_per_day = round(total_questions / total_days_active, 1) if total_days_active > 0 else 0

    # Find longest streak
    dates_active = set(d["date"] for d in heatmap_data)
    current_streak = 0
    longest_streak = 0
    check_date = end_date

    while check_date >= start_date:
        date_str = str(check_date)
        if date_str in dates_active:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0
        check_date -= timedelta(days=1)

    return {
        "data": heatmap_data,
        "summary": {
            "total_days_active": total_days_active,
            "total_questions": total_questions,
            "avg_per_active_day": avg_per_day,
            "longest_streak": longest_streak,
            "current_streak": calculate_streak(db, user_id),
            "date_range": {
                "start": str(start_date),
                "end": str(end_date)
            }
        }
    }


@router.get("/specialty-breakdown")
def get_specialty_breakdown(user_id: str, db: Session = Depends(get_db)):
    """
    Get performance breakdown by specialty for the dashboard.

    Returns accuracy, questions answered, and predicted scores per specialty.
    """
    # Define the 8 main specialties
    specialties = [
        "Internal Medicine",
        "Surgery",
        "Pediatrics",
        "Psychiatry",
        "Obstetrics and Gynecology",
        "Family Medicine",
        "Emergency Medicine",
        "Neurology"
    ]

    breakdown = {}

    for specialty in specialties:
        # Get attempts for this specialty (match source containing specialty name)
        attempts = db.query(
            QuestionAttempt.is_correct,
            Question.recency_weight
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id,
            Question.source.ilike(f"%{specialty}%")
        ).all()

        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        accuracy = round((correct / total * 100), 1) if total > 0 else 0

        # Calculate weighted accuracy for predicted score
        if attempts:
            total_weight = sum(w or 0.5 for _, w in attempts)
            weighted_correct = sum((w or 0.5) for c, w in attempts if c)
            weighted_accuracy = (weighted_correct / total_weight) if total_weight > 0 else 0
            # Predicted score formula: 194 + (accuracy - 0.6) * 265
            predicted = int(194 + (weighted_accuracy - 0.6) * 265) if total >= 10 else None
        else:
            predicted = None

        breakdown[specialty] = {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "predicted_score": predicted
        }

    return {
        "specialties": breakdown,
        "total_answered": sum(b["total"] for b in breakdown.values()),
        "overall_accuracy": round(
            sum(b["correct"] for b in breakdown.values()) /
            max(sum(b["total"] for b in breakdown.values()), 1) * 100, 1
        )
    }


@router.get("/peer-comparison")
def get_peer_comparison(user_id: str, db: Session = Depends(get_db)):
    """
    Get anonymous peer comparison data.

    Compares the user's performance against all other users in the system.
    All data is anonymized - no usernames or identifiable information shared.

    Returns:
    - User's stats vs platform averages
    - Percentile rankings
    - Distribution charts data
    - Specialty comparisons
    """
    from sqlalchemy import Integer, distinct

    # Get user's stats
    user_attempts = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).filter(
        QuestionAttempt.user_id == user_id
    ).first()

    user_total = user_attempts.total or 0
    user_correct = user_attempts.correct or 0
    user_accuracy = round((user_correct / user_total * 100), 1) if user_total > 0 else 0

    # Get user's predicted score
    user_predicted_score = calculate_predicted_score(db, user_id)

    # Get user's streak
    user_streak = calculate_streak(db, user_id)

    # Get all users' stats for comparison (anonymized)
    all_users_stats = db.query(
        QuestionAttempt.user_id,
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).group_by(
        QuestionAttempt.user_id
    ).having(
        func.count(QuestionAttempt.id) >= 10  # Only users with 10+ questions
    ).all()

    if not all_users_stats:
        return {
            "user_stats": {
                "total_questions": user_total,
                "accuracy": user_accuracy,
                "predicted_score": user_predicted_score,
                "streak": user_streak
            },
            "comparison": {
                "message": "Not enough peer data for comparison yet",
                "total_peers": 0
            }
        }

    # Calculate peer statistics
    peer_accuracies = []
    peer_totals = []

    for peer_user_id, total, correct in all_users_stats:
        if total > 0:
            peer_accuracy = (correct or 0) / total * 100
            peer_accuracies.append(peer_accuracy)
            peer_totals.append(total)

    # Calculate percentiles
    def calculate_percentile(value, data_list):
        if not data_list:
            return 50
        sorted_data = sorted(data_list)
        count_below = sum(1 for x in sorted_data if x < value)
        return round((count_below / len(sorted_data)) * 100)

    accuracy_percentile = calculate_percentile(user_accuracy, peer_accuracies)
    questions_percentile = calculate_percentile(user_total, peer_totals)

    # Calculate platform averages
    avg_accuracy = round(sum(peer_accuracies) / len(peer_accuracies), 1) if peer_accuracies else 0
    avg_questions = round(sum(peer_totals) / len(peer_totals), 1) if peer_totals else 0
    median_accuracy = sorted(peer_accuracies)[len(peer_accuracies) // 2] if peer_accuracies else 0

    # Create accuracy distribution buckets
    accuracy_distribution = {
        "0-50": 0,
        "50-60": 0,
        "60-70": 0,
        "70-80": 0,
        "80-90": 0,
        "90-100": 0
    }

    for acc in peer_accuracies:
        if acc < 50:
            accuracy_distribution["0-50"] += 1
        elif acc < 60:
            accuracy_distribution["50-60"] += 1
        elif acc < 70:
            accuracy_distribution["60-70"] += 1
        elif acc < 80:
            accuracy_distribution["70-80"] += 1
        elif acc < 90:
            accuracy_distribution["80-90"] += 1
        else:
            accuracy_distribution["90-100"] += 1

    # Determine user's bucket for highlighting
    user_bucket = "0-50"
    if user_accuracy >= 90:
        user_bucket = "90-100"
    elif user_accuracy >= 80:
        user_bucket = "80-90"
    elif user_accuracy >= 70:
        user_bucket = "70-80"
    elif user_accuracy >= 60:
        user_bucket = "60-70"
    elif user_accuracy >= 50:
        user_bucket = "50-60"

    # Get specialty comparison
    specialties = ["Internal Medicine", "Surgery", "Pediatrics", "Psychiatry",
                   "Obstetrics and Gynecology", "Emergency Medicine"]

    specialty_comparison = {}
    for specialty in specialties:
        # User's performance in this specialty
        user_spec = db.query(
            func.count(QuestionAttempt.id).label('total'),
            func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id,
            Question.source.ilike(f"%{specialty}%")
        ).first()

        user_spec_total = user_spec.total or 0
        user_spec_correct = user_spec.correct or 0
        user_spec_accuracy = round((user_spec_correct / user_spec_total * 100), 1) if user_spec_total > 0 else None

        # Platform average for this specialty
        platform_spec = db.query(
            func.count(QuestionAttempt.id).label('total'),
            func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            Question.source.ilike(f"%{specialty}%")
        ).first()

        platform_spec_total = platform_spec.total or 0
        platform_spec_correct = platform_spec.correct or 0
        platform_spec_accuracy = round((platform_spec_correct / platform_spec_total * 100), 1) if platform_spec_total > 0 else None

        specialty_comparison[specialty] = {
            "user_accuracy": user_spec_accuracy,
            "user_questions": user_spec_total,
            "platform_accuracy": platform_spec_accuracy,
            "platform_questions": platform_spec_total,
            "difference": round(user_spec_accuracy - platform_spec_accuracy, 1) if user_spec_accuracy and platform_spec_accuracy else None
        }

    return {
        "user_stats": {
            "total_questions": user_total,
            "accuracy": user_accuracy,
            "predicted_score": user_predicted_score,
            "streak": user_streak
        },
        "comparison": {
            "total_peers": len(all_users_stats),
            "percentiles": {
                "accuracy": accuracy_percentile,
                "questions_answered": questions_percentile,
                "accuracy_label": _get_percentile_label(accuracy_percentile),
                "questions_label": _get_percentile_label(questions_percentile)
            },
            "platform_averages": {
                "accuracy": avg_accuracy,
                "median_accuracy": round(median_accuracy, 1),
                "questions_per_user": avg_questions
            },
            "accuracy_vs_average": round(user_accuracy - avg_accuracy, 1),
            "questions_vs_average": round(user_total - avg_questions, 1)
        },
        "distribution": {
            "accuracy_buckets": accuracy_distribution,
            "user_bucket": user_bucket
        },
        "specialty_comparison": specialty_comparison
    }


def _get_percentile_label(percentile: int) -> str:
    """Get human-readable label for percentile."""
    if percentile >= 90:
        return "Top 10%"
    elif percentile >= 75:
        return "Top 25%"
    elif percentile >= 50:
        return "Above Average"
    elif percentile >= 25:
        return "Below Average"
    else:
        return "Bottom 25%"


@router.get("/quality-metrics")
def get_quality_metrics_dashboard(db: Session = Depends(get_db)):
    """
    Get quality metrics dashboard for monitoring question and AI performance.

    This endpoint is for admin/monitoring purposes.

    Returns:
    - Overall platform health metrics
    - AI question performance
    - User engagement metrics
    - Content quality indicators
    """
    from sqlalchemy import Integer, distinct
    from app.models.models import QuestionRating

    # Total questions and attempts
    total_questions = db.query(func.count(Question.id)).scalar() or 0
    total_attempts = db.query(func.count(QuestionAttempt.id)).scalar() or 0
    total_users = db.query(func.count(distinct(QuestionAttempt.user_id))).scalar() or 0

    # Overall accuracy
    correct_attempts = db.query(
        func.sum(func.cast(QuestionAttempt.is_correct, Integer))
    ).scalar() or 0
    overall_accuracy = round((correct_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0

    # AI vs NBME question comparison
    ai_attempts = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        Question.source.ilike('%AI%')
    ).first()

    nbme_attempts = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        ~Question.source.ilike('%AI%')
    ).first()

    ai_accuracy = round(((ai_attempts.correct or 0) / ai_attempts.total * 100), 1) if ai_attempts.total else None
    nbme_accuracy = round(((nbme_attempts.correct or 0) / nbme_attempts.total * 100), 1) if nbme_attempts.total else None

    # Question ratings summary
    ratings = db.query(
        func.count(QuestionRating.id).label('total'),
        func.sum(func.cast(QuestionRating.rating, Integer)).label('approved')
    ).first()

    total_ratings = ratings.total or 0
    approved_ratings = ratings.approved or 0
    approval_rate = round((approved_ratings / total_ratings * 100), 1) if total_ratings > 0 else None

    # Questions by difficulty distribution
    difficulty_dist = db.query(
        Question.difficulty_level,
        func.count(Question.id).label('count')
    ).group_by(
        Question.difficulty_level
    ).all()

    difficulty_distribution = {row.difficulty_level or 'unknown': row.count for row in difficulty_dist}

    # Questions needing attention (low accuracy or negative ratings)
    low_accuracy_questions = db.query(
        Question.id,
        func.count(QuestionAttempt.id).label('attempts'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).group_by(
        Question.id
    ).having(
        func.count(QuestionAttempt.id) >= 10,
        (func.sum(func.cast(QuestionAttempt.is_correct, Integer)) / func.count(QuestionAttempt.id)) < 0.3
    ).count()

    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.created_at >= week_ago
    ).scalar() or 0

    recent_users = db.query(func.count(distinct(QuestionAttempt.user_id))).filter(
        QuestionAttempt.created_at >= week_ago
    ).scalar() or 0

    return {
        "platform_health": {
            "total_questions": total_questions,
            "total_attempts": total_attempts,
            "total_users": total_users,
            "overall_accuracy": overall_accuracy,
            "avg_attempts_per_question": round(total_attempts / total_questions, 1) if total_questions else 0,
            "avg_questions_per_user": round(total_attempts / total_users, 1) if total_users else 0
        },
        "ai_performance": {
            "ai_questions_attempted": ai_attempts.total or 0,
            "ai_accuracy": ai_accuracy,
            "nbme_questions_attempted": nbme_attempts.total or 0,
            "nbme_accuracy": nbme_accuracy,
            "ai_vs_nbme_difference": round(ai_accuracy - nbme_accuracy, 1) if ai_accuracy and nbme_accuracy else None,
            "ai_is_comparable": abs(ai_accuracy - nbme_accuracy) <= 10 if ai_accuracy and nbme_accuracy else None
        },
        "content_quality": {
            "total_ratings": total_ratings,
            "approval_rate": approval_rate,
            "questions_needing_review": low_accuracy_questions,
            "difficulty_distribution": difficulty_distribution
        },
        "recent_activity": {
            "attempts_last_7_days": recent_attempts,
            "active_users_last_7_days": recent_users,
            "avg_daily_attempts": round(recent_attempts / 7, 1)
        }
    }
