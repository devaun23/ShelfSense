"""
StudySync AI - Curriculum Upload and Personalization API

Endpoints for uploading lecture slides, NBME reports, and getting
personalized study recommendations based on curriculum alignment.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.dependencies.auth import get_current_user, verify_user_access
from app.models.models import User, CurriculumUpload, CurriculumTopic, UserStudyFocus
from app.services.curriculum_sync_service import curriculum_sync_service, escape_like_pattern

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


# ============================================================================
# Response Models
# ============================================================================

class UploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    topics_found: int
    topics: List[str]
    message: str

    class Config:
        from_attributes = True


class TopicDetail(BaseModel):
    topic: str
    specialty: Optional[str]
    questions_available: int
    completed: int
    accuracy: float
    mastery: str
    is_high_yield: bool


class StudyFocusSummary(BaseModel):
    has_focus: bool
    focus_specialty: Optional[str] = None
    focus_topics: List[str] = []
    weak_areas: List[str] = []
    daily_target: int = 40
    topic_stats: List[TopicDetail] = []
    message: Optional[str] = None


class PersonalizedQuestionsRequest(BaseModel):
    count: int = 10
    specialty: Optional[str] = None


# ============================================================================
# Upload Endpoints
# ============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_curriculum_file(
    file: UploadFile = File(...),
    context: Optional[str] = Form(None),  # "lecture", "syllabus", "nbme_report", "notes"
    course_name: Optional[str] = Form(None),
    week_number: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a lecture slide, PDF, or NBME score report for AI analysis.

    The AI will:
    1. Extract text from the document
    2. Identify medical topics covered
    3. Match topics to available questions
    4. Update your personalized study focus

    Supported file types: PDF, PPTX, DOCX, PNG, JPG
    Maximum size: 10MB
    """
    # Read file content
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        upload = await curriculum_sync_service.process_upload(
            db=db,
            user_id=current_user.id,
            file_content=content,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            upload_context=context,
            course_name=course_name,
            week_number=week_number
        )

        topics = upload.ai_extracted_topics or []

        if upload.status == "completed":
            message = f"Successfully extracted {len(topics)} topics from your {context or 'document'}."
            if context == "nbme_report":
                message += " Your weak areas have been identified and will be prioritized."
        else:
            message = f"Processing failed: {upload.error_message}"

        return UploadResponse(
            id=upload.id,
            filename=upload.filename,
            status=upload.status,
            topics_found=len(topics),
            topics=topics[:20],  # Return first 20 topics
            message=message
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process upload")


@router.get("/uploads")
async def list_uploads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100)
):
    """
    List user's curriculum uploads.
    """
    uploads = db.query(CurriculumUpload).filter(
        CurriculumUpload.user_id == current_user.id
    ).order_by(CurriculumUpload.created_at.desc()).limit(limit).all()

    return {
        "uploads": [
            {
                "id": u.id,
                "filename": u.filename,
                "file_type": u.file_type,
                "status": u.status,
                "context": u.upload_context,
                "course_name": u.course_name,
                "topics_found": len(u.ai_extracted_topics or []),
                "uploaded_at": u.created_at.isoformat(),
                "processed_at": u.processed_at.isoformat() if u.processed_at else None
            }
            for u in uploads
        ]
    }


