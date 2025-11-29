"""
NBME Self-Assessment Simulator API Router

Provides full-length NBME-style practice assessments with:
- 4 blocks x 40 questions x 60 minutes (default configuration)
- Real exam simulation experience
- Predicted score calculation on completion
- Peer comparison percentile rankings
- Performance breakdown by system and difficulty
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import random


class AssessmentStatus(str, Enum):
    """Valid status values for assessments."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

from app.database import get_db
from app.models.models import (
    SelfAssessment, AssessmentBlock, AssessmentComparison,
    Question, QuestionAttempt, User, generate_uuid
)
from app.services.score_predictor import calculate_nbme_calibrated_score
from app.dependencies.auth import get_current_user, verify_user_access


router = APIRouter(prefix="/api/self-assessment", tags=["self-assessment"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateAssessmentRequest(BaseModel):
    """Request to create a new self-assessment."""
    name: str = Field(default="Practice Assessment", min_length=1, max_length=100)
    total_blocks: int = Field(default=4, ge=1, le=8)
    questions_per_block: int = Field(default=40, ge=10, le=50)
    time_per_block_minutes: int = Field(default=60, ge=30, le=90)


class AssessmentSummary(BaseModel):
    """Summary of a self-assessment."""
    id: str
    name: str
    total_blocks: int
    questions_per_block: int
    time_per_block_minutes: int
    status: str
    current_block: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    percentage_score: Optional[float]
    predicted_step2_score: Optional[int]
    percentile_rank: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class BlockSummary(BaseModel):
    """Summary of an assessment block."""
    block_number: int
    status: str
    questions_total: int
    questions_answered: int
    questions_correct: Optional[int]
    time_limit_seconds: int
    time_spent_seconds: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class AssessmentDetailResponse(BaseModel):
    """Detailed assessment with blocks."""
    id: str
    name: str
    total_blocks: int
    questions_per_block: int
    time_per_block_minutes: int
    status: str
    current_block: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_time_seconds: int
    raw_score: Optional[int]
    percentage_score: Optional[float]
    predicted_step2_score: Optional[int]
    confidence_interval_low: Optional[int]
    confidence_interval_high: Optional[int]
    percentile_rank: Optional[int]
    performance_by_system: Optional[Dict[str, float]]
    performance_by_difficulty: Optional[Dict[str, float]]
    blocks: List[BlockSummary]
    created_at: datetime


class QuestionForBlock(BaseModel):
    """Question data for assessment block."""
    id: str
    index: int
    vignette: str
    choices: List[str]
    source: Optional[str]
    user_answer: Optional[str]
    flagged: bool
    time_spent: int


class BlockQuestionsResponse(BaseModel):
    """Response with questions for a block."""
    assessment_id: str
    block_number: int
    status: str
    time_limit_seconds: int
    time_remaining_seconds: int
    questions: List[QuestionForBlock]
    current_index: int


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer."""
    question_id: str = Field(..., min_length=1, max_length=64)
    answer: str = Field(..., pattern="^[A-E]$", description="Valid answer choice (A-E)")
    time_spent_seconds: int = Field(ge=0, le=7200)  # Max 2 hours per question
    flagged: bool = False


class SubmitAnswerResponse(BaseModel):
    """Response after submitting an answer."""
    saved: bool
    questions_answered: int
    questions_remaining: int


class CompleteBlockRequest(BaseModel):
    """Request to complete a block."""
    time_spent_seconds: int = Field(ge=0, le=10800)  # Max 3 hours per block


class BlockResultsResponse(BaseModel):
    """Results for a completed block."""
    block_number: int
    questions_total: int
    questions_answered: int
    questions_correct: int
    accuracy: float
    time_spent_seconds: int
    avg_time_per_question: float
    questions: List[Dict[str, Any]]


class AssessmentResultsResponse(BaseModel):
    """Full assessment results."""
    id: str
    name: str
    status: str
    total_questions: int
    questions_answered: int
    questions_correct: int
    raw_score: int
    percentage_score: float
    predicted_step2_score: int
    confidence_interval_low: int
    confidence_interval_high: int
    percentile_rank: int
    total_time_seconds: int
    avg_time_per_question: float
    performance_by_system: Dict[str, float]
    performance_by_difficulty: Dict[str, float]
    blocks: List[BlockResultsResponse]
    readiness_verdict: str
    recommendations: List[str]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def select_assessment_questions(db: Session, count: int) -> List[str]:
    """
    Select questions for an assessment block.
    Mixes different difficulty levels and sources for NBME-like distribution.
    """
    # Get all available questions (not rejected)
    all_questions = db.query(Question.id, Question.difficulty_level, Question.source).filter(
        Question.rejected == False,
        Question.content_status == "active"
    ).all()

    if len(all_questions) < count:
        # Fallback: use all available
        return [q.id for q in all_questions]

    # Target distribution (NBME-like)
    # 20% easy, 50% medium, 30% hard
    easy_count = int(count * 0.2)
    medium_count = int(count * 0.5)
    hard_count = count - easy_count - medium_count

    easy_qs = [q.id for q in all_questions if q.difficulty_level == "easy"]
    medium_qs = [q.id for q in all_questions if q.difficulty_level == "medium"]
    hard_qs = [q.id for q in all_questions if q.difficulty_level == "hard"]
    other_qs = [q.id for q in all_questions if q.difficulty_level not in ["easy", "medium", "hard"]]

    selected = []

    # Select from each category
    random.shuffle(easy_qs)
    random.shuffle(medium_qs)
    random.shuffle(hard_qs)
    random.shuffle(other_qs)

    selected.extend(easy_qs[:easy_count])
    selected.extend(medium_qs[:medium_count])
    selected.extend(hard_qs[:hard_count])

    # Fill remaining with other questions
    remaining = count - len(selected)
    if remaining > 0:
        filler = other_qs + easy_qs[easy_count:] + medium_qs[medium_count:] + hard_qs[hard_count:]
        random.shuffle(filler)
        selected.extend(filler[:remaining])

    random.shuffle(selected)
    return selected[:count]


def calculate_percentile(db: Session, percentage_score: float) -> int:
    """
    Calculate percentile rank based on score.

    Percentile represents the percentage of test-takers who scored BELOW this score.
    Higher percentile = better performance relative to peers.
    """
    # Round down to nearest 5% bucket
    bucket = int(percentage_score // 5) * 5

    # First try to find exact bucket match
    comparison = db.query(AssessmentComparison).filter(
        AssessmentComparison.score_bucket == bucket
    ).first()

    # If no exact match, find the closest lower bucket
    if not comparison:
        comparison = db.query(AssessmentComparison).filter(
            AssessmentComparison.score_bucket < bucket
        ).order_by(AssessmentComparison.score_bucket.desc()).first()

    if comparison:
        return int(comparison.percentile)

    # Default percentile estimation if no data
    # Based on typical NBME score distribution (centered around 65%, SD ~10%)
    if percentage_score >= 90:
        return 97  # Top 3%
    elif percentage_score >= 85:
        return 93  # Top 7%
    elif percentage_score >= 80:
        return 84  # Top 16%
    elif percentage_score >= 75:
        return 73  # Top 27%
    elif percentage_score >= 70:
        return 60  # Top 40%
    elif percentage_score >= 65:
        return 50  # Median
    elif percentage_score >= 60:
        return 40  # Below median
    elif percentage_score >= 55:
        return 27
    elif percentage_score >= 50:
        return 16
    else:
        return 7  # Bottom 7%


def calculate_assessment_score(percentage: float) -> int:
    """
    Convert percentage to predicted Step 2 CK score.
    Based on NBME correlation data.
    """
    # Approximate mapping (NBME-style)
    # 90%+ -> 270+
    # 80% -> 250
    # 70% -> 235
    # 60% -> 220
    # 50% -> 205
    if percentage >= 95:
        return 280
    elif percentage >= 90:
        return 270
    elif percentage >= 85:
        return 260
    elif percentage >= 80:
        return 250
    elif percentage >= 75:
        return 243
    elif percentage >= 70:
        return 235
    elif percentage >= 65:
        return 228
    elif percentage >= 60:
        return 220
    elif percentage >= 55:
        return 213
    elif percentage >= 50:
        return 205
    elif percentage >= 45:
        return 198
    else:
        return 190


# =============================================================================
# ASSESSMENT MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/create", response_model=AssessmentSummary)
def create_assessment(
    request: CreateAssessmentRequest,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new NBME-style self-assessment.

    SECURITY: Requires authentication. Users can only create assessments for themselves.

    Default configuration mimics real NBME:
    - 4 blocks x 40 questions x 60 minutes = 160 questions in 4 hours
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    # Check for existing in-progress assessment
    existing = db.query(SelfAssessment).filter(
        SelfAssessment.user_id == user_id,
        SelfAssessment.status == "in_progress"
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="You have an assessment in progress. Complete or abandon it first."
        )

    total_questions = request.total_blocks * request.questions_per_block

    # Select questions for all blocks
    all_question_ids = select_assessment_questions(db, total_questions)

    if len(all_question_ids) < total_questions:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough questions available. Need {total_questions}, have {len(all_question_ids)}."
        )

    # Split into blocks
    question_blocks = []
    for i in range(request.total_blocks):
        start = i * request.questions_per_block
        end = start + request.questions_per_block
        question_blocks.append(all_question_ids[start:end])

    # Create assessment
    assessment = SelfAssessment(
        id=generate_uuid(),
        user_id=user_id,
        name=request.name,
        total_blocks=request.total_blocks,
        questions_per_block=request.questions_per_block,
        time_per_block_minutes=request.time_per_block_minutes,
        question_blocks=question_blocks,
        status="not_started"
    )
    db.add(assessment)

    # Create blocks
    for i, block_questions in enumerate(question_blocks):
        block = AssessmentBlock(
            id=generate_uuid(),
            assessment_id=assessment.id,
            block_number=i + 1,
            question_ids=block_questions,
            time_limit_seconds=request.time_per_block_minutes * 60,
            answers={}
        )
        db.add(block)

    db.commit()
    db.refresh(assessment)

    return assessment


@router.get("/list", response_model=List[AssessmentSummary])
def list_assessments(
    user_id: str = Query(..., description="User ID"),
    status: Optional[AssessmentStatus] = Query(None, description="Filter by status: not_started, in_progress, completed, abandoned"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all self-assessments for a user.

    SECURITY: Requires authentication. Users can only access their own assessments.

    Optionally filter by status: not_started, in_progress, completed, abandoned.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    query = db.query(SelfAssessment).filter(SelfAssessment.user_id == user_id)

    if status:
        query = query.filter(SelfAssessment.status == status.value)

    assessments = query.order_by(SelfAssessment.created_at.desc()).all()
    return assessments


@router.get("/{assessment_id}", response_model=AssessmentDetailResponse)
def get_assessment(
    assessment_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific assessment.

    SECURITY: Requires authentication. Users can only access their own assessments.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Get blocks
    blocks = db.query(AssessmentBlock).filter(
        AssessmentBlock.assessment_id == assessment_id
    ).order_by(AssessmentBlock.block_number).all()

    block_summaries = []
    for block in blocks:
        block_summaries.append(BlockSummary(
            block_number=block.block_number,
            status=block.status,
            questions_total=len(block.question_ids),
            questions_answered=block.questions_answered,
            questions_correct=block.questions_correct if block.status == "completed" else None,
            time_limit_seconds=block.time_limit_seconds,
            time_spent_seconds=block.time_spent_seconds,
            started_at=block.started_at,
            completed_at=block.completed_at
        ))

    return AssessmentDetailResponse(
        id=assessment.id,
        name=assessment.name,
        total_blocks=assessment.total_blocks,
        questions_per_block=assessment.questions_per_block,
        time_per_block_minutes=assessment.time_per_block_minutes,
        status=assessment.status,
        current_block=assessment.current_block,
        started_at=assessment.started_at,
        completed_at=assessment.completed_at,
        total_time_seconds=assessment.total_time_seconds,
        raw_score=assessment.raw_score,
        percentage_score=assessment.percentage_score,
        predicted_step2_score=assessment.predicted_step2_score,
        confidence_interval_low=assessment.confidence_interval_low,
        confidence_interval_high=assessment.confidence_interval_high,
        percentile_rank=assessment.percentile_rank,
        performance_by_system=assessment.performance_by_system,
        performance_by_difficulty=assessment.performance_by_difficulty,
        blocks=block_summaries,
        created_at=assessment.created_at
    )


@router.post("/{assessment_id}/start")
def start_assessment(
    assessment_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a self-assessment. Marks first block as in_progress.

    SECURITY: Requires authentication. Users can only start their own assessments.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.status != "not_started":
        raise HTTPException(status_code=400, detail="Assessment already started")

    # Update assessment
    assessment.status = "in_progress"
    assessment.started_at = datetime.utcnow()
    assessment.current_block = 1

    # Start first block
    first_block = db.query(AssessmentBlock).filter(
        AssessmentBlock.assessment_id == assessment_id,
        AssessmentBlock.block_number == 1
    ).first()

    if first_block:
        first_block.status = "in_progress"
        first_block.started_at = datetime.utcnow()

    db.commit()

    return {"message": "Assessment started", "current_block": 1}


@router.post("/{assessment_id}/abandon")
def abandon_assessment(
    assessment_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Abandon an in-progress assessment.

    SECURITY: Requires authentication. Users can only abandon their own assessments.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.status not in ["not_started", "in_progress"]:
        raise HTTPException(status_code=400, detail="Cannot abandon completed assessment")

    assessment.status = "abandoned"
    db.commit()

    return {"message": "Assessment abandoned"}


@router.delete("/{assessment_id}")
def delete_assessment(
    assessment_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an assessment (only not_started or abandoned assessments).

    SECURITY: Requires authentication. Users can only delete their own assessments.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.status in ["in_progress", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete in-progress or completed assessments"
        )

    db.delete(assessment)
    db.commit()

    return {"message": "Assessment deleted"}


# =============================================================================
# BLOCK ENDPOINTS
# =============================================================================

@router.get("/{assessment_id}/block/{block_number}/questions", response_model=BlockQuestionsResponse)
def get_block_questions(
    assessment_id: str,
    block_number: int,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get questions for a specific block.
    Only returns questions if block is in_progress.

    SECURITY: Requires authentication. Users can only access their own assessments.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    block = db.query(AssessmentBlock).filter(
        AssessmentBlock.assessment_id == assessment_id,
        AssessmentBlock.block_number == block_number
    ).first()

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    if block.status == "not_started":
        raise HTTPException(status_code=400, detail="Block not yet started")

    # Get questions
    questions = db.query(Question).filter(
        Question.id.in_(block.question_ids)
    ).all()

    # Create ID to question map for ordering
    q_map = {q.id: q for q in questions}

    # Build response in order
    answers = block.answers or {}
    question_list = []
    for i, qid in enumerate(block.question_ids):
        q = q_map.get(qid)
        if q:
            answer_data = answers.get(qid, {})
            question_list.append(QuestionForBlock(
                id=q.id,
                index=i,
                vignette=q.vignette,
                choices=q.choices,
                source=q.source,
                user_answer=answer_data.get("answer"),
                flagged=answer_data.get("flagged", False),
                time_spent=answer_data.get("time_spent", 0)
            ))

    # Calculate time remaining
    if block.started_at:
        elapsed = (datetime.utcnow() - block.started_at).total_seconds()
        time_remaining = max(0, block.time_limit_seconds - int(elapsed) - block.time_spent_seconds)
    else:
        time_remaining = block.time_limit_seconds

    return BlockQuestionsResponse(
        assessment_id=assessment_id,
        block_number=block_number,
        status=block.status,
        time_limit_seconds=block.time_limit_seconds,
        time_remaining_seconds=int(time_remaining),
        questions=question_list,
        current_index=0
    )


@router.post("/{assessment_id}/block/{block_number}/answer", response_model=SubmitAnswerResponse)
def submit_block_answer(
    assessment_id: str,
    block_number: int,
    request: SubmitAnswerRequest,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit an answer for a question in a block.
    Answers can be changed until block is completed.

    SECURITY: Requires authentication. Users can only submit answers for their own assessments.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    block = db.query(AssessmentBlock).filter(
        AssessmentBlock.assessment_id == assessment_id,
        AssessmentBlock.block_number == block_number
    ).first()

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    if block.status != "in_progress":
        raise HTTPException(status_code=400, detail="Block is not in progress")

    if request.question_id not in block.question_ids:
        raise HTTPException(status_code=400, detail="Question not in this block")

    # Update answer
    answers = block.answers or {}
    was_answered = request.question_id in answers

    answers[request.question_id] = {
        "answer": request.answer,
        "time_spent": request.time_spent_seconds,
        "flagged": request.flagged
    }
    block.answers = answers

    # Update count
    if not was_answered:
        block.questions_answered = len([a for a in answers.values() if a.get("answer")])

    db.commit()

    return SubmitAnswerResponse(
        saved=True,
        questions_answered=block.questions_answered,
        questions_remaining=len(block.question_ids) - block.questions_answered
    )


@router.post("/{assessment_id}/block/{block_number}/complete", response_model=BlockResultsResponse)
def complete_block(
    assessment_id: str,
    block_number: int,
    request: CompleteBlockRequest,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete a block and get results.
    Moves to next block or completes assessment if last block.

    SECURITY: Requires authentication. Users can only complete their own assessment blocks.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    block = db.query(AssessmentBlock).filter(
        AssessmentBlock.assessment_id == assessment_id,
        AssessmentBlock.block_number == block_number
    ).first()

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    if block.status != "in_progress":
        raise HTTPException(status_code=400, detail="Block is not in progress")

    # Get questions to grade
    questions = db.query(Question).filter(
        Question.id.in_(block.question_ids)
    ).all()
    q_map = {q.id: q for q in questions}

    # Grade answers
    answers = block.answers or {}
    correct_count = 0
    question_results = []

    for qid in block.question_ids:
        q = q_map.get(qid)
        answer_data = answers.get(qid, {})
        user_answer = answer_data.get("answer")
        is_correct = user_answer == q.answer_key if q and user_answer else False

        if is_correct:
            correct_count += 1

        # Also record attempt in QuestionAttempt for analytics
        if user_answer:
            attempt = QuestionAttempt(
                id=generate_uuid(),
                user_id=user_id,
                question_id=qid,
                user_answer=user_answer,
                is_correct=is_correct,
                time_spent_seconds=answer_data.get("time_spent", 0)
            )
            db.add(attempt)

        question_results.append({
            "question_id": qid,
            "user_answer": user_answer,
            "correct_answer": q.answer_key if q else None,
            "is_correct": is_correct,
            "time_spent": answer_data.get("time_spent", 0),
            "flagged": answer_data.get("flagged", False),
            "source": q.source if q else None
        })

    # Update block
    block.status = "completed"
    block.completed_at = datetime.utcnow()
    block.time_spent_seconds = request.time_spent_seconds
    block.questions_correct = correct_count

    # Check if there's a next block
    if block_number < assessment.total_blocks:
        # Start next block
        next_block = db.query(AssessmentBlock).filter(
            AssessmentBlock.assessment_id == assessment_id,
            AssessmentBlock.block_number == block_number + 1
        ).first()

        if next_block:
            next_block.status = "in_progress"
            next_block.started_at = datetime.utcnow()
            assessment.current_block = block_number + 1
    else:
        # Complete assessment
        _finalize_assessment(db, assessment)

    db.commit()

    return BlockResultsResponse(
        block_number=block_number,
        questions_total=len(block.question_ids),
        questions_answered=block.questions_answered,
        questions_correct=correct_count,
        accuracy=round(correct_count / len(block.question_ids) * 100, 1) if block.question_ids else 0,
        time_spent_seconds=request.time_spent_seconds,
        avg_time_per_question=round(request.time_spent_seconds / len(block.question_ids), 1) if block.question_ids else 0,
        questions=question_results
    )


def _finalize_assessment(db: Session, assessment: SelfAssessment):
    """Calculate final scores and complete assessment."""
    # Get all blocks
    blocks = db.query(AssessmentBlock).filter(
        AssessmentBlock.assessment_id == assessment.id
    ).all()

    total_correct = sum(b.questions_correct or 0 for b in blocks)
    total_questions = sum(len(b.question_ids) for b in blocks)
    total_time = sum(b.time_spent_seconds or 0 for b in blocks)

    percentage = (total_correct / total_questions * 100) if total_questions > 0 else 0
    predicted_score = calculate_assessment_score(percentage)

    # Calculate performance by system
    performance_by_system = {}
    performance_by_difficulty = {"easy": [], "medium": [], "hard": []}

    for block in blocks:
        answers = block.answers or {}
        questions = db.query(Question).filter(
            Question.id.in_(block.question_ids)
        ).all()

        for q in questions:
            answer_data = answers.get(q.id, {})
            is_correct = answer_data.get("answer") == q.answer_key if answer_data.get("answer") else False

            # By system/source
            source = q.source or "Unknown"
            if source not in performance_by_system:
                performance_by_system[source] = []
            performance_by_system[source].append(1 if is_correct else 0)

            # By difficulty
            diff = q.difficulty_level or "medium"
            if diff in performance_by_difficulty:
                performance_by_difficulty[diff].append(1 if is_correct else 0)

    # Calculate averages
    for source, scores in performance_by_system.items():
        performance_by_system[source] = round(sum(scores) / len(scores) * 100, 1) if scores else 0

    for diff, scores in performance_by_difficulty.items():
        performance_by_difficulty[diff] = round(sum(scores) / len(scores) * 100, 1) if scores else 0

    # Calculate percentile
    percentile = calculate_percentile(db, percentage)

    # Update assessment
    assessment.status = "completed"
    assessment.completed_at = datetime.utcnow()
    assessment.total_time_seconds = total_time
    assessment.raw_score = total_correct
    assessment.percentage_score = round(percentage, 1)
    assessment.predicted_step2_score = predicted_score
    assessment.confidence_interval_low = max(190, predicted_score - 10)
    assessment.confidence_interval_high = min(300, predicted_score + 10)
    assessment.percentile_rank = percentile
    assessment.performance_by_system = performance_by_system
    assessment.performance_by_difficulty = performance_by_difficulty


# =============================================================================
# RESULTS ENDPOINTS
# =============================================================================

@router.get("/{assessment_id}/results", response_model=AssessmentResultsResponse)
def get_assessment_results(
    assessment_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get full results for a completed assessment.

    SECURITY: Requires authentication. Users can only view their own assessment results.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    assessment = db.query(SelfAssessment).filter(
        SelfAssessment.id == assessment_id,
        SelfAssessment.user_id == user_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.status != "completed":
        raise HTTPException(status_code=400, detail="Assessment not yet completed")

    # Get block results
    blocks = db.query(AssessmentBlock).filter(
        AssessmentBlock.assessment_id == assessment_id
    ).order_by(AssessmentBlock.block_number).all()

    block_results = []
    for block in blocks:
        questions = db.query(Question).filter(
            Question.id.in_(block.question_ids)
        ).all()
        q_map = {q.id: q for q in questions}

        answers = block.answers or {}
        question_details = []
        for qid in block.question_ids:
            q = q_map.get(qid)
            answer_data = answers.get(qid, {})
            question_details.append({
                "question_id": qid,
                "user_answer": answer_data.get("answer"),
                "correct_answer": q.answer_key if q else None,
                "is_correct": answer_data.get("answer") == q.answer_key if q and answer_data.get("answer") else False,
                "source": q.source if q else None
            })

        block_results.append(BlockResultsResponse(
            block_number=block.block_number,
            questions_total=len(block.question_ids),
            questions_answered=block.questions_answered,
            questions_correct=block.questions_correct or 0,
            accuracy=round((block.questions_correct or 0) / len(block.question_ids) * 100, 1) if block.question_ids else 0,
            time_spent_seconds=block.time_spent_seconds,
            avg_time_per_question=round(block.time_spent_seconds / len(block.question_ids), 1) if block.question_ids else 0,
            questions=question_details
        ))

    total_questions = assessment.total_blocks * assessment.questions_per_block

    # Generate readiness verdict
    if assessment.percentage_score >= 75:
        verdict = "Ready to Test"
    elif assessment.percentage_score >= 65:
        verdict = "Almost Ready"
    elif assessment.percentage_score >= 55:
        verdict = "Need More Preparation"
    else:
        verdict = "Significant Review Needed"

    # Generate recommendations
    recommendations = []
    perf_by_system = assessment.performance_by_system or {}
    weak_systems = [s for s, score in perf_by_system.items() if score < 60]

    if weak_systems:
        recommendations.append(f"Focus on weak areas: {', '.join(weak_systems[:3])}")

    if assessment.percentage_score < 70:
        recommendations.append("Consider completing more practice questions before your exam")

    perf_by_diff = assessment.performance_by_difficulty or {}
    if perf_by_diff.get("hard", 100) < 50:
        recommendations.append("Work on more challenging questions to improve score ceiling")

    if not recommendations:
        recommendations.append("Great performance! Maintain your study routine and stay confident")

    return AssessmentResultsResponse(
        id=assessment.id,
        name=assessment.name,
        status=assessment.status,
        total_questions=total_questions,
        questions_answered=assessment.raw_score + (total_questions - assessment.raw_score),  # Answered = correct + incorrect
        questions_correct=assessment.raw_score,
        raw_score=assessment.raw_score,
        percentage_score=assessment.percentage_score,
        predicted_step2_score=assessment.predicted_step2_score,
        confidence_interval_low=assessment.confidence_interval_low,
        confidence_interval_high=assessment.confidence_interval_high,
        percentile_rank=assessment.percentile_rank,
        total_time_seconds=assessment.total_time_seconds,
        avg_time_per_question=round(assessment.total_time_seconds / total_questions, 1) if total_questions > 0 else 0,
        performance_by_system=perf_by_system,
        performance_by_difficulty=perf_by_diff,
        blocks=block_results,
        readiness_verdict=verdict,
        recommendations=recommendations
    )


# =============================================================================
# COMPARISON ENDPOINTS
# =============================================================================

@router.get("/stats/comparison")
def get_assessment_stats(
    user_id: str = Query(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregate statistics for user's assessments compared to others.

    SECURITY: Requires authentication. Users can only view their own statistics.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    # User's assessments
    user_assessments = db.query(SelfAssessment).filter(
        SelfAssessment.user_id == user_id,
        SelfAssessment.status == "completed"
    ).all()

    if not user_assessments:
        return {
            "assessments_completed": 0,
            "avg_score": None,
            "best_score": None,
            "avg_percentile": None,
            "improvement_trend": None
        }

    scores = [a.percentage_score for a in user_assessments if a.percentage_score]
    percentiles = [a.percentile_rank for a in user_assessments if a.percentile_rank]

    # Calculate improvement trend
    if len(scores) >= 2:
        recent = sum(scores[-3:]) / len(scores[-3:])
        earlier = sum(scores[:3]) / len(scores[:3])
        trend = "improving" if recent > earlier + 2 else "declining" if recent < earlier - 2 else "stable"
    else:
        trend = "insufficient_data"

    return {
        "assessments_completed": len(user_assessments),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "best_score": max(scores) if scores else None,
        "avg_percentile": round(sum(percentiles) / len(percentiles)) if percentiles else None,
        "improvement_trend": trend
    }
