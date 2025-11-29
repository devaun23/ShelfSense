"""
Admin Router
Handles admin dashboard operations: user management, content management, and audit logs.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from app.database import get_db
from app.models.models import User, Question, QuestionAttempt, AdminAuditLog, ReviewQueue, FlaggedQuestion, generate_uuid
from app.routers.auth import get_admin_user, get_client_info
from app.services.openai_service import openai_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==================== Request/Response Models ====================

class UserListItem(BaseModel):
    user_id: str
    full_name: str
    email: str
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserListItem]
    total: int
    page: int
    per_page: int


class UserDetailResponse(BaseModel):
    user_id: str
    full_name: str
    first_name: str
    email: str
    is_admin: bool
    email_verified: bool
    target_score: Optional[int] = None
    exam_date: Optional[datetime] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    total_attempts: int
    accuracy: Optional[float] = None
    # Extended stats
    correct_attempts: int = 0
    attempts_last_7_days: int = 0
    attempts_last_30_days: int = 0
    streak_days: int = 0
    specialty_breakdown: Optional[dict] = None

    class Config:
        from_attributes = True


class UserAttemptItem(BaseModel):
    id: str
    question_id: str
    question_preview: str
    specialty: Optional[str] = None
    selected_answer: str
    is_correct: bool
    time_spent: Optional[int] = None
    created_at: datetime


class UserAttemptsResponse(BaseModel):
    attempts: List[UserAttemptItem]
    total: int
    page: int
    per_page: int


class ToggleAdminRequest(BaseModel):
    is_admin: bool


class QuestionListItem(BaseModel):
    id: str
    vignette_preview: str
    specialty: Optional[str] = None
    content_status: str
    quality_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionListResponse(BaseModel):
    questions: List[QuestionListItem]
    total: int
    page: int
    per_page: int


class QuestionUpdateRequest(BaseModel):
    vignette: Optional[str] = None
    answer_key: Optional[str] = None
    choices: Optional[dict] = None
    explanation: Optional[dict] = None
    specialty: Optional[str] = None
    content_status: Optional[str] = None
    difficulty_level: Optional[str] = None


# ==================== Moderation Queue Models ====================

class ModerationQueueItem(BaseModel):
    id: str
    question_id: str
    question_preview: str
    specialty: Optional[str] = None
    status: str
    priority: int
    submission_source: Optional[str] = None
    submitted_by_email: Optional[str] = None
    assigned_to_email: Optional[str] = None
    revision_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ModerationQueueResponse(BaseModel):
    items: List[ModerationQueueItem]
    total: int
    page: int
    per_page: int


class ModerationDetailResponse(BaseModel):
    id: str
    question_id: str
    question: dict  # Full question details
    status: str
    priority: int
    submission_source: Optional[str] = None
    submitted_by_email: Optional[str] = None
    assigned_to_email: Optional[str] = None
    decision: Optional[str] = None
    decision_notes: Optional[str] = None
    clinical_accuracy_score: Optional[int] = None
    question_clarity_score: Optional[int] = None
    distractor_quality_score: Optional[int] = None
    explanation_quality_score: Optional[int] = None
    revision_requested: bool
    revision_notes: Optional[str] = None
    revision_count: int
    created_at: datetime
    reviewed_at: Optional[datetime] = None


class ModerationDecisionRequest(BaseModel):
    decision: str  # "approve", "reject", "revise"
    decision_notes: Optional[str] = None
    clinical_accuracy_score: Optional[int] = None
    question_clarity_score: Optional[int] = None
    distractor_quality_score: Optional[int] = None
    explanation_quality_score: Optional[int] = None
    revision_notes: Optional[str] = None


class SubmitToQueueRequest(BaseModel):
    question_id: str
    priority: int = 5
    submission_source: Optional[str] = "admin"


# ==================== Flagged Questions Models ====================

class FlaggedQuestionItem(BaseModel):
    id: str
    question_id: str
    question_preview: str
    specialty: Optional[str] = None
    user_email: str
    flag_reason: Optional[str] = None
    custom_note: Optional[str] = None
    priority: int
    flagged_after_correct: Optional[bool] = None
    times_reviewed: int
    flagged_at: datetime

    class Config:
        from_attributes = True


class FlaggedQuestionsResponse(BaseModel):
    items: List[FlaggedQuestionItem]
    total: int
    page: int
    per_page: int


class FlaggedQuestionStats(BaseModel):
    total_flagged: int
    by_reason: dict
    by_specialty: dict
    most_flagged_questions: List[dict]


class AuditLogItem(BaseModel):
    id: str
    admin_email: str
    action_type: str
    target_type: str
    target_id: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    logs: List[AuditLogItem]
    total: int
    page: int
    per_page: int


class DashboardStatsResponse(BaseModel):
    total_users: int
    total_questions: int
    total_attempts: int
    active_users_7d: int
    questions_by_status: dict
    recent_activity: List[dict]


class MessageResponse(BaseModel):
    message: str


# ==================== Helper Functions ====================

import logging

logger = logging.getLogger(__name__)


def log_admin_action(
    db: Session,
    admin: User,
    action_type: str,
    target_type: str,
    target_id: str = None,
    previous_state: dict = None,
    new_state: dict = None,
    summary: str = None,
    ip_address: str = None,
    commit: bool = False
):
    """
    Log an admin action to the audit log.

    SECURITY: All admin actions should be logged for:
    - Compliance (HIPAA, FERPA audit trails)
    - Security incident investigation
    - Abuse detection

    Args:
        db: Database session
        admin: Admin user performing the action
        action_type: Type of action (e.g., "user:view", "content:edit")
        target_type: Type of target (e.g., "user", "question")
        target_id: ID of the target entity
        previous_state: State before the action (for modifications)
        new_state: State after the action (for modifications)
        summary: Human-readable summary of the action
        ip_address: Client IP address
        commit: Whether to commit the transaction (default False)
    """
    log = AdminAuditLog(
        id=generate_uuid(),
        admin_user_id=admin.id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        previous_state=previous_state,
        new_state=new_state,
        summary=summary,
        ip_address=ip_address
    )
    db.add(log)

    # Also log to application logger for real-time monitoring
    logger.info(
        f"ADMIN_AUDIT: action={action_type} admin={admin.email} "
        f"target={target_type}:{target_id or 'N/A'} ip={ip_address}"
    )

    if commit:
        db.commit()


def log_security_event(
    db: Session,
    event_type: str,
    details: dict,
    ip_address: str = None,
    user_id: str = None,
    severity: str = "warning"
):
    """
    Log a security event (failed access attempts, suspicious activity, etc.)

    SECURITY: Security events are logged for:
    - Failed authentication attempts
    - Unauthorized access attempts
    - Rate limit violations
    - Suspicious activity patterns
    """
    log = AdminAuditLog(
        id=generate_uuid(),
        admin_user_id=user_id,  # May be None for anonymous attempts
        action_type=f"security:{event_type}",
        target_type="security_event",
        target_id=None,
        previous_state=None,
        new_state=details,
        summary=f"Security event: {event_type}",
        ip_address=ip_address
    )
    db.add(log)
    db.commit()

    # Log to application logger at appropriate severity
    log_msg = f"SECURITY_EVENT: type={event_type} ip={ip_address} details={details}"
    if severity == "critical":
        logger.critical(log_msg)
    elif severity == "error":
        logger.error(log_msg)
    else:
        logger.warning(log_msg)


# ==================== Dashboard Endpoints ====================

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics overview"""
    from datetime import timedelta

    # Total counts
    total_users = db.query(func.count(User.id)).scalar()
    total_questions = db.query(func.count(Question.id)).scalar()
    total_attempts = db.query(func.count(QuestionAttempt.id)).scalar()

    # Active users in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_users_7d = db.query(func.count(User.id)).filter(
        User.last_login >= week_ago
    ).scalar()

    # Questions by status
    status_counts = db.query(
        Question.content_status,
        func.count(Question.id)
    ).group_by(Question.content_status).all()

    questions_by_status = {status: count for status, count in status_counts}

    # Recent admin activity
    recent_logs = db.query(AdminAuditLog).order_by(
        desc(AdminAuditLog.created_at)
    ).limit(10).all()

    recent_activity = []
    for log in recent_logs:
        admin_user = db.query(User).filter(User.id == log.admin_user_id).first()
        recent_activity.append({
            "action": log.action_type,
            "admin": admin_user.email if admin_user else "Unknown",
            "target": f"{log.target_type}:{log.target_id}" if log.target_id else log.target_type,
            "summary": log.summary,
            "timestamp": log.created_at.isoformat()
        })

    return DashboardStatsResponse(
        total_users=total_users or 0,
        total_questions=total_questions or 0,
        total_attempts=total_attempts or 0,
        active_users_7d=active_users_7d or 0,
        questions_by_status=questions_by_status,
        recent_activity=recent_activity
    )


