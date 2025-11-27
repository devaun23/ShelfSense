"""
NBME-Calibrated Score Prediction Service

Combines multiple signals for improved Step 2 CK score prediction:
1. ShelfSense question bank performance (weighted accuracy)
2. NBME self-assessment scores
3. UWSA self-assessment scores
4. Recency weighting (newer data weighted more heavily)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from app.models.models import (
    QuestionAttempt, Question, ExternalAssessmentScore,
    ScorePredictionHistory
)


# =============================================================================
# WEIGHTING STRATEGIES
# =============================================================================

WEIGHTING_STRATEGIES = {
    # ShelfSense only
    "shelfsense_only": {
        "shelfsense": 1.0,
        "nbme": 0.0,
        "uwsa": 0.0,
        "base_confidence_interval": 20
    },
    # ShelfSense + 1 NBME
    "shelfsense_1_nbme": {
        "shelfsense": 0.5,
        "nbme": 0.5,
        "uwsa": 0.0,
        "base_confidence_interval": 15
    },
    # ShelfSense + multiple NBMEs (2+)
    "shelfsense_multi_nbme": {
        "shelfsense": 0.4,
        "nbme": 0.6,
        "uwsa": 0.0,
        "base_confidence_interval": 10
    },
    # ShelfSense + NBME + UWSA (full calibration)
    "full_calibration": {
        "shelfsense": 0.3,
        "nbme": 0.4,
        "uwsa": 0.3,
        "base_confidence_interval": 8
    },
    # ShelfSense + UWSA only
    "shelfsense_uwsa": {
        "shelfsense": 0.5,
        "nbme": 0.0,
        "uwsa": 0.5,
        "base_confidence_interval": 12
    }
}

ALGORITHM_VERSION = "v1.0"


# =============================================================================
# CORE PREDICTION FUNCTIONS
# =============================================================================

def calculate_nbme_calibrated_score(
    db: Session,
    user_id: str,
    save_to_history: bool = False
) -> Dict:
    """
    Calculate predicted Step 2 CK score using multiple signals.

    Returns:
        {
            "predicted_score": int (194-300),
            "confidence_interval_low": int,
            "confidence_interval_high": int,
            "confidence_level": str,
            "shelfsense_contribution": {...},
            "external_contribution": {...},
            "weight_breakdown": {...},
            "strategy": str,
            "recommendations": [...]
        }
    """
    # Step 1: Get ShelfSense performance
    shelfsense_data = _get_shelfsense_score_data(db, user_id)

    # Step 2: Get external assessments with recency weighting
    external_scores = _get_weighted_external_scores(db, user_id)

    # Count by type
    nbme_scores = [s for s in external_scores if s["type"] == "nbme"]
    uwsa_scores = [s for s in external_scores if s["type"] == "uwsa"]

    # Step 3: Determine weighting strategy
    strategy_name, weights = _get_weighting_strategy(
        shelfsense_data["questions"],
        len(nbme_scores),
        len(uwsa_scores)
    )

    # Step 4: Calculate weighted score
    predicted_score = _calculate_weighted_score(
        shelfsense_data,
        nbme_scores,
        uwsa_scores,
        weights
    )

    # Step 5: Calculate confidence interval
    ci_low, ci_high, confidence_level = _calculate_confidence_interval(
        predicted_score,
        shelfsense_data["questions"],
        external_scores,
        strategy_name
    )

    # Step 6: Generate recommendations
    recommendations = _generate_recommendations(
        shelfsense_data,
        external_scores,
        confidence_level
    )

    result = {
        "predicted_score": predicted_score,
        "confidence_interval_low": ci_low,
        "confidence_interval_high": ci_high,
        "confidence_level": confidence_level,
        "shelfsense_contribution": {
            "weight": weights["shelfsense"],
            "raw_score": shelfsense_data["raw_score"],
            "questions": shelfsense_data["questions"],
            "weighted_accuracy": shelfsense_data["weighted_accuracy"]
        },
        "external_contribution": {
            "nbme": {
                "weight": weights["nbme"],
                "scores": nbme_scores,
                "avg": _calc_weighted_avg(nbme_scores) if nbme_scores else None
            },
            "uwsa": {
                "weight": weights["uwsa"],
                "scores": uwsa_scores,
                "avg": _calc_weighted_avg(uwsa_scores) if uwsa_scores else None
            }
        },
        "weight_breakdown": weights,
        "strategy": strategy_name,
        "recommendations": recommendations,
        "data_sources": {
            "shelfsense_questions": shelfsense_data["questions"],
            "nbme_count": len(nbme_scores),
            "uwsa_count": len(uwsa_scores)
        }
    }

    # Save to history if requested
    if save_to_history and shelfsense_data["questions"] > 0:
        _save_prediction_snapshot(db, user_id, result)

    return result


def get_prediction_history(
    db: Session,
    user_id: str,
    days: int = 30
) -> Dict:
    """
    Get prediction history for a user.

    Returns:
        {
            "history": [...],
            "trend": str,
            "score_change_30d": int,
            "score_change_7d": int
        }
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    history = db.query(ScorePredictionHistory).filter(
        ScorePredictionHistory.user_id == user_id,
        ScorePredictionHistory.calculated_at >= cutoff
    ).order_by(
        ScorePredictionHistory.calculated_at.asc()
    ).all()

    history_list = [
        {
            "date": h.calculated_at.isoformat(),
            "predicted_score": h.predicted_score,
            "confidence_low": h.confidence_interval_low,
            "confidence_high": h.confidence_interval_high,
            "confidence_level": h.confidence_level,
            "external_score_count": h.external_score_count
        }
        for h in history
    ]

    # Calculate trend
    trend = "stable"
    score_change_30d = None
    score_change_7d = None

    if len(history) >= 2:
        first_score = history[0].predicted_score
        last_score = history[-1].predicted_score
        score_change_30d = last_score - first_score

        if score_change_30d > 5:
            trend = "improving"
        elif score_change_30d < -5:
            trend = "declining"

    # 7-day change
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_history = [h for h in history if h.calculated_at >= seven_days_ago]
    if len(recent_history) >= 2:
        score_change_7d = recent_history[-1].predicted_score - recent_history[0].predicted_score

    return {
        "history": history_list,
        "trend": trend,
        "score_change_30d": score_change_30d,
        "score_change_7d": score_change_7d
    }


