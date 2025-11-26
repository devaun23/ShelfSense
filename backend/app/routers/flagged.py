"""
Flagged Questions Router

API endpoints for question flagging/marking system.
Allows users to mark questions for later review.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.models import FlaggedQuestion, Question, QuestionAttempt


router = APIRouter(prefix="/api/flagged", tags=["flagged"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FlagQuestionRequest(BaseModel):
    question_id: str
    flag_reason: Optional[str] = None  # "review_concept", "tricky_wording", "high_yield", "uncertain", "custom"
    custom_note: Optional[str] = None
    attempt_id: Optional[str] = None  # Link to the attempt when flagging
    flagged_after_correct: Optional[bool] = None
    folder: Optional[str] = None
    priority: Optional[int] = 1  # 1-3


class UpdateFlagRequest(BaseModel):
    flag_reason: Optional[str] = None
    custom_note: Optional[str] = None
    folder: Optional[str] = None
    priority: Optional[int] = None
    review_mastered: Optional[bool] = None


class FlaggedQuestionResponse(BaseModel):
    id: str
    question_id: str
    flag_reason: Optional[str]
    custom_note: Optional[str]
    flagged_after_correct: Optional[bool]
    folder: Optional[str]
    priority: int
    times_reviewed: int
    last_reviewed_at: Optional[str]
    review_mastered: bool
    flagged_at: str
    question: Optional[Dict[str, Any]] = None


class FlaggedListResponse(BaseModel):
    total: int
    flagged: List[FlaggedQuestionResponse]
    folders: List[str]
    stats: Dict[str, Any]


# =============================================================================
# FLAG QUESTION ENDPOINTS
# =============================================================================

@router.post("/flag")
def flag_question(
    user_id: str,
    request: FlagQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Flag a question for later review.

    If the question is already flagged, update the existing flag.
    """
    # Check if already flagged
    existing = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.question_id == request.question_id,
        FlaggedQuestion.review_mastered == False
    ).first()

    if existing:
        # Update existing flag
        if request.flag_reason:
            existing.flag_reason = request.flag_reason
        if request.custom_note:
            existing.custom_note = request.custom_note
        if request.folder:
            existing.folder = request.folder
        if request.priority:
            existing.priority = request.priority
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)

        return {
            "success": True,
            "action": "updated",
            "flag_id": existing.id,
            "message": "Flag updated"
        }

    # Create new flag
    flag = FlaggedQuestion(
        user_id=user_id,
        question_id=request.question_id,
        flag_reason=request.flag_reason,
        custom_note=request.custom_note,
        attempt_id=request.attempt_id,
        flagged_after_correct=request.flagged_after_correct,
        folder=request.folder,
        priority=request.priority or 1
    )

    db.add(flag)
    db.commit()
    db.refresh(flag)

    return {
        "success": True,
        "action": "created",
        "flag_id": flag.id,
        "message": "Question flagged for review"
    }


@router.delete("/unflag")
def unflag_question(
    user_id: str,
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove flag from a question.
    """
    flag = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.question_id == question_id,
        FlaggedQuestion.review_mastered == False
    ).first()

    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    db.delete(flag)
    db.commit()

    return {
        "success": True,
        "message": "Question unflagged"
    }


@router.get("/check/{question_id}")
def check_if_flagged(
    user_id: str,
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a specific question is flagged by the user.
    """
    flag = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.question_id == question_id,
        FlaggedQuestion.review_mastered == False
    ).first()

    if flag:
        return {
            "is_flagged": True,
            "flag_id": flag.id,
            "flag_reason": flag.flag_reason,
            "custom_note": flag.custom_note,
            "folder": flag.folder,
            "priority": flag.priority,
            "flagged_at": flag.flagged_at.isoformat()
        }

    return {"is_flagged": False}


@router.put("/update/{flag_id}")
def update_flag(
    flag_id: str,
    user_id: str,
    request: UpdateFlagRequest,
    db: Session = Depends(get_db)
):
    """
    Update an existing flag.
    """
    flag = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.id == flag_id,
        FlaggedQuestion.user_id == user_id
    ).first()

    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    if request.flag_reason is not None:
        flag.flag_reason = request.flag_reason
    if request.custom_note is not None:
        flag.custom_note = request.custom_note
    if request.folder is not None:
        flag.folder = request.folder
    if request.priority is not None:
        flag.priority = request.priority
    if request.review_mastered is not None:
        flag.review_mastered = request.review_mastered

    flag.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(flag)

    return {
        "success": True,
        "message": "Flag updated",
        "flag": {
            "id": flag.id,
            "flag_reason": flag.flag_reason,
            "custom_note": flag.custom_note,
            "folder": flag.folder,
            "priority": flag.priority,
            "review_mastered": flag.review_mastered
        }
    }


