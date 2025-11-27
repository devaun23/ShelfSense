"""
Profile Router
Handles user profile management, settings, and preferences.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models.models import User, UserSettings
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ==================== Request/Response Models ====================

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None


class TargetUpdateRequest(BaseModel):
    target_score: int = Field(..., ge=200, le=280)


class ExamDateUpdateRequest(BaseModel):
    exam_date: datetime


class SettingsUpdateRequest(BaseModel):
    # Study preferences
    show_timer: Optional[bool] = None
    keyboard_shortcuts: Optional[bool] = None
    questions_per_session: Optional[int] = Field(None, ge=5, le=100)
    auto_advance: Optional[bool] = None

    # Notifications
    email_notifications: Optional[bool] = None
    daily_reminder: Optional[bool] = None
    reminder_time: Optional[str] = None  # "HH:MM" format

    # Display
    theme: Optional[str] = None  # "dark", "light", "system"
    font_size: Optional[str] = None  # "small", "medium", "large"


class ProfileResponse(BaseModel):
    user_id: str
    full_name: str
    first_name: str
    email: str
    email_verified: bool
    target_score: Optional[int] = None
    exam_date: Optional[datetime] = None
    avatar_url: Optional[str] = None
    is_admin: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SettingsResponse(BaseModel):
    # Study preferences
    show_timer: bool
    keyboard_shortcuts: bool
    questions_per_session: int
    auto_advance: bool

    # Notifications
    email_notifications: bool
    daily_reminder: bool
    reminder_time: Optional[str] = None

    # Display
    theme: str
    font_size: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str


class ExamCountdownResponse(BaseModel):
    exam_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    target_score: Optional[int] = None


# ==================== Profile Endpoints ====================

@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile"""
    return ProfileResponse(
        user_id=current_user.id,
        full_name=current_user.full_name,
        first_name=current_user.first_name,
        email=current_user.email,
        email_verified=current_user.email_verified or False,
        target_score=current_user.target_score,
        exam_date=current_user.exam_date,
        avatar_url=current_user.avatar_url,
        is_admin=current_user.is_admin or False,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put("/me", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Update fields if provided
    if request.full_name is not None:
        current_user.full_name = request.full_name
        current_user.first_name = request.full_name.strip().split(' ')[0]

    if request.email is not None and request.email != current_user.email:
        # Check if email is taken
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = request.email
        current_user.email_verified = False  # Reset verification

    db.commit()
    db.refresh(current_user)

    return ProfileResponse(
        user_id=current_user.id,
        full_name=current_user.full_name,
        first_name=current_user.first_name,
        email=current_user.email,
        email_verified=current_user.email_verified or False,
        target_score=current_user.target_score,
        exam_date=current_user.exam_date,
        avatar_url=current_user.avatar_url,
        is_admin=current_user.is_admin or False,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put("/me/target", response_model=MessageResponse)
async def update_target_score(
    request: TargetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update target Step 2 CK score (200-280)"""
    current_user.target_score = request.target_score
    db.commit()

    return MessageResponse(message=f"Target score set to {request.target_score}")


@router.put("/me/exam-date", response_model=MessageResponse)
async def update_exam_date(
    request: ExamDateUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update exam date"""
    if request.exam_date < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam date must be in the future"
        )

    current_user.exam_date = request.exam_date
    db.commit()

    return MessageResponse(message="Exam date updated successfully")


@router.get("/me/countdown", response_model=ExamCountdownResponse)
async def get_exam_countdown(
    current_user: User = Depends(get_current_user)
):
    """Get exam countdown and target score"""
    days_remaining = None
    if current_user.exam_date:
        delta = current_user.exam_date - datetime.utcnow()
        days_remaining = max(0, delta.days)

    return ExamCountdownResponse(
        exam_date=current_user.exam_date,
        days_remaining=days_remaining,
        target_score=current_user.target_score
    )


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account and all associated data.
    This action is irreversible.
    """
    # Delete user (cascades will handle related records)
    db.delete(current_user)
    db.commit()

    return MessageResponse(message="Account deleted successfully")


# ==================== Settings Endpoints ====================

@router.get("/me/settings", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not settings:
        # Create default settings if they don't exist
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return SettingsResponse(
        show_timer=settings.show_timer,
        keyboard_shortcuts=settings.keyboard_shortcuts,
        questions_per_session=settings.questions_per_session,
        auto_advance=settings.auto_advance,
        email_notifications=settings.email_notifications,
        daily_reminder=settings.daily_reminder,
        reminder_time=settings.reminder_time,
        theme=settings.theme,
        font_size=settings.font_size
    )


@router.put("/me/settings", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    # Update only provided fields
    if request.show_timer is not None:
        settings.show_timer = request.show_timer

    if request.keyboard_shortcuts is not None:
        settings.keyboard_shortcuts = request.keyboard_shortcuts

    if request.questions_per_session is not None:
        settings.questions_per_session = request.questions_per_session

    if request.auto_advance is not None:
        settings.auto_advance = request.auto_advance

    if request.email_notifications is not None:
        settings.email_notifications = request.email_notifications

    if request.daily_reminder is not None:
        settings.daily_reminder = request.daily_reminder

    if request.reminder_time is not None:
        # Validate time format
        try:
            datetime.strptime(request.reminder_time, "%H:%M")
            settings.reminder_time = request.reminder_time
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time format. Use HH:MM (e.g., 09:00)"
            )

    if request.theme is not None:
        if request.theme not in ["dark", "light", "system"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid theme. Use 'dark', 'light', or 'system'"
            )
        settings.theme = request.theme

    if request.font_size is not None:
        if request.font_size not in ["small", "medium", "large"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid font size. Use 'small', 'medium', or 'large'"
            )
        settings.font_size = request.font_size

    db.commit()
    db.refresh(settings)

    return SettingsResponse(
        show_timer=settings.show_timer,
        keyboard_shortcuts=settings.keyboard_shortcuts,
        questions_per_session=settings.questions_per_session,
        auto_advance=settings.auto_advance,
        email_notifications=settings.email_notifications,
        daily_reminder=settings.daily_reminder,
        reminder_time=settings.reminder_time,
        theme=settings.theme,
        font_size=settings.font_size
    )


# ==================== Data Export (GDPR) ====================

@router.get("/me/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all user data (GDPR compliance).
    Returns a JSON object with all user-related data.
    """
    from app.models.models import (
        QuestionAttempt, UserPerformance, ScheduledReview,
        ChatMessage, QuestionRating, ErrorAnalysis
    )

    # Get user profile
    profile = {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "target_score": current_user.target_score,
        "exam_date": current_user.exam_date.isoformat() if current_user.exam_date else None,
        "created_at": current_user.created_at.isoformat(),
    }

    # Get settings
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    settings_data = None
    if settings:
        settings_data = {
            "show_timer": settings.show_timer,
            "keyboard_shortcuts": settings.keyboard_shortcuts,
            "questions_per_session": settings.questions_per_session,
            "theme": settings.theme,
            "font_size": settings.font_size,
        }

    # Get attempts
    attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == current_user.id
    ).all()

    attempts_data = [
        {
            "question_id": a.question_id,
            "user_answer": a.user_answer,
            "is_correct": a.is_correct,
            "time_spent_seconds": a.time_spent_seconds,
            "attempted_at": a.attempted_at.isoformat(),
        }
        for a in attempts
    ]

    # Get performance records
    performance = db.query(UserPerformance).filter(
        UserPerformance.user_id == current_user.id
    ).all()

    performance_data = [
        {
            "session_date": p.session_date.isoformat(),
            "questions_answered": p.questions_answered,
            "accuracy_overall": p.accuracy_overall,
            "predicted_score": p.predicted_score,
        }
        for p in performance
    ]

    # Get scheduled reviews
    reviews = db.query(ScheduledReview).filter(
        ScheduledReview.user_id == current_user.id
    ).all()

    reviews_data = [
        {
            "question_id": r.question_id,
            "scheduled_for": r.scheduled_for.isoformat(),
            "learning_stage": r.learning_stage,
        }
        for r in reviews
    ]

    # Get chat messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).all()

    messages_data = [
        {
            "question_id": m.question_id,
            "message": m.message,
            "role": m.role,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]

    # Get ratings
    ratings = db.query(QuestionRating).filter(
        QuestionRating.user_id == current_user.id
    ).all()

    ratings_data = [
        {
            "question_id": r.question_id,
            "rating": r.rating,
            "feedback_text": r.feedback_text,
            "created_at": r.created_at.isoformat(),
        }
        for r in ratings
    ]

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "profile": profile,
        "settings": settings_data,
        "question_attempts": attempts_data,
        "performance_records": performance_data,
        "scheduled_reviews": reviews_data,
        "chat_messages": messages_data,
        "question_ratings": ratings_data,
    }
