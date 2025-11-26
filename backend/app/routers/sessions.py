"""
Sessions Router
Handles user session management - view active sessions, logout from devices.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from app.database import get_db
from app.models.models import User, UserSession
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ==================== Response Models ====================

class SessionInfo(BaseModel):
    id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_used: datetime
    expires_at: datetime
    is_current: bool = False

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]
    total: int


class MessageResponse(BaseModel):
    message: str
    terminated_count: Optional[int] = None


# ==================== Session Management Endpoints ====================

@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active sessions for the current user.
    Shows device info, IP address, and last activity time.
    """
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.expires_at > datetime.utcnow()
    ).order_by(UserSession.last_used.desc()).all()

    session_list = []
    for s in sessions:
        # Truncate/anonymize device info for display
        device_display = s.device_info
        if device_display and len(device_display) > 50:
            device_display = device_display[:50] + "..."

        session_list.append(SessionInfo(
            id=s.id,
            device_info=device_display,
            ip_address=s.ip_address,
            created_at=s.created_at,
            last_used=s.last_used,
            expires_at=s.expires_at,
            is_current=False  # We can't determine this without the token
        ))

    return SessionListResponse(
        sessions=session_list,
        total=len(session_list)
    )


@router.delete("/{session_id}", response_model=MessageResponse)
async def terminate_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Terminate a specific session by ID.
    The user will need to log in again on that device.
    """
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    db.delete(session)
    db.commit()

    return MessageResponse(message="Session terminated successfully")


@router.delete("/", response_model=MessageResponse)
async def terminate_all_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Terminate all sessions except the current one.
    Useful for "log out from all devices" functionality.

    Note: Since we can't identify the current session without
    the refresh token, this logs out ALL sessions. The user
    will need to log in again.
    """
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id
    ).all()

    count = len(sessions)

    for session in sessions:
        db.delete(session)

    db.commit()

    return MessageResponse(
        message=f"Terminated {count} session(s)",
        terminated_count=count
    )


@router.post("/cleanup", response_model=MessageResponse)
async def cleanup_expired_sessions(
    db: Session = Depends(get_db)
):
    """
    Clean up all expired sessions (admin/maintenance endpoint).
    Can be called periodically to free up database space.
    """
    expired = db.query(UserSession).filter(
        UserSession.expires_at < datetime.utcnow()
    ).all()

    count = len(expired)

    for session in expired:
        db.delete(session)

    db.commit()

    return MessageResponse(
        message=f"Cleaned up {count} expired session(s)",
        terminated_count=count
    )


# ==================== Session Stats (Debug) ====================

@router.get("/stats")
async def get_session_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get session statistics for the current user.
    Debug endpoint showing session history.
    """
    all_sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id
    ).all()

    active_sessions = [s for s in all_sessions if s.expires_at > datetime.utcnow()]
    expired_sessions = [s for s in all_sessions if s.expires_at <= datetime.utcnow()]

    # Get unique devices
    devices = set()
    for s in all_sessions:
        if s.device_info:
            # Extract browser/OS from user agent
            device = s.device_info.split(' ')[0] if ' ' in s.device_info else s.device_info
            devices.add(device[:30])

    # Get unique IPs
    ips = set(s.ip_address for s in all_sessions if s.ip_address)

    return {
        "total_sessions": len(all_sessions),
        "active_sessions": len(active_sessions),
        "expired_sessions": len(expired_sessions),
        "unique_devices": list(devices)[:10],  # Limit to 10
        "unique_ips": list(ips)[:10],  # Limit to 10
        "first_session": min(s.created_at for s in all_sessions).isoformat() if all_sessions else None,
        "last_activity": max(s.last_used for s in all_sessions).isoformat() if all_sessions else None,
    }
