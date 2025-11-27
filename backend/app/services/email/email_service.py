"""
Core email service using Resend API.
Handles sending and logging all email notifications.
"""

import os
import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import User, UserSettings, EmailLog, UnsubscribeToken
from app.services.email.email_templates import render_template

logger = logging.getLogger(__name__)

# Lazy-loaded Resend client
_resend = None


def get_resend():
    """Lazy-load Resend client to avoid import-time errors."""
    global _resend
    if _resend is None:
        import resend
        api_key = os.getenv("RESEND_API_KEY")
        if not api_key:
            logger.warning("RESEND_API_KEY not set - emails will not be sent")
            return None
        resend.api_key = api_key
        _resend = resend
    return _resend


class EmailService:
    """
    Email service for sending transactional emails.
    Integrates with Resend API and logs all email activity.
    """

    def __init__(self):
        self.from_email = os.getenv("EMAIL_FROM", "ShelfSense <noreply@resend.dev>")
        self.frontend_url = os.getenv("FRONTEND_URL", "https://shelfsense99.netlify.app")
        self.api_url = os.getenv("API_URL", "https://shelfsense-api.up.railway.app")

    def _generate_unsubscribe_token(
        self,
        db: Session,
        user_id: str,
        email_type: Optional[str] = None
    ) -> str:
        """Generate a unique unsubscribe token for a user."""
        token = secrets.token_urlsafe(32)
        unsub = UnsubscribeToken(
            user_id=user_id,
            token=token,
            email_type=email_type
        )
        db.add(unsub)
        db.commit()
        return token

    def _get_unsubscribe_url(self, token: str) -> str:
        """Get the unsubscribe URL for a token."""
        return f"{self.api_url}/api/email/unsubscribe/{token}"

    async def send_welcome_email(self, db: Session, user: User) -> bool:
        """
        Send welcome email after user registration.
        Returns True if sent successfully.
        """
        # Check if user has email notifications enabled
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()

        if settings and not settings.email_notifications:
            logger.info(f"User {user.id} has email notifications disabled")
            return False

        if not user.email:
            logger.warning(f"User {user.id} has no email address")
            return False

        # Generate unsubscribe token
        unsub_token = self._generate_unsubscribe_token(db, user.id, None)
        unsubscribe_url = self._get_unsubscribe_url(unsub_token)

        # Render template
        context = {
            "first_name": user.first_name or "there",
            "dashboard_url": f"{self.frontend_url}/dashboard",
            "unsubscribe_url": unsubscribe_url
        }
        html_content = render_template("welcome.html", context)

        subject = f"Welcome to ShelfSense, {user.first_name}!"

        return await self._send_and_log(
            db=db,
            user_id=user.id,
            email_type="welcome",
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )

    async def send_password_reset_email(
        self,
        db: Session,
        user: User,
        reset_token: str,
        expire_hours: int = 1
    ) -> bool:
        """
        Send password reset email with reset link.
        Returns True if sent successfully.
        """
        if not user.email:
            logger.warning(f"User {user.id} has no email address")
            return False

        # Generate unsubscribe token
        unsub_token = self._generate_unsubscribe_token(db, user.id, None)
        unsubscribe_url = self._get_unsubscribe_url(unsub_token)

        # Build reset URL
        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"

        # Render template
        context = {
            "first_name": user.first_name or "there",
            "reset_url": reset_url,
            "expire_hours": expire_hours,
            "unsubscribe_url": unsubscribe_url
        }
        html_content = render_template("password_reset.html", context)

        subject = "Reset your ShelfSense password"

        return await self._send_and_log(
            db=db,
            user_id=user.id,
            email_type="password_reset",
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )

    async def send_subscription_confirmation(
        self,
        db: Session,
        user: User,
        tier: str,
        billing_cycle: str,
        next_billing_date: Optional[str] = None
    ) -> bool:
        """
        Send subscription confirmation email after successful payment.
        Returns True if sent successfully.
        """
        if not user.email:
            logger.warning(f"User {user.id} has no email address")
            return False

        # Generate unsubscribe token
        unsub_token = self._generate_unsubscribe_token(db, user.id, None)
        unsubscribe_url = self._get_unsubscribe_url(unsub_token)

        # Format tier name for display
        tier_names = {
            "student": "Student Plan",
            "premium": "Premium Plan",
        }
        tier_name = tier_names.get(tier, tier.title())

        # Format billing cycle
        billing_display = "Monthly" if billing_cycle == "monthly" else "Yearly"

        # Render template
        context = {
            "first_name": user.first_name or "there",
            "tier_name": tier_name,
            "billing_cycle": billing_display,
            "next_billing_date": next_billing_date,
            "dashboard_url": f"{self.frontend_url}/dashboard",
            "settings_url": f"{self.frontend_url}/settings",
            "unsubscribe_url": unsubscribe_url
        }
        html_content = render_template("subscription_confirmation.html", context)

        subject = f"Welcome to ShelfSense {tier_name}!"

        return await self._send_and_log(
            db=db,
            user_id=user.id,
            email_type="subscription",
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )

    async def send_review_reminder(
        self,
        db: Session,
        user: User,
        review_count: int
    ) -> bool:
        """
        Send daily review reminder.
        Returns True if sent successfully.
        """
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()

        if not settings or not settings.daily_reminder or not settings.email_notifications:
            return False

        if not user.email:
            return False

        # Generate unsubscribe token for reminders specifically
        unsub_token = self._generate_unsubscribe_token(db, user.id, "reminder")
        unsubscribe_url = self._get_unsubscribe_url(unsub_token)

        # Render template
        context = {
            "first_name": user.first_name or "there",
            "review_count": review_count,
            "review_url": f"{self.frontend_url}/reviews",
            "unsubscribe_url": unsubscribe_url
        }
        html_content = render_template("review_reminder.html", context)

        subject = f"You have {review_count} questions to review today"

        return await self._send_and_log(
            db=db,
            user_id=user.id,
            email_type="reminder",
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )

    async def _send_and_log(
        self,
        db: Session,
        user_id: str,
        email_type: str,
        to_email: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Send email via Resend and log the result."""
        # Create log entry
        log = EmailLog(
            user_id=user_id,
            email_type=email_type,
            recipient_email=to_email,
            subject=subject,
            provider="resend",
            status="queued"
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        resend = get_resend()
        if not resend:
            log.status = "failed"
            log.error_message = "Resend API key not configured"
            db.commit()
            return False

        try:
            result = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            })

            # Update log with success
            log.status = "sent"
            log.provider_message_id = result.get("id")
            log.sent_at = datetime.utcnow()
            db.commit()

            logger.info(f"Email sent: {email_type} to {to_email} (id: {result.get('id')})")
            return True

        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            db.commit()

            logger.error(f"Failed to send {email_type} email to {to_email}: {e}")
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the singleton EmailService instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
