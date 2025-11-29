"""
Adaptive Question Selection Engine.

THIS IS WHERE 252 SCORERS BECOME 285+ SCORERS.

Zero API cost - pure local computation using:
- Weak area detection
- Spaced repetition scheduling
- Difficulty targeting (70% accuracy zone)
- Performance plateau detection

The 285+ Secret:
A student who masters EVERY question in their weak areas will score 285+.
This algorithm FORCES them to study weak areas - they can't avoid them.

Usage:
    from app.services.adaptive_engine import adaptive_engine

    # Get optimal next question for a user
    question = await adaptive_engine.select_next_question(user_id, specialty)

    # Get user's weak areas
    weaknesses = await adaptive_engine.identify_weaknesses(user_id, specialty)

    # Check for learning plateau
    if await adaptive_engine.detect_plateau(user_id):
        # Trigger intervention
        pass
"""

import logging
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import random
import math

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.models import Question, QuestionAttempt, User

logger = logging.getLogger(__name__)


class InvalidUserIdError(Exception):
    """Raised when user_id is invalid or not authorized."""
    pass


def validate_user_id(user_id: str) -> str:
    """
    Validate and sanitize user_id.

    Args:
        user_id: The user ID to validate

    Returns:
        Sanitized user_id string

    Raises:
        InvalidUserIdError: If user_id is invalid
    """
    if not user_id:
        raise InvalidUserIdError("user_id is required")

    if not isinstance(user_id, str):
        raise InvalidUserIdError("user_id must be a string")

    # Trim whitespace
    user_id = user_id.strip()

    if not user_id:
        raise InvalidUserIdError("user_id cannot be empty")

    # Check length
    if len(user_id) > 100:
        raise InvalidUserIdError("user_id too long")

    # Try to validate as UUID (common format)
    try:
        uuid.UUID(user_id)
        return user_id
    except ValueError:
        pass

    # Allow alphanumeric with hyphens/underscores (Clerk-style IDs)
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        raise InvalidUserIdError("user_id contains invalid characters")

    return user_id


class LearningStage(Enum):
    """Spaced repetition learning stages."""
    NEW = "new"  # Never seen
    LEARNING = "learning"  # Seen 1-2 times, not mastered
    YOUNG = "young"  # Correct 2-3 times, still fragile
    MATURE = "mature"  # Correct 4+ times, stable memory
    MASTERED = "mastered"  # Correct 5+ times with long intervals


@dataclass
class QuestionCandidate:
    """A question being considered for selection."""
    question_id: str
    topic: str
    difficulty: str
    priority_score: float
    reason: str
    due_for_review: bool
    user_accuracy: Optional[float]
    attempts_count: int


@dataclass
class UserWeakness:
    """A topic where the user needs improvement."""
    topic: str
    accuracy: float
    attempts: int
    last_attempt: Optional[datetime]
    severity: str  # "critical" (<50%), "weak" (50-70%), "developing" (70-80%)


