"""
Content Management API Router for ShelfSense
Provides endpoints for:
- Question CRUD operations
- Rating/approval system
- Feedback collection
- Quality filtering
- Source tracking
- Community contributions
- Expert review pipeline
- Content freshness management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.services.content_management_agent import (
    ContentManagementAgent,
    ContentStatus,
    SourceType,
    ReviewStatus
)

router = APIRouter(prefix="/api/content", tags=["content-management"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateQuestionRequest(BaseModel):
    vignette: str = Field(..., min_length=50, description="Clinical vignette text")
    choices: List[str] = Field(..., min_items=5, max_items=5, description="5 answer choices")
    answer_key: str = Field(..., pattern="^[A-E]$", description="Correct answer (A-E)")
    explanation: Optional[Dict[str, Any]] = Field(None, description="Structured explanation")
    source: Optional[str] = Field(None, description="Source reference")
    source_type: Optional[str] = Field(SourceType.AI_GENERATED, description="Source type")
    specialty: Optional[str] = Field(None, description="Medical specialty")
    difficulty_level: Optional[str] = Field(None, description="easy, medium, or hard")
    submit_for_review: bool = Field(False, description="Submit to review queue")


class UpdateQuestionRequest(BaseModel):
    vignette: Optional[str] = None
    choices: Optional[List[str]] = None
    answer_key: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    specialty: Optional[str] = None
    difficulty_level: Optional[str] = None
    change_reason: Optional[str] = None


class QuestionResponse(BaseModel):
    id: str
    vignette: str
    choices: List[str]
    answer_key: str
    explanation: Optional[Dict[str, Any]]
    source: Optional[str]
    source_type: Optional[str]
    specialty: Optional[str]
    difficulty_level: Optional[str]
    content_status: str
    quality_score: Optional[float]
    expert_reviewed: bool
    version: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class RateQuestionRequest(BaseModel):
    rating: bool = Field(..., description="True = approve, False = reject")
    feedback_text: Optional[str] = Field(None, description="Optional feedback")


class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="quality, accuracy, clarity, difficulty, other")
    feedback_text: str = Field(..., min_length=10, description="Detailed feedback")
    severity: Optional[str] = Field(None, description="minor, major, critical")


class CommunitySubmissionRequest(BaseModel):
    vignette: str = Field(..., min_length=50)
    choices: List[str] = Field(..., min_items=5, max_items=5)
    answer_key: str = Field(..., pattern="^[A-E]$")
    explanation: Optional[Dict[str, Any]] = None
    specialty: Optional[str] = None
    source_reference: Optional[str] = None
    is_original: bool = True


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="approve, reject, or revise")
    clinical_accuracy_score: int = Field(..., ge=1, le=5)
    question_clarity_score: int = Field(..., ge=1, le=5)
    distractor_quality_score: int = Field(..., ge=1, le=5)
    explanation_quality_score: int = Field(..., ge=1, le=5)
    decision_notes: Optional[str] = None
    revision_notes: Optional[str] = None


class RegisterExpertRequest(BaseModel):
    specialties: List[str] = Field(..., min_items=1)
    credentials: Optional[str] = None
    institution: Optional[str] = None
    years_experience: Optional[int] = None


class BulkImportRequest(BaseModel):
    questions: List[Dict[str, Any]]
    source_type: str = SourceType.IMPORTED
    submit_for_review: bool = True


class BulkStatusUpdateRequest(BaseModel):
    question_ids: List[str]
    new_status: str


# ============================================================================
# QUESTION CRUD ENDPOINTS
# ============================================================================

@router.post("/questions", response_model=QuestionResponse, status_code=201)
def create_question(
    request: CreateQuestionRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Create a new question with content management tracking."""
    agent = ContentManagementAgent(db, user_id)

    question = agent.create_question(
        vignette=request.vignette,
        choices=request.choices,
        answer_key=request.answer_key,
        explanation=request.explanation,
        source=request.source,
        source_type=request.source_type,
        specialty=request.specialty,
        difficulty_level=request.difficulty_level,
        submit_for_review=request.submit_for_review
    )

    return question


