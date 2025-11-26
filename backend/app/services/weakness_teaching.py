"""
Weakness-Targeted Teaching Service

Identifies when a student's error matches their known weakness patterns
and generates concise, targeted interventions.

Triggered ONLY after wrong answers - least intrusive approach.
"""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer

from app.models.models import (
    ErrorAnalysis,
    QuestionAttempt,
    Question,
    UserPerformance,
    LearningMetricsCache
)


# Error type descriptions for interventions
ERROR_TYPE_FIXES = {
    "knowledge_gap": {
        "pattern": "missing key medical knowledge",
        "fix": "Review high-yield facts for this topic before continuing."
    },
    "premature_closure": {
        "pattern": "stopping at first diagnosis without considering alternatives",
        "fix": "List 3 differentials before selecting your answer."
    },
    "misread_stem": {
        "pattern": "missing critical clinical details in the vignette",
        "fix": "Underline age, vitals, and timeline as you read."
    },
    "faulty_reasoning": {
        "pattern": "logical error in clinical reasoning",
        "fix": "Trace the pathophysiology: cause → effect → finding."
    },
    "test_taking_error": {
        "pattern": "second-guessing or changing correct answers",
        "fix": "Trust your first instinct if you reasoned through it."
    },
    "time_pressure": {
        "pattern": "rushing through questions",
        "fix": "Spend 60-90 seconds minimum on each question."
    }
}


def get_user_weakness_profile(db: Session, user_id: str) -> Dict:
    """
    Get user's top error patterns and weak areas.

    Returns:
        {
            "top_error_types": [("premature_closure", 5), ("knowledge_gap", 3), ...],
            "weak_areas": ["Cardiology", "Neurology"],
            "total_errors": 15
        }
    """
    # Get error type frequency
    error_counts = db.query(
        ErrorAnalysis.error_type,
        func.count(ErrorAnalysis.id).label('count')
    ).filter(
        ErrorAnalysis.user_id == user_id
    ).group_by(
        ErrorAnalysis.error_type
    ).order_by(
        func.count(ErrorAnalysis.id).desc()
    ).all()

    top_errors = [(e.error_type, e.count) for e in error_counts[:3]]
    total_errors = sum(e.count for e in error_counts)

    # Get weak areas from cache or performance table
    cache = db.query(LearningMetricsCache).filter_by(
        user_id=user_id,
        is_stale=False
    ).first()

    weak_areas = []
    if cache and cache.weak_areas:
        weak_areas = cache.weak_areas if isinstance(cache.weak_areas, list) else []
    else:
        # Fallback to UserPerformance
        perf = db.query(UserPerformance).filter_by(
            user_id=user_id
        ).order_by(UserPerformance.session_date.desc()).first()

        if perf and perf.weak_areas:
            weak_areas = [w.get('source', w) if isinstance(w, dict) else w
                         for w in perf.weak_areas]

    return {
        "top_error_types": top_errors,
        "weak_areas": weak_areas,
        "total_errors": total_errors
    }


def check_weakness_match(
    db: Session,
    user_id: str,
    error_type: str,
    source: str
) -> Dict:
    """
    Check if current error matches user's weakness pattern.

    Returns:
        {
            "triggered": True/False,
            "priority": "high" | "moderate" | None,
            "error_in_top3": True/False,
            "source_is_weak": True/False,
            "pattern_count": int
        }
    """
    profile = get_user_weakness_profile(db, user_id)

    # Check if error type is in top 3 patterns (with >= 3 occurrences)
    top_error_types = [e[0] for e in profile["top_error_types"]]
    error_counts = {e[0]: e[1] for e in profile["top_error_types"]}

    error_in_top3 = (
        error_type in top_error_types and
        error_counts.get(error_type, 0) >= 3
    )
    pattern_count = error_counts.get(error_type, 0)

    # Check if source is in weak areas
    source_is_weak = any(
        source.lower() in wa.lower() or wa.lower() in source.lower()
        for wa in profile["weak_areas"]
    )

    # Determine priority
    if error_in_top3 and source_is_weak:
        priority = "high"
        triggered = True
    elif error_in_top3 or source_is_weak:
        priority = "moderate"
        triggered = True
    else:
        priority = None
        triggered = False

    return {
        "triggered": triggered,
        "priority": priority,
        "error_in_top3": error_in_top3,
        "source_is_weak": source_is_weak,
        "pattern_count": pattern_count
    }


def generate_intervention(
    error_type: str,
    source: str,
    pattern_count: int,
    priority: str
) -> str:
    """
    Generate concise targeted teaching message (max 50 words).

    Format: "Pattern: [description]. Key: [fix]"
    """
    error_info = ERROR_TYPE_FIXES.get(error_type, {
        "pattern": "error pattern",
        "fix": "Review the explanation carefully."
    })

    # Build message based on priority
    if priority == "high":
        # Both error type and source match
        msg = (
            f"Pattern: {error_info['pattern']} in {source} "
            f"({pattern_count}x). {error_info['fix']}"
        )
    else:
        # Only one matches
        if pattern_count >= 3:
            msg = f"Pattern: {error_info['pattern']} ({pattern_count}x). {error_info['fix']}"
        else:
            msg = f"Weak area: {source}. {error_info['fix']}"

    return msg


def get_weakness_intervention(
    db: Session,
    user_id: str,
    error_type: str,
    source: str
) -> Optional[Dict]:
    """
    Main function: Check for weakness match and generate intervention.

    Returns None if no intervention needed, otherwise:
    {
        "triggered": True,
        "priority": "high" | "moderate",
        "message": "Pattern: ... Key: ...",
        "pattern_count": int
    }
    """
    match = check_weakness_match(db, user_id, error_type, source)

    if not match["triggered"]:
        return None

    message = generate_intervention(
        error_type=error_type,
        source=source,
        pattern_count=match["pattern_count"],
        priority=match["priority"]
    )

    return {
        "triggered": True,
        "priority": match["priority"],
        "message": message,
        "pattern_count": match["pattern_count"]
    }
