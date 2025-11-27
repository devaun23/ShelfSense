"""
Daily Streak Service.
Tracks consecutive study days and updates user streaks.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.models import User, UserEngagementScore, QuestionAttempt

logger = logging.getLogger(__name__)


class StreakService:
    """
    Service for managing user study streaks.

    A streak is defined as consecutive calendar days with at least one question attempted.
    Streaks reset if a user misses a full calendar day.
    """

    def get_or_create_engagement(self, db: Session, user_id: str) -> UserEngagementScore:
        """Get or create engagement score record for a user."""
        engagement = db.query(UserEngagementScore).filter(
            UserEngagementScore.user_id == user_id
        ).first()

        if not engagement:
            engagement = UserEngagementScore(
                user_id=user_id,
                streak_current=0,
                streak_best=0,
                engagement_status="new"
            )
            db.add(engagement)
            db.commit()
            db.refresh(engagement)

        return engagement

    def get_streak_data(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive streak data for a user.

        Returns:
            Dict with current_streak, best_streak, studied_today,
            last_activity_date, and streak_at_risk (if they need to study today)
        """
        engagement = self.get_or_create_engagement(db, user_id)

        # Check if user studied today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        studied_today = db.query(QuestionAttempt).filter(
            and_(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.attempted_at >= today_start,
                QuestionAttempt.attempted_at < today_end
            )
        ).first() is not None

        # Check if streak is at risk (studied yesterday but not today)
        yesterday_start = today_start - timedelta(days=1)
        studied_yesterday = db.query(QuestionAttempt).filter(
            and_(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.attempted_at >= yesterday_start,
                QuestionAttempt.attempted_at < today_start
            )
        ).first() is not None

        streak_at_risk = studied_yesterday and not studied_today and engagement.streak_current > 0

        # Calculate streak milestones
        milestones = self._get_streak_milestones(engagement.streak_current)

        return {
            "current_streak": engagement.streak_current,
            "best_streak": engagement.streak_best,
            "studied_today": studied_today,
            "streak_at_risk": streak_at_risk,
            "last_activity_at": engagement.last_activity_at.isoformat() if engagement.last_activity_at else None,
            "next_milestone": milestones.get("next"),
            "current_milestone": milestones.get("current"),
            "days_to_next_milestone": milestones.get("days_to_next")
        }

    def _get_streak_milestones(self, current_streak: int) -> Dict[str, Any]:
        """Get streak milestone information."""
        milestones = [3, 7, 14, 30, 60, 100, 150, 200, 365]

        current_milestone = None
        next_milestone = None

        for m in milestones:
            if current_streak >= m:
                current_milestone = m
            elif next_milestone is None:
                next_milestone = m

        days_to_next = next_milestone - current_streak if next_milestone else None

        return {
            "current": current_milestone,
            "next": next_milestone,
            "days_to_next": days_to_next
        }

    def update_streak_on_activity(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Update streak when user completes a question.
        Called automatically when a question attempt is submitted.

        Returns:
            Dict with updated streak data and any celebrations
        """
        engagement = self.get_or_create_engagement(db, user_id)
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        celebrations = []
        streak_increased = False
        new_best = False

        # If this is first activity ever
        if engagement.last_activity_at is None:
            engagement.streak_current = 1
            engagement.streak_best = 1
            engagement.first_activity_at = now
            streak_increased = True
            celebrations.append({"type": "first_question", "message": "Welcome! You've started your learning journey!"})
        else:
            last_activity_date = engagement.last_activity_at.replace(hour=0, minute=0, second=0, microsecond=0)
            days_since_last = (today_start - last_activity_date).days

            if days_since_last == 0:
                # Already studied today, no streak change
                pass
            elif days_since_last == 1:
                # Studied yesterday, streak continues
                engagement.streak_current += 1
                streak_increased = True

                # Check for new best
                if engagement.streak_current > engagement.streak_best:
                    engagement.streak_best = engagement.streak_current
                    new_best = True
                    celebrations.append({
                        "type": "new_best",
                        "message": f"New personal best! {engagement.streak_current} day streak!"
                    })

                # Check milestones
                milestones = [3, 7, 14, 30, 60, 100, 150, 200, 365]
                if engagement.streak_current in milestones:
                    celebrations.append({
                        "type": "milestone",
                        "days": engagement.streak_current,
                        "message": f"Amazing! {engagement.streak_current} day streak!"
                    })
            else:
                # Streak broken, start fresh
                old_streak = engagement.streak_current
                engagement.streak_current = 1
                streak_increased = True
                if old_streak > 0:
                    celebrations.append({
                        "type": "streak_restart",
                        "message": "New streak started! Keep going!"
                    })

        # Update activity tracking
        engagement.last_activity_at = now
        engagement.days_since_last_activity = 0

        # Update engagement status based on streak
        if engagement.streak_current >= 7:
            engagement.engagement_status = "active"
            engagement.return_frequency = "daily"
        elif engagement.streak_current >= 3:
            engagement.engagement_status = "active"

        db.commit()
        db.refresh(engagement)

        return {
            "current_streak": engagement.streak_current,
            "best_streak": engagement.streak_best,
            "streak_increased": streak_increased,
            "new_best": new_best,
            "celebrations": celebrations
        }

    def check_and_update_broken_streaks(self, db: Session) -> int:
        """
        Batch job to check and reset broken streaks.
        Should run daily to update users who haven't studied.

        Returns:
            Number of streaks that were reset
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = today_start

        # Find users with active streaks who haven't studied since yesterday
        users_with_streaks = db.query(UserEngagementScore).filter(
            and_(
                UserEngagementScore.streak_current > 0,
                UserEngagementScore.last_activity_at < yesterday_end - timedelta(days=1)
            )
        ).all()

        reset_count = 0
        for engagement in users_with_streaks:
            # Double check they didn't study yesterday or today
            recent_attempt = db.query(QuestionAttempt).filter(
                and_(
                    QuestionAttempt.user_id == engagement.user_id,
                    QuestionAttempt.attempted_at >= yesterday_end - timedelta(days=1)
                )
            ).first()

            if not recent_attempt:
                old_streak = engagement.streak_current
                engagement.streak_current = 0
                engagement.days_since_last_activity = (today_start - engagement.last_activity_at.replace(hour=0, minute=0, second=0, microsecond=0)).days

                # Update churn risk
                if engagement.days_since_last_activity >= 14:
                    engagement.engagement_status = "churned"
                elif engagement.days_since_last_activity >= 7:
                    engagement.engagement_status = "at_risk"
                    engagement.churn_risk_score = 0.7
                elif engagement.days_since_last_activity >= 3:
                    engagement.churn_risk_score = 0.4

                reset_count += 1
                logger.info(f"Reset streak for user {engagement.user_id}: {old_streak} -> 0")

        db.commit()
        return reset_count

    def get_streak_leaderboard(
        self,
        db: Session,
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get streak leaderboard.

        Args:
            db: Database session
            limit: Number of top users to return
            user_id: Optional user ID to include their rank

        Returns:
            Dict with top_streaks list and optionally user_rank
        """
        # Get top streaks
        top_users = db.query(
            UserEngagementScore.user_id,
            UserEngagementScore.streak_current,
            UserEngagementScore.streak_best,
            User.first_name
        ).join(
            User, UserEngagementScore.user_id == User.id
        ).filter(
            UserEngagementScore.streak_current > 0
        ).order_by(
            UserEngagementScore.streak_current.desc()
        ).limit(limit).all()

        leaderboard = [
            {
                "rank": i + 1,
                "first_name": user.first_name,
                "current_streak": user.streak_current,
                "best_streak": user.streak_best
            }
            for i, user in enumerate(top_users)
        ]

        result = {"top_streaks": leaderboard}

        # Get user's rank if requested
        if user_id:
            user_engagement = db.query(UserEngagementScore).filter(
                UserEngagementScore.user_id == user_id
            ).first()

            if user_engagement and user_engagement.streak_current > 0:
                # Count users with higher streaks
                higher_count = db.query(UserEngagementScore).filter(
                    UserEngagementScore.streak_current > user_engagement.streak_current
                ).count()

                result["user_rank"] = higher_count + 1
                result["user_streak"] = user_engagement.streak_current

        return result


# Singleton instance
_streak_service: Optional[StreakService] = None


def get_streak_service() -> StreakService:
    """Get the singleton StreakService instance."""
    global _streak_service
    if _streak_service is None:
        _streak_service = StreakService()
    return _streak_service
