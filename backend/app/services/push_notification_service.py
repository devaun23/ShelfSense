"""
Web Push Notification Service.
Sends push notifications for daily study reminders and streak alerts.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Lazy-loaded pywebpush
_webpush = None


def get_webpush():
    """Lazy-load pywebpush to avoid import errors if not installed."""
    global _webpush
    if _webpush is None:
        try:
            from pywebpush import webpush, WebPushException
            _webpush = {"webpush": webpush, "WebPushException": WebPushException}
        except ImportError:
            logger.warning("pywebpush not installed - push notifications disabled")
            return None
    return _webpush


class PushNotificationService:
    """
    Service for managing web push notifications.

    Sends notifications for:
    - Daily study reminders
    - Streak at risk alerts
    - Achievement celebrations
    - Weekly progress updates
    """

    def __init__(self):
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_email = os.getenv("VAPID_EMAIL", "mailto:admin@shelfsense.app")

        if not self.vapid_private_key or not self.vapid_public_key:
            logger.warning("VAPID keys not configured - push notifications disabled")

    def is_configured(self) -> bool:
        """Check if push notifications are properly configured."""
        return bool(self.vapid_private_key and self.vapid_public_key and get_webpush())

    def get_vapid_public_key(self) -> Optional[str]:
        """Get the VAPID public key for client subscription."""
        return self.vapid_public_key

    async def send_notification(
        self,
        subscription_info: Dict[str, Any],
        title: str,
        body: str,
        icon: str = "/icon-192.png",
        badge: str = "/badge-72.png",
        tag: Optional[str] = None,
        url: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a push notification to a single subscription.

        Args:
            subscription_info: The PushSubscription object from the browser
            title: Notification title
            body: Notification body text
            icon: Icon URL
            badge: Badge icon URL (shown in notification tray)
            tag: Optional tag for notification grouping
            url: URL to open when notification is clicked
            data: Additional data to send with the notification

        Returns:
            True if sent successfully, False otherwise
        """
        wp = get_webpush()
        if not wp or not self.is_configured():
            return False

        payload = {
            "title": title,
            "body": body,
            "icon": icon,
            "badge": badge,
            "tag": tag or "shelfsense",
            "data": {
                "url": url or "/",
                **(data or {})
            }
        }

        try:
            wp["webpush"](
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims={
                    "sub": self.vapid_email
                }
            )
            logger.info(f"Push notification sent: {title}")
            return True

        except wp["WebPushException"] as e:
            logger.error(f"Push notification failed: {e}")
            # If subscription is expired (410), we should remove it
            if e.response and e.response.status_code == 410:
                logger.info("Subscription expired, should be removed")
            return False

        except Exception as e:
            logger.error(f"Unexpected push notification error: {e}")
            return False

    async def send_study_reminder(
        self,
        subscription_info: Dict[str, Any],
        user_name: str,
        reviews_due: int = 0,
        streak_at_risk: bool = False,
        current_streak: int = 0
    ) -> bool:
        """Send a daily study reminder notification."""
        if streak_at_risk and current_streak > 0:
            title = f"Don't lose your {current_streak}-day streak!"
            body = "Study now to keep your streak going. Just one question counts!"
            tag = "streak-risk"
        elif reviews_due > 0:
            title = f"You have {reviews_due} reviews due!"
            body = f"Hi {user_name}, time for your spaced repetition review."
            tag = "review-reminder"
        else:
            title = "Time to study!"
            body = f"Hi {user_name}, keep building your knowledge today."
            tag = "study-reminder"

        return await self.send_notification(
            subscription_info=subscription_info,
            title=title,
            body=body,
            tag=tag,
            url="/study"
        )

    async def send_streak_celebration(
        self,
        subscription_info: Dict[str, Any],
        days: int,
        is_new_best: bool = False
    ) -> bool:
        """Send a streak milestone celebration notification."""
        if is_new_best:
            title = f"New Personal Best: {days} Days!"
            body = "You've set a new streak record! Keep up the amazing work!"
        else:
            title = f"{days} Day Streak!"
            body = "Amazing consistency! You're building great study habits."

        return await self.send_notification(
            subscription_info=subscription_info,
            title=title,
            body=body,
            tag="streak-celebration",
            url="/analytics"
        )

    async def send_achievement_unlocked(
        self,
        subscription_info: Dict[str, Any],
        badge_name: str,
        badge_description: str
    ) -> bool:
        """Send a badge unlock notification."""
        return await self.send_notification(
            subscription_info=subscription_info,
            title=f"Badge Unlocked: {badge_name}!",
            body=badge_description,
            tag="achievement",
            url="/achievements"
        )


# Singleton instance
_push_service: Optional[PushNotificationService] = None


def get_push_notification_service() -> PushNotificationService:
    """Get the singleton PushNotificationService instance."""
    global _push_service
    if _push_service is None:
        _push_service = PushNotificationService()
    return _push_service