def save_daily_prediction_snapshot(db: Session, user_id: str) -> bool:
    """
    Save a daily prediction snapshot if one doesn't exist for today.
    Called automatically when user studies.

    Returns True if a new snapshot was created.
    """
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Check if we already have a snapshot for today
    existing = db.query(ScorePredictionHistory).filter(
        ScorePredictionHistory.user_id == user_id,
        ScorePredictionHistory.calculated_at >= today_start,
        ScorePredictionHistory.calculated_at <= today_end
    ).first()

    if existing:
        return False

    # Calculate and save new prediction
    calculate_nbme_calibrated_score(db, user_id, save_to_history=True)
    return True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_shelfsense_score_data(db: Session, user_id: str) -> Dict:
    """
    Get ShelfSense performance data and convert to predicted score.
    Uses the weighted accuracy formula from adaptive.py.
    """
    attempts = db.query(
        QuestionAttempt.is_correct,
        Question.recency_weight
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).all()

    if not attempts:
        return {
            "questions": 0,
            "weighted_accuracy": 0.0,
            "raw_score": None
        }

    total_weight = 0.0
    weighted_correct = 0.0

    for is_correct, weight in attempts:
        weight = weight or 0.5
        total_weight += weight
        if is_correct:
            weighted_correct += weight

    weighted_accuracy = weighted_correct / total_weight if total_weight > 0 else 0

    # Use existing formula: Score = 194 + (accuracy - 0.6) * 265
    raw_score = int(194 + (weighted_accuracy - 0.6) * 265)
    raw_score = max(194, min(300, raw_score))

    return {
        "questions": len(attempts),
        "weighted_accuracy": round(weighted_accuracy, 4),
        "raw_score": raw_score
    }


def _get_weighted_external_scores(
    db: Session,
    user_id: str,
    decay_half_life_days: int = 90
) -> List[Dict]:
    """
    Get external assessment scores with recency weighting.
    More recent scores are weighted more heavily.
    """
    scores = db.query(ExternalAssessmentScore).filter(
        ExternalAssessmentScore.user_id == user_id
    ).order_by(
        ExternalAssessmentScore.date_taken.desc()
    ).all()

    weighted_scores = []
    now = datetime.utcnow()

    for score in scores:
        days_ago = (now - score.date_taken).days
        # Exponential decay: weight = 0.5^(days/half_life)
        recency_weight = math.pow(0.5, days_ago / decay_half_life_days)

        weighted_scores.append({
            "id": score.id,
            "type": score.assessment_type,
            "name": score.assessment_name,
            "score": score.score,
            "date_taken": score.date_taken.isoformat(),
            "days_ago": days_ago,
            "recency_weight": round(recency_weight, 4)
        })

    return weighted_scores


def _get_weighting_strategy(
    shelfsense_questions: int,
    nbme_count: int,
    uwsa_count: int
) -> Tuple[str, Dict]:
    """
    Determine optimal weighting strategy based on available data.
    """
    if nbme_count == 0 and uwsa_count == 0:
        return "shelfsense_only", WEIGHTING_STRATEGIES["shelfsense_only"]

    if nbme_count >= 1 and uwsa_count >= 1:
        return "full_calibration", WEIGHTING_STRATEGIES["full_calibration"]

    if nbme_count >= 2:
        return "shelfsense_multi_nbme", WEIGHTING_STRATEGIES["shelfsense_multi_nbme"]

    if nbme_count == 1:
        return "shelfsense_1_nbme", WEIGHTING_STRATEGIES["shelfsense_1_nbme"]

    if uwsa_count >= 1:
        return "shelfsense_uwsa", WEIGHTING_STRATEGIES["shelfsense_uwsa"]

    return "shelfsense_only", WEIGHTING_STRATEGIES["shelfsense_only"]


