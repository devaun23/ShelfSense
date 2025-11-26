"""
Testing/QA Router for ShelfSense.

Provides API endpoints for test validation, coverage analysis,
and quality assurance of AI-generated questions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.services.testing_qa_agent import TestingQAAgent


router = APIRouter(prefix="/api/qa", tags=["testing-qa"])


# ==================== Request/Response Models ====================

class QuestionValidationRequest(BaseModel):
    question_id: str


class BatchValidationRequest(BaseModel):
    question_ids: Optional[List[str]] = None
    sample_size: Optional[int] = Field(None, ge=1, le=500)
    log_results: bool = True


class RunTestsRequest(BaseModel):
    test_path: Optional[str] = None


class ValidationResult(BaseModel):
    question_id: str
    is_valid: bool
    quality_score: float
    issues: List[str]
    suggestions: List[str]


class BatchValidationResult(BaseModel):
    validated: int
    passed: int
    failed: int
    needs_improvement: int
    average_score: float
    details: List[ValidationResult]


class CoverageReport(BaseModel):
    status: str
    overall_coverage: Optional[float] = None
    files: Optional[dict] = None
    message: Optional[str] = None
    generated_at: Optional[str] = None


class QualityOverview(BaseModel):
    total_questions: int
    active_questions: int
    with_explanation: int
    without_explanation: int
    structured_explanations: int
    with_distractor_explanations: int
    quality_score: float
    average_recent_validation_score: float
    recent_validations: int
    generated_at: str


class TestSuiteResult(BaseModel):
    status: str
    passed: Optional[int] = None
    failed: Optional[int] = None
    errors: Optional[int] = None
    exit_code: Optional[int] = None
    message: Optional[str] = None
    ran_at: Optional[str] = None


class UntestedModules(BaseModel):
    untested_modules: dict
    total_untested: int
    generated_at: str


# ==================== Endpoints ====================

@router.post("/validate-question", response_model=ValidationResult)
async def validate_question(
    request: QuestionValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a single question for quality compliance.

    Checks:
    - Vignette length and structure
    - Answer choices format
    - Explanation presence and structure
    - Distractor explanations
    """
    agent = TestingQAAgent(db)
    result = agent.validate_question(request.question_id)

    return ValidationResult(**result)


@router.post("/validate-batch", response_model=BatchValidationResult)
async def validate_batch(
    request: BatchValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate multiple questions in batch.

    Either provide specific question_ids or set sample_size to
    randomly sample questions from the database.
    """
    agent = TestingQAAgent(db)
    result = agent.batch_validate_questions(
        question_ids=request.question_ids,
        sample_size=request.sample_size,
        log_results=request.log_results
    )

    return BatchValidationResult(**result)


@router.get("/coverage", response_model=CoverageReport)
async def get_coverage():
    """
    Get test coverage report.

    Runs pytest with coverage and returns the results.
    Note: This may take some time to execute.
    """
    # This doesn't need a db session
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        agent = TestingQAAgent(db)
        result = agent.get_coverage_report()
        return CoverageReport(**result)
    finally:
        db.close()


@router.get("/quality-overview", response_model=QualityOverview)
async def get_quality_overview(db: Session = Depends(get_db)):
    """
    Get an overview of question quality across the database.

    Returns counts of questions with various quality attributes
    and an overall quality score.
    """
    agent = TestingQAAgent(db)
    result = agent.get_quality_overview()

    return QualityOverview(**result)


@router.get("/untested", response_model=UntestedModules)
async def get_untested_modules(db: Session = Depends(get_db)):
    """
    List modules that don't have corresponding test files.

    Helps identify gaps in test coverage.
    """
    agent = TestingQAAgent(db)
    result = agent.get_untested_modules()

    return UntestedModules(**result)


@router.post("/run-suite", response_model=TestSuiteResult)
async def run_test_suite(
    request: RunTestsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger a test suite execution.

    Optionally specify a test_path to run specific tests.
    Results are returned after execution completes.

    Note: This endpoint has a 5-minute timeout.
    """
    agent = TestingQAAgent(db)
    result = agent.run_test_suite(request.test_path)

    return TestSuiteResult(**result)


@router.get("/report")
async def get_full_qa_report(db: Session = Depends(get_db)):
    """
    Get a comprehensive QA report.

    Combines quality overview, untested modules, and recent validation results.
    """
    agent = TestingQAAgent(db)

    quality_overview = agent.get_quality_overview()
    untested = agent.get_untested_modules()

    # Get recent validation sample
    recent_validation = agent.batch_validate_questions(
        sample_size=10,
        log_results=False
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "quality_overview": quality_overview,
        "untested_modules": untested,
        "recent_validation_sample": {
            "validated": recent_validation["validated"],
            "passed": recent_validation["passed"],
            "failed": recent_validation["failed"],
            "average_score": recent_validation["average_score"]
        },
        "recommendations": _generate_recommendations(
            quality_overview,
            untested,
            recent_validation
        )
    }


def _generate_recommendations(
    quality: dict,
    untested: dict,
    validation: dict
) -> List[str]:
    """Generate actionable recommendations based on QA data."""
    recommendations = []

    # Check explanation coverage
    if quality["without_explanation"] > 0:
        pct = (quality["without_explanation"] / quality["total_questions"]) * 100
        recommendations.append(
            f"{quality['without_explanation']} questions ({pct:.1f}%) are missing explanations. "
            "Run the content quality agent to generate them."
        )

    # Check distractor explanations
    if quality["structured_explanations"] > quality["with_distractor_explanations"]:
        missing = quality["structured_explanations"] - quality["with_distractor_explanations"]
        recommendations.append(
            f"{missing} questions have structured explanations but are missing distractor explanations."
        )

    # Check test coverage
    if untested["total_untested"] > 5:
        recommendations.append(
            f"{untested['total_untested']} modules lack test coverage. "
            "Consider adding tests for critical modules."
        )

    # Check validation scores
    if validation["average_score"] < 70:
        recommendations.append(
            f"Average quality score ({validation['average_score']}) is below target (70). "
            "Review and improve question quality."
        )

    # Check quality score
    if quality["quality_score"] < 60:
        recommendations.append(
            "Overall quality score is low. Focus on adding structured explanations "
            "and distractor explanations to existing questions."
        )

    if not recommendations:
        recommendations.append("All quality metrics look good! Keep up the good work.")

    return recommendations
