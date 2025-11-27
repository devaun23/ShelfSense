"""
Email notification service for ShelfSense.
Handles welcome emails, review reminders, and weekly digests using Resend.
"""

from app.services.email.email_service import EmailService, get_email_service
from app.services.email.email_scheduler import run_hourly_reminder_check
from app.services.email.weekly_digest import run_weekly_digest_scheduler, send_weekly_digests

__all__ = [
    "EmailService",
    "get_email_service",
    "run_hourly_reminder_check",
    "run_weekly_digest_scheduler",
    "send_weekly_digests"
]