@router.get("/uploads/{upload_id}")
async def get_upload_detail(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific upload including extracted topics.
    """
    upload = db.query(CurriculumUpload).filter(
        CurriculumUpload.id == upload_id
    ).first()

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    verify_user_access(current_user, upload.user_id)

    # Get associated topics
    topics = db.query(CurriculumTopic).filter(
        CurriculumTopic.upload_id == upload_id
    ).all()

    return {
        "id": upload.id,
        "filename": upload.filename,
        "file_type": upload.file_type,
        "status": upload.status,
        "context": upload.upload_context,
        "course_name": upload.course_name,
        "week_number": upload.week_number,
        "uploaded_at": upload.created_at.isoformat(),
        "processed_at": upload.processed_at.isoformat() if upload.processed_at else None,
        "error_message": upload.error_message,
        "topics": [
            {
                "id": t.id,
                "topic_name": t.topic_name,
                "specialty": t.specialty,
                "subsystem": t.subsystem,
                "confidence": t.confidence_score,
                "is_high_yield": t.is_high_yield,
                "questions_available": t.matched_question_count,
                "questions_completed": t.questions_completed,
                "questions_correct": t.questions_correct,
                "mastery_status": t.mastery_status
            }
            for t in topics
        ]
    }


@router.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an upload and its associated topics.
    """
    upload = db.query(CurriculumUpload).filter(
        CurriculumUpload.id == upload_id
    ).first()

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    verify_user_access(current_user, upload.user_id)

    db.delete(upload)
    db.commit()

    return {"message": "Upload deleted successfully"}


# ============================================================================
# Study Focus Endpoints
# ============================================================================

@router.get("/focus", response_model=StudyFocusSummary)
async def get_study_focus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current study focus derived from curriculum uploads.
    Includes topic statistics and recommendations.
    """
    summary = curriculum_sync_service.get_study_focus_summary(db, current_user.id)

    if not summary.get("has_focus"):
        return StudyFocusSummary(
            has_focus=False,
            message=summary.get("message", "Upload content to get personalized study recommendations")
        )

    return StudyFocusSummary(
        has_focus=True,
        focus_specialty=summary.get("focus_specialty"),
        focus_topics=summary.get("focus_topics", []),
        weak_areas=summary.get("weak_areas", []),
        daily_target=summary.get("daily_target", 40),
        topic_stats=[
            TopicDetail(**stat) for stat in summary.get("topic_stats", [])
        ]
    )


@router.post("/focus/reset")
async def reset_study_focus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset user's study focus (deactivate current focus).
    """
    focus = db.query(UserStudyFocus).filter(
        UserStudyFocus.user_id == current_user.id,
        UserStudyFocus.is_active == True
    ).first()

    if focus:
        focus.is_active = False
        db.commit()

    return {"message": "Study focus has been reset"}


@router.put("/focus/settings")
async def update_focus_settings(
    daily_target: int = Query(ge=5, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update study focus settings (daily question target, etc).
    """
    focus = db.query(UserStudyFocus).filter(
        UserStudyFocus.user_id == current_user.id,
        UserStudyFocus.is_active == True
    ).first()

    if not focus:
        raise HTTPException(status_code=404, detail="No active study focus. Upload content first.")

    focus.daily_question_target = daily_target
    db.commit()

    return {"message": f"Daily target updated to {daily_target} questions"}


# ============================================================================
# Personalized Questions Endpoints
# ============================================================================

@router.get("/questions")
async def get_personalized_questions(
    count: int = Query(default=10, ge=1, le=50),
    specialty: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get questions personalized to user's study focus.

    Questions are selected based on:
    - 50% from weak areas (if NBME report uploaded)
    - 30% from current focus topics (from lectures/syllabi)
    - 20% from spaced repetition review
    """
    questions = curriculum_sync_service.get_personalized_questions(
        db=db,
        user_id=current_user.id,
        count=count,
        specialty_filter=specialty
    )

    return {
        "questions": [
            {
                "id": q.id,
                "vignette": q.vignette,
                "choices": q.choices,
                "specialty": q.specialty,
                "difficulty": q.difficulty_level
            }
            for q in questions
        ],
        "count": len(questions),
        "personalized": True if len(questions) > 0 else False
    }


# ============================================================================
# Topics Endpoints
# ============================================================================

@router.get("/topics")
async def list_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    specialty: Optional[str] = None,
    mastery: Optional[str] = None,  # "not_started", "learning", "mastered"
    limit: int = Query(default=50, le=200)
):
    """
    List all topics extracted from user's uploads.
    """
    query = db.query(CurriculumTopic).filter(
        CurriculumTopic.user_id == current_user.id
    )

    if specialty:
        # SECURITY: Escape ILIKE pattern to prevent injection
        safe_specialty = escape_like_pattern(specialty)
        query = query.filter(CurriculumTopic.specialty.ilike(f"%{safe_specialty}%"))

    if mastery:
        query = query.filter(CurriculumTopic.mastery_status == mastery)

    topics = query.order_by(
        CurriculumTopic.is_high_yield.desc(),
        CurriculumTopic.created_at.desc()
    ).limit(limit).all()

    return {
        "topics": [
            {
                "id": t.id,
                "topic_name": t.topic_name,
                "specialty": t.specialty,
                "subsystem": t.subsystem,
                "is_high_yield": t.is_high_yield,
                "questions_available": t.matched_question_count,
                "questions_completed": t.questions_completed,
                "accuracy": (t.questions_correct / t.questions_completed * 100) if t.questions_completed > 0 else 0,
                "mastery_status": t.mastery_status,
                "upload_id": t.upload_id
            }
            for t in topics
        ],
        "count": len(topics)
    }


@router.get("/topics/{topic_id}/questions")
async def get_topic_questions(
    topic_id: str,
    count: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get questions for a specific topic.
    """
    topic = db.query(CurriculumTopic).filter(
        CurriculumTopic.id == topic_id
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    verify_user_access(current_user, topic.user_id)

    questions = curriculum_sync_service._get_topic_questions(
        db=db,
        user_id=current_user.id,
        topics=[topic.topic_name],
        count=count,
        specialty_filter=topic.specialty
    )

    return {
        "topic": topic.topic_name,
        "questions": [
            {
                "id": q.id,
                "vignette": q.vignette,
                "choices": q.choices,
                "specialty": q.specialty,
                "difficulty": q.difficulty_level
            }
            for q in questions
        ],
        "count": len(questions)
    }
