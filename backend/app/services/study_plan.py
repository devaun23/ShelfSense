"""
Study Plan Recommendation Service

Generates algorithm-based study plans using exam countdown,
weak areas, learning velocity, and spaced repetition data.

Plan Types:
- Full exam countdown with weekly milestones
- Daily focus recommendations
- Progress tracking against targets
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    User,
    QuestionAttempt,
    Question,
    ErrorAnalysis,
    ScheduledReview,
    UserPerformance,
    LearningMetricsCache
)


# Target questions per week by learning stage
QUESTIONS_PER_WEEK = {
    "new": 100,          # Building foundation
    "learning": 150,     # Increasing volume
    "review": 200,       # Peak volume
    "mastered": 100      # Maintenance
}

# Step 2 CK specialties with typical weight on exam
SPECIALTIES = {
    "Internal Medicine": 0.25,
    "Surgery": 0.15,
    "Pediatrics": 0.15,
    "Obstetrics and Gynecology": 0.12,
    "Psychiatry": 0.10,
    "Neurology": 0.08,
    "Emergency Medicine": 0.08,
    "Family Medicine": 0.07
}


def get_days_until_exam(db: Session, user_id: str) -> Optional[int]:
    """Get days remaining until user's exam date."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.exam_date:
        return None

    delta = user.exam_date - datetime.utcnow()
    return max(0, delta.days)


def get_user_stats(db: Session, user_id: str) -> Dict:
    """Get current user performance stats."""
    # Total questions answered
    total = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id
    ).scalar() or 0

    # Correct answers
    correct = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    accuracy = (correct / total * 100) if total > 0 else 0

    # Questions in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_questions = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= week_ago
    ).scalar() or 0

    return {
        "total_questions": total,
        "correct": correct,
        "accuracy": round(accuracy, 1),
        "weekly_questions": weekly_questions,
        "daily_average": round(weekly_questions / 7, 1)
    }


def get_specialty_performance(db: Session, user_id: str) -> Dict[str, Dict]:
    """Get accuracy by specialty."""
    performance = {}

    for specialty in SPECIALTIES.keys():
        attempts = db.query(
            QuestionAttempt.is_correct
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id,
            Question.source.ilike(f"%{specialty}%")
        ).all()

        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        accuracy = (correct / total * 100) if total > 0 else 0

        performance[specialty] = {
            "total": total,
            "correct": correct,
            "accuracy": round(accuracy, 1),
            "exam_weight": SPECIALTIES[specialty]
        }

    return performance


def get_error_patterns(db: Session, user_id: str) -> Dict[str, int]:
    """Get count of each error type."""
    errors = db.query(
        ErrorAnalysis.error_type,
        func.count(ErrorAnalysis.id).label('count')
    ).filter(
        ErrorAnalysis.user_id == user_id
    ).group_by(
        ErrorAnalysis.error_type
    ).all()

    return {e.error_type: e.count for e in errors}


def calculate_target_score(db: Session, user_id: str) -> int:
    """Get user's target score or default to 240."""
    user = db.query(User).filter(User.id == user_id).first()
    return user.target_score if user and user.target_score else 240


def calculate_current_predicted_score(accuracy: float, total_questions: int) -> Optional[int]:
    """Calculate predicted score from accuracy."""
    if total_questions < 20:
        return None

    # Formula: 194 + (accuracy/100 - 0.6) * 265
    # 60% accuracy = 194, 80% = 247, 90% = 273
    score = int(194 + (accuracy / 100 - 0.6) * 265)
    return max(194, min(300, score))


def determine_learning_phase(days_remaining: int) -> str:
    """Determine study phase based on days until exam."""
    if days_remaining > 90:
        return "foundation"      # Building knowledge base
    elif days_remaining > 45:
        return "strengthening"   # Targeting weaknesses
    elif days_remaining > 14:
        return "review"          # High-volume review
    else:
        return "final"           # Final preparation


