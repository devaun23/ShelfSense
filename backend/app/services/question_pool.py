"""
Question Pool Service for Instant Question Delivery

Maintains a pre-generated pool of AI questions for instant delivery.
Background process replenishes pool when it runs low.

Architecture:
1. QuestionPool table stores ready-to-serve AI questions
2. get_instant_question() returns immediately from pool
3. Background worker replenishes pool based on specialty distribution
4. Specialty-specific pools ensure balanced content

Guidelines followed:
- Occam's Razor: Simple pool/queue pattern
- 3-Second Feedback: Questions served instantly
- Adaptive First: Pool weighted by USMLE specialty distribution
- ALWAYS RUN TASKS SIMULTANEOUSLY: Background replenishment
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.models import Question, generate_uuid
from app.database import SessionLocal

logger = logging.getLogger(__name__)
from app.services.step2ck_content_outline import (
    DISCIPLINE_DISTRIBUTION,
    get_weighted_specialty,
    get_high_yield_topic,
)
from app.services.adaptive import get_user_difficulty_target

# Pool configuration
MIN_POOL_SIZE = 20  # Minimum questions per specialty
TARGET_POOL_SIZE = 50  # Target questions per specialty
REPLENISH_THRESHOLD = 10  # Trigger replenishment when below this
REPLENISH_BATCH_SIZE = 5  # Generate this many at once

# Specialty mapping for pool keys
SPECIALTIES = list(DISCIPLINE_DISTRIBUTION.keys())


class QuestionPoolManager:
    """
    Manages pre-generated question pool for instant delivery.

    Design principles:
    - Questions pre-generated in background
    - Instant retrieval (<100ms)
    - Specialty-weighted distribution
    - Automatic replenishment
    """

    def __init__(self):
        self._replenish_lock = threading.Lock()
        self._is_replenishing = False

    def get_pool_stats(self, db: Session) -> Dict[str, int]:
        """Get count of available questions per specialty in pool."""
        stats = {}

        for specialty in SPECIALTIES:
            count = db.query(Question).filter(
                Question.source.like(f"AI Pool - {specialty}%"),
                Question.rejected == False
            ).count()
            stats[specialty] = count

        # Also count general pool
        general_count = db.query(Question).filter(
            Question.source.like("AI Pool%"),
            Question.rejected == False
        ).count()
        stats["total"] = general_count

        return stats

    def get_instant_question(
        self,
        db: Session,
        specialty: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Question]:
        """
        Get a question instantly from the pre-generated pool.

        Args:
            db: Database session
            specialty: Optional specialty filter
            user_id: Optional user ID to exclude already-answered questions

        Returns:
            Question from pool, or None if pool is empty
        """
        # Build query for pool questions
        query = db.query(Question).filter(
            Question.source.like("AI Pool%"),
            Question.rejected == False
        )

        # Filter by specialty if specified
        if specialty:
            query = query.filter(Question.source.like(f"AI Pool - {specialty}%"))

        # Exclude questions user has already answered
        if user_id:
            from app.models.models import QuestionAttempt
            attempted_ids = db.query(QuestionAttempt.question_id).filter(
                QuestionAttempt.user_id == user_id
            ).subquery()
            query = query.filter(~Question.id.in_(attempted_ids))

        # Get random question from pool (weighted by recency)
        question = query.order_by(func.random()).first()

        if question:
            # Mark as served by updating source (move out of pool)
            question.source = question.source.replace("AI Pool", "AI Generated")
            db.commit()

            # Trigger background replenishment if pool is low
            self._check_and_replenish(specialty)

        return question

    def add_to_pool(
        self,
        db: Session,
        question_data: Dict,
        specialty: str
    ) -> Question:
        """
        Add a generated question to the pool.

        Args:
            db: Database session
            question_data: Generated question dictionary
            specialty: Specialty for this question

        Returns:
            Saved Question object
        """
        question = Question(
            id=generate_uuid(),
            vignette=question_data["vignette"],
            answer_key=question_data["answer_key"],
            choices=question_data["choices"],
            explanation=question_data.get("explanation"),
            source=f"AI Pool - {specialty}",
            recency_weight=1.0,
            recency_tier=1,
            extra_data={
                "ai_generated": True,
                "specialty": specialty,
                "pooled_at": datetime.utcnow().isoformat(),
                "metadata": question_data.get("metadata", {})
            }
        )

        db.add(question)
        db.commit()
        db.refresh(question)

        return question

    def _check_and_replenish(self, specialty: Optional[str] = None):
        """Check if pool needs replenishment and trigger background job."""
        if self._is_replenishing:
            return

        def replenish_async():
            self._is_replenishing = True
            db = SessionLocal()
            try:
                stats = self.get_pool_stats(db)

                # Check each specialty
                for spec in SPECIALTIES:
                    if stats.get(spec, 0) < REPLENISH_THRESHOLD:
                        logger.info("Pool %s low (%d), replenishing...", spec, stats.get(spec, 0))
                        self._replenish_specialty(db, spec, REPLENISH_BATCH_SIZE)

            except Exception as e:
                logger.error("Pool replenishment error: %s", e, exc_info=True)
            finally:
                db.close()
                self._is_replenishing = False

        # Launch in background thread
        thread = threading.Thread(target=replenish_async, daemon=True)
        thread.start()

    def _replenish_specialty(self, db: Session, specialty: str, count: int):
        """Generate questions for a specific specialty using batch generation."""
        from app.services.question_agent import generate_questions_batch

        try:
            # Use batch generation for efficiency
            logger.info("Batch generating %d %s questions...", count, specialty)
            questions = generate_questions_batch(
                db,
                count=count,
                specialty=specialty,
                difficulty="medium"  # Default to medium for pool
            )

            for i, question_data in enumerate(questions):
                self.add_to_pool(db, question_data, specialty)
                logger.debug("Added %s question %d/%d", specialty, i+1, len(questions))

            logger.info("Successfully added %d/%d %s questions", len(questions), count, specialty)

        except Exception as e:
            logger.error("Batch generation failed for %s: %s", specialty, e, exc_info=True)
            # Fallback to sequential generation
            from app.services.question_agent import QuestionGenerationAgent
            agent = QuestionGenerationAgent(db)

            for i in range(count):
                try:
                    topic = get_high_yield_topic(specialty)
                    question_data = agent.generate_question(
                        specialty=specialty,
                        topic=topic,
                        max_retries=1
                    )
                    self.add_to_pool(db, question_data, specialty)
                    logger.debug("Added %s question %d/%d (fallback)", specialty, i+1, count)
                except Exception as e2:
                    logger.warning("Failed to generate %s question: %s", specialty, e2)
                    continue

    def warm_pool(self, target_per_specialty: int = MIN_POOL_SIZE):
        """
        Warm up the pool with initial questions.
        Run this at startup or via management command.

        Args:
            target_per_specialty: Number of questions per specialty to generate
        """
        logger.info("Warming pool with %d questions per specialty...", target_per_specialty)

        db = SessionLocal()
        try:
            stats = self.get_pool_stats(db)

            for specialty in SPECIALTIES:
                current = stats.get(specialty, 0)
                needed = max(0, target_per_specialty - current)

                if needed > 0:
                    logger.info("Generating %d questions for %s...", needed, specialty)
                    self._replenish_specialty(db, specialty, needed)

            final_stats = self.get_pool_stats(db)
            logger.info("Pool warmed. Final stats: %s", final_stats)

        finally:
            db.close()


# Singleton instance
_pool_manager = None


def get_pool_manager() -> QuestionPoolManager:
    """Get or create the singleton pool manager."""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = QuestionPoolManager()
    return _pool_manager


def get_instant_question(
    db: Session,
    specialty: Optional[str] = None,
    user_id: Optional[str] = None
) -> Optional[Question]:
    """
    Get a question instantly from the pre-generated pool.

    This is the main entry point for instant question delivery.
    Falls back to on-demand generation if pool is empty.

    Args:
        db: Database session
        specialty: Optional specialty filter
        user_id: Optional user ID for personalization (affects difficulty)

    Returns:
        Question object (instant from pool, or generated on-demand)
    """
    manager = get_pool_manager()

    # Try to get from pool first (instant)
    question = manager.get_instant_question(db, specialty, user_id)

    if question:
        logger.debug("Served question instantly from pool")
        return question

    # Pool empty - generate on-demand (slower, but rare)
    logger.info("Pool empty, generating on-demand...")
    from app.services.question_agent import generate_question_with_agent
    from app.services.question_generator import save_generated_question

    # Get user's difficulty target if user_id provided
    difficulty = "medium"
    if user_id:
        try:
            difficulty_info = get_user_difficulty_target(db, user_id)
            difficulty = difficulty_info.get("difficulty_level", "medium")
            logger.debug("User difficulty target: %s (accuracy: %.1f%%)", difficulty, difficulty_info.get('accuracy', 0) * 100)
        except Exception as e:
            logger.warning("Could not get user difficulty: %s", e)

    try:
        question_data = generate_question_with_agent(db, specialty=specialty, difficulty=difficulty)
        question = save_generated_question(db, question_data)
        return question
    except Exception as e:
        logger.error("On-demand generation failed: %s", e, exc_info=True)
        return None


def warm_pool_async(target_per_specialty: int = MIN_POOL_SIZE):
    """
    Warm the pool in background thread.
    Call this at application startup.
    """
    def warm():
        manager = get_pool_manager()
        manager.warm_pool(target_per_specialty)

    thread = threading.Thread(target=warm, daemon=True)
    thread.start()
    logger.info("Pool warming started in background")


def get_pool_stats(db: Session) -> Dict[str, int]:
    """Get current pool statistics."""
    manager = get_pool_manager()
    return manager.get_pool_stats(db)
