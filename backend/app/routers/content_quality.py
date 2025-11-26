"""
Content Quality API Router

Provides endpoints for:
- Quality overview and metrics
- Batch validation of questions
- Explanation generation and improvement
- Quality reports
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.database import get_db
from app.services.content_quality_agent import (
    ContentQualityAgent,
    get_content_quality_agent,
    run_quality_check,
    generate_quality_report,
    batch_improve_questions
)
from app.models.models import Question

router = APIRouter(prefix="/api/content-quality", tags=["content-quality"])


# =========================================================================
# Response Models
# =========================================================================

class QualityOverviewResponse(BaseModel):
    total_questions: int
    with_explanation: int
    without_explanation: int
    structured_explanations: int
    with_distractor_explanations: int
    coverage_metrics: Dict[str, float]
    by_explanation_type: Dict[str, int]
    recent_validation: Dict[str, int]
    quality_score: float


class AttentionNeededResponse(BaseModel):
    missing_explanation: List[Dict[str, Any]]
    text_only_explanation: List[Dict[str, Any]]
    missing_distractors: List[Dict[str, Any]]
    low_quality: List[Dict[str, Any]]
    summary: Dict[str, int]


class ValidationResultsResponse(BaseModel):
    validated: int
    valid: int
    needs_improvement: int
    needs_regeneration: int
    details: List[Dict[str, Any]]
    by_issue: Dict[str, int]


class ImprovementResultsResponse(BaseModel):
    processed: int
    improved: int
    failed: int
    applied: int
    details: List[Dict[str, Any]]


class QualityReportResponse(BaseModel):
    generated_at: str
    overview: Dict[str, Any]
    attention_needed: Dict[str, int]
    trends: Dict[str, Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    quality_score: float


class SourceBreakdownResponse(BaseModel):
    by_source: Dict[str, Dict[str, Any]]
    total_sources: int


# =========================================================================
# Quality Overview Endpoints
# =========================================================================

@router.get("/overview", response_model=QualityOverviewResponse)
async def get_quality_overview(db: Session = Depends(get_db)):
    """
    Get comprehensive quality overview for all questions.

    Returns:
    - Total questions and explanation coverage
    - Structured vs text explanations
    - Breakdown by explanation type
    - Overall quality score (0-100)
    """
    agent = get_content_quality_agent(db)
    return agent.get_quality_overview()


@router.get("/attention-needed", response_model=AttentionNeededResponse)
async def get_questions_needing_attention(
    limit: int = Query(50, ge=1, le=500, description="Max questions per category"),
    db: Session = Depends(get_db)
):
    """
    Identify questions that need quality improvements.

    Categories:
    - missing_explanation: No explanation at all
    - text_only_explanation: String explanation (not structured)
    - missing_distractors: No distractor explanations
    - low_quality: Poor quality based on validation
    """
    agent = get_content_quality_agent(db)
    return agent.identify_questions_needing_attention(limit=limit)


@router.get("/report", response_model=QualityReportResponse)
async def get_quality_report(db: Session = Depends(get_db)):
    """
    Generate comprehensive quality report with recommendations.

    Includes:
    - Overall quality metrics
    - Weekly and monthly trends
    - Prioritized recommendations
    """
    return generate_quality_report(db)


@router.get("/source-breakdown", response_model=SourceBreakdownResponse)
async def get_source_quality_breakdown(db: Session = Depends(get_db)):
    """
    Get quality breakdown by question source (specialty/exam).

    Shows quality metrics for each source to identify
    which specialties need the most attention.
    """
    agent = get_content_quality_agent(db)
    return agent.get_source_quality_breakdown()


# =========================================================================
# Validation Endpoints
# =========================================================================

@router.post("/validate", response_model=ValidationResultsResponse)
async def validate_questions(
    question_ids: Optional[List[str]] = None,
    limit: int = Query(50, ge=1, le=500, description="Max questions to validate"),
    log_results: bool = Query(True, description="Save results to database"),
    db: Session = Depends(get_db)
):
    """
    Validate questions for quality.

    Checks:
    - Explanation structure and completeness
    - Distractor explanations
    - Clinical reasoning format
    - Quality rules compliance

    Optionally logs results to track improvement over time.
    """
    agent = get_content_quality_agent(db)
    return agent.batch_validate_questions(
        question_ids=question_ids,
        limit=limit,
        log_results=log_results
    )


@router.get("/validate/{question_id}")
async def validate_single_question(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate a single question's explanation quality.
    """
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    agent = get_content_quality_agent(db)
    result = agent._validate_single_question(question)
    result["question_id"] = question_id
    result["source"] = question.source

    return result