def calculate_weekly_targets(
    days_remaining: int,
    current_accuracy: float,
    target_score: int,
    specialty_performance: Dict
) -> List[Dict]:
    """Calculate weekly study targets with milestones."""
    weeks_remaining = max(1, days_remaining // 7)
    phase = determine_learning_phase(days_remaining)

    # Target accuracy for score
    # 240 score ≈ 71% accuracy, 250 ≈ 75%, 260 ≈ 79%
    target_accuracy = 60 + (target_score - 194) / 265 * 100
    accuracy_gap = target_accuracy - current_accuracy
    weekly_improvement = accuracy_gap / weeks_remaining if weeks_remaining > 0 else 0

    # Identify weak specialties (< 60% or below target)
    weak_specialties = [
        spec for spec, data in specialty_performance.items()
        if data["accuracy"] < 60 or data["total"] < 20
    ]

    # Sort by exam weight * weakness
    weak_specialties.sort(
        key=lambda s: (
            specialty_performance[s]["exam_weight"] *
            (100 - specialty_performance[s]["accuracy"])
        ),
        reverse=True
    )

    weeks = []
    current_week_accuracy = current_accuracy

    for week_num in range(1, min(weeks_remaining + 1, 13)):  # Max 12 weeks shown
        week_days = min(7, days_remaining - (week_num - 1) * 7)

        # Determine focus based on phase
        if phase == "foundation":
            focus_areas = list(SPECIALTIES.keys())[:3]  # Cover breadth
            questions_target = QUESTIONS_PER_WEEK["new"]
        elif phase == "strengthening":
            focus_areas = weak_specialties[:2] if weak_specialties else list(SPECIALTIES.keys())[:2]
            questions_target = QUESTIONS_PER_WEEK["learning"]
        elif phase == "review":
            focus_areas = weak_specialties[:3] if weak_specialties else list(SPECIALTIES.keys())[:3]
            questions_target = QUESTIONS_PER_WEEK["review"]
        else:  # final
            focus_areas = ["Mixed Review"]
            questions_target = QUESTIONS_PER_WEEK["mastered"]

        current_week_accuracy += weekly_improvement

        weeks.append({
            "week": week_num,
            "days_from_now": (week_num - 1) * 7,
            "days_until_exam": days_remaining - (week_num - 1) * 7,
            "focus_areas": focus_areas,
            "questions_target": questions_target,
            "daily_target": round(questions_target / 7),
            "accuracy_milestone": round(min(target_accuracy, current_week_accuracy), 1),
            "phase": phase
        })

        # Update phase for next weeks
        remaining = days_remaining - week_num * 7
        phase = determine_learning_phase(remaining)

    return weeks


def get_daily_recommendation(
    specialty_performance: Dict,
    error_patterns: Dict,
    days_remaining: int
) -> Dict:
    """Get today's specific study recommendation."""
    phase = determine_learning_phase(days_remaining)

    # Find weakest specialty with sufficient data
    weak_specialty = None
    lowest_accuracy = 100

    for spec, data in specialty_performance.items():
        if data["total"] >= 5 and data["accuracy"] < lowest_accuracy:
            lowest_accuracy = data["accuracy"]
            weak_specialty = spec

    # Find most common error
    top_error = max(error_patterns.items(), key=lambda x: x[1])[0] if error_patterns else None

    # Error type to actionable advice
    error_advice = {
        "knowledge_gap": "Focus on high-yield facts and First Aid review",
        "premature_closure": "Practice creating full differential lists",
        "misread_stem": "Slow down - underline key clinical details",
        "faulty_reasoning": "Review pathophysiology connections",
        "test_taking_error": "Trust your first instinct after reasoning",
        "time_pressure": "Practice timed question sets"
    }

    # Calculate recommended questions for today
    if phase == "foundation":
        daily_questions = 15
    elif phase == "strengthening":
        daily_questions = 20
    elif phase == "review":
        daily_questions = 30
    else:
        daily_questions = 15

    return {
        "focus_specialty": weak_specialty or "Mixed Practice",
        "focus_reason": f"Lowest accuracy at {lowest_accuracy:.0f}%" if weak_specialty else "Balanced review",
        "questions_recommended": daily_questions,
        "error_focus": top_error,
        "error_advice": error_advice.get(top_error, "Focus on clinical reasoning"),
        "phase": phase
    }


def generate_study_plan(db: Session, user_id: str) -> Dict:
    """
    Generate comprehensive study plan with exam countdown.

    Returns:
    - Overview (days remaining, current vs target score)
    - Weekly milestones with targets
    - Today's recommendation
    - Progress indicators
    """
    # Get base data
    days_remaining = get_days_until_exam(db, user_id)
    stats = get_user_stats(db, user_id)
    specialty_perf = get_specialty_performance(db, user_id)
    error_patterns = get_error_patterns(db, user_id)
    target_score = calculate_target_score(db, user_id)
    predicted_score = calculate_current_predicted_score(stats["accuracy"], stats["total_questions"])

    # Handle no exam date set
    if days_remaining is None:
        return {
            "status": "no_exam_date",
            "message": "Set your exam date to get a personalized study plan",
            "today": get_daily_recommendation(specialty_perf, error_patterns, 60),
            "stats": stats
        }

    # Calculate weekly targets
    weekly_targets = calculate_weekly_targets(
        days_remaining=days_remaining,
        current_accuracy=stats["accuracy"],
        target_score=target_score,
        specialty_performance=specialty_perf
    )

    # Get today's recommendation
    today = get_daily_recommendation(specialty_perf, error_patterns, days_remaining)

    # Calculate if on track
    phase = determine_learning_phase(days_remaining)
    expected_questions = {
        "foundation": 100 * (90 - days_remaining) // 7 if days_remaining < 90 else 0,
        "strengthening": 800 + 150 * (45 - days_remaining) // 7 if days_remaining < 45 else 0,
        "review": 1800 + 200 * (14 - days_remaining) // 7 if days_remaining < 14 else 0,
        "final": 2500
    }
    min_expected = expected_questions.get(phase, 0)
    on_track = stats["total_questions"] >= min_expected * 0.8

    # Identify weak specialties
    weak_specialties = [
        {"specialty": spec, "accuracy": data["accuracy"], "total": data["total"]}
        for spec, data in specialty_perf.items()
        if data["accuracy"] < 60 or data["total"] < 20
    ]
    weak_specialties.sort(key=lambda x: x["accuracy"])

    return {
        "status": "active",
        "overview": {
            "days_remaining": days_remaining,
            "weeks_remaining": days_remaining // 7,
            "current_phase": phase,
            "target_score": target_score,
            "predicted_score": predicted_score,
            "score_gap": target_score - predicted_score if predicted_score else None,
            "on_track": on_track
        },
        "stats": stats,
        "today": today,
        "weekly_plan": weekly_targets[:8],  # Show next 8 weeks max
        "weak_specialties": weak_specialties[:3],
        "error_patterns": error_patterns,
        "specialty_breakdown": specialty_perf
    }


def get_quick_plan_summary(db: Session, user_id: str) -> str:
    """
    Get a concise text summary of the study plan (< 100 words).
    Used for chat responses or quick display.
    """
    plan = generate_study_plan(db, user_id)

    if plan["status"] == "no_exam_date":
        return "Set your exam date in settings to get a personalized study plan."

    overview = plan["overview"]
    today = plan["today"]

    summary_parts = [
        f"{overview['days_remaining']} days until exam.",
    ]

    if overview["predicted_score"]:
        gap = overview["score_gap"]
        if gap and gap > 0:
            summary_parts.append(f"Need +{gap} points to reach {overview['target_score']}.")
        elif gap and gap <= 0:
            summary_parts.append(f"On track for {overview['target_score']}.")

    summary_parts.append(
        f"Today: {today['questions_recommended']} questions in {today['focus_specialty']}."
    )

    if today["error_focus"]:
        summary_parts.append(f"Focus: {today['error_advice']}")

    return " ".join(summary_parts)
