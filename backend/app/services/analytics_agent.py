"""
Analytics & Insights Agent Service

Provides comprehensive analytics including:
- Performance tracking by specialty/source
- Predicted score calculation (194-300 range)
- Weak/strong area identification
- Behavioral pattern analysis (time, hover, scroll)
- Progress visualization data
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer, Date, case, extract
from collections import defaultdict

from app.models.models import (
    QuestionAttempt, Question, User, ErrorAnalysis, UserPerformance
)


def get_performance_trends(db: Session, user_id: str, days: int = 30, specialty: Optional[str] = None) -> Dict[str, Any]:
    """
    Get daily performance trends over specified time period.

    Args:
        db: Database session
        user_id: User identifier
        days: Number of days to analyze
        specialty: Optional specialty filter

    Returns:
        - daily_data: List of {date, questions_answered, correct, accuracy, predicted_score}
        - weekly_summary: Aggregated weekly stats
        - overall_trend: "improving", "declining", or "stable"
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Build base query for daily aggregated data
    base_query = db.query(
        func.date(QuestionAttempt.attempted_at).label('date'),
        func.count(QuestionAttempt.id).label('questions_answered'),
        func.sum(cast(QuestionAttempt.is_correct, Integer)).label('correct'),
        func.avg(QuestionAttempt.time_spent_seconds).label('avg_time')
    ).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= start_date
    )

    # Add specialty filter if provided
    if specialty:
        base_query = base_query.join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(Question.specialty == specialty)

    daily_stats = base_query.group_by(
        func.date(QuestionAttempt.attempted_at)
    ).order_by(
        func.date(QuestionAttempt.attempted_at)
    ).all()

    daily_data = []
    for stat in daily_stats:
        accuracy = (stat.correct or 0) / stat.questions_answered if stat.questions_answered > 0 else 0
        # Simplified score calculation for daily trend
        predicted_score = int(194 + (accuracy - 0.6) * 265) if accuracy > 0 else None
        predicted_score = max(194, min(300, predicted_score)) if predicted_score else None

        daily_data.append({
            "date": str(stat.date),
            "questions_answered": stat.questions_answered,
            "correct": stat.correct or 0,
            "accuracy": round(accuracy * 100, 1),
            "avg_time_seconds": round(stat.avg_time or 0, 1),
            "predicted_score": predicted_score
        })

    # Calculate weekly summary
    weekly_summary = _calculate_weekly_summary(daily_data)

    # Determine overall trend
    overall_trend = _calculate_trend(daily_data)

    return {
        "daily_data": daily_data,
        "weekly_summary": weekly_summary,
        "overall_trend": overall_trend,
        "period_days": days
    }