# ==================== User Management Endpoints ====================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all users with filtering and pagination"""
    query = db.query(User)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_term)) |
            (User.email.ilike(search_term))
        )

    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)

    total = query.count()

    users = query.order_by(desc(User.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return UserListResponse(
        users=[
            UserListItem(
                user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                is_admin=u.is_admin or False,
                created_at=u.created_at,
                last_login=u.last_login
            )
            for u in users
        ],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    from datetime import timedelta

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # SECURITY: Log access to user PII data
    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="user:view_detail",
        target_type="user",
        target_id=user_id,
        summary=f"Viewed user details for {user.email}",
        ip_address=ip,
        commit=True
    )

    # Get attempt stats
    total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id
    ).scalar() or 0

    correct_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else None

    # Get attempts in last 7 and 30 days
    now = datetime.utcnow()
    attempts_last_7_days = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.created_at >= now - timedelta(days=7)
    ).scalar() or 0

    attempts_last_30_days = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.created_at >= now - timedelta(days=30)
    ).scalar() or 0

    # Get specialty breakdown
    specialty_stats = db.query(
        Question.specialty,
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, db.bind.dialect.type_descriptor(type(1)))).label('correct')
    ).join(Question, QuestionAttempt.question_id == Question.id).filter(
        QuestionAttempt.user_id == user_id
    ).group_by(Question.specialty).all()

    specialty_breakdown = {}
    for stat in specialty_stats:
        if stat.specialty:
            specialty_breakdown[stat.specialty] = {
                'total': stat.total,
                'correct': stat.correct or 0,
                'accuracy': round((stat.correct or 0) / stat.total * 100, 1) if stat.total > 0 else 0
            }

    # Calculate streak (consecutive days with attempts)
    streak_days = 0
    if total_attempts > 0:
        # Get distinct dates of attempts in descending order
        attempt_dates = db.query(
            func.date(QuestionAttempt.created_at).label('date')
        ).filter(
            QuestionAttempt.user_id == user_id
        ).distinct().order_by(desc('date')).limit(90).all()

        if attempt_dates:
            today = now.date()
            current_date = today
            for row in attempt_dates:
                attempt_date = row.date
                if attempt_date == current_date or attempt_date == current_date - timedelta(days=1):
                    streak_days += 1
                    current_date = attempt_date - timedelta(days=1)
                else:
                    break

    return UserDetailResponse(
        user_id=user.id,
        full_name=user.full_name,
        first_name=user.first_name,
        email=user.email,
        is_admin=user.is_admin or False,
        email_verified=user.email_verified or False,
        target_score=user.target_score,
        exam_date=user.exam_date,
        created_at=user.created_at,
        last_login=user.last_login,
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        accuracy=accuracy,
        attempts_last_7_days=attempts_last_7_days,
        attempts_last_30_days=attempts_last_30_days,
        streak_days=streak_days,
        specialty_breakdown=specialty_breakdown if specialty_breakdown else None
    )


