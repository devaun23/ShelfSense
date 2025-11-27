"""
Email notification service for ShelfSense.
Handles welcome emails and review reminders using Resend.
"""

from app.services.email.email_service import EmailService, get_email_service
from app.services.email.email_scheduler import run_hourly_reminder_check

__all__ = ["EmailService", "get_email_service", "run_hourly_reminder_check"]