class AdaptiveEngine:
    """
    Adaptive question selection engine for 285+ scorer production.

    The algorithm prioritizes:
    1. Weak areas (topics with <70% accuracy)
    2. Due reviews (spaced repetition schedule)
    3. Optimal difficulty (70% target accuracy zone)
    4. Coverage (ensuring all topics are touched)

    This is the core differentiator - not the questions themselves,
    but HOW we route students to the right questions at the right time.
    """

    # Configuration
    WEAK_AREA_THRESHOLD = 0.70  # Below 70% = weak
    CRITICAL_THRESHOLD = 0.50  # Below 50% = critical
    TARGET_ACCURACY = 0.70  # Optimal learning zone
    MIN_ATTEMPTS_FOR_ANALYSIS = 3  # Need 3+ attempts to judge

    # Spaced repetition intervals (in days)
    REVIEW_INTERVALS = {
        LearningStage.NEW: 0,
        LearningStage.LEARNING: 1,
        LearningStage.YOUNG: 3,
        LearningStage.MATURE: 7,
        LearningStage.MASTERED: 21
    }

    # Priority weights
    WEIGHTS = {
        "weak_area": 3.0,  # Highest priority
        "due_review": 2.5,
        "difficulty_match": 1.5,
        "coverage": 1.0,
        "recency": 0.5
    }

    def __init__(self, db: Session):
        self.db = db

    async def select_next_question(
        self,
        user_id: str,
        specialty: str,
        exclude_ids: List[str] = None
    ) -> Optional[Question]:
        """
        Select the optimal next question for maximum learning.

        This is the 285+ secret: Always push into weak areas.

        Args:
            user_id: The user's ID (must be validated)
            specialty: Current specialty (e.g., "internal_medicine")
            exclude_ids: Question IDs to exclude (e.g., current session)

        Returns:
            The optimal next Question, or None if no questions available

        Raises:
            InvalidUserIdError: If user_id is invalid
        """
        # Validate user_id to prevent injection and ensure authorization
        user_id = validate_user_id(user_id)

        exclude_ids = exclude_ids or []

        # Step 1: Identify weak areas
        weaknesses = await self.identify_weaknesses(user_id, specialty)

        # Step 2: Get candidate questions
        candidates = await self._get_candidates(
            user_id, specialty, weaknesses, exclude_ids
        )

        if not candidates:
            # Fallback: any unseen question in specialty
            return await self._get_any_unseen(user_id, specialty, exclude_ids)

        # Step 3: Score and rank candidates
        scored = self._score_candidates(candidates, weaknesses)

        # Step 4: Select with weighted randomness (top 3)
        top_candidates = sorted(scored, key=lambda x: x.priority_score, reverse=True)[:3]

        if not top_candidates:
            return None

        # Weighted random selection from top 3
        weights = [c.priority_score for c in top_candidates]
        total = sum(weights)
        weights = [w / total for w in weights]

        selected = random.choices(top_candidates, weights=weights, k=1)[0]

        logger.info(
            f"Selected question {selected.question_id} for user {user_id}: "
            f"{selected.reason} (score: {selected.priority_score:.2f})"
        )

        return self.db.query(Question).filter(
            Question.id == selected.question_id
        ).first()

    async def identify_weaknesses(
        self,
        user_id: str,
        specialty: str = None
    ) -> List[UserWeakness]:
        """
        Identify topics where user accuracy is below threshold.

        Args:
            user_id: The user's ID (will be validated)
            specialty: Optional specialty filter

        Returns:
            List of UserWeakness objects sorted by severity

        Raises:
            InvalidUserIdError: If user_id is invalid
        """
        # Validate user_id
        user_id = validate_user_id(user_id)

        # Query attempts grouped by topic
        query = self.db.query(
            Question.extra_data['topic'].label('topic'),
            func.count(QuestionAttempt.id).label('attempts'),
            func.avg(
                func.cast(QuestionAttempt.is_correct, func.Float)
            ).label('accuracy'),
            func.max(QuestionAttempt.attempted_at).label('last_attempt')
        ).join(
            QuestionAttempt, Question.id == QuestionAttempt.question_id
        ).filter(
            QuestionAttempt.user_id == user_id
        )

        if specialty:
            query = query.filter(Question.specialty == specialty)

        results = query.group_by(
            Question.extra_data['topic']
        ).having(
            func.count(QuestionAttempt.id) >= self.MIN_ATTEMPTS_FOR_ANALYSIS
        ).all()

        weaknesses = []
        for row in results:
            accuracy = float(row.accuracy) if row.accuracy else 0

            if accuracy < self.WEAK_AREA_THRESHOLD:
                severity = "critical" if accuracy < self.CRITICAL_THRESHOLD else "weak"
                if accuracy >= 0.6:
                    severity = "developing"

                weaknesses.append(UserWeakness(
                    topic=row.topic or "general",
                    accuracy=accuracy,
                    attempts=row.attempts,
                    last_attempt=row.last_attempt,
                    severity=severity
                ))

        # Sort by severity (critical first) then by accuracy (lowest first)
        severity_order = {"critical": 0, "weak": 1, "developing": 2}
        weaknesses.sort(key=lambda w: (severity_order[w.severity], w.accuracy))

        return weaknesses

    async def detect_plateau(
        self,
        user_id: str,
        window_days: int = 14,
        min_sessions: int = 5
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect when user stops improving.

        A plateau indicates the student may need:
        - Different question types
        - Topic change
        - Difficulty adjustment
        - Study strategy review

        Args:
            user_id: The user's ID
            window_days: Number of days to analyze
            min_sessions: Minimum sessions needed for analysis

        Returns:
            Tuple of (is_plateau, details_dict)
        """
        cutoff = datetime.utcnow() - timedelta(days=window_days)

        # Get daily accuracy over the window
        daily_stats = self.db.query(
            func.date(QuestionAttempt.attempted_at).label('date'),
            func.count(QuestionAttempt.id).label('attempts'),
            func.avg(
                func.cast(QuestionAttempt.is_correct, func.Float)
            ).label('accuracy')
        ).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= cutoff
        ).group_by(
            func.date(QuestionAttempt.attempted_at)
        ).order_by('date').all()

        if len(daily_stats) < min_sessions:
            return False, {"reason": "insufficient_data", "sessions": len(daily_stats)}

        # Calculate improvement trend
        accuracies = [float(s.accuracy) for s in daily_stats if s.accuracy]

        if len(accuracies) < 3:
            return False, {"reason": "insufficient_accuracy_data"}

        # Linear regression for trend
        n = len(accuracies)
        x_mean = (n - 1) / 2
        y_mean = sum(accuracies) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(accuracies))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Plateau if improvement < 0.5% per session over window
        is_plateau = abs(slope) < 0.005

        # Also check if variance is very low (stuck at same level)
        variance = sum((a - y_mean) ** 2 for a in accuracies) / n
        is_stuck = variance < 0.01

        details = {
            "sessions": len(daily_stats),
            "average_accuracy": round(y_mean * 100, 1),
            "improvement_per_session": round(slope * 100, 2),
            "variance": round(variance, 4),
            "is_stuck": is_stuck
        }

        return is_plateau or is_stuck, details

    async def get_learning_stage(
        self,
        user_id: str,
        question_id: str
    ) -> LearningStage:
        """
        Determine the learning stage for a question.
        """
        attempts = self.db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.question_id == question_id
        ).order_by(QuestionAttempt.attempted_at.desc()).all()

        if not attempts:
            return LearningStage.NEW

        correct_count = sum(1 for a in attempts if a.is_correct)
        total_count = len(attempts)

        if total_count <= 2:
            return LearningStage.LEARNING
        elif correct_count >= 5 and (correct_count / total_count) >= 0.8:
            return LearningStage.MASTERED
        elif correct_count >= 4 and (correct_count / total_count) >= 0.7:
            return LearningStage.MATURE
        elif correct_count >= 2:
            return LearningStage.YOUNG
        else:
            return LearningStage.LEARNING

    async def is_due_for_review(
        self,
        user_id: str,
        question_id: str
    ) -> bool:
        """
        Check if a question is due for spaced repetition review.
        """
        last_attempt = self.db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.question_id == question_id
        ).order_by(QuestionAttempt.attempted_at.desc()).first()

        if not last_attempt:
            return True  # Never seen = due

        stage = await self.get_learning_stage(user_id, question_id)
        interval_days = self.REVIEW_INTERVALS[stage]

        due_date = last_attempt.attempted_at + timedelta(days=interval_days)
        return datetime.utcnow() >= due_date

    # Maximum candidates to consider
    MAX_CANDIDATES = 200

    async def _get_candidates(
        self,
        user_id: str,
        specialty: str,
        weaknesses: List[UserWeakness],
        exclude_ids: List[str]
    ) -> List[QuestionCandidate]:
        """
        Get candidate questions for selection using a single optimized query.

        This uses a JOIN to avoid N+1 queries when checking user attempts.
        """
        from sqlalchemy import case, literal

        candidates = []
        weak_topics = {w.topic for w in weaknesses}

        # Validate and sanitize exclude_ids
        if exclude_ids:
            exclude_ids = [str(id).strip() for id in exclude_ids if id]

        # SINGLE OPTIMIZED QUERY with LEFT JOIN and aggregation
        # This replaces the N+1 pattern of querying attempts for each question
        question_stats = self.db.query(
            Question.id,
            Question.difficulty_level,
            Question.extra_data,
            func.count(QuestionAttempt.id).label('attempts_count'),
            func.sum(
                case(
                    (QuestionAttempt.is_correct == True, 1),
                    else_=0
                )
            ).label('correct_count'),
            func.max(QuestionAttempt.attempted_at).label('last_attempt')
        ).outerjoin(
            QuestionAttempt,
            and_(
                Question.id == QuestionAttempt.question_id,
                QuestionAttempt.user_id == user_id
            )
        ).filter(
            Question.specialty == specialty,
            Question.content_status == "active"
        )

        if exclude_ids:
            question_stats = question_stats.filter(~Question.id.in_(exclude_ids))

        question_stats = question_stats.group_by(
            Question.id
        ).limit(self.MAX_CANDIDATES).all()

        now = datetime.utcnow()

        for row in question_stats:
            # Safely access extra_data
            topic = "general"
            if isinstance(row.extra_data, dict):
                topic = row.extra_data.get("topic", "general")

            attempts_count = row.attempts_count or 0
            correct_count = row.correct_count or 0

            # Calculate user accuracy
            user_accuracy = None
            if attempts_count > 0:
                user_accuracy = correct_count / attempts_count

            # Calculate if due for review (inline, avoiding another query)
            due = True  # New questions are always due
            if row.last_attempt and attempts_count > 0:
                # Estimate learning stage based on correct rate
                if attempts_count >= 5 and user_accuracy and user_accuracy >= 0.8:
                    interval_days = 21  # Mastered
                elif attempts_count >= 4 and user_accuracy and user_accuracy >= 0.7:
                    interval_days = 7  # Mature
                elif correct_count >= 2:
                    interval_days = 3  # Young
                else:
                    interval_days = 1  # Learning

                due_date = row.last_attempt + timedelta(days=interval_days)
                due = now >= due_date

            # Determine reason for selection
            if topic in weak_topics:
                reason = f"Weak area: {topic}"
            elif due and attempts_count > 0:
                reason = "Due for spaced review"
            elif attempts_count == 0:
                reason = "New question"
            else:
                reason = "Coverage"

            candidates.append(QuestionCandidate(
                question_id=str(row.id),
                topic=topic,
                difficulty=row.difficulty_level or "medium",
                priority_score=0,  # Will be calculated
                reason=reason,
                due_for_review=due,
                user_accuracy=user_accuracy,
                attempts_count=attempts_count
            ))

        return candidates

    def _score_candidates(
        self,
        candidates: List[QuestionCandidate],
        weaknesses: List[UserWeakness]
    ) -> List[QuestionCandidate]:
        """
        Score each candidate question for priority selection.
        """
        weak_topics = {w.topic: w for w in weaknesses}

        for c in candidates:
            score = 0.0

            # Weak area bonus
            if c.topic in weak_topics:
                weakness = weak_topics[c.topic]
                if weakness.severity == "critical":
                    score += self.WEIGHTS["weak_area"] * 1.5
                elif weakness.severity == "weak":
                    score += self.WEIGHTS["weak_area"]
                else:
                    score += self.WEIGHTS["weak_area"] * 0.7

            # Due for review bonus
            if c.due_for_review:
                score += self.WEIGHTS["due_review"]

            # Difficulty match (prefer questions where user gets ~70%)
            if c.user_accuracy is not None:
                accuracy_diff = abs(c.user_accuracy - self.TARGET_ACCURACY)
                difficulty_score = max(0, 1 - accuracy_diff * 2)
                score += self.WEIGHTS["difficulty_match"] * difficulty_score

            # New question bonus (for coverage)
            if c.attempts_count == 0:
                score += self.WEIGHTS["coverage"]

            # Slight randomness to prevent predictability
            score += random.uniform(0, 0.3)

            c.priority_score = score

        return candidates

    async def _get_any_unseen(
        self,
        user_id: str,
        specialty: str,
        exclude_ids: List[str]
    ) -> Optional[Question]:
        """
        Fallback: get any unseen question in specialty.
        """
        # Subquery for seen question IDs
        seen_ids = self.db.query(QuestionAttempt.question_id).filter(
            QuestionAttempt.user_id == user_id
        ).subquery()

        question = self.db.query(Question).filter(
            Question.specialty == specialty,
            Question.content_status == "active",
            ~Question.id.in_(exclude_ids) if exclude_ids else True,
            ~Question.id.in_(seen_ids)
        ).order_by(func.random()).first()

        return question

    def get_study_recommendations(
        self,
        weaknesses: List[UserWeakness],
        plateau_detected: bool
    ) -> List[str]:
        """
        Generate actionable study recommendations.
        """
        recommendations = []

        if plateau_detected:
            recommendations.append(
                "Your progress has plateaued. Consider: "
                "(1) Taking a 1-day break, "
                "(2) Reviewing explanations more carefully, "
                "(3) Trying a different specialty temporarily."
            )

        critical = [w for w in weaknesses if w.severity == "critical"]
        if critical:
            topics = ", ".join(w.topic for w in critical[:3])
            recommendations.append(
                f"Focus on these critical weak areas today: {topics}"
            )

        weak = [w for w in weaknesses if w.severity == "weak"]
        if weak and not critical:
            topics = ", ".join(w.topic for w in weak[:3])
            recommendations.append(
                f"Good progress! Continue strengthening: {topics}"
            )

        if not weaknesses:
            recommendations.append(
                "Excellent! No significant weak areas detected. "
                "Continue with spaced review to maintain mastery."
            )

        return recommendations


def get_adaptive_engine(db: Session) -> AdaptiveEngine:
    """Factory function to create an AdaptiveEngine instance."""
    return AdaptiveEngine(db)