# =============================================================================
# LIST FLAGGED QUESTIONS
# =============================================================================

@router.get("/list")
def list_flagged_questions(
    user_id: str,
    folder: Optional[str] = None,
    reason: Optional[str] = None,
    priority: Optional[int] = None,
    include_mastered: bool = False,
    sort_by: str = Query(default="flagged_at", description="Sort: flagged_at, priority, times_reviewed"),
    sort_order: str = Query(default="desc", description="Sort order: asc or desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get list of flagged questions for a user.

    Supports filtering by folder, reason, priority.
    """
    query = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id
    )

    # Filter by mastered status
    if not include_mastered:
        query = query.filter(FlaggedQuestion.review_mastered == False)

    # Apply filters
    if folder:
        query = query.filter(FlaggedQuestion.folder == folder)
    if reason:
        query = query.filter(FlaggedQuestion.flag_reason == reason)
    if priority:
        query = query.filter(FlaggedQuestion.priority == priority)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(FlaggedQuestion, sort_by, FlaggedQuestion.flagged_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    flagged = query.offset(offset).limit(limit).all()

    # Get question details for each flag
    result = []
    for flag in flagged:
        question = db.query(Question).filter(Question.id == flag.question_id).first()

        flag_data = {
            "id": flag.id,
            "question_id": flag.question_id,
            "flag_reason": flag.flag_reason,
            "custom_note": flag.custom_note,
            "flagged_after_correct": flag.flagged_after_correct,
            "folder": flag.folder,
            "priority": flag.priority,
            "times_reviewed": flag.times_reviewed,
            "last_reviewed_at": flag.last_reviewed_at.isoformat() if flag.last_reviewed_at else None,
            "review_mastered": flag.review_mastered,
            "flagged_at": flag.flagged_at.isoformat()
        }

        if question:
            flag_data["question"] = {
                "id": question.id,
                "vignette": question.vignette[:200] + "..." if len(question.vignette) > 200 else question.vignette,
                "source": question.source,
                "specialty": question.specialty,
                "difficulty_level": question.difficulty_level
            }

        result.append(flag_data)

    # Get unique folders for this user
    folders = db.query(FlaggedQuestion.folder).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.folder.isnot(None)
    ).distinct().all()
    folder_list = [f[0] for f in folders if f[0]]

    # Get stats
    stats = {
        "total_flagged": total,
        "by_reason": {},
        "by_priority": {},
        "by_folder": {}
    }

    # Count by reason
    reason_counts = db.query(
        FlaggedQuestion.flag_reason,
        func.count(FlaggedQuestion.id)
    ).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False
    ).group_by(FlaggedQuestion.flag_reason).all()

    for r, count in reason_counts:
        stats["by_reason"][r or "none"] = count

    # Count by priority
    priority_counts = db.query(
        FlaggedQuestion.priority,
        func.count(FlaggedQuestion.id)
    ).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False
    ).group_by(FlaggedQuestion.priority).all()

    for p, count in priority_counts:
        stats["by_priority"][str(p)] = count

    return {
        "total": total,
        "flagged": result,
        "folders": folder_list,
        "stats": stats
    }


# =============================================================================
# FLAGGED QUESTIONS REVIEW SESSION
# =============================================================================

@router.get("/review-session")
def get_flagged_review_session(
    user_id: str,
    count: int = Query(default=20, ge=1, le=100),
    folder: Optional[str] = None,
    priority: Optional[int] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get a batch of flagged questions for a review session.

    Returns question IDs prioritized by:
    1. Higher priority flags first
    2. Questions not reviewed recently
    3. Questions reviewed fewer times
    """
    query = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False
    )

    # Apply filters
    if folder:
        query = query.filter(FlaggedQuestion.folder == folder)
    if priority:
        query = query.filter(FlaggedQuestion.priority == priority)
    if reason:
        query = query.filter(FlaggedQuestion.flag_reason == reason)

    # Sort by priority (desc), times_reviewed (asc), last_reviewed_at (asc/null first)
    query = query.order_by(
        FlaggedQuestion.priority.desc(),
        FlaggedQuestion.times_reviewed.asc(),
        FlaggedQuestion.last_reviewed_at.asc().nullsfirst()
    )

    flagged = query.limit(count).all()

    # Get question IDs and full question data
    question_ids = [f.question_id for f in flagged]

    questions = []
    for flag in flagged:
        question = db.query(Question).filter(Question.id == flag.question_id).first()
        if question:
            questions.append({
                "flag_id": flag.id,
                "question_id": question.id,
                "flag_reason": flag.flag_reason,
                "custom_note": flag.custom_note,
                "priority": flag.priority,
                "question": {
                    "id": question.id,
                    "vignette": question.vignette,
                    "choices": question.choices,
                    "answer_key": question.answer_key,
                    "explanation": question.explanation,
                    "source": question.source,
                    "specialty": question.specialty
                }
            })

    return {
        "count": len(questions),
        "total_available": query.count(),
        "questions": questions
    }


@router.post("/mark-reviewed/{flag_id}")
def mark_flag_reviewed(
    flag_id: str,
    user_id: str,
    mastered: bool = False,
    db: Session = Depends(get_db)
):
    """
    Mark a flagged question as reviewed.

    Optionally mark as mastered to remove from future review sessions.
    """
    flag = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.id == flag_id,
        FlaggedQuestion.user_id == user_id
    ).first()

    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    flag.times_reviewed += 1
    flag.last_reviewed_at = datetime.utcnow()

    if mastered:
        flag.review_mastered = True

    db.commit()

    return {
        "success": True,
        "times_reviewed": flag.times_reviewed,
        "review_mastered": flag.review_mastered
    }