def _calculate_weekly_summary(daily_data: List[Dict]) -> Dict[str, Any]:
    """Calculate weekly aggregated statistics."""
    if not daily_data:
        return {"weeks": []}

    weeks = defaultdict(lambda: {"questions": 0, "correct": 0, "total_time": 0})

    for day in daily_data:
        day_date = datetime.strptime(day["date"], "%Y-%m-%d")
        week_start = day_date - timedelta(days=day_date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")

        weeks[week_key]["questions"] += day["questions_answered"]
        weeks[week_key]["correct"] += day["correct"]
        weeks[week_key]["total_time"] += day["avg_time_seconds"] * day["questions_answered"]

    weekly_list = []
    for week_start, stats in sorted(weeks.items()):
        accuracy = stats["correct"] / stats["questions"] if stats["questions"] > 0 else 0
        weekly_list.append({
            "week_start": week_start,
            "questions_answered": stats["questions"],
            "accuracy": round(accuracy * 100, 1),
            "study_time_minutes": round(stats["total_time"] / 60, 1)
        })

    return {"weeks": weekly_list}


def _calculate_trend(daily_data: List[Dict]) -> str:
    """Determine if performance is improving, declining, or stable."""
    if len(daily_data) < 7:
        return "insufficient_data"

    # Compare first half vs second half accuracy
    mid = len(daily_data) // 2
    first_half = daily_data[:mid]
    second_half = daily_data[mid:]

    first_accuracy = sum(d["accuracy"] for d in first_half) / len(first_half) if first_half else 0
    second_accuracy = sum(d["accuracy"] for d in second_half) / len(second_half) if second_half else 0

    diff = second_accuracy - first_accuracy

    if diff > 3:
        return "improving"
    elif diff < -3:
        return "declining"
    else:
        return "stable"


def get_detailed_weak_areas(db: Session, user_id: str, threshold: float = 0.6, specialty: Optional[str] = None) -> Dict[str, Any]:
    """
    Identify weak and strong areas with detailed breakdown.

    Args:
        db: Database session
        user_id: User identifier
        threshold: Accuracy threshold for weak areas (default 0.6)
        specialty: Optional specialty filter

    Returns:
        - weak_areas: List sorted by priority (impact * weakness)
        - strong_areas: List of mastered topics
        - focus_recommendation: Top 3 areas to focus on
    """
    # Build base query for performance by source (topic)
    base_query = db.query(
        Question.source,
        func.count(QuestionAttempt.id).label('total'),
        func.sum(cast(QuestionAttempt.is_correct, Integer)).label('correct'),
        func.avg(QuestionAttempt.time_spent_seconds).label('avg_time')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        QuestionAttempt.user_id == user_id
    )

    # Add specialty filter if provided
    if specialty:
        base_query = base_query.filter(Question.specialty == specialty)

    results = base_query.group_by(Question.source).all()

    weak_areas = []
    strong_areas = []

    for source, total, correct, avg_time in results:
        if total < 3:  # Need minimum questions for reliable data
            continue

        accuracy = (correct or 0) / total

        # Calculate priority score (lower accuracy + more questions = higher priority)
        priority_score = (1 - accuracy) * min(total / 10, 1)  # Cap at 10 questions for normalization

        area_data = {
            "source": source or "Unknown",
            "total_questions": total,
            "correct": correct or 0,
            "accuracy": round(accuracy * 100, 1),
            "avg_time_seconds": round(avg_time or 0, 1),
            "priority_score": round(priority_score, 3)
        }

        if accuracy < threshold:
            weak_areas.append(area_data)
        elif accuracy >= 0.75:
            strong_areas.append(area_data)

    # Sort weak areas by priority score (highest first)
    weak_areas.sort(key=lambda x: x["priority_score"], reverse=True)

    # Sort strong areas by accuracy (highest first)
    strong_areas.sort(key=lambda x: x["accuracy"], reverse=True)

    # Top 3 focus recommendations
    focus_recommendation = [area["source"] for area in weak_areas[:3]]

    return {
        "weak_areas": weak_areas,
        "strong_areas": strong_areas,
        "focus_recommendation": focus_recommendation,
        "threshold_percent": threshold * 100
    }


def analyze_behavioral_patterns(db: Session, user_id: str, specialty: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze behavioral data from question attempts.

    Args:
        db: Database session
        user_id: User identifier
        specialty: Optional specialty filter

    Returns:
        - time_analysis: Average time by outcome, time distribution
        - hover_analysis: Hover patterns indicating uncertainty
        - scroll_analysis: Reading thoroughness patterns
        - optimal_conditions: Best time of day, session length
    """
    base_query = db.query(
        QuestionAttempt.is_correct,
        QuestionAttempt.time_spent_seconds,
        QuestionAttempt.hover_events,
        QuestionAttempt.scroll_events,
        QuestionAttempt.confidence_level,
        QuestionAttempt.attempted_at
    ).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.time_spent_seconds.isnot(None)
    )

    # Add specialty filter if provided
    if specialty:
        base_query = base_query.join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(Question.specialty == specialty)

    attempts = base_query.all()

    if not attempts:
        return {
            "time_analysis": {},
            "hover_analysis": {},
            "confidence_analysis": {},
            "optimal_conditions": {},
            "sample_size": 0
        }

    # Time analysis
    correct_times = [a.time_spent_seconds for a in attempts if a.is_correct and a.time_spent_seconds]
    incorrect_times = [a.time_spent_seconds for a in attempts if not a.is_correct and a.time_spent_seconds]

    time_analysis = {
        "avg_time_correct": round(sum(correct_times) / len(correct_times), 1) if correct_times else 0,
        "avg_time_incorrect": round(sum(incorrect_times) / len(incorrect_times), 1) if incorrect_times else 0,
        "avg_time_overall": round(sum(a.time_spent_seconds or 0 for a in attempts) / len(attempts), 1),
        "time_distribution": _calculate_time_distribution(attempts)
    }

    # Hover analysis (from JSON data if available)
    hover_counts = []
    for a in attempts:
        if a.hover_events and isinstance(a.hover_events, dict):
            hover_counts.append(len(a.hover_events))

    hover_analysis = {
        "avg_hovers_per_question": round(sum(hover_counts) / len(hover_counts), 1) if hover_counts else 0,
        "high_uncertainty_count": len([h for h in hover_counts if h > 3])
    }

    # Confidence analysis
    confidence_data = [(a.confidence_level, a.is_correct) for a in attempts if a.confidence_level]
    confidence_analysis = _analyze_confidence_accuracy(confidence_data)

    # Optimal conditions - time of day analysis
    hourly_performance = defaultdict(lambda: {"total": 0, "correct": 0})
    for a in attempts:
        if a.attempted_at:
            hour = a.attempted_at.hour
            hourly_performance[hour]["total"] += 1
            if a.is_correct:
                hourly_performance[hour]["correct"] += 1

    best_hours = []
    for hour, stats in hourly_performance.items():
        if stats["total"] >= 5:  # Minimum sample size
            accuracy = stats["correct"] / stats["total"]
            best_hours.append({"hour": hour, "accuracy": round(accuracy * 100, 1), "sample_size": stats["total"]})

    best_hours.sort(key=lambda x: x["accuracy"], reverse=True)

    optimal_conditions = {
        "best_hours": best_hours[:3],
        "hourly_breakdown": [
            {"hour": h, "accuracy": round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0, "count": s["total"]}
            for h, s in sorted(hourly_performance.items())
        ]
    }

    return {
        "time_analysis": time_analysis,
        "hover_analysis": hover_analysis,
        "confidence_analysis": confidence_analysis,
        "optimal_conditions": optimal_conditions,
        "sample_size": len(attempts)
    }


def _calculate_time_distribution(attempts: List) -> Dict[str, int]:
    """Categorize attempts by time spent."""
    distribution = {
        "under_30s": 0,
        "30s_to_60s": 0,
        "60s_to_90s": 0,
        "90s_to_120s": 0,
        "over_120s": 0
    }

    for a in attempts:
        time = a.time_spent_seconds or 0
        if time < 30:
            distribution["under_30s"] += 1
        elif time < 60:
            distribution["30s_to_60s"] += 1
        elif time < 90:
            distribution["60s_to_90s"] += 1
        elif time < 120:
            distribution["90s_to_120s"] += 1
        else:
            distribution["over_120s"] += 1

    return distribution


def _analyze_confidence_accuracy(confidence_data: List) -> Dict[str, Any]:
    """Analyze correlation between confidence and accuracy."""
    if not confidence_data:
        return {"correlation": "insufficient_data", "by_level": {}}

    by_level = defaultdict(lambda: {"total": 0, "correct": 0})

    for confidence, is_correct in confidence_data:
        by_level[confidence]["total"] += 1
        if is_correct:
            by_level[confidence]["correct"] += 1

    level_data = {}
    for level in range(1, 6):
        if by_level[level]["total"] > 0:
            accuracy = by_level[level]["correct"] / by_level[level]["total"]
            level_data[level] = {
                "accuracy": round(accuracy * 100, 1),
                "count": by_level[level]["total"]
            }

    # Check if high confidence correlates with accuracy
    high_conf_accuracy = level_data.get(5, {}).get("accuracy", 0) if 5 in level_data else 0
    low_conf_accuracy = level_data.get(1, {}).get("accuracy", 0) if 1 in level_data else 0

    if high_conf_accuracy > low_conf_accuracy + 20:
        correlation = "well_calibrated"
    elif high_conf_accuracy < low_conf_accuracy:
        correlation = "overconfident"
    else:
        correlation = "needs_calibration"

    return {
        "correlation": correlation,
        "by_level": level_data
    }


def calculate_predicted_score_detailed(db: Session, user_id: str, specialty: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate detailed predicted Step 2 CK score.

    Args:
        db: Database session
        user_id: User identifier
        specialty: Optional specialty filter

    Returns:
        - current_score: 194-300
        - confidence_interval: ±X based on sample size
        - score_trajectory: improving/declining/stable
        - breakdown: by specialty contribution
    """
    # Build base query for all attempts with question weights
    base_query = db.query(
        QuestionAttempt.is_correct,
        QuestionAttempt.attempted_at,
        Question.recency_weight,
        Question.source
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        QuestionAttempt.user_id == user_id
    )

    # Add specialty filter if provided
    if specialty:
        base_query = base_query.filter(Question.specialty == specialty)

    attempts = base_query.order_by(QuestionAttempt.attempted_at).all()

    if not attempts:
        return {
            "current_score": None,
            "confidence_interval": None,
            "score_trajectory": "insufficient_data",
            "breakdown": {},
            "total_questions": 0
        }

    # Calculate weighted accuracy
    total_weight = 0.0
    weighted_correct = 0.0

    for is_correct, _, weight, _ in attempts:
        weight = weight or 0.5
        total_weight += weight
        if is_correct:
            weighted_correct += weight

    weighted_accuracy = weighted_correct / total_weight if total_weight > 0 else 0

    # Calculate score (194-300 range)
    # 60% = 194 (fail), 75% = 245 (average), 90% = 270+
    current_score = int(194 + (weighted_accuracy - 0.6) * 265)
    current_score = max(194, min(300, current_score))

    # Confidence interval based on sample size
    total_questions = len(attempts)
    if total_questions < 50:
        confidence_interval = 20
    elif total_questions < 100:
        confidence_interval = 15
    elif total_questions < 250:
        confidence_interval = 10
    elif total_questions < 500:
        confidence_interval = 7
    else:
        confidence_interval = 5

    # Score trajectory (compare recent vs earlier performance)
    if len(attempts) >= 20:
        recent = attempts[-int(len(attempts) * 0.3):]
        earlier = attempts[:int(len(attempts) * 0.3)]

        recent_accuracy = sum(1 for a in recent if a[0]) / len(recent)
        earlier_accuracy = sum(1 for a in earlier if a[0]) / len(earlier)

        diff = recent_accuracy - earlier_accuracy
        if diff > 0.05:
            score_trajectory = "improving"
        elif diff < -0.05:
            score_trajectory = "declining"
        else:
            score_trajectory = "stable"
    else:
        score_trajectory = "insufficient_data"

    # Breakdown by specialty
    specialty_scores = defaultdict(lambda: {"weight": 0, "weighted_correct": 0})
    for is_correct, _, weight, source in attempts:
        weight = weight or 0.5
        specialty_scores[source or "Unknown"]["weight"] += weight
        if is_correct:
            specialty_scores[source or "Unknown"]["weighted_correct"] += weight

    breakdown = {}
    for source, data in specialty_scores.items():
        if data["weight"] > 0:
            source_accuracy = data["weighted_correct"] / data["weight"]
            source_score = int(194 + (source_accuracy - 0.6) * 265)
            source_score = max(194, min(300, source_score))
            breakdown[source] = {
                "score": source_score,
                "accuracy": round(source_accuracy * 100, 1),
                "weight_contribution": round(data["weight"] / total_weight * 100, 1)
            }

    return {
        "current_score": current_score,
        "weighted_accuracy": round(weighted_accuracy * 100, 1),
        "confidence_interval": confidence_interval,
        "score_trajectory": score_trajectory,
        "breakdown": breakdown,
        "total_questions": total_questions
    }


def get_error_distribution(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Get distribution of error types from ErrorAnalysis table.

    Returns:
        - error_counts: Count by error type
        - most_common: Most frequent error type
        - improvement_over_time: Are specific errors decreasing?
    """
    # Get all error analyses for user
    errors = db.query(
        ErrorAnalysis.error_type,
        ErrorAnalysis.created_at
    ).filter(
        ErrorAnalysis.user_id == user_id
    ).order_by(
        ErrorAnalysis.created_at
    ).all()

    if not errors:
        return {
            "error_counts": {},
            "most_common": None,
            "total_errors": 0,
            "improvement_over_time": {}
        }

    # Count by type
    error_counts = defaultdict(int)
    for error_type, _ in errors:
        error_counts[error_type] += 1

    error_counts = dict(error_counts)
    most_common = max(error_counts.items(), key=lambda x: x[1])[0] if error_counts else None

    # Improvement over time - compare first half to second half
    mid = len(errors) // 2
    first_half_errors = errors[:mid]
    second_half_errors = errors[mid:]

    first_half_counts = defaultdict(int)
    second_half_counts = defaultdict(int)

    for error_type, _ in first_half_errors:
        first_half_counts[error_type] += 1
    for error_type, _ in second_half_errors:
        second_half_counts[error_type] += 1

    improvement = {}
    for error_type in error_counts.keys():
        first = first_half_counts.get(error_type, 0)
        second = second_half_counts.get(error_type, 0)

        if first > 0:
            change_pct = ((second - first) / first) * 100
            if change_pct < -20:
                improvement[error_type] = "improving"
            elif change_pct > 20:
                improvement[error_type] = "worsening"
            else:
                improvement[error_type] = "stable"
        else:
            improvement[error_type] = "new"

    return {
        "error_counts": error_counts,
        "most_common": most_common,
        "total_errors": len(errors),
        "improvement_over_time": improvement
    }


def get_dashboard_data(db: Session, user_id: str, specialty: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all dashboard data in a single call for efficiency.
    Combines all analytics into one response.

    Args:
        db: Database session
        user_id: User identifier
        specialty: Optional specialty filter (e.g., 'Internal Medicine')

    Optimized: Consolidated initial stats into single query.
    """
    # Build base query with optional specialty filter
    base_query = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).filter(
        QuestionAttempt.user_id == user_id
    )

    # Add specialty filter if provided
    if specialty:
        base_query = base_query.join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(Question.specialty == specialty)

    summary_stats = base_query.first()

    total_questions = summary_stats.total or 0
    correct_count = summary_stats.correct or 0
    overall_accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0

    # Get all component data (pass specialty to filter these as well)
    score_data = calculate_predicted_score_detailed(db, user_id, specialty=specialty)
    weak_strong = get_detailed_weak_areas(db, user_id, specialty=specialty)
    trends = get_performance_trends(db, user_id, days=30, specialty=specialty)
    behavioral = analyze_behavioral_patterns(db, user_id, specialty=specialty)
    errors = get_error_distribution(db, user_id)

    # Calculate streak (not specialty-filtered - global)
    streak = _calculate_streak(db, user_id)

    return {
        "summary": {
            "total_questions": total_questions,
            "correct_count": correct_count,
            "overall_accuracy": round(overall_accuracy, 1),
            "weighted_accuracy": score_data.get("weighted_accuracy", 0),
            "predicted_score": score_data.get("current_score"),
            "score_confidence": score_data.get("confidence_interval"),
            "current_streak": streak
        },
        "score_details": score_data,
        "weak_areas": weak_strong["weak_areas"],
        "strong_areas": weak_strong["strong_areas"],
        "focus_recommendation": weak_strong["focus_recommendation"],
        "trends": trends,
        "behavioral_insights": behavioral,
        "error_distribution": errors,
        "specialty_filter": specialty
    }


def _calculate_streak(db: Session, user_id: str) -> int:
    """Calculate current study streak (consecutive days)."""
    attempts = db.query(
        func.date(QuestionAttempt.attempted_at).label('date')
    ).filter(
        QuestionAttempt.user_id == user_id
    ).distinct().order_by(
        func.date(QuestionAttempt.attempted_at).desc()
    ).all()

    if not attempts:
        return 0

    dates = [datetime.strptime(str(a.date), '%Y-%m-%d').date() for a in attempts]
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    if dates[0] not in [today, yesterday]:
        return 0

    streak = 1
    for i in range(1, len(dates)):
        expected_date = dates[i-1] - timedelta(days=1)
        if dates[i] == expected_date:
            streak += 1
        else:
            break

    return streak