def _calculate_weighted_score(
    shelfsense_data: Dict,
    nbme_scores: List[Dict],
    uwsa_scores: List[Dict],
    weights: Dict
) -> int:
    """
    Calculate the final predicted score using weighted average.
    """
    total_weight = 0.0
    weighted_sum = 0.0

    # ShelfSense contribution
    if shelfsense_data["raw_score"] is not None and weights["shelfsense"] > 0:
        weighted_sum += shelfsense_data["raw_score"] * weights["shelfsense"]
        total_weight += weights["shelfsense"]

    # NBME contribution
    if nbme_scores and weights["nbme"] > 0:
        nbme_avg = _calc_weighted_avg(nbme_scores)
        if nbme_avg is not None:
            weighted_sum += nbme_avg * weights["nbme"]
            total_weight += weights["nbme"]

    # UWSA contribution
    if uwsa_scores and weights["uwsa"] > 0:
        uwsa_avg = _calc_weighted_avg(uwsa_scores)
        if uwsa_avg is not None:
            weighted_sum += uwsa_avg * weights["uwsa"]
            total_weight += weights["uwsa"]

    if total_weight == 0:
        return 194  # Default to passing score

    final_score = weighted_sum / total_weight
    return round(max(194, min(300, final_score)))


def _calc_weighted_avg(scores: List[Dict]) -> Optional[float]:
    """
    Calculate recency-weighted average of scores.
    """
    if not scores:
        return None

    total_weight = sum(s["recency_weight"] for s in scores)
    if total_weight == 0:
        return sum(s["score"] for s in scores) / len(scores)

    weighted_sum = sum(s["score"] * s["recency_weight"] for s in scores)
    return weighted_sum / total_weight


def _calculate_confidence_interval(
    base_score: int,
    shelfsense_questions: int,
    external_scores: List[Dict],
    strategy_name: str
) -> Tuple[int, int, str]:
    """
    Calculate confidence interval that narrows with more data.
    """
    base_interval = WEIGHTING_STRATEGIES[strategy_name]["base_confidence_interval"]

    # Question count bonus: -1 point per 100 questions, max -5
    question_bonus = min(5, shelfsense_questions // 100)

    # Consistency bonus: If external scores are within 15 points, -2
    consistency_bonus = 0
    if len(external_scores) >= 2:
        scores = [s["score"] for s in external_scores]
        score_range = max(scores) - min(scores)
        if score_range <= 15:
            consistency_bonus = 2

    # Final interval
    final_interval = base_interval - question_bonus - consistency_bonus
    final_interval = max(5, final_interval)  # Minimum ±5

    # Determine confidence level
    if final_interval >= 15:
        confidence_level = "low"
    elif final_interval >= 10:
        confidence_level = "medium"
    else:
        confidence_level = "high"

    return (
        max(194, base_score - final_interval),
        min(300, base_score + final_interval),
        confidence_level
    )


def _generate_recommendations(
    shelfsense_data: Dict,
    external_scores: List[Dict],
    confidence_level: str
) -> List[str]:
    """
    Generate actionable recommendations to improve prediction accuracy.
    """
    recommendations = []

    if shelfsense_data["questions"] < 100:
        recommendations.append(
            f"Answer {100 - shelfsense_data['questions']} more questions to improve prediction accuracy"
        )

    nbme_count = len([s for s in external_scores if s["type"] == "nbme"])
    uwsa_count = len([s for s in external_scores if s["type"] == "uwsa"])

    if nbme_count == 0:
        recommendations.append(
            "Add an NBME self-assessment score to calibrate your prediction"
        )
    elif nbme_count == 1:
        recommendations.append(
            "Add another NBME score for more accurate calibration"
        )

    if uwsa_count == 0 and nbme_count > 0:
        recommendations.append(
            "Consider adding a UWSA score for additional validation"
        )

    if confidence_level == "low":
        recommendations.append(
            "Your prediction confidence is low - more data will help narrow the range"
        )

    return recommendations


def _save_prediction_snapshot(db: Session, user_id: str, result: Dict) -> None:
    """
    Save a prediction snapshot to history.
    """
    from app.models.models import generate_uuid

    nbme_scores = result["external_contribution"]["nbme"]["scores"]
    uwsa_scores = result["external_contribution"]["uwsa"]["scores"]
    all_external = nbme_scores + uwsa_scores

    external_avg = None
    if all_external:
        external_avg = sum(s["score"] for s in all_external) / len(all_external)

    snapshot = ScorePredictionHistory(
        id=generate_uuid(),
        user_id=user_id,
        predicted_score=result["predicted_score"],
        confidence_interval_low=result["confidence_interval_low"],
        confidence_interval_high=result["confidence_interval_high"],
        confidence_level=result["confidence_level"],
        shelfsense_accuracy=result["shelfsense_contribution"]["weighted_accuracy"],
        shelfsense_questions=result["shelfsense_contribution"]["questions"],
        external_score_count=len(all_external),
        external_score_avg=external_avg,
        weight_breakdown=result["weight_breakdown"],
        algorithm_version=ALGORITHM_VERSION
    )

    db.add(snapshot)
    db.commit()