# =========================================================================
# Improvement Endpoints
# =========================================================================

@router.post("/improve/{question_id}")
async def improve_single_question(
    question_id: str,
    auto_apply: bool = Query(False, description="Automatically save improvement"),
    db: Session = Depends(get_db)
):
    """
    Generate improved explanation for a single question.

    Uses AI to create a complete explanation following the 6-type framework.
    Optionally applies the improvement immediately.
    """
    agent = get_content_quality_agent(db)
    result = agent.generate_explanation_for_question(question_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to generate explanation")
        )

    if auto_apply:
        question = db.query(Question).filter(Question.id == question_id).first()
        if question:
            question.explanation = result["explanation"]
            db.commit()
            result["applied"] = True

    return result


@router.post("/batch-improve", response_model=ImprovementResultsResponse)
async def batch_improve_questions_endpoint(
    max_questions: int = Query(10, ge=1, le=50, description="Max questions to improve"),
    priority: str = Query("missing", description="Priority: missing, text_only, low_quality, all"),
    auto_apply: bool = Query(False, description="Automatically save improvements"),
    db: Session = Depends(get_db)
):
    """
    Batch improve explanations for multiple questions.

    Priority options:
    - missing: Questions with no explanation
    - text_only: Questions with text-only explanations
    - low_quality: Questions with low quality scores
    - all: Mix of all categories
    """
    if priority not in ["missing", "text_only", "low_quality", "all"]:
        raise HTTPException(status_code=400, detail="Invalid priority value")

    agent = get_content_quality_agent(db)
    return agent.batch_improve_explanations(
        max_questions=max_questions,
        priority=priority,
        auto_apply=auto_apply
    )


@router.post("/batch-improve-background")
async def batch_improve_background(
    background_tasks: BackgroundTasks,
    max_questions: int = Query(50, ge=1, le=200, description="Max questions to improve"),
    priority: str = Query("all", description="Priority: missing, text_only, low_quality, all"),
    db: Session = Depends(get_db)
):
    """
    Start a background task to improve multiple questions.

    This is useful for larger batches that would timeout on a normal request.
    """

    def run_batch_improvement(db_session, max_q, prio):
        agent = ContentQualityAgent(db_session)
        return agent.batch_improve_explanations(
            max_questions=max_q,
            priority=prio,
            auto_apply=True
        )

    background_tasks.add_task(run_batch_improvement, db, max_questions, priority)

    return {
        "message": f"Background improvement task started for {max_questions} questions",
        "priority": priority,
        "status": "running"
    }


# =========================================================================
# Quick Actions
# =========================================================================

@router.post("/quick-check")
async def quick_quality_check(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Run a quick quality check on questions.

    Validates questions and logs results. Useful for periodic quality monitoring.
    """
    return run_quality_check(db, limit=limit)


@router.get("/stats")
async def get_quality_stats(db: Session = Depends(get_db)):
    """
    Get quick quality statistics.

    Returns high-level numbers for dashboard display.
    """
    agent = get_content_quality_agent(db)
    overview = agent.get_quality_overview()

    return {
        "quality_score": overview["quality_score"],
        "total_questions": overview["total_questions"],
        "coverage": {
            "with_explanation": overview["with_explanation"],
            "without_explanation": overview["without_explanation"],
            "structured": overview["structured_explanations"],
            "with_distractors": overview["with_distractor_explanations"]
        },
        "percentages": overview["coverage_metrics"]
    }
