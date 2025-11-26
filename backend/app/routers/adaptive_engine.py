"""
Adaptive Learning Engine API Router

Provides endpoints for:
- Weak area identification with recency weighting
- Adaptive question selection
- Time-to-answer analysis
- Confidence tracking
- Learning velocity measurement
- Predictive analytics
- Explanation validation and improvement
- Answer choice validation and improvement
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.database import get_db
from app.services.adaptive_learning_engine import (
    AdaptiveLearningEngineAgent,
    get_adaptive_learning_engine,
    validate_all_explanations,
    get_user_learning_report,
    improve_question_explanation,
    select_next_adaptive_question
)
from app.models.models import Question

router = APIRouter(prefix="/api/adaptive", tags=["adaptive-learning"])


# =========================================================================
# Response Models
# =========================================================================

class WeakAreaItem(BaseModel):
    source: str
    weighted_accuracy: float
    raw_accuracy: float
    total_attempts: int
    trend: str
    avg_time_spent: float
    avg_confidence: float


class WeakAreasResponse(BaseModel):
    weak_areas: List[WeakAreaItem]
    strong_areas: List[WeakAreaItem]
    threshold: float
    analysis: str
    recommendations: List[Dict[str, Any]]


class QuestionResponse(BaseModel):
    id: str
    vignette: str
    choices: List[str]
    source: Optional[str]
    recency_weight: Optional[float]


class TimeAnalysisResponse(BaseModel):
    time_buckets: Dict[str, Dict[str, Any]]
    optimal_time_range: Optional[str]
    avg_time_correct: float
    avg_time_incorrect: float
    total_analyzed: int
    recommendations: List[str]
    analysis: str


class ConfidenceAnalysisResponse(BaseModel):
    calibration_score: Optional[float]
    by_confidence_level: Dict[str, Dict[str, Any]]
    overconfident_errors: int
    underconfident_correct: int
    metacognitive_analysis: str
    recommendations: List[str]
    total_analyzed: int


class LearningVelocityResponse(BaseModel):
    velocity_score: Optional[float]
    velocity_label: Optional[str]
    velocity_per_week: Optional[float]
    current_accuracy: Optional[float]
    weeks_to_target: Optional[float]
    weekly_trend: List[Dict[str, Any]]
    topic_velocity: Dict[str, Dict[str, Any]]
    analysis: str


class PredictionResponse(BaseModel):
    predicted_score: Optional[int]
    confidence_interval: Optional[int]
    score_range: Optional[str]
    weighted_accuracy: Optional[float]
    total_attempts: int
    specialty_predictions: Dict[str, Dict[str, Any]]
    risk_areas: List[Dict[str, Any]]
    readiness: str
    readiness_label: str
    analysis: str


class ExplanationValidationResponse(BaseModel):
    valid: bool
    question_id: str
    quality_score: Optional[float]
    issues: List[str]
    suggestions: List[str]
    needs_regeneration: bool
    explanation_type: Optional[str]
    has_distractor_explanations: Optional[bool]


class ImprovedExplanationResponse(BaseModel):
    success: bool
    question_id: str
    new_explanation: Optional[Dict[str, Any]]
    validation: Optional[Dict[str, Any]]
    explanation_type: Optional[str]
    error: Optional[str]
    needs_manual_review: Optional[bool]


class BatchValidationResponse(BaseModel):
    total_validated: int
    valid: int
    needs_improvement: int
    needs_regeneration: int
    questions_needing_attention: List[Dict[str, Any]]
    by_issue_type: Dict[str, int]


class AnswerChoiceValidationResponse(BaseModel):
    valid: bool
    question_id: str
    quality_score: float
    category_type: Optional[str]
    issues: List[str]
    suggestions: List[str]
    needs_revision: bool


class ImprovedChoicesResponse(BaseModel):
    success: bool
    question_id: str
    original_choices: Optional[List[str]]
    improved_choices: Optional[List[str]]
    correct_answer: Optional[str]
    category: Optional[str]
    distractor_rationales: Optional[Dict[str, str]]
    changes_made: Optional[List[str]]
    error: Optional[str]
    message: Optional[str]


class ComprehensiveReportResponse(BaseModel):
    user_id: str
    generated_at: str
    summary: Dict[str, Any]
    weak_areas: Dict[str, Any]
    time_analysis: Dict[str, Any]
    confidence_analysis: Dict[str, Any]
    learning_velocity: Dict[str, Any]
    performance_prediction: Dict[str, Any]
    top_recommendations: List[Dict[str, Any]]
    next_session_focus: str


# =========================================================================
# User Analytics Endpoints
# =========================================================================

@router.get("/weak-areas/{user_id}", response_model=WeakAreasResponse)
async def get_weak_areas(
    user_id: str,
    threshold: float = Query(0.6, ge=0, le=1, description="Accuracy threshold for weak areas"),
    db: Session = Depends(get_db)
):
    """
    Get detailed weak area analysis with recency weighting.

    Returns areas where user has accuracy below threshold, including:
    - Recency-weighted accuracy
    - Performance trend (improving/declining/stable)
    - Average time spent and confidence
    - Actionable recommendations
    """
    agent = get_adaptive_learning_engine(db)
    result = agent.get_detailed_weak_areas(user_id, threshold)
    return result


@router.get("/next-question/{user_id}", response_model=QuestionResponse)
async def get_next_adaptive_question(
    user_id: str,
    prefer_weak_areas: bool = Query(True, description="Prioritize weak areas"),
    difficulty_adjustment: float = Query(0.0, ge=-1, le=1, description="Difficulty adjustment (-1 to 1)"),
    db: Session = Depends(get_db)
):
    """
    Get the next question using adaptive selection algorithm.

    Algorithm considers:
    - User's weak areas (if prefer_weak_areas=True)
    - Recent performance for difficulty adjustment
    - Recently answered questions (avoided)
    - Question recency weight
    """
    agent = get_adaptive_learning_engine(db)
    question = agent.select_adaptive_question(
        user_id,
        prefer_weak_areas=prefer_weak_areas,
        difficulty_adjustment=difficulty_adjustment
    )

    if not question:
        raise HTTPException(status_code=404, detail="No questions available")

    return QuestionResponse(
        id=question.id,
        vignette=question.vignette,
        choices=question.choices,
        source=question.source,
        recency_weight=question.recency_weight
    )


@router.get("/time-analysis/{user_id}", response_model=TimeAnalysisResponse)
async def get_time_analysis(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Analyze user's time-to-answer patterns.

    Returns:
    - Accuracy by time bucket (rushed, quick, normal, careful, slow)
    - Optimal time range
    - Average time for correct vs incorrect answers
    - Personalized recommendations
    """
    agent = get_adaptive_learning_engine(db)
    return agent.analyze_time_patterns(user_id)


