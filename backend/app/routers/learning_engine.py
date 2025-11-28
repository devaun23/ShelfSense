"""
Learning Engine Router

API endpoints for the advanced learning engine features:
- Per-specialty difficulty tracking (Gap 1)
- Personalized SM-2 intervals (Gap 2)
- Interleaving strategy (Gap 3)
- Forgetting curve model (Gap 4)
- Confidence-weighted selection (Gap 5)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.models import User
from app.routers.auth import get_current_user
from app.services.learning_engine import (
    # Gap 1
    get_specialty_difficulty_target,
    get_all_specialty_difficulties,
    update_specialty_difficulty,
    # Gap 2
    get_or_create_retention_metrics,
    calculate_personalized_interval,
    # Gap 3
    calculate_optimal_mix,
    select_interleaved_question,
    # Gap 4
    get_concepts_needing_review,
    update_all_concept_retentions,
    calculate_memory_strength,
    # Gap 5
    calculate_confidence_calibration,
    # Combined
    select_next_question_advanced,
    process_answer_advanced
)

router = APIRouter(prefix="/api/learning-engine", tags=["Learning Engine"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SpecialtyDifficultyResponse(BaseModel):
    specialty: str
    difficulty_level: str
    target_correct_rate: float
    accuracy: float
    recent_accuracy: Optional[float]
    trend: str
    total_attempts: int


class RetentionMetricsResponse(BaseModel):
    easiness_factor: float
    optimal_first_interval_days: float
    optimal_interval_multiplier: float
    retention_1d: Optional[float]
    retention_3d: Optional[float]
    retention_7d: Optional[float]
    retention_14d: Optional[float]
    retention_30d: Optional[float]


class SessionMixResponse(BaseModel):
    new_ratio: float
    review_ratio: float
    specialty_ratios: dict
    difficulty_ratios: dict


class ConceptReviewResponse(BaseModel):
    concept: str
    specialty: Optional[str]
    current_retention: float
    stability: float
    days_since_review: float
    total_exposures: int
    question_ids: Optional[List[str]]


class ConfidenceCalibrationResponse(BaseModel):
    calibration_score: float
    overconfident_rate: float
    underconfident_rate: float
    by_confidence: dict


class NextQuestionResponse(BaseModel):
    question_id: Optional[str]
    selection_type: Optional[str]
    specialty: Optional[str]
    difficulty: Optional[str]
    algorithms_used: List[str]


class AnswerProcessRequest(BaseModel):
    question_id: str
    is_correct: bool
    confidence_level: Optional[int] = None
    specialty: Optional[str] = None
    concepts: Optional[List[str]] = None


class AnswerProcessResponse(BaseModel):
    specialty_difficulty: Optional[dict]
    scheduled_review: dict
    concept_retentions: List[dict]


# =============================================================================
# GAP 1: PER-SPECIALTY DIFFICULTY ENDPOINTS
# =============================================================================

@router.get("/specialty-difficulty/{specialty}", response_model=SpecialtyDifficultyResponse)
def get_specialty_difficulty(
    specialty: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get difficulty target for a specific specialty for authenticated user."""
    user_id = current_user.id
    return get_specialty_difficulty_target(db, user_id, specialty)


@router.get("/specialty-difficulties", response_model=List[SpecialtyDifficultyResponse])
def get_all_specialty_difficulty_levels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get difficulty levels for all specialties the authenticated user has attempted."""
    user_id = current_user.id
    return get_all_specialty_difficulties(db, user_id)


# =============================================================================
# GAP 2: PERSONALIZED SM-2 ENDPOINTS
# =============================================================================

@router.get("/retention-metrics", response_model=RetentionMetricsResponse)
def get_retention_metrics(
    specialty: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized retention metrics for authenticated user."""
    user_id = current_user.id
    metrics = get_or_create_retention_metrics(db, user_id, specialty)
    return {
        "easiness_factor": metrics.easiness_factor,
        "optimal_first_interval_days": metrics.optimal_first_interval_days,
        "optimal_interval_multiplier": metrics.optimal_interval_multiplier,
        "retention_1d": metrics.retention_1d,
        "retention_3d": metrics.retention_3d,
        "retention_7d": metrics.retention_7d,
        "retention_14d": metrics.retention_14d,
        "retention_30d": metrics.retention_30d
    }


