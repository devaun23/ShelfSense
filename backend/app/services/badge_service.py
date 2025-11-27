"""
Achievement Badge Service.
Defines, tracks, and awards badges for user milestones.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.models import (
    UserBadge, User, QuestionAttempt, UserEngagementScore,
    StudySession, UserPerformance
)

logger = logging.getLogger(__name__)


@dataclass
class BadgeDefinition:
    """Definition of a badge that can be earned."""
    id: str
    name: str
    description: str
    icon: str  # Emoji or icon name
    category: str  # streak, accuracy, volume, milestone, special
    requirement_description: str
    check_function: str  # Name of the check function


# All available badges
BADGE_DEFINITIONS: Dict[str, BadgeDefinition] = {
    # Streak Badges
    "streak_3": BadgeDefinition(
        id="streak_3",
        name="Getting Started",
        description="Studied for 3 consecutive days",
        icon="fire",
        category="streak",
        requirement_description="3-day study streak",
        check_function="check_streak_badge"
    ),
    "streak_7": BadgeDefinition(
        id="streak_7",
        name="Week Warrior",
        description="Studied for 7 consecutive days",
        icon="flame",
        category="streak",
        requirement_description="7-day study streak",
        check_function="check_streak_badge"
    ),
    "streak_14": BadgeDefinition(
        id="streak_14",
        name="Two Week Champion",
        description="Studied for 14 consecutive days",
        icon="trophy",
        category="streak",
        requirement_description="14-day study streak",
        check_function="check_streak_badge"
    ),
    "streak_30": BadgeDefinition(
        id="streak_30",
        name="Monthly Master",
        description="Studied for 30 consecutive days",
        icon="crown",
        category="streak",
        requirement_description="30-day study streak",
        check_function="check_streak_badge"
    ),
    "streak_60": BadgeDefinition(
        id="streak_60",
        name="Dedication Legend",
        description="Studied for 60 consecutive days",
        icon="star",
        category="streak",
        requirement_description="60-day study streak",
        check_function="check_streak_badge"
    ),
    "streak_100": BadgeDefinition(
        id="streak_100",
        name="Century Club",
        description="Studied for 100 consecutive days",
        icon="medal",
        category="streak",
        requirement_description="100-day study streak",
        check_function="check_streak_badge"
    ),

    # Volume Badges
    "questions_50": BadgeDefinition(
        id="questions_50",
        name="First Fifty",
        description="Answered 50 questions",
        icon="book",
        category="volume",
        requirement_description="Answer 50 questions",
        check_function="check_volume_badge"
    ),
    "questions_100": BadgeDefinition(
        id="questions_100",
        name="Century",
        description="Answered 100 questions",
        icon="books",
        category="volume",
        requirement_description="Answer 100 questions",
        check_function="check_volume_badge"
    ),
    "questions_500": BadgeDefinition(
        id="questions_500",
        name="Half Thousand",
        description="Answered 500 questions",
        icon="library",
        category="volume",
        requirement_description="Answer 500 questions",
        check_function="check_volume_badge"
    ),
    "questions_1000": BadgeDefinition(
        id="questions_1000",
        name="Thousand Strong",
        description="Answered 1,000 questions",
        icon="rocket",
        category="volume",
        requirement_description="Answer 1,000 questions",
        check_function="check_volume_badge"
    ),
    "questions_2500": BadgeDefinition(
        id="questions_2500",
        name="Question Master",
        description="Answered 2,500 questions",
        icon="brain",
        category="volume",
        requirement_description="Answer 2,500 questions",
        check_function="check_volume_badge"
    ),

    # Accuracy Badges
    "accuracy_streak_5": BadgeDefinition(
        id="accuracy_streak_5",
        name="Hot Hand",
        description="Got 5 questions correct in a row",
        icon="target",
        category="accuracy",
        requirement_description="5 correct answers in a row",
        check_function="check_accuracy_streak_badge"
    ),
    "accuracy_streak_10": BadgeDefinition(
        id="accuracy_streak_10",
        name="On Fire",
        description="Got 10 questions correct in a row",
        icon="bullseye",
        category="accuracy",
        requirement_description="10 correct answers in a row",
        check_function="check_accuracy_streak_badge"
    ),
    "accuracy_streak_20": BadgeDefinition(
        id="accuracy_streak_20",
        name="Unstoppable",
        description="Got 20 questions correct in a row",
        icon="lightning",
        category="accuracy",
        requirement_description="20 correct answers in a row",
        check_function="check_accuracy_streak_badge"
    ),
    "accuracy_70": BadgeDefinition(
        id="accuracy_70",
        name="Solid Performer",
        description="Achieved 70% overall accuracy (min 100 questions)",
        icon="chart",
        category="accuracy",
        requirement_description="70% accuracy with 100+ questions",
        check_function="check_overall_accuracy_badge"
    ),
    "accuracy_80": BadgeDefinition(
        id="accuracy_80",
        name="High Achiever",
        description="Achieved 80% overall accuracy (min 200 questions)",
        icon="trending",
        category="accuracy",
        requirement_description="80% accuracy with 200+ questions",
        check_function="check_overall_accuracy_badge"
    ),
    "accuracy_90": BadgeDefinition(
        id="accuracy_90",
        name="Excellence",
        description="Achieved 90% overall accuracy (min 300 questions)",
        icon="diamond",
        category="accuracy",
        requirement_description="90% accuracy with 300+ questions",
        check_function="check_overall_accuracy_badge"
    ),

    # Score Milestone Badges
    "score_220": BadgeDefinition(
        id="score_220",
        name="Passing Potential",
        description="Predicted score reached 220",
        icon="check",
        category="milestone",
        requirement_description="Predicted score of 220+",
        check_function="check_score_badge"
    ),
    "score_240": BadgeDefinition(
        id="score_240",
        name="Competitive Edge",
        description="Predicted score reached 240",
        icon="medal",
        category="milestone",
        requirement_description="Predicted score of 240+",
        check_function="check_score_badge"
    ),
    "score_260": BadgeDefinition(
        id="score_260",
        name="Top Tier",
        description="Predicted score reached 260",
        icon="trophy",
        category="milestone",
        requirement_description="Predicted score of 260+",
        check_function="check_score_badge"
    ),

    # Special Badges
    "first_question": BadgeDefinition(
        id="first_question",
        name="First Step",
        description="Answered your first question",
        icon="flag",
        category="special",
        requirement_description="Answer your first question",
        check_function="check_first_question_badge"
    ),
    "first_perfect_session": BadgeDefinition(
        id="first_perfect_session",
        name="Perfect Session",
        description="Completed a session with 100% accuracy",
        icon="sparkles",
        category="special",
        requirement_description="100% on any study session",
        check_function="check_perfect_session_badge"
    ),
    "night_owl": BadgeDefinition(
        id="night_owl",
        name="Night Owl",
        description="Studied between midnight and 5 AM",
        icon="moon",
        category="special",
        requirement_description="Study after midnight",
        check_function="check_night_owl_badge"
    ),
    "early_bird": BadgeDefinition(
        id="early_bird",
        name="Early Bird",
        description="Studied between 5 AM and 7 AM",
        icon="sun",
        category="special",
        requirement_description="Study before 7 AM",
        check_function="check_early_bird_badge"
    ),
}


class BadgeService:
    """Service for managing achievement badges."""

    def get_all_badges(self) -> List[Dict[str, Any]]:
        """Get all available badge definitions."""
        return [
            {
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon": badge.icon,
                "category": badge.category,
                "requirement": badge.requirement_description
            }
            for badge in BADGE_DEFINITIONS.values()
        ]

    def get_user_badges(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Get all badges for a user, including earned and in-progress.

        Returns:
            Dict with 'earned', 'in_progress', 'total_earned', 'total_available'
        """
        # Get earned badges
        earned_badges = db.query(UserBadge).filter(
            UserBadge.user_id == user_id
        ).all()

        earned_ids = {b.badge_id for b in earned_badges}

        earned = []
        in_progress = []

        for badge_id, definition in BADGE_DEFINITIONS.items():
            badge_info = {
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "icon": definition.icon,
                "category": definition.category,
                "requirement": definition.requirement_description
            }

            if badge_id in earned_ids:
                user_badge = next(b for b in earned_badges if b.badge_id == badge_id)
                badge_info["earned"] = True
                badge_info["earned_at"] = user_badge.earned_at.isoformat()
                badge_info["context"] = user_badge.context
                earned.append(badge_info)
            else:
                # Calculate progress
                progress = self._calculate_badge_progress(db, user_id, definition)
                badge_info["earned"] = False
                badge_info["progress"] = progress
                if progress > 0:  # Only show badges with some progress
                    in_progress.append(badge_info)

        # Sort earned by date (most recent first)
        earned.sort(key=lambda x: x.get("earned_at", ""), reverse=True)

        # Sort in_progress by progress (closest to earning first)
        in_progress.sort(key=lambda x: x.get("progress", 0), reverse=True)

        return {
            "earned": earned,
            "in_progress": in_progress[:10],  # Top 10 in-progress
            "total_earned": len(earned),
            "total_available": len(BADGE_DEFINITIONS)
        }

    def _calculate_badge_progress(
        self,
        db: Session,
        user_id: str,
        badge: BadgeDefinition
    ) -> float:
        """Calculate progress (0-1) towards earning a badge."""
        if badge.category == "streak":
            engagement = db.query(UserEngagementScore).filter(
                UserEngagementScore.user_id == user_id
            ).first()

            if not engagement:
                return 0

            target = int(badge.id.split("_")[1])
            current = engagement.streak_current or 0
            return min(1.0, current / target)

        elif badge.category == "volume":
            count = db.query(func.count(QuestionAttempt.id)).filter(
                QuestionAttempt.user_id == user_id
            ).scalar() or 0

            target = int(badge.id.split("_")[1])
            return min(1.0, count / target)

        elif badge.category == "accuracy" and "accuracy_streak" in badge.id:
            # For accuracy streak badges, we'd need to calculate current streak
            # This is a simplified version
            return 0

        elif badge.category == "milestone":
            performance = db.query(UserPerformance).filter(
                UserPerformance.user_id == user_id
            ).order_by(UserPerformance.calculated_at.desc()).first()

            if not performance or not performance.predicted_score:
                return 0

            target = int(badge.id.split("_")[1])
            current = performance.predicted_score
            # Progress from 200 to target
            return min(1.0, max(0, (current - 200) / (target - 200)))

        return 0

    def check_and_award_badges(
        self,
        db: Session,
        user_id: str,
        trigger_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Check all badge conditions and award any newly earned badges.

        Args:
            db: Database session
            user_id: User to check
            trigger_context: Optional context about what triggered the check

        Returns:
            List of newly awarded badges
        """
        newly_awarded = []

        # Get already earned badges
        earned_ids = set(
            db.query(UserBadge.badge_id).filter(
                UserBadge.user_id == user_id
            ).all()
        )
        earned_ids = {e[0] for e in earned_ids}

        for badge_id, definition in BADGE_DEFINITIONS.items():
            if badge_id in earned_ids:
                continue

            # Check if badge is earned
            is_earned, context = self._check_badge_condition(
                db, user_id, definition, trigger_context
            )

            if is_earned:
                # Award the badge
                new_badge = UserBadge(
                    user_id=user_id,
                    badge_id=badge_id,
                    context=context
                )
                db.add(new_badge)

                newly_awarded.append({
                    "id": definition.id,
                    "name": definition.name,
                    "description": definition.description,
                    "icon": definition.icon,
                    "category": definition.category
                })

                logger.info(f"Awarded badge {badge_id} to user {user_id}")

        if newly_awarded:
            db.commit()

        return newly_awarded

    def _check_badge_condition(
        self,
        db: Session,
        user_id: str,
        badge: BadgeDefinition,
        trigger_context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check if a badge condition is met. Returns (is_earned, context)."""

        if badge.category == "streak":
            return self._check_streak_badge(db, user_id, badge)

        elif badge.category == "volume":
            return self._check_volume_badge(db, user_id, badge)

        elif badge.category == "accuracy" and badge.id.startswith("accuracy_streak"):
            return self._check_accuracy_streak_badge(db, user_id, badge)

        elif badge.category == "accuracy":
            return self._check_overall_accuracy_badge(db, user_id, badge)

        elif badge.category == "milestone":
            return self._check_score_badge(db, user_id, badge)

        elif badge.id == "first_question":
            return self._check_first_question_badge(db, user_id)

        elif badge.id == "first_perfect_session":
            return self._check_perfect_session_badge(db, user_id)

        elif badge.id == "night_owl":
            return self._check_time_badge(db, user_id, 0, 5)

        elif badge.id == "early_bird":
            return self._check_time_badge(db, user_id, 5, 7)

        return False, None

    def _check_streak_badge(
        self,
        db: Session,
        user_id: str,
        badge: BadgeDefinition
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check streak badge conditions."""
        engagement = db.query(UserEngagementScore).filter(
            UserEngagementScore.user_id == user_id
        ).first()

        if not engagement:
            return False, None

        target = int(badge.id.split("_")[1])
        current = engagement.streak_current or 0

        if current >= target:
            return True, {"streak": current}

        return False, None

    def _check_volume_badge(
        self,
        db: Session,
        user_id: str,
        badge: BadgeDefinition
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check question volume badge conditions."""
        count = db.query(func.count(QuestionAttempt.id)).filter(
            QuestionAttempt.user_id == user_id
        ).scalar() or 0

        target = int(badge.id.split("_")[1])

        if count >= target:
            return True, {"questions_answered": count}

        return False, None

    def _check_accuracy_streak_badge(
        self,
        db: Session,
        user_id: str,
        badge: BadgeDefinition
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check consecutive correct answers badge."""
        target = int(badge.id.split("_")[2])

        # Get recent attempts ordered by time
        recent = db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id
        ).order_by(QuestionAttempt.attempted_at.desc()).limit(target).all()

        if len(recent) < target:
            return False, None

        # Check if all are correct
        all_correct = all(a.is_correct for a in recent)

        if all_correct:
            return True, {"consecutive_correct": target}

        return False, None

    def _check_overall_accuracy_badge(
        self,
        db: Session,
        user_id: str,
        badge: BadgeDefinition
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check overall accuracy badge conditions."""
        target_accuracy = int(badge.id.split("_")[1])

        # Minimum questions required
        min_questions = {70: 100, 80: 200, 90: 300}.get(target_accuracy, 100)

        total = db.query(func.count(QuestionAttempt.id)).filter(
            QuestionAttempt.user_id == user_id
        ).scalar() or 0

        if total < min_questions:
            return False, None

        correct = db.query(func.count(QuestionAttempt.id)).filter(
            and_(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.is_correct == True
            )
        ).scalar() or 0

        accuracy = (correct / total) * 100 if total > 0 else 0

        if accuracy >= target_accuracy:
            return True, {"accuracy": round(accuracy, 1), "total_questions": total}

        return False, None

    def _check_score_badge(
        self,
        db: Session,
        user_id: str,
        badge: BadgeDefinition
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check predicted score badge conditions."""
        performance = db.query(UserPerformance).filter(
            UserPerformance.user_id == user_id
        ).order_by(UserPerformance.calculated_at.desc()).first()

        if not performance or not performance.predicted_score:
            return False, None

        target = int(badge.id.split("_")[1])

        if performance.predicted_score >= target:
            return True, {"predicted_score": performance.predicted_score}

        return False, None

    def _check_first_question_badge(
        self,
        db: Session,
        user_id: str
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check if user answered their first question."""
        count = db.query(func.count(QuestionAttempt.id)).filter(
            QuestionAttempt.user_id == user_id
        ).scalar() or 0

        if count >= 1:
            return True, {"questions_answered": count}

        return False, None

    def _check_perfect_session_badge(
        self,
        db: Session,
        user_id: str
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check if user completed a perfect session."""
        perfect_session = db.query(StudySession).filter(
            and_(
                StudySession.user_id == user_id,
                StudySession.status == "completed",
                StudySession.accuracy == 100.0,
                StudySession.questions_answered >= 5  # Min 5 questions
            )
        ).first()

        if perfect_session:
            return True, {
                "session_id": perfect_session.id,
                "questions": perfect_session.questions_answered
            }

        return False, None

    def _check_time_badge(
        self,
        db: Session,
        user_id: str,
        start_hour: int,
        end_hour: int
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check if user studied during specific hours."""
        # Get attempts in the time range
        from sqlalchemy import extract

        attempt = db.query(QuestionAttempt).filter(
            and_(
                QuestionAttempt.user_id == user_id,
                extract('hour', QuestionAttempt.attempted_at) >= start_hour,
                extract('hour', QuestionAttempt.attempted_at) < end_hour
            )
        ).first()

        if attempt:
            return True, {"studied_at": attempt.attempted_at.strftime("%H:%M")}

        return False, None


# Singleton instance
_badge_service: Optional[BadgeService] = None


def get_badge_service() -> BadgeService:
    """Get the singleton BadgeService instance."""
    global _badge_service
    if _badge_service is None:
        _badge_service = BadgeService()
    return _badge_service
