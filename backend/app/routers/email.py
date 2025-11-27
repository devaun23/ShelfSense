"""
Email notification router.
Handles webhooks for email tracking and unsubscribe functionality.
"""

import os
import hmac
import hashlib
import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import EmailLog, UserSettings, UnsubscribeToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])


@router.post("/webhooks/resend")
async def resend_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Resend webhook events for email tracking.

    Supported events:
    - email.delivered: Email was delivered to recipient
    - email.opened: Recipient opened the email
    - email.clicked: Recipient clicked a link
    - email.bounced: Email bounced (hard or soft)
    - email.complained: Recipient marked as spam
    """
    # Verify webhook signature if secret is configured
    webhook_secret = os.getenv("RESEND_WEBHOOK_SECRET")
    if webhook_secret:
        signature = request.headers.get("resend-signature", "")
        payload = await request.body()

        expected = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event_type = data.get("type", "")
    email_data = data.get("data", {})
    message_id = email_data.get("email_id")

    if not message_id:
        return {"status": "ignored", "reason": "no message_id"}

    # Find the email log
    log = db.query(EmailLog).filter(
        EmailLog.provider_message_id == message_id
    ).first()

    if not log:
        return {"status": "not_found"}

    now = datetime.utcnow()

    # Update status based on event type
    if event_type == "email.delivered":
        log.status = "delivered"
        log.delivered_at = now

    elif event_type == "email.opened":
        log.status = "opened"
        log.opened_at = now

    elif event_type == "email.clicked":
        log.status = "clicked"
        log.clicked_at = now

    elif event_type == "email.bounced":
        log.status = "bounced"
        bounce_data = email_data.get("bounce", {})
        log.error_message = bounce_data.get("message", "Unknown bounce")

        # Disable emails for hard bounces
        bounce_type = bounce_data.get("bounce_type", "")
        if bounce_type == "hard":
            await _disable_email_for_user(db, log.user_id)
            logger.info(f"Disabled emails for user {log.user_id} due to hard bounce")

    elif event_type == "email.complained":
        log.status = "complained"
        # Auto-unsubscribe users who mark as spam
        await _disable_email_for_user(db, log.user_id)
        logger.info(f"Disabled emails for user {log.user_id} due to spam complaint")

    db.commit()

    return {"status": "processed", "event": event_type}


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe(token: str, db: Session = Depends(get_db)):
    """
    One-click unsubscribe handler.
    Disables email notifications for the user associated with the token.
    """
    # Find the unsubscribe token
    unsub = db.query(UnsubscribeToken).filter(
        UnsubscribeToken.token == token,
        UnsubscribeToken.used_at.is_(None)
    ).first()

    if not unsub:
        return _render_unsubscribe_page(
            success=False,
            message="This unsubscribe link is invalid or has already been used."
        )

    # Mark token as used
    unsub.used_at = datetime.utcnow()

    # Find user settings
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == unsub.user_id
    ).first()

    if settings:
        if unsub.email_type == "reminder":
            # Unsubscribe from reminders only
            settings.daily_reminder = False
            message = "You've been unsubscribed from daily review reminders."
        else:
            # Unsubscribe from all emails
            settings.email_notifications = False
            settings.daily_reminder = False
            message = "You've been unsubscribed from all ShelfSense emails."
    else:
        message = "Settings not found, but you won't receive further emails."

    db.commit()

    logger.info(f"User {unsub.user_id} unsubscribed (type: {unsub.email_type or 'all'})")

    return _render_unsubscribe_page(success=True, message=message)


async def _disable_email_for_user(db: Session, user_id: str):
    """Disable all email notifications for a user."""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == user_id
    ).first()

    if settings:
        settings.email_notifications = False
        settings.daily_reminder = False
        db.commit()


def _render_unsubscribe_page(success: bool, message: str) -> str:
    """Render a simple HTML page for unsubscribe confirmation."""
    status_color = "#28a745" if success else "#dc3545"
    status_icon = "&#10003;" if success else "&#10007;"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Unsubscribe - ShelfSense</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 40px 20px;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .card {{
                background: white;
                border-radius: 12px;
                padding: 40px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .icon {{
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: {status_color};
                color: white;
                font-size: 32px;
                line-height: 60px;
                margin: 0 auto 20px;
            }}
            h1 {{
                margin: 0 0 16px;
                color: #1a1a1a;
                font-size: 24px;
            }}
            p {{
                margin: 0;
                color: #666;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">{status_icon}</div>
            <h1>{'Unsubscribed' if success else 'Error'}</h1>
            <p>{message}</p>
        </div>
    </body>
    </html>
    """