@router.get("/calculate-interval")
def get_personalized_interval(
    current_interval_days: int = Query(..., ge=0),
    is_correct: bool = Query(...),
    specialty: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate the next personalized review interval for authenticated user."""
    user_id = current_user.id
    interval = calculate_personalized_interval(
        db, user_id, current_interval_days, is_correct, specialty
    )
    return {"next_interval_days": interval}


# =============================================================================
# GAP 3: INTERLEAVING STRATEGY ENDPOINTS
# =============================================================================

@router.get("/session-mix", response_model=SessionMixResponse)
def get_session_mix(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the optimal question mix for a study session for authenticated user."""
    user_id = current_user.id
    return calculate_optimal_mix(db, user_id)


@router.get("/interleaved-question")
def get_interleaved_question(
    session_questions: Optional[str] = Query(None, description="Comma-separated list of question IDs already in session"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the next question using interleaving strategy for authenticated user."""
    user_id = current_user.id
    question_list = session_questions.split(",") if session_questions else []
    question, selection_type = select_interleaved_question(db, user_id, question_list)

    if not question:
        return {"question_id": None, "selection_type": "none"}

    return {
        "question_id": question.id,
        "selection_type": selection_type,
        "specialty": question.specialty,
        "difficulty": question.difficulty_level
    }


# =============================================================================
# GAP 4: FORGETTING CURVE ENDPOINTS
# =============================================================================

@router.get("/concepts-needing-review", response_model=List[ConceptReviewResponse])
def get_concepts_for_review(
    min_retention: float = Query(0.7, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get concepts whose retention has dropped below threshold for authenticated user."""
    user_id = current_user.id
    return get_concepts_needing_review(db, user_id, min_retention, limit)


@router.post("/update-concept-retentions")
def update_concept_retentions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update all concept retentions (decay calculation) for authenticated user."""
    user_id = current_user.id
    updated = update_all_concept_retentions(db, user_id)
    return {"concepts_updated": updated}


@router.get("/calculate-retention")
def calculate_retention(
    stability: float = Query(..., ge=0.1),
    days_since_review: float = Query(..., ge=0)
):
    """Calculate current memory strength using Ebbinghaus formula."""
    retention = calculate_memory_strength(stability, days_since_review)
    return {
        "stability": stability,
        "days_since_review": days_since_review,
        "retention": retention
    }


# =============================================================================
# GAP 5: CONFIDENCE CALIBRATION ENDPOINTS
# =============================================================================

@router.get("/confidence-calibration/{user_id}", response_model=ConfidenceCalibrationResponse)
def get_confidence_calibration(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get confidence calibration metrics for a user."""
    return calculate_confidence_calibration(db, user_id)


# =============================================================================
# COMBINED ENDPOINTS
# =============================================================================

@router.get("/next-question/{user_id}", response_model=NextQuestionResponse)
def get_next_question_advanced(
    user_id: str,
    session_questions: Optional[str] = Query(None, description="Comma-separated list of question IDs"),
    use_interleaving: bool = Query(True),
    use_confidence_weighting: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Get the next question using all advanced algorithms.

    Combines:
    - Per-specialty difficulty (Gap 1)
    - Interleaving strategy (Gap 3)
    - Forgetting curve priority (Gap 4)
    - Confidence-weighted selection (Gap 5)
    """
    question_list = session_questions.split(",") if session_questions else []
    question, metadata = select_next_question_advanced(
        db, user_id, question_list, use_interleaving, use_confidence_weighting
    )

    return {
        "question_id": question.id if question else None,
        "selection_type": metadata.get("selection_type"),
        "specialty": metadata.get("specialty"),
        "difficulty": metadata.get("difficulty"),
        "algorithms_used": metadata.get("algorithms_used", [])
    }


@router.post("/process-answer/{user_id}", response_model=AnswerProcessResponse)
def process_answer(
    user_id: str,
    request: AnswerProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process an answer using all advanced algorithms.

    Updates:
    - Per-specialty difficulty (Gap 1)
    - Personalized SM-2 intervals (Gap 2)
    - Concept retention (Gap 4)
    """
    result = process_answer_advanced(
        db,
        user_id,
        request.question_id,
        request.is_correct,
        request.confidence_level,
        request.specialty,
        request.concepts
    )
    return result


# =============================================================================
# DASHBOARD ENDPOINT
# =============================================================================

@router.get("/dashboard/{user_id}")
def get_learning_dashboard(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a comprehensive learning dashboard with all metrics.

    Useful for frontend to display learning progress and recommendations.
    """
    # Update concept retentions first
    update_all_concept_retentions(db, user_id)

    # Gather all data
    specialty_difficulties = get_all_specialty_difficulties(db, user_id)
    retention_metrics = get_or_create_retention_metrics(db, user_id)
    session_mix = calculate_optimal_mix(db, user_id)
    concepts_needing_review = get_concepts_needing_review(db, user_id, min_retention=0.7, limit=10)
    confidence_calibration = calculate_confidence_calibration(db, user_id)

    return {
        "specialty_difficulties": specialty_difficulties,
        "retention_metrics": {
            "easiness_factor": retention_metrics.easiness_factor,
            "optimal_interval_multiplier": retention_metrics.optimal_interval_multiplier,
            "retention_by_interval": {
                "1d": retention_metrics.retention_1d,
                "3d": retention_metrics.retention_3d,
                "7d": retention_metrics.retention_7d,
                "14d": retention_metrics.retention_14d,
                "30d": retention_metrics.retention_30d
            }
        },
        "session_mix": session_mix,
        "concepts_needing_review": concepts_needing_review,
        "confidence_calibration": confidence_calibration,
        "recommendations": _generate_recommendations(
            specialty_difficulties,
            concepts_needing_review,
            confidence_calibration,
            session_mix
        )
    }


def _generate_recommendations(
    specialty_difficulties: list,
    concepts_needing_review: list,
    confidence_calibration: dict,
    session_mix: dict
) -> List[str]:
    """Generate personalized learning recommendations."""
    recommendations = []

    # Specialty-based recommendations
    if specialty_difficulties:
        weak_specialties = [s for s in specialty_difficulties if s["accuracy"] < 0.6]
        if weak_specialties:
            weakest = weak_specialties[0]
            recommendations.append(
                f"Focus on {weakest['specialty']} - your accuracy is {weakest['accuracy']:.0%}"
            )

        improving = [s for s in specialty_difficulties if s["trend"] == "improving"]
        if improving:
            recommendations.append(
                f"Great progress in {improving[0]['specialty']}! Keep it up."
            )

    # Concept retention recommendations
    if concepts_needing_review:
        urgent = [c for c in concepts_needing_review if c["current_retention"] < 0.5]
        if urgent:
            recommendations.append(
                f"{len(urgent)} concepts need urgent review before you forget them"
            )

    # Confidence calibration recommendations
    if confidence_calibration["overconfident_rate"] > 0.3:
        recommendations.append(
            "You're getting overconfident - slow down on high-confidence answers"
        )
    elif confidence_calibration["underconfident_rate"] > 0.4:
        recommendations.append(
            "Trust yourself more - you know more than you think!"
        )

    # Session mix recommendations
    if session_mix["review_ratio"] > 0.5:
        recommendations.append(
            "You have many reviews due - consider a review-focused session"
        )

    return recommendations