@router.get("/users/{user_id}/attempts", response_model=UserAttemptsResponse)
async def get_user_attempts(
    user_id: str,
    req: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get a user's question attempts with pagination"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # SECURITY: Log access to user learning history
    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="user:view_attempts",
        target_type="user",
        target_id=user_id,
        summary=f"Viewed attempts for {user.email} (page {page})",
        ip_address=ip,
        commit=True
    )

    # Get total count
    total = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id
    ).scalar() or 0

    # Get paginated attempts with question info
    offset = (page - 1) * per_page
    attempts = db.query(QuestionAttempt, Question).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).order_by(desc(QuestionAttempt.created_at)).offset(offset).limit(per_page).all()

    attempt_items = []
    for attempt, question in attempts:
        attempt_items.append(UserAttemptItem(
            id=attempt.id,
            question_id=attempt.question_id,
            question_preview=question.vignette[:150] + "..." if len(question.vignette) > 150 else question.vignette,
            specialty=question.specialty,
            selected_answer=attempt.selected_answer,
            is_correct=attempt.is_correct,
            time_spent=attempt.time_spent,
            created_at=attempt.created_at
        ))

    return UserAttemptsResponse(
        attempts=attempt_items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.put("/users/{user_id}/admin", response_model=MessageResponse)
async def toggle_user_admin(
    user_id: str,
    request: ToggleAdminRequest,
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle a user's admin status"""
    if user_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own admin status"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_status = user.is_admin
    user.is_admin = request.is_admin

    # Log the action
    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="user:role_change",
        target_type="user",
        target_id=user_id,
        previous_state={"is_admin": old_status},
        new_state={"is_admin": request.is_admin},
        summary=f"Changed admin status from {old_status} to {request.is_admin}",
        ip_address=ip
    )

    db.commit()

    action = "granted" if request.is_admin else "revoked"
    return MessageResponse(message=f"Admin access {action} for {user.email}")


# ==================== Content Management Endpoints ====================

@router.get("/questions", response_model=QuestionListResponse)
async def list_questions(
    search: Optional[str] = Query(None, description="Search in vignette"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    content_status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List questions with filtering and pagination"""
    query = db.query(Question)

    if search:
        query = query.filter(Question.vignette.ilike(f"%{search}%"))

    if specialty:
        query = query.filter(Question.specialty == specialty)

    if content_status:
        query = query.filter(Question.content_status == content_status)

    total = query.count()

    questions = query.order_by(desc(Question.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return QuestionListResponse(
        questions=[
            QuestionListItem(
                id=q.id,
                vignette_preview=q.vignette[:200] + "..." if len(q.vignette) > 200 else q.vignette,
                specialty=q.specialty,
                content_status=q.content_status or "active",
                quality_score=q.quality_score,
                created_at=q.created_at
            )
            for q in questions
        ],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/questions/{question_id}")
async def get_question_detail(
    question_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed question information"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Get attempt stats
    total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.question_id == question_id
    ).scalar() or 0

    correct_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.question_id == question_id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    return {
        "id": question.id,
        "vignette": question.vignette,
        "answer_key": question.answer_key,
        "choices": question.choices,
        "explanation": question.explanation,
        "specialty": question.specialty,
        "source": question.source,
        "content_status": question.content_status,
        "difficulty_level": question.difficulty_level,
        "quality_score": question.quality_score,
        "expert_reviewed": question.expert_reviewed,
        "created_at": question.created_at,
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "accuracy": (correct_attempts / total_attempts * 100) if total_attempts > 0 else None
    }


@router.put("/questions/{question_id}", response_model=MessageResponse)
async def update_question(
    question_id: str,
    request: QuestionUpdateRequest,
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update a question"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Track changes for audit
    changes = {}

    if request.vignette is not None:
        changes["vignette"] = {"old": question.vignette[:100], "new": request.vignette[:100]}
        question.vignette = request.vignette

    if request.answer_key is not None:
        changes["answer_key"] = {"old": question.answer_key, "new": request.answer_key}
        question.answer_key = request.answer_key

    if request.choices is not None:
        changes["choices"] = {"old": "updated", "new": "updated"}
        question.choices = request.choices

    if request.explanation is not None:
        changes["explanation"] = {"old": "updated", "new": "updated"}
        question.explanation = request.explanation

    if request.specialty is not None:
        changes["specialty"] = {"old": question.specialty, "new": request.specialty}
        question.specialty = request.specialty

    if request.content_status is not None:
        changes["content_status"] = {"old": question.content_status, "new": request.content_status}
        question.content_status = request.content_status

    if request.difficulty_level is not None:
        changes["difficulty_level"] = {"old": question.difficulty_level, "new": request.difficulty_level}
        question.difficulty_level = request.difficulty_level

    question.last_edited_by = admin.id
    question.last_edited_at = datetime.utcnow()

    # Log the action
    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="content:edit",
        target_type="question",
        target_id=question_id,
        previous_state={"changes": changes},
        new_state={"fields_updated": list(changes.keys())},
        summary=f"Updated fields: {', '.join(changes.keys())}",
        ip_address=ip
    )

    db.commit()

    return MessageResponse(message=f"Question updated successfully")


@router.delete("/questions/{question_id}", response_model=MessageResponse)
async def delete_question(
    question_id: str,
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a question (archives it by setting status to 'deleted')"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    old_status = question.content_status
    question.content_status = "deleted"
    question.last_edited_by = admin.id
    question.last_edited_at = datetime.utcnow()

    # Log the action
    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="content:delete",
        target_type="question",
        target_id=question_id,
        previous_state={"content_status": old_status},
        new_state={"content_status": "deleted"},
        summary=f"Deleted question (archived)",
        ip_address=ip
    )

    db.commit()

    return MessageResponse(message="Question deleted (archived)")


# ==================== Audit Log Endpoints ====================

@router.get("/audit", response_model=AuditLogResponse)
async def get_audit_logs(
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin audit logs"""
    query = db.query(AdminAuditLog)

    if action_type:
        query = query.filter(AdminAuditLog.action_type == action_type)

    if target_type:
        query = query.filter(AdminAuditLog.target_type == target_type)

    total = query.count()

    logs = query.order_by(desc(AdminAuditLog.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    log_items = []
    for log in logs:
        admin_user = db.query(User).filter(User.id == log.admin_user_id).first()
        log_items.append(AuditLogItem(
            id=log.id,
            admin_email=admin_user.email if admin_user else "Unknown",
            action_type=log.action_type,
            target_type=log.target_type,
            target_id=log.target_id,
            summary=log.summary,
            created_at=log.created_at
        ))

    return AuditLogResponse(
        logs=log_items,
        total=total,
        page=page,
        per_page=per_page
    )


# ==================== OpenAI Service Health Endpoints ====================

class OpenAIStatusResponse(BaseModel):
    circuit_breaker: dict
    retry_metrics: dict
    recent_performance: dict
    service_info: dict


@router.get("/openai-status", response_model=OpenAIStatusResponse)
async def get_openai_status(
    admin: User = Depends(get_admin_user)
):
    """
    Get OpenAI service status including circuit breaker state and metrics.

    Returns:
        - circuit_breaker: State, failure count, thresholds
        - retry_metrics: Total calls, successful, retried, failed
        - recent_performance: Success rate and average latency
        - service_info: Configuration details
    """
    status = openai_service.get_status()
    return OpenAIStatusResponse(**status)


@router.post("/openai-reset-circuit", response_model=MessageResponse)
async def reset_circuit_breaker(
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Manually reset the OpenAI circuit breaker to CLOSED state.

    Use with caution - this should only be used for emergency recovery
    when the circuit breaker is stuck open but OpenAI is actually available.
    """
    # Get current state for logging
    current_state = openai_service.get_status()["circuit_breaker"]["state"]

    # Reset the circuit breaker
    openai_service.reset_circuit_breaker()

    # Log the admin action
    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="service:reset_circuit_breaker",
        target_type="openai_service",
        target_id=None,
        previous_state={"circuit_state": current_state},
        new_state={"circuit_state": "closed"},
        summary=f"Manually reset circuit breaker from {current_state} to closed",
        ip_address=ip
    )
    db.commit()

    return MessageResponse(
        message=f"Circuit breaker reset from '{current_state}' to 'closed'. "
                "OpenAI requests will now be attempted."
    )


# ==================== Moderation Queue Endpoints ====================

@router.get("/moderation", response_model=ModerationQueueResponse)
async def get_moderation_queue(
    status: Optional[str] = Query(None, description="Filter by status: pending, in_review, approved, rejected, needs_revision"),
    priority: Optional[int] = Query(None, ge=1, le=10, description="Filter by priority (1=highest, 10=lowest)"),
    submission_source: Optional[str] = Query(None, description="Filter by source: ai_generated, community, import, admin"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get content moderation queue with filtering and pagination"""
    from sqlalchemy.orm import joinedload

    query = db.query(ReviewQueue).options(
        joinedload(ReviewQueue.question),
        joinedload(ReviewQueue.submitter),
        joinedload(ReviewQueue.assignee)
    )

    if status:
        query = query.filter(ReviewQueue.status == status)
    if priority:
        query = query.filter(ReviewQueue.priority == priority)
    if submission_source:
        query = query.filter(ReviewQueue.submission_source == submission_source)

    total = query.count()

    items = query.order_by(
        ReviewQueue.priority.asc(),
        ReviewQueue.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    queue_items = []
    for item in items:
        question_preview = item.question.vignette[:150] + "..." if item.question and len(item.question.vignette) > 150 else (item.question.vignette if item.question else "")
        queue_items.append(ModerationQueueItem(
            id=item.id,
            question_id=item.question_id,
            question_preview=question_preview,
            specialty=item.question.specialty if item.question else None,
            status=item.status,
            priority=item.priority,
            submission_source=item.submission_source,
            submitted_by_email=item.submitter.email if item.submitter else None,
            assigned_to_email=item.assignee.email if item.assignee else None,
            revision_count=item.revision_count,
            created_at=item.created_at
        ))

    return ModerationQueueResponse(
        items=queue_items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/moderation/{item_id}", response_model=ModerationDetailResponse)
async def get_moderation_item(
    item_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a moderation queue item"""
    from sqlalchemy.orm import joinedload

    item = db.query(ReviewQueue).options(
        joinedload(ReviewQueue.question),
        joinedload(ReviewQueue.submitter),
        joinedload(ReviewQueue.assignee),
        joinedload(ReviewQueue.reviewer)
    ).filter(ReviewQueue.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Moderation item not found")

    question_data = {}
    if item.question:
        question_data = {
            "id": item.question.id,
            "vignette": item.question.vignette,
            "answer_key": item.question.answer_key,
            "choices": item.question.choices,
            "explanation": item.question.explanation,
            "specialty": item.question.specialty,
            "difficulty_level": item.question.difficulty_level,
            "content_status": item.question.content_status,
            "quality_score": item.question.quality_score,
        }

    return ModerationDetailResponse(
        id=item.id,
        question_id=item.question_id,
        question=question_data,
        status=item.status,
        priority=item.priority,
        submission_source=item.submission_source,
        submitted_by_email=item.submitter.email if item.submitter else None,
        assigned_to_email=item.assignee.email if item.assignee else None,
        decision=item.decision,
        decision_notes=item.decision_notes,
        clinical_accuracy_score=item.clinical_accuracy_score,
        question_clarity_score=item.question_clarity_score,
        distractor_quality_score=item.distractor_quality_score,
        explanation_quality_score=item.explanation_quality_score,
        revision_requested=item.revision_requested,
        revision_notes=item.revision_notes,
        revision_count=item.revision_count,
        created_at=item.created_at,
        reviewed_at=item.reviewed_at
    )


@router.post("/moderation", response_model=MessageResponse)
async def submit_to_moderation(
    request: SubmitToQueueRequest,
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Submit a question to the moderation queue"""
    # Check if question exists
    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if already in queue
    existing = db.query(ReviewQueue).filter(
        ReviewQueue.question_id == request.question_id,
        ReviewQueue.status.in_(["pending", "in_review"])
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Question is already in the moderation queue")

    # Create queue item
    queue_item = ReviewQueue(
        id=generate_uuid(),
        question_id=request.question_id,
        status="pending",
        priority=request.priority,
        submission_source=request.submission_source,
        submitted_by=admin.id,
        created_at=datetime.utcnow()
    )
    db.add(queue_item)

    # Update question status
    question.content_status = "pending_review"

    # Log action
    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="moderation:submit",
        target_type="question",
        target_id=request.question_id,
        previous_state={"content_status": question.content_status},
        new_state={"moderation_status": "pending", "priority": request.priority},
        summary=f"Submitted question to moderation queue",
        ip_address=ip
    )

    db.commit()

    return MessageResponse(message="Question submitted to moderation queue")


@router.put("/moderation/{item_id}/assign", response_model=MessageResponse)
async def assign_moderation_item(
    item_id: str,
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Assign a moderation item to yourself"""
    item = db.query(ReviewQueue).filter(ReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Moderation item not found")

    if item.status not in ["pending", "needs_revision"]:
        raise HTTPException(status_code=400, detail=f"Cannot assign item with status '{item.status}'")

    item.assigned_to = admin.id
    item.assigned_at = datetime.utcnow()
    item.status = "in_review"

    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type="moderation:assign",
        target_type="review_queue",
        target_id=item_id,
        previous_state={"status": "pending"},
        new_state={"status": "in_review", "assigned_to": admin.email},
        summary=f"Assigned moderation item to self",
        ip_address=ip
    )

    db.commit()

    return MessageResponse(message="Item assigned to you for review")


@router.put("/moderation/{item_id}/decision", response_model=MessageResponse)
async def make_moderation_decision(
    item_id: str,
    request: ModerationDecisionRequest,
    req: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Make a decision on a moderation item (approve, reject, or request revision)"""
    item = db.query(ReviewQueue).filter(ReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Moderation item not found")

    if request.decision not in ["approve", "reject", "revise"]:
        raise HTTPException(status_code=400, detail="Invalid decision. Must be 'approve', 'reject', or 'revise'")

    # Update review queue item
    item.decision = request.decision
    item.decision_notes = request.decision_notes
    item.reviewed_by = admin.id
    item.reviewed_at = datetime.utcnow()

    # Set quality scores if provided
    if request.clinical_accuracy_score:
        item.clinical_accuracy_score = request.clinical_accuracy_score
    if request.question_clarity_score:
        item.question_clarity_score = request.question_clarity_score
    if request.distractor_quality_score:
        item.distractor_quality_score = request.distractor_quality_score
    if request.explanation_quality_score:
        item.explanation_quality_score = request.explanation_quality_score

    # Update status based on decision
    if request.decision == "approve":
        item.status = "approved"
        # Update question to active
        question = db.query(Question).filter(Question.id == item.question_id).first()
        if question:
            question.content_status = "active"
            question.expert_reviewed = True
            # Calculate quality score from reviewer scores
            scores = [s for s in [item.clinical_accuracy_score, item.question_clarity_score,
                                   item.distractor_quality_score, item.explanation_quality_score] if s]
            if scores:
                question.quality_score = sum(scores) / len(scores) * 20  # Convert 1-5 to 0-100

    elif request.decision == "reject":
        item.status = "rejected"
        question = db.query(Question).filter(Question.id == item.question_id).first()
        if question:
            question.content_status = "archived"

    elif request.decision == "revise":
        item.status = "needs_revision"
        item.revision_requested = True
        item.revision_notes = request.revision_notes
        item.revision_count += 1
        question = db.query(Question).filter(Question.id == item.question_id).first()
        if question:
            question.content_status = "draft"

    ip, _ = get_client_info(req)
    log_admin_action(
        db=db,
        admin=admin,
        action_type=f"moderation:{request.decision}",
        target_type="review_queue",
        target_id=item_id,
        previous_state={"status": "in_review"},
        new_state={"status": item.status, "decision": request.decision},
        summary=f"Made moderation decision: {request.decision}",
        ip_address=ip
    )

    db.commit()

    return MessageResponse(message=f"Decision recorded: {request.decision}")


# ==================== Flagged Questions Endpoints ====================

@router.get("/flagged", response_model=FlaggedQuestionsResponse)
async def get_flagged_questions(
    flag_reason: Optional[str] = Query(None, description="Filter by flag reason"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    question_id: Optional[str] = Query(None, description="Filter by question ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all flagged questions across all users with filtering"""
    from sqlalchemy.orm import joinedload

    query = db.query(FlaggedQuestion).options(
        joinedload(FlaggedQuestion.question),
        joinedload(FlaggedQuestion.user)
    )

    if flag_reason:
        query = query.filter(FlaggedQuestion.flag_reason == flag_reason)
    if specialty:
        query = query.join(Question).filter(Question.specialty == specialty)
    if question_id:
        query = query.filter(FlaggedQuestion.question_id == question_id)

    # Only show active flags (not mastered/resolved)
    query = query.filter(FlaggedQuestion.review_mastered == False)

    total = query.count()

    items = query.order_by(
        desc(FlaggedQuestion.flagged_at)
    ).offset((page - 1) * per_page).limit(per_page).all()

    flagged_items = []
    for item in items:
        question_preview = item.question.vignette[:150] + "..." if item.question and len(item.question.vignette) > 150 else (item.question.vignette if item.question else "")
        flagged_items.append(FlaggedQuestionItem(
            id=item.id,
            question_id=item.question_id,
            question_preview=question_preview,
            specialty=item.question.specialty if item.question else None,
            user_email=item.user.email if item.user else "Unknown",
            flag_reason=item.flag_reason,
            custom_note=item.custom_note,
            priority=item.priority,
            flagged_after_correct=item.flagged_after_correct,
            times_reviewed=item.times_reviewed,
            flagged_at=item.flagged_at
        ))

    return FlaggedQuestionsResponse(
        items=flagged_items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/flagged/stats", response_model=FlaggedQuestionStats)
async def get_flagged_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get statistics about flagged questions"""
    # Total count
    total_flagged = db.query(func.count(FlaggedQuestion.id)).filter(
        FlaggedQuestion.review_mastered == False
    ).scalar() or 0

    # By reason
    reason_counts = db.query(
        FlaggedQuestion.flag_reason,
        func.count(FlaggedQuestion.id).label('count')
    ).filter(
        FlaggedQuestion.review_mastered == False
    ).group_by(FlaggedQuestion.flag_reason).all()

    by_reason = {r.flag_reason or 'no_reason': r.count for r in reason_counts}

    # By specialty
    specialty_counts = db.query(
        Question.specialty,
        func.count(FlaggedQuestion.id).label('count')
    ).join(Question, FlaggedQuestion.question_id == Question.id).filter(
        FlaggedQuestion.review_mastered == False
    ).group_by(Question.specialty).all()

    by_specialty = {s.specialty or 'unknown': s.count for s in specialty_counts}

    # Most flagged questions (top 10)
    most_flagged = db.query(
        FlaggedQuestion.question_id,
        Question.vignette,
        Question.specialty,
        func.count(FlaggedQuestion.id).label('flag_count')
    ).join(Question, FlaggedQuestion.question_id == Question.id).filter(
        FlaggedQuestion.review_mastered == False
    ).group_by(
        FlaggedQuestion.question_id, Question.vignette, Question.specialty
    ).order_by(desc('flag_count')).limit(10).all()

    most_flagged_questions = [
        {
            'question_id': q.question_id,
            'preview': q.vignette[:100] + "..." if len(q.vignette) > 100 else q.vignette,
            'specialty': q.specialty,
            'flag_count': q.flag_count
        }
        for q in most_flagged
    ]

    return FlaggedQuestionStats(
        total_flagged=total_flagged,
        by_reason=by_reason,
        by_specialty=by_specialty,
        most_flagged_questions=most_flagged_questions
    )


@router.get("/flagged/question/{question_id}")
async def get_question_flags(
    question_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all flags for a specific question"""
    from sqlalchemy.orm import joinedload

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    flags = db.query(FlaggedQuestion).options(
        joinedload(FlaggedQuestion.user)
    ).filter(
        FlaggedQuestion.question_id == question_id,
        FlaggedQuestion.review_mastered == False
    ).order_by(desc(FlaggedQuestion.flagged_at)).all()

    return {
        "question": {
            "id": question.id,
            "vignette": question.vignette,
            "answer_key": question.answer_key,
            "choices": question.choices,
            "explanation": question.explanation,
            "specialty": question.specialty,
            "difficulty_level": question.difficulty_level,
            "content_status": question.content_status,
        },
        "flags": [
            {
                "id": f.id,
                "user_email": f.user.email if f.user else "Unknown",
                "flag_reason": f.flag_reason,
                "custom_note": f.custom_note,
                "priority": f.priority,
                "flagged_after_correct": f.flagged_after_correct,
                "times_reviewed": f.times_reviewed,
                "flagged_at": f.flagged_at.isoformat()
            }
            for f in flags
        ],
        "total_flags": len(flags)
    }