# =============================================================================
# STATS & SUMMARY
# =============================================================================

@router.get("/stats")
def get_flagged_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for flagged questions.
    """
    # Total active flags
    total_active = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False
    ).count()

    # Total mastered
    total_mastered = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == True
    ).count()

    # By reason
    by_reason = {}
    reason_counts = db.query(
        FlaggedQuestion.flag_reason,
        func.count(FlaggedQuestion.id)
    ).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False
    ).group_by(FlaggedQuestion.flag_reason).all()

    for r, count in reason_counts:
        by_reason[r or "no_reason"] = count

    # By specialty (need to join with Question)
    by_specialty = {}
    specialty_counts = db.query(
        Question.specialty,
        func.count(FlaggedQuestion.id)
    ).join(
        Question, FlaggedQuestion.question_id == Question.id
    ).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False
    ).group_by(Question.specialty).all()

    for s, count in specialty_counts:
        by_specialty[s or "unknown"] = count

    # Flags that were correct vs incorrect when flagged
    correct_when_flagged = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False,
        FlaggedQuestion.flagged_after_correct == True
    ).count()

    incorrect_when_flagged = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False,
        FlaggedQuestion.flagged_after_correct == False
    ).count()

    # Never reviewed
    never_reviewed = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False,
        FlaggedQuestion.times_reviewed == 0
    ).count()

    # High priority (3)
    high_priority = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.review_mastered == False,
        FlaggedQuestion.priority == 3
    ).count()

    return {
        "total_active": total_active,
        "total_mastered": total_mastered,
        "never_reviewed": never_reviewed,
        "high_priority": high_priority,
        "correct_when_flagged": correct_when_flagged,
        "incorrect_when_flagged": incorrect_when_flagged,
        "by_reason": by_reason,
        "by_specialty": by_specialty
    }


# =============================================================================
# FOLDER MANAGEMENT
# =============================================================================

@router.get("/folders")
def get_folders(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all folders used by the user for organizing flags.
    """
    folders = db.query(
        FlaggedQuestion.folder,
        func.count(FlaggedQuestion.id)
    ).filter(
        FlaggedQuestion.user_id == user_id,
        FlaggedQuestion.folder.isnot(None),
        FlaggedQuestion.review_mastered == False
    ).group_by(FlaggedQuestion.folder).all()

    return {
        "folders": [
            {"name": f[0], "count": f[1]}
            for f in folders
        ]
    }


@router.put("/move-to-folder")
def move_to_folder(
    user_id: str,
    flag_ids: List[str],
    folder: Optional[str],
    db: Session = Depends(get_db)
):
    """
    Move multiple flags to a folder (or remove from folder if folder is None).
    """
    updated = db.query(FlaggedQuestion).filter(
        FlaggedQuestion.id.in_(flag_ids),
        FlaggedQuestion.user_id == user_id
    ).update({"folder": folder}, synchronize_session=False)

    db.commit()

    return {
        "success": True,
        "updated_count": updated,
        "folder": folder
    }
