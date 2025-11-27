"""
NBME-Calibrated Score Predictor API Router

Endpoints for managing external assessment scores and getting calibrated predictions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from datetime import datetime

from app.database import get_db
from app.models.models import ExternalAssessmentScore, ScorePredictionHistory, generate_uuid
from app.services.score_predictor import (
    calculate_nbme_calibrated_score,
    get_prediction_history,
    save_daily_prediction_snapshot,
    _get_shelfsense_score_data
)


router = APIRouter(prefix="/api/score-predictor", tags=["score-predictor"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ExternalAssessmentCreate(BaseModel):
    """Request model for creating a new external assessment score."""
    assessment_type: str = Field(..., pattern="^(nbme|uwsa|free120)$")
    assessment_name: str = Field(..., min_length=2, max_length=50)
    score: int = Field(..., ge=100, le=300)
    percentile: Optional[int] = Field(None, ge=1, le=99)
    date_taken: datetime
    notes: Optional[str] = None


class ExternalAssessmentResponse(BaseModel):
    """Response model for external assessment scores."""
    id: str
    assessment_type: str
    assessment_name: str
    score: int
    percentile: Optional[int]
    date_taken: datetime
    shelfsense_accuracy_at_time: Optional[float]
    shelfsense_questions_at_time: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PredictedScoreResponse(BaseModel):
    """Response model for predicted score."""
    predicted_score: int
    confidence_interval_low: int
    confidence_interval_high: int
    confidence_level: str
    data_sources: Dict[str, int]


class DetailedPredictionResponse(BaseModel):
    """Response model for detailed prediction with breakdown."""
    predicted_score: int
    confidence_interval_low: int
    confidence_interval_high: int
    confidence_level: str
    shelfsense_contribution: Dict[str, Any]
    external_contribution: Dict[str, Any]
    weight_breakdown: Dict[str, float]
    strategy: str
    recommendations: List[str]
    data_sources: Dict[str, int]


class PredictionHistoryItem(BaseModel):
    """Single prediction history item."""
    date: str
    predicted_score: int
    confidence_low: int
    confidence_high: int
    confidence_level: str
    external_score_count: int


class PredictionHistoryResponse(BaseModel):
    """Response model for prediction history."""
    history: List[PredictionHistoryItem]
    trend: str
    score_change_30d: Optional[int]
    score_change_7d: Optional[int]


# =============================================================================
# EXTERNAL ASSESSMENT ENDPOINTS
# =============================================================================

@router.post("/assessments", response_model=ExternalAssessmentResponse)
def create_external_assessment(
    request: ExternalAssessmentCreate,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Add a new NBME/UWSA self-assessment score.

    Valid assessment types:
    - nbme: NBME 9, 10, 11, 12, 13, etc.
    - uwsa: UWSA 1, UWSA 2
    - free120: Free 120 practice exam
    """
    # Get current ShelfSense stats for context
    shelfsense_data = _get_shelfsense_score_data(db, user_id)

    # Validate date is not in the future
    if request.date_taken > datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="Assessment date cannot be in the future"
        )

    # Create assessment
    assessment = ExternalAssessmentScore(
        id=generate_uuid(),
        user_id=user_id,
        assessment_type=request.assessment_type,
        assessment_name=request.assessment_name,
        score=request.score,
        percentile=request.percentile,
        date_taken=request.date_taken,
        shelfsense_accuracy_at_time=shelfsense_data["weighted_accuracy"] if shelfsense_data["questions"] > 0 else None,
        shelfsense_questions_at_time=shelfsense_data["questions"],
        notes=request.notes
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return assessment


@router.get("/assessments", response_model=List[ExternalAssessmentResponse])
def get_external_assessments(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get all external assessment scores for a user.
    Returns scores ordered by date taken (newest first).
    """
    assessments = db.query(ExternalAssessmentScore).filter(
        ExternalAssessmentScore.user_id == user_id
    ).order_by(
        ExternalAssessmentScore.date_taken.desc()
    ).all()

    return assessments


@router.get("/assessments/{assessment_id}", response_model=ExternalAssessmentResponse)
def get_external_assessment(
    assessment_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get a specific external assessment score.
    """
    assessment = db.query(ExternalAssessmentScore).filter(
        ExternalAssessmentScore.id == assessment_id,
        ExternalAssessmentScore.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return assessment


@router.delete("/assessments/{assessment_id}")
def delete_external_assessment(
    assessment_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Delete an external assessment score.
    """
    assessment = db.query(ExternalAssessmentScore).filter(
        ExternalAssessmentScore.id == assessment_id,
        ExternalAssessmentScore.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    db.delete(assessment)
    db.commit()

    return {"message": "Assessment deleted successfully"}


# =============================================================================
# PREDICTION ENDPOINTS
# =============================================================================

@router.get("/predict", response_model=PredictedScoreResponse)
def get_predicted_score(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get NBME-calibrated predicted Step 2 CK score.

    Returns predicted score with confidence interval based on:
    - ShelfSense question bank performance
    - NBME self-assessment scores (if entered)
    - UWSA self-assessment scores (if entered)
    """
    result = calculate_nbme_calibrated_score(db, user_id, save_to_history=False)

    return PredictedScoreResponse(
        predicted_score=result["predicted_score"],
        confidence_interval_low=result["confidence_interval_low"],
        confidence_interval_high=result["confidence_interval_high"],
        confidence_level=result["confidence_level"],
        data_sources=result["data_sources"]
    )


@router.get("/predict/detailed", response_model=DetailedPredictionResponse)
def get_detailed_prediction(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed NBME-calibrated prediction with full breakdown.

    Includes:
    - Predicted score and confidence interval
    - Contribution breakdown (ShelfSense, NBME, UWSA weights)
    - Weighting strategy used
    - Recommendations for improving prediction accuracy
    """
    result = calculate_nbme_calibrated_score(db, user_id, save_to_history=False)

    return DetailedPredictionResponse(
        predicted_score=result["predicted_score"],
        confidence_interval_low=result["confidence_interval_low"],
        confidence_interval_high=result["confidence_interval_high"],
        confidence_level=result["confidence_level"],
        shelfsense_contribution=result["shelfsense_contribution"],
        external_contribution=result["external_contribution"],
        weight_breakdown=result["weight_breakdown"],
        strategy=result["strategy"],
        recommendations=result["recommendations"],
        data_sources=result["data_sources"]
    )


@router.get("/history", response_model=PredictionHistoryResponse)
def get_score_prediction_history(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(30, ge=7, le=365, description="Number of days of history"),
    db: Session = Depends(get_db)
):
    """
    Get prediction history showing how the predicted score evolved over time.

    Returns daily snapshots of predictions with trend analysis.
    """
    result = get_prediction_history(db, user_id, days)

    return PredictionHistoryResponse(
        history=[
            PredictionHistoryItem(
                date=h["date"],
                predicted_score=h["predicted_score"],
                confidence_low=h["confidence_low"],
                confidence_high=h["confidence_high"],
                confidence_level=h["confidence_level"],
                external_score_count=h["external_score_count"]
            )
            for h in result["history"]
        ],
        trend=result["trend"],
        score_change_30d=result["score_change_30d"],
        score_change_7d=result["score_change_7d"]
    )


@router.post("/snapshot")
def save_prediction_snapshot(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a prediction snapshot save.
    Typically called automatically once per day when user studies.

    Returns whether a new snapshot was created (False if one exists for today).
    """
    created = save_daily_prediction_snapshot(db, user_id)

    return {
        "snapshot_created": created,
        "message": "Snapshot saved" if created else "Snapshot already exists for today"
    }
