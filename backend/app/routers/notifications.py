"""
Push Notifications API Router.
Endpoints for managing push notification subscriptions and sending notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, PushSubscription, UserSettings, ScheduledReview, UserEngagementScore
from app.services.push_notification_service import get_push_notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    device_name: Optional[str] = None


class PushSubscriptionResponse(BaseModel):
    id: str
    device_name: Optional[str]
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class NotificationPreferences(BaseModel):
    push_enabled: bool
    daily_reminder: bool
    reminder_time: Optional[str] = None  # HH:MM format
    streak_alerts: bool
    achievement_alerts: bool


class TestNotificationRequest(BaseModel):
    title: str = "Test Notification"
    body: str = "This is a test notification from ShelfSense!"


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Get the VAPID public key for push subscription."""
    push_service = get_push_notification_service()
    public_key = push_service.get_vapid_public_key()

    if not public_key:
        raise HTTPException(
            status_code=503,
            detail="Push notifications not configured"
        )

    return {"vapid_public_key": public_key}


@router.post("/subscribe", response_model=PushSubscriptionResponse)
async def subscribe_to_push(
    subscription: PushSubscriptionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Subscribe to push notifications.
    Registers a new push subscription for the current user.
    """
    # Check if subscription already exists
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == subscription.endpoint
    ).first()

    if existing:
        # Update existing subscription
        existing.p256dh_key = subscription.keys.p256dh
        existing.auth_key = subscription.keys.auth
        existing.user_id = current_user.id
        existing.is_active = True
        existing.failed_attempts = 0
        existing.device_name = subscription.device_name
        existing.user_agent = request.headers.get("user-agent")
        db.commit()
        db.refresh(existing)
        return existing

    # Create new subscription
    new_sub = PushSubscription(
        user_id=current_user.id,
        endpoint=subscription.endpoint,
        p256dh_key=subscription.keys.p256dh,
        auth_key=subscription.keys.auth,
        device_name=subscription.device_name,
        user_agent=request.headers.get("user-agent")
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    return new_sub


@router.delete("/unsubscribe")
async def unsubscribe_from_push(
    endpoint: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unsubscribe from push notifications."""
    sub = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint,
        PushSubscription.user_id == current_user.id
    ).first()

    if sub:
        db.delete(sub)
        db.commit()

    return {"status": "unsubscribed"}


@router.get("/subscriptions", response_model=List[PushSubscriptionResponse])
async def list_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all push subscriptions for the current user."""
    subs = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.is_active == True
    ).all()

    return subs


@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a test notification to all user's devices."""
    push_service = get_push_notification_service()

    if not push_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Push notifications not configured"
        )

    # Get all active subscriptions for user
    subs = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.is_active == True
    ).all()

    if not subs:
        raise HTTPException(
            status_code=404,
            detail="No active push subscriptions found"
        )

    sent_count = 0
    for sub in subs:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh_key,
                "auth": sub.auth_key
            }
        }

        success = await push_service.send_notification(
            subscription_info=subscription_info,
            title=request.title,
            body=request.body,
            tag="test"
        )

        if success:
            sent_count += 1
            sub.last_used = datetime.utcnow()
        else:
            sub.failed_attempts += 1
            if sub.failed_attempts >= 3:
                sub.is_active = False

    db.commit()

    return {
        "status": "sent",
        "devices_reached": sent_count,
        "total_devices": len(subs)
    }


@router.get("/preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification preferences for the current user."""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    # Check if user has any active push subscriptions
    has_push = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.is_active == True
    ).first() is not None

    if not settings:
        return NotificationPreferences(
            push_enabled=has_push,
            daily_reminder=False,
            reminder_time=None,
            streak_alerts=True,
            achievement_alerts=True
        )

    return NotificationPreferences(
        push_enabled=has_push,
        daily_reminder=settings.daily_reminder,
        reminder_time=settings.reminder_time,
        streak_alerts=True,  # Default to true, can add to UserSettings if needed
        achievement_alerts=True
    )


@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update notification preferences."""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    settings.daily_reminder = preferences.daily_reminder
    settings.reminder_time = preferences.reminder_time

    db.commit()

    return {"status": "updated"}