@router.get("/confidence/{user_id}", response_model=ConfidenceAnalysisResponse)
async def get_confidence_analysis(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Analyze user's confidence calibration.

    Returns:
    - Calibration score (0-100, higher is better calibrated)
    - Accuracy by confidence level
    - Overconfident/underconfident patterns
    - Metacognitive analysis and recommendations
    """
    agent = get_adaptive_learning_engine(db)
    return agent.analyze_confidence_patterns(user_id)


@router.get("/velocity/{user_id}", response_model=LearningVelocityResponse)
async def get_learning_velocity(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Measure user's learning velocity.

    Returns:
    - Velocity score (0-100)
    - Improvement rate per week
    - Topic-specific learning speed
    - Estimated weeks to target accuracy
    """
    agent = get_adaptive_learning_engine(db)
    return agent.calculate_learning_velocity(user_id)


@router.get("/prediction/{user_id}", response_model=PredictionResponse)
async def get_performance_prediction(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get predicted exam performance.

    Returns:
    - Predicted Step 2 CK score with confidence interval
    - Specialty-specific predictions
    - Risk areas for exam
    - Readiness assessment
    """
    agent = get_adaptive_learning_engine(db)
    return agent.predict_exam_performance(user_id)


@router.get("/report/{user_id}", response_model=ComprehensiveReportResponse)
async def get_comprehensive_report(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive learning report.

    Combines all analytics:
    - Weak areas
    - Time analysis
    - Confidence calibration
    - Learning velocity
    - Performance prediction
    - Top recommendations
    """
    report = get_user_learning_report(db, user_id)
    return report


# =========================================================================
# Explanation Validation & Improvement Endpoints
# =========================================================================

@router.get("/validate-explanation/{question_id}", response_model=ExplanationValidationResponse)
async def validate_explanation(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate a question's explanation against ShelfSense quality standards.

    Checks:
    - Required fields (principle, clinical_reasoning, correct_answer_explanation)
    - Explanation type classification (TYPE_A through TYPE_F)
    - Distractor explanations for each wrong answer
    - Arrow notation in clinical reasoning
    - Quality rules compliance
    """
    agent = get_adaptive_learning_engine(db)
    result = agent.validate_question_explanation(question_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/improve-explanation/{question_id}", response_model=ImprovedExplanationResponse)
async def generate_improved_explanation(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate an improved explanation for a question.

    Uses AI to create a new explanation that:
    - Follows the 6 explanation types framework
    - Has proper principle, clinical reasoning, and distractor explanations
    - Meets all ShelfSense quality rules
    """
    result = improve_question_explanation(db, question_id)
    return result


@router.post("/batch-validate", response_model=BatchValidationResponse)
async def batch_validate_explanations(
    limit: int = Query(100, ge=1, le=1000, description="Maximum questions to validate"),
    source_filter: Optional[str] = Query(None, description="Filter by source (e.g., 'Internal Medicine')"),
    db: Session = Depends(get_db)
):
    """
    Validate explanations for multiple questions.

    Returns summary of:
    - Valid vs needs improvement vs needs regeneration
    - Questions needing attention (sorted by priority)
    - Common issue types
    """
    result = validate_all_explanations(db, limit)
    return result


@router.post("/apply-explanation/{question_id}")
async def apply_improved_explanation(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate and apply an improved explanation to a question.

    This will update the question's explanation in the database.
    """
    agent = get_adaptive_learning_engine(db)

    # Generate improved explanation
    result = agent.generate_improved_explanation(question_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to generate explanation")
        )

    # Update the question
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.explanation = result["new_explanation"]
    db.commit()

    return {
        "success": True,
        "question_id": question_id,
        "message": "Explanation updated successfully",
        "new_explanation": result["new_explanation"]
    }


# =========================================================================
# Answer Choice Validation & Improvement Endpoints
# =========================================================================

@router.get("/validate-choices/{question_id}", response_model=AnswerChoiceValidationResponse)
async def validate_answer_choices(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate a question's answer choices.

    Checks:
    - All choices same category (diagnoses/treatments/etc.)
    - No duplicates or near-duplicates
    - Correct answer is unambiguous
    - Distractors are plausible
    - Proper medical terminology
    """
    agent = get_adaptive_learning_engine(db)
    result = agent.validate_answer_choices(question_id)

    if "error" in result and result.get("valid") == False:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/improve-choices/{question_id}", response_model=ImprovedChoicesResponse)
async def generate_improved_choices(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate improved answer choices for a question.

    Maintains the correct answer concept but improves distractors to:
    - Be same category as correct answer
    - Be plausible but distinguishable
    - Use proper medical terminology
    """
    agent = get_adaptive_learning_engine(db)
    return agent.generate_improved_answer_choices(question_id)


@router.post("/apply-choices/{question_id}")
async def apply_improved_choices(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate and apply improved answer choices to a question.

    This will update the question's choices in the database.
    """
    agent = get_adaptive_learning_engine(db)

    # Generate improved choices
    result = agent.generate_improved_answer_choices(question_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to generate choices")
        )

    # Check if already valid
    if result.get("message") == "Answer choices already meet quality standards":
        return {
            "success": True,
            "question_id": question_id,
            "message": "No changes needed - choices already meet standards",
            "choices": result.get("current_choices")
        }

    # Update the question
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.choices = result["improved_choices"]

    # Update explanation with new distractor rationales if available
    if result.get("distractor_rationales") and question.explanation:
        if isinstance(question.explanation, dict):
            question.explanation["distractor_explanations"] = result["distractor_rationales"]

    db.commit()

    return {
        "success": True,
        "question_id": question_id,
        "message": "Answer choices updated successfully",
        "original_choices": result.get("original_choices"),
        "new_choices": result.get("improved_choices"),
        "changes_made": result.get("changes_made", [])
    }


# =========================================================================
# Bulk Operations Endpoints
# =========================================================================

@router.post("/bulk-improve-explanations")
async def bulk_improve_explanations(
    limit: int = Query(10, ge=1, le=50, description="Maximum questions to improve"),
    source_filter: Optional[str] = Query(None, description="Filter by source"),
    auto_apply: bool = Query(False, description="Automatically apply improvements"),
    db: Session = Depends(get_db)
):
    """
    Bulk improve explanations for questions that need attention.

    Validates questions and generates improved explanations for those
    that don't meet quality standards.
    """
    agent = get_adaptive_learning_engine(db)

    # First, validate to find questions needing improvement
    validation_result = agent.batch_validate_explanations(limit * 2, source_filter)

    questions_to_improve = validation_result.get("questions_needing_attention", [])[:limit]

    results = {
        "processed": 0,
        "improved": 0,
        "failed": 0,
        "applied": 0,
        "details": []
    }

    for q in questions_to_improve:
        try:
            improvement = agent.generate_improved_explanation(q["question_id"])
            results["processed"] += 1

            if improvement.get("success"):
                results["improved"] += 1

                detail = {
                    "question_id": q["question_id"],
                    "source": q.get("source"),
                    "status": "improved",
                    "applied": False
                }

                if auto_apply:
                    question = db.query(Question).filter(Question.id == q["question_id"]).first()
                    if question:
                        question.explanation = improvement["new_explanation"]
                        db.commit()
                        detail["applied"] = True
                        results["applied"] += 1

                results["details"].append(detail)
            else:
                results["failed"] += 1
                results["details"].append({
                    "question_id": q["question_id"],
                    "source": q.get("source"),
                    "status": "failed",
                    "error": improvement.get("error", "Unknown error")
                })

        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "question_id": q["question_id"],
                "status": "error",
                "error": str(e)
            })

    return results


@router.get("/explanation-stats")
async def get_explanation_stats(
    source_filter: Optional[str] = Query(None, description="Filter by source"),
    db: Session = Depends(get_db)
):
    """
    Get statistics about explanation quality across all questions.
    """
    query = db.query(Question).filter(Question.rejected == False)

    if source_filter:
        query = query.filter(Question.source.like(f"%{source_filter}%"))

    questions = query.all()

    stats = {
        "total_questions": len(questions),
        "has_explanation": 0,
        "has_structured_explanation": 0,
        "has_distractor_explanations": 0,
        "by_type": {},
        "missing_explanation": 0
    }

    for q in questions:
        if not q.explanation:
            stats["missing_explanation"] += 1
            continue

        stats["has_explanation"] += 1

        if isinstance(q.explanation, dict):
            stats["has_structured_explanation"] += 1

            exp_type = q.explanation.get("type", "unknown")
            stats["by_type"][exp_type] = stats["by_type"].get(exp_type, 0) + 1

            if q.explanation.get("distractor_explanations"):
                stats["has_distractor_explanations"] += 1

    # Calculate percentages
    if stats["total_questions"] > 0:
        stats["explanation_coverage"] = round(
            stats["has_explanation"] / stats["total_questions"] * 100, 1
        )
        stats["structured_percentage"] = round(
            stats["has_structured_explanation"] / stats["total_questions"] * 100, 1
        )
        stats["distractor_coverage"] = round(
            stats["has_distractor_explanations"] / stats["total_questions"] * 100, 1
        )

    return stats
