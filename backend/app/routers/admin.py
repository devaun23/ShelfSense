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
from app.models.models import User, Question, QuestionAttempt, AdminAuditLog, generate_uuid
from app.routers.auth import get_admin_user, get_client_info

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

    class Config:
        from_attributes = True


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

def log_admin_action(
    db: Session,
    admin: User,
    action_type: str,
    target_type: str,
    target_id: str = None,
    previous_state: dict = None,
    new_state: dict = None,
    summary: str = None,
    ip_address: str = None
):
    """Log an admin action to the audit log"""
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
    # Caller handles commit


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
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get attempt stats
    total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id
    ).scalar() or 0

    correct_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else None

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
        accuracy=accuracy
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