@router.get("/questions/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get a question by ID."""
    agent = ContentManagementAgent(db)
    question = agent.get_question(question_id)

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return question


@router.put("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: str,
    request: UpdateQuestionRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Update a question with version tracking."""
    agent = ContentManagementAgent(db, user_id)

    updates = {k: v for k, v in request.dict().items() if v is not None and k != "change_reason"}

    question = agent.update_question(
        question_id=question_id,
        updates=updates,
        change_reason=request.change_reason
    )

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return question


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: str,
    hard_delete: bool = Query(False, description="Permanently delete instead of archive"),
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Delete (archive) a question."""
    agent = ContentManagementAgent(db, user_id)

    success = agent.delete_question(question_id, hard_delete=hard_delete)

    if not success:
        raise HTTPException(status_code=404, detail="Question not found")

    return {"success": True, "action": "deleted" if hard_delete else "archived"}


@router.post("/questions/{question_id}/restore", response_model=QuestionResponse)
def restore_question(
    question_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Restore an archived question."""
    agent = ContentManagementAgent(db, user_id)

    question = agent.restore_question(question_id)

    if not question:
        raise HTTPException(status_code=404, detail="Question not found or not archived")

    return question


@router.get("/questions")
def list_questions(
    content_status: Optional[str] = Query(None, description="Filter by status"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty"),
    expert_reviewed: Optional[bool] = Query(None, description="Filter by expert review status"),
    rejected: Optional[bool] = Query(None, description="Filter by rejection status"),
    min_quality_score: Optional[float] = Query(None, description="Minimum quality score"),
    search: Optional[str] = Query(None, description="Search in vignette text"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="asc or desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List questions with filtering and pagination."""
    agent = ContentManagementAgent(db)

    filters = {
        "content_status": content_status,
        "source_type": source_type,
        "specialty": specialty,
        "difficulty_level": difficulty_level,
        "expert_reviewed": expert_reviewed,
        "rejected": rejected,
        "min_quality_score": min_quality_score,
        "search": search
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    questions, total = agent.list_questions(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

    return {
        "questions": [
            {
                "id": q.id,
                "vignette": q.vignette[:200] + "..." if len(q.vignette) > 200 else q.vignette,
                "specialty": q.specialty,
                "source_type": q.source_type,
                "content_status": q.content_status,
                "quality_score": q.quality_score,
                "expert_reviewed": q.expert_reviewed
            }
            for q in questions
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


# ============================================================================
# RATING ENDPOINTS
# ============================================================================

@router.post("/questions/{question_id}/rate")
def rate_question(
    question_id: str,
    request: RateQuestionRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Rate a question (approve/reject)."""
    agent = ContentManagementAgent(db, user_id)

    rating = agent.rate_question(
        question_id=question_id,
        rating=request.rating,
        feedback_text=request.feedback_text
    )

    return {
        "success": True,
        "rating_id": rating.id,
        "action": "approved" if request.rating else "rejected"
    }


@router.get("/questions/{question_id}/ratings")
def get_question_ratings(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get rating summary for a question."""
    agent = ContentManagementAgent(db)
    return agent.get_question_ratings(question_id)


# ============================================================================
# FEEDBACK ENDPOINTS
# ============================================================================

@router.post("/questions/{question_id}/feedback")
def submit_feedback(
    question_id: str,
    request: FeedbackRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Submit detailed feedback about a question."""
    agent = ContentManagementAgent(db, user_id)

    result = agent.collect_feedback(
        question_id=question_id,
        feedback_type=request.feedback_type,
        feedback_text=request.feedback_text,
        severity=request.severity
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@router.get("/questions/{question_id}/feedback")
def get_feedback_summary(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get feedback summary for a question."""
    agent = ContentManagementAgent(db)
    return agent.get_feedback_summary(question_id)


# ============================================================================
# QUALITY ENDPOINTS
# ============================================================================

@router.post("/questions/{question_id}/calculate-quality")
def calculate_quality_score(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Calculate/recalculate quality score for a question."""
    agent = ContentManagementAgent(db)
    score = agent.calculate_quality_score(question_id)
    return {"question_id": question_id, "quality_score": score}


@router.get("/quality-filtered")
def get_quality_filtered_questions(
    min_score: float = Query(70.0, description="Minimum quality score"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get questions filtered by quality score."""
    agent = ContentManagementAgent(db)

    questions = agent.get_quality_filtered_questions(
        min_score=min_score,
        specialty=specialty,
        limit=limit
    )

    return {
        "questions": [
            {
                "id": q.id,
                "vignette": q.vignette[:200] + "..." if len(q.vignette) > 200 else q.vignette,
                "specialty": q.specialty,
                "quality_score": q.quality_score
            }
            for q in questions
        ],
        "count": len(questions)
    }


# ============================================================================
# SOURCE TRACKING ENDPOINTS
# ============================================================================

@router.get("/sources/{source_type}")
def get_content_by_source(
    source_type: str,
    db: Session = Depends(get_db)
):
    """Get content statistics by source type."""
    agent = ContentManagementAgent(db)
    return agent.get_content_by_source(source_type)


@router.get("/sources/comparison")
def get_source_comparison(
    db: Session = Depends(get_db)
):
    """Compare quality metrics across different sources."""
    agent = ContentManagementAgent(db)
    return agent.get_source_comparison()


@router.put("/questions/{question_id}/source")
def update_source_type(
    question_id: str,
    source_type: str = Query(..., description="New source type"),
    source_reference: Optional[str] = Query(None, description="Source reference"),
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Update the source type for a question."""
    agent = ContentManagementAgent(db, user_id)

    question = agent.update_source_type(
        question_id=question_id,
        source_type=source_type,
        source_reference=source_reference
    )

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return {"success": True, "source_type": source_type}


# ============================================================================
# COMMUNITY CONTRIBUTION ENDPOINTS
# ============================================================================

@router.post("/community/submit")
def submit_community_question(
    request: CommunitySubmissionRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Submit a community-contributed question for review."""
    agent = ContentManagementAgent(db, user_id)

    contribution = agent.submit_community_question(
        vignette=request.vignette,
        choices=request.choices,
        answer_key=request.answer_key,
        explanation=request.explanation,
        specialty=request.specialty,
        source_reference=request.source_reference,
        is_original=request.is_original
    )

    return {
        "success": True,
        "contribution_id": contribution.id,
        "status": contribution.status
    }


@router.get("/community/contributions")
def list_community_contributions(
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[str] = Query(None, description="Filter by contributor"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List community contributions."""
    agent = ContentManagementAgent(db)

    contributions = agent.get_community_contributions(
        status=status,
        user_id=user_id,
        limit=limit
    )

    return {
        "contributions": [
            {
                "id": c.id,
                "vignette": c.vignette[:200] + "..." if len(c.vignette) > 200 else c.vignette,
                "specialty": c.specialty,
                "status": c.status,
                "submitted_by": c.submitted_by,
                "created_at": c.created_at.isoformat()
            }
            for c in contributions
        ],
        "count": len(contributions)
    }


@router.post("/community/{contribution_id}/approve")
def approve_community_contribution(
    contribution_id: str,
    reviewer_feedback: Optional[str] = Query(None),
    user_id: str = Query(..., description="Reviewer user ID"),
    db: Session = Depends(get_db)
):
    """Approve a community contribution and create a question."""
    agent = ContentManagementAgent(db, user_id)

    question, contribution = agent.approve_community_contribution(
        contribution_id=contribution_id,
        reviewer_feedback=reviewer_feedback
    )

    if not question:
        raise HTTPException(status_code=404, detail="Contribution not found")

    return {
        "success": True,
        "question_id": question.id,
        "contribution_id": contribution.id
    }


@router.post("/community/{contribution_id}/reject")
def reject_community_contribution(
    contribution_id: str,
    reviewer_feedback: str = Query(..., description="Required feedback for rejection"),
    user_id: str = Query(..., description="Reviewer user ID"),
    db: Session = Depends(get_db)
):
    """Reject a community contribution with feedback."""
    agent = ContentManagementAgent(db, user_id)

    contribution = agent.reject_community_contribution(
        contribution_id=contribution_id,
        reviewer_feedback=reviewer_feedback
    )

    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    return {"success": True, "contribution_id": contribution.id}


# ============================================================================
# EXPERT REVIEW ENDPOINTS
# ============================================================================

@router.get("/review-queue")
def get_review_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get items in the expert review queue."""
    agent = ContentManagementAgent(db)

    return agent.get_review_queue(
        status=status,
        specialty=specialty,
        assigned_to=assigned_to,
        limit=limit
    )


@router.post("/review-queue/{review_id}/assign")
def assign_reviewer(
    review_id: str,
    reviewer_id: str = Query(..., description="Expert reviewer user ID"),
    user_id: str = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Assign an expert reviewer to a review item."""
    agent = ContentManagementAgent(db, user_id)

    review = agent.assign_reviewer(
        review_id=review_id,
        reviewer_id=reviewer_id
    )

    if not review:
        raise HTTPException(status_code=404, detail="Review not found or reviewer not valid")

    return {"success": True, "review_id": review.id, "assigned_to": reviewer_id}


@router.post("/review-queue/{review_id}/submit")
def submit_review(
    review_id: str,
    request: ReviewDecisionRequest,
    user_id: str = Query(..., description="Reviewer user ID"),
    db: Session = Depends(get_db)
):
    """Submit an expert review decision."""
    agent = ContentManagementAgent(db, user_id)

    review = agent.submit_review(
        review_id=review_id,
        decision=request.decision,
        clinical_accuracy_score=request.clinical_accuracy_score,
        question_clarity_score=request.question_clarity_score,
        distractor_quality_score=request.distractor_quality_score,
        explanation_quality_score=request.explanation_quality_score,
        decision_notes=request.decision_notes,
        revision_notes=request.revision_notes
    )

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return {
        "success": True,
        "review_id": review.id,
        "decision": request.decision,
        "status": review.status
    }


@router.post("/experts/register")
def register_expert(
    request: RegisterExpertRequest,
    user_id: str = Query(..., description="User ID to register as expert"),
    db: Session = Depends(get_db)
):
    """Register a user as an expert reviewer."""
    agent = ContentManagementAgent(db)

    expert = agent.register_expert_reviewer(
        user_id=user_id,
        specialties=request.specialties,
        credentials=request.credentials,
        institution=request.institution,
        years_experience=request.years_experience
    )

    return {
        "success": True,
        "expert_id": expert.id,
        "user_id": user_id,
        "specialties": expert.specialties
    }


@router.get("/experts/available")
def get_available_reviewers(
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    db: Session = Depends(get_db)
):
    """Get available expert reviewers."""
    agent = ContentManagementAgent(db)
    return agent.get_available_reviewers(specialty=specialty)


# ============================================================================
# FRESHNESS ENDPOINTS
# ============================================================================

@router.post("/questions/{question_id}/freshness")
def calculate_freshness_score(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Calculate freshness score for a question."""
    agent = ContentManagementAgent(db)
    score = agent.calculate_freshness_score(question_id)
    return {"question_id": question_id, "freshness_score": score}


@router.get("/stale-content")
def get_stale_content(
    threshold: float = Query(50.0, description="Freshness threshold"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get content that needs attention due to low freshness."""
    agent = ContentManagementAgent(db)
    return agent.get_stale_content(threshold=threshold, limit=limit)


@router.post("/questions/{question_id}/refresh")
def refresh_content(
    question_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Mark content as refreshed/updated."""
    agent = ContentManagementAgent(db, user_id)
    agent.refresh_content(question_id)
    return {"success": True, "question_id": question_id}


@router.post("/freshness/batch-refresh")
def batch_refresh_freshness_scores(
    db: Session = Depends(get_db)
):
    """Batch update freshness scores for all questions."""
    agent = ContentManagementAgent(db)
    return agent.batch_refresh_freshness_scores()


# ============================================================================
# BULK OPERATION ENDPOINTS
# ============================================================================

@router.post("/bulk/import")
def bulk_import_questions(
    request: BulkImportRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Bulk import questions from structured data."""
    agent = ContentManagementAgent(db, user_id)

    return agent.bulk_import_questions(
        questions_data=request.questions,
        source_type=request.source_type,
        submit_for_review=request.submit_for_review
    )


@router.post("/bulk/status-update")
def bulk_update_status(
    request: BulkStatusUpdateRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Bulk update content status for multiple questions."""
    agent = ContentManagementAgent(db, user_id)

    return agent.bulk_update_status(
        question_ids=request.question_ids,
        new_status=request.new_status
    )


@router.get("/export")
def export_questions(
    content_status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Export questions matching filters."""
    agent = ContentManagementAgent(db, user_id)

    filters = {
        "content_status": content_status,
        "source_type": source_type,
        "specialty": specialty
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    return agent.export_questions(filters=filters)


# ============================================================================
# AUDIT & ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/audit-log")
def get_audit_log(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get audit log entries."""
    agent = ContentManagementAgent(db)

    return agent.get_audit_log(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit
    )


@router.get("/dashboard")
def get_content_dashboard(
    db: Session = Depends(get_db)
):
    """Get comprehensive content management dashboard data."""
    agent = ContentManagementAgent(db)
    return agent.get_content_dashboard()


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/status-options")
def get_status_options():
    """Get available content status options."""
    return {
        "content_status": [
            ContentStatus.DRAFT,
            ContentStatus.PENDING_REVIEW,
            ContentStatus.ACTIVE,
            ContentStatus.ARCHIVED
        ],
        "source_types": [
            SourceType.NBME,
            SourceType.AI_GENERATED,
            SourceType.COMMUNITY,
            SourceType.IMPORTED
        ],
        "review_status": [
            ReviewStatus.PENDING,
            ReviewStatus.IN_REVIEW,
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.NEEDS_REVISION
        ]
    }
