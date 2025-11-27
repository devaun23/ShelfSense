"""
Advanced Learning Engine

Implements 5 key algorithm improvements:
1. Per-specialty difficulty tracking
2. Personalized SM-2 intervals (adaptive retention)
3. Interleaving strategy for optimal learning mix
4. Ebbinghaus forgetting curve model
5. Confidence-weighted question selection

This module provides the core algorithms for adaptive, personalized learning.
"""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, Integer, or_

from app.models.models import (
    Question, QuestionAttempt, ScheduledReview,
    UserSpecialtyDifficulty, UserRetentionMetrics,
    LearningSessionMix, ConceptRetention
)


# =============================================================================
# GAP 1: PER-SPECIALTY DIFFICULTY TRACKING
# =============================================================================

def get_or_create_specialty_difficulty(
    db: Session,
    user_id: str,
    specialty: str
) -> UserSpecialtyDifficulty:
    """Get or create a specialty difficulty record for a user."""
    record = db.query(UserSpecialtyDifficulty).filter_by(
        user_id=user_id,
        specialty=specialty
    ).first()

    if not record:
        record = UserSpecialtyDifficulty(
            user_id=user_id,
            specialty=specialty
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return record


def update_specialty_difficulty(
    db: Session,
    user_id: str,
    specialty: str,
    is_correct: bool
) -> UserSpecialtyDifficulty:
    """
    Update specialty difficulty after a question attempt.

    Algorithm:
    - Updates attempt counts and accuracy
    - Calculates recent accuracy (last 10 questions)
    - Determines difficulty level based on specialty-specific performance
    - Tracks trend (improving/declining/stable)
    """
    record = get_or_create_specialty_difficulty(db, user_id, specialty)

    # Update counts
    record.total_attempts += 1
    if is_correct:
        record.correct_attempts += 1

    # Recalculate overall accuracy
    record.accuracy = record.correct_attempts / record.total_attempts

    # Calculate recent accuracy (last 10 questions for this specialty)
    recent_attempts = db.query(QuestionAttempt).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        QuestionAttempt.user_id == user_id,
        Question.specialty == specialty
    ).order_by(
        QuestionAttempt.attempted_at.desc()
    ).limit(10).all()

    if len(recent_attempts) >= 5:
        recent_correct = sum(1 for a in recent_attempts if a.is_correct)
        new_recent_accuracy = recent_correct / len(recent_attempts)

        # Determine trend
        if record.recent_accuracy is not None:
            diff = new_recent_accuracy - record.recent_accuracy
            if diff > 0.1:
                record.trend = "improving"
            elif diff < -0.1:
                record.trend = "declining"
            else:
                record.trend = "stable"

        record.recent_accuracy = new_recent_accuracy

    # Determine difficulty level based on specialty-specific accuracy
    accuracy = record.recent_accuracy or record.accuracy

    if accuracy >= 0.80:
        record.difficulty_level = "hard"
        record.target_correct_rate = 0.55
    elif accuracy >= 0.60:
        record.difficulty_level = "medium"
        record.target_correct_rate = 0.65
    else:
        record.difficulty_level = "easy"
        record.target_correct_rate = 0.75

    record.updated_at = datetime.utcnow()
    db.commit()

    return record


def get_specialty_difficulty_target(
    db: Session,
    user_id: str,
    specialty: str
) -> Dict:
    """
    Get difficulty target for a specific specialty.

    Returns:
        {
            "specialty": str,
            "difficulty_level": "easy" | "medium" | "hard",
            "target_correct_rate": float,
            "accuracy": float,
            "recent_accuracy": float,
            "trend": "improving" | "declining" | "stable",
            "total_attempts": int
        }
    """
    record = db.query(UserSpecialtyDifficulty).filter_by(
        user_id=user_id,
        specialty=specialty
    ).first()

    if not record or record.total_attempts < 5:
        # Not enough data - return default
        return {
            "specialty": specialty,
            "difficulty_level": "medium",
            "target_correct_rate": 0.65,
            "accuracy": record.accuracy if record else 0.0,
            "recent_accuracy": None,
            "trend": "stable",
            "total_attempts": record.total_attempts if record else 0
        }

    return {
        "specialty": specialty,
        "difficulty_level": record.difficulty_level,
        "target_correct_rate": record.target_correct_rate,
        "accuracy": record.accuracy,
        "recent_accuracy": record.recent_accuracy,
        "trend": record.trend,
        "total_attempts": record.total_attempts
    }


def get_all_specialty_difficulties(db: Session, user_id: str) -> List[Dict]:
    """Get difficulty levels for all specialties the user has attempted."""
    records = db.query(UserSpecialtyDifficulty).filter_by(
        user_id=user_id
    ).order_by(UserSpecialtyDifficulty.accuracy.asc()).all()

    return [
        {
            "specialty": r.specialty,
            "difficulty_level": r.difficulty_level,
            "accuracy": r.accuracy,
            "recent_accuracy": r.recent_accuracy,
            "trend": r.trend,
            "total_attempts": r.total_attempts
        }
        for r in records
    ]


# =============================================================================
# GAP 2: PERSONALIZED SM-2 INTERVALS
# =============================================================================

def get_or_create_retention_metrics(
    db: Session,
    user_id: str,
    specialty: Optional[str] = None
) -> UserRetentionMetrics:
    """Get or create retention metrics for a user (optionally per-specialty)."""
    query = db.query(UserRetentionMetrics).filter_by(user_id=user_id)
    if specialty:
        query = query.filter_by(specialty=specialty)
    else:
        query = query.filter(UserRetentionMetrics.specialty.is_(None))

    record = query.first()

    if not record:
        record = UserRetentionMetrics(
            user_id=user_id,
            specialty=specialty
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return record


def update_retention_metrics(
    db: Session,
    user_id: str,
    interval_days: int,
    is_correct: bool,
    specialty: Optional[str] = None
) -> UserRetentionMetrics:
    """
    Update retention metrics after a review.

    Uses SM-2 easiness factor adjustment:
    - EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    - where q is the quality of response (0-5, we map boolean to 0 or 5)
    """
    record = get_or_create_retention_metrics(db, user_id, specialty)

    # Map interval to bucket
    interval_bucket = None
    if interval_days <= 1:
        interval_bucket = "1d"
        record.reviews_1d += 1
        if is_correct:
            record.success_1d += 1
        record.retention_1d = record.success_1d / record.reviews_1d if record.reviews_1d > 0 else None
    elif interval_days <= 3:
        interval_bucket = "3d"
        record.reviews_3d += 1
        if is_correct:
            record.success_3d += 1
        record.retention_3d = record.success_3d / record.reviews_3d if record.reviews_3d > 0 else None
    elif interval_days <= 7:
        interval_bucket = "7d"
        record.reviews_7d += 1
        if is_correct:
            record.success_7d += 1
        record.retention_7d = record.success_7d / record.reviews_7d if record.reviews_7d > 0 else None
    elif interval_days <= 14:
        interval_bucket = "14d"
        record.reviews_14d += 1
        if is_correct:
            record.success_14d += 1
        record.retention_14d = record.success_14d / record.reviews_14d if record.reviews_14d > 0 else None
    else:
        interval_bucket = "30d"
        record.reviews_30d += 1
        if is_correct:
            record.success_30d += 1
        record.retention_30d = record.success_30d / record.reviews_30d if record.reviews_30d > 0 else None

    # Update easiness factor using SM-2 formula
    # q = 5 for correct, 0 for incorrect
    q = 5 if is_correct else 0
    ef_delta = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
    record.easiness_factor = max(1.3, record.easiness_factor + ef_delta)

    # Calculate optimal intervals based on retention data
    record.optimal_interval_multiplier = record.easiness_factor

    # If we have enough data, adjust first interval based on 1d retention
    if record.reviews_1d >= 10:
        if record.retention_1d and record.retention_1d < 0.7:
            # User forgets quickly - shorter first interval
            record.optimal_first_interval_days = 0.5
        elif record.retention_1d and record.retention_1d > 0.9:
            # User retains well - can start with longer interval
            record.optimal_first_interval_days = 2.0
        else:
            record.optimal_first_interval_days = 1.0

    record.updated_at = datetime.utcnow()
    db.commit()

    return record


def calculate_personalized_interval(
    db: Session,
    user_id: str,
    current_interval_days: int,
    is_correct: bool,
    specialty: Optional[str] = None
) -> float:
    """
    Calculate the next review interval using personalized SM-2.

    Returns:
        Next interval in days (float for sub-day precision)
    """
    metrics = get_or_create_retention_metrics(db, user_id, specialty)

    if not is_correct:
        # Reset to first interval on incorrect
        return metrics.optimal_first_interval_days

    # Use personalized multiplier
    if current_interval_days == 0:
        # First review
        return metrics.optimal_first_interval_days
    else:
        # Subsequent reviews - multiply by easiness factor
        next_interval = current_interval_days * metrics.optimal_interval_multiplier

        # Cap at 60 days
        return min(next_interval, 60.0)


def schedule_personalized_review(
    db: Session,
    user_id: str,
    question_id: str,
    is_correct: bool,
    source: Optional[str] = None,
    specialty: Optional[str] = None,
    confidence_level: Optional[int] = None
) -> ScheduledReview:
    """
    Schedule a review using personalized intervals.

    Enhances the basic SM-2 with:
    - User-specific easiness factors
    - Confidence-weighted intervals (Gap 5 integration)
    - Per-specialty retention tracking
    """
    existing = db.query(ScheduledReview).filter_by(
        user_id=user_id,
        question_id=question_id
    ).first()

    # Calculate current interval
    current_interval_days = 0
    if existing and existing.last_reviewed:
        days_since_review = (datetime.utcnow() - existing.last_reviewed).days
        current_interval_days = days_since_review

    # Get personalized next interval
    next_interval = calculate_personalized_interval(
        db, user_id, current_interval_days, is_correct, specialty
    )

    # Gap 5: Adjust interval based on confidence
    if confidence_level is not None:
        # High confidence + correct = can wait longer
        # Low confidence + correct = review sooner to reinforce
        # High confidence + wrong = definitely review soon
        if is_correct:
            if confidence_level >= 4:
                next_interval *= 1.2  # More confident, can wait
            elif confidence_level <= 2:
                next_interval *= 0.7  # Less confident, review sooner
        else:
            if confidence_level >= 4:
                next_interval *= 0.5  # Overconfident error - needs attention

    # Update retention metrics
    if current_interval_days > 0:
        update_retention_metrics(db, user_id, current_interval_days, is_correct, specialty)

    scheduled_for = datetime.utcnow() + timedelta(days=next_interval)

    # Determine learning stage
    if next_interval >= 30:
        stage = "Mastered"
    elif next_interval >= 7:
        stage = "Review"
    else:
        stage = "Learning"

    # Format interval string
    if next_interval < 1:
        interval_str = f"{int(next_interval * 24)}h"
    elif next_interval == int(next_interval):
        interval_str = f"{int(next_interval)}d"
    else:
        interval_str = f"{next_interval:.1f}d"

    if not existing:
        review = ScheduledReview(
            user_id=user_id,
            question_id=question_id,
            scheduled_for=scheduled_for,
            review_interval=interval_str,
            times_reviewed=1,
            learning_stage=stage,
            source=source,
            last_reviewed=datetime.utcnow()
        )
        db.add(review)
    else:
        existing.times_reviewed += 1
        existing.last_reviewed = datetime.utcnow()
        existing.scheduled_for = scheduled_for
        existing.review_interval = interval_str
        existing.learning_stage = stage
        review = existing

    db.commit()
    return review


# =============================================================================
# GAP 3: INTERLEAVING STRATEGY
# =============================================================================

def get_or_create_session_mix(db: Session, user_id: str) -> LearningSessionMix:
    """Get or create the learning session mix settings for a user."""
    record = db.query(LearningSessionMix).filter_by(user_id=user_id).first()

    if not record:
        record = LearningSessionMix(user_id=user_id)
        db.add(record)
        db.commit()
        db.refresh(record)

    return record


def calculate_optimal_mix(db: Session, user_id: str) -> Dict:
    """
    Calculate the optimal question mix based on user's learning patterns.

    Returns:
        {
            "new_ratio": float,
            "review_ratio": float,
            "specialty_ratios": {"specialty": float, ...},
            "difficulty_ratios": {"easy": float, "medium": float, "hard": float}
        }
    """
    mix = get_or_create_session_mix(db, user_id)

    # Get specialty performance data
    specialty_data = get_all_specialty_difficulties(db, user_id)

    # Calculate specialty ratios - prioritize weak areas
    specialty_ratios = {}
    if specialty_data:
        total_weight = 0
        for s in specialty_data:
            # Inverse accuracy weighting (worse performance = higher weight)
            weight = 1.0 - s["accuracy"] + 0.2  # Minimum 0.2 weight
            specialty_ratios[s["specialty"]] = weight
            total_weight += weight

        # Normalize to sum to 1
        if total_weight > 0:
            for spec in specialty_ratios:
                specialty_ratios[spec] /= total_weight

    # Get review vs new balance
    # Check how many reviews are due
    due_reviews = db.query(ScheduledReview).filter(
        ScheduledReview.user_id == user_id,
        ScheduledReview.scheduled_for <= datetime.utcnow()
    ).count()

    total_reviews = db.query(ScheduledReview).filter_by(user_id=user_id).count()

    if due_reviews > 20:
        # Many reviews due - prioritize them
        new_ratio = 0.3
        review_ratio = 0.7
    elif due_reviews > 10:
        new_ratio = 0.5
        review_ratio = 0.5
    else:
        # Few reviews - focus on new material
        new_ratio = 0.7
        review_ratio = 0.3

    # Calculate difficulty ratios based on overall performance
    total_attempts = db.query(QuestionAttempt).filter_by(user_id=user_id).count()
    correct_attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.is_correct == True
    ).count()

    if total_attempts > 0:
        accuracy = correct_attempts / total_attempts
        if accuracy >= 0.75:
            # Doing well - more hard questions
            difficulty_ratios = {"easy": 0.1, "medium": 0.4, "hard": 0.5}
        elif accuracy >= 0.60:
            # Average - balanced
            difficulty_ratios = {"easy": 0.2, "medium": 0.5, "hard": 0.3}
        else:
            # Struggling - more easy questions
            difficulty_ratios = {"easy": 0.4, "medium": 0.4, "hard": 0.2}
    else:
        difficulty_ratios = {"easy": 0.2, "medium": 0.5, "hard": 0.3}

    # Update stored mix
    mix.new_question_ratio = new_ratio
    mix.review_question_ratio = review_ratio
    mix.specialty_ratios = specialty_ratios
    mix.easy_ratio = difficulty_ratios["easy"]
    mix.medium_ratio = difficulty_ratios["medium"]
    mix.hard_ratio = difficulty_ratios["hard"]
    mix.updated_at = datetime.utcnow()
    db.commit()

    return {
        "new_ratio": new_ratio,
        "review_ratio": review_ratio,
        "specialty_ratios": specialty_ratios,
        "difficulty_ratios": difficulty_ratios
    }


def select_interleaved_question(
    db: Session,
    user_id: str,
    session_questions: List[str] = None
) -> Tuple[Optional[Question], str]:
    """
    Select the next question using interleaving strategy.

    Returns:
        (Question, selection_type) where selection_type is "new", "review", or "none"
    """
    mix = calculate_optimal_mix(db, user_id)
    session_questions = session_questions or []

    # Decide: new question or review?
    if random.random() < mix["review_ratio"]:
        # Try to get a review question
        reviews = db.query(ScheduledReview).filter(
            ScheduledReview.user_id == user_id,
            ScheduledReview.scheduled_for <= datetime.utcnow(),
            ScheduledReview.question_id.notin_(session_questions) if session_questions else True
        ).order_by(
            ScheduledReview.scheduled_for.asc()
        ).limit(10).all()

        if reviews:
            # Select from reviews, weighted by overdue-ness
            selected_review = random.choice(reviews)
            question = db.query(Question).get(selected_review.question_id)
            if question:
                return question, "review"

    # Get a new question with interleaving
    # First, select specialty based on ratios
    specialty_ratios = mix.get("specialty_ratios", {})
    selected_specialty = None

    if specialty_ratios:
        rand = random.random()
        cumulative = 0
        for spec, ratio in specialty_ratios.items():
            cumulative += ratio
            if rand <= cumulative:
                selected_specialty = spec
                break

    # Select difficulty based on ratios
    diff_ratios = mix["difficulty_ratios"]
    rand = random.random()
    if rand < diff_ratios["easy"]:
        selected_difficulty = "easy"
    elif rand < diff_ratios["easy"] + diff_ratios["medium"]:
        selected_difficulty = "medium"
    else:
        selected_difficulty = "hard"

    # Get attempted question IDs
    attempted_ids = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id
    ).all()
    attempted_ids = [q[0] for q in attempted_ids]

    # Build query for new question
    query = db.query(Question).filter(
        Question.id.notin_(attempted_ids) if attempted_ids else True,
        Question.id.notin_(session_questions) if session_questions else True,
        Question.rejected == False
    )

    if selected_specialty:
        query = query.filter(Question.specialty == selected_specialty)

    if selected_difficulty:
        query = query.filter(Question.difficulty_level == selected_difficulty)

    # Order by recency weight and limit
    query = query.order_by(Question.recency_weight.desc()).limit(20)
    candidates = query.all()

    if candidates:
        return random.choice(candidates), "new"

    # Fallback: any unanswered question
    fallback = db.query(Question).filter(
        Question.id.notin_(attempted_ids) if attempted_ids else True,
        Question.rejected == False
    ).order_by(Question.recency_weight.desc()).first()

    if fallback:
        return fallback, "new"

    return None, "none"


# =============================================================================
# GAP 4: EBBINGHAUS FORGETTING CURVE MODEL
# =============================================================================

def calculate_memory_strength(
    stability: float,
    time_since_review_days: float
) -> float:
    """
    Calculate current memory strength using Ebbinghaus forgetting curve.

    Formula: R = e^(-t/S)
    Where:
        R = retention (memory strength)
        t = time since last review
        S = stability (how long until 90% retention drops to ~36.8%)

    Args:
        stability: Memory stability factor (days)
        time_since_review_days: Days since last review

    Returns:
        Memory strength (0-1 scale, 1 = perfect retention)
    """
    if time_since_review_days <= 0:
        return 1.0

    return math.exp(-time_since_review_days / stability)


def update_concept_retention(
    db: Session,
    user_id: str,
    concept: str,
    is_correct: bool,
    specialty: Optional[str] = None,
    question_id: Optional[str] = None
) -> ConceptRetention:
    """
    Update concept retention after a review.

    Stability increases with successful recalls (spaced repetition effect).
    Stability decreases (resets) on failures.
    """
    record = db.query(ConceptRetention).filter_by(
        user_id=user_id,
        concept=concept
    ).first()

    now = datetime.utcnow()

    if not record:
        record = ConceptRetention(
            user_id=user_id,
            concept=concept,
            specialty=specialty,
            memory_strength=1.0 if is_correct else 0.5,
            stability=1.0,  # Start with 1 day stability
            last_reviewed=now,
            total_exposures=1,
            successful_recalls=1 if is_correct else 0,
            consecutive_correct=1 if is_correct else 0
        )
        if question_id:
            record.question_ids = [question_id]
        db.add(record)
    else:
        record.total_exposures += 1
        record.last_reviewed = now

        if is_correct:
            record.successful_recalls += 1
            record.consecutive_correct += 1
            record.last_correct = now

            # Increase stability with each successful recall
            # Stability grows faster with consecutive correct answers
            stability_gain = 1.0 + (0.5 * record.consecutive_correct)
            record.stability = min(record.stability * stability_gain, 365)  # Cap at 1 year
        else:
            record.consecutive_correct = 0
            record.last_incorrect = now

            # Reset stability on failure (but not completely)
            record.stability = max(record.stability * 0.5, 0.5)

        # Update memory strength to 1.0 (just reviewed)
        record.memory_strength = 1.0 if is_correct else 0.7

        # Add question ID if not already tracked
        if question_id:
            existing_ids = record.question_ids or []
            if question_id not in existing_ids:
                existing_ids.append(question_id)
                record.question_ids = existing_ids

    # Calculate next optimal review time (when retention drops to 90%)
    # R = 0.9 = e^(-t/S) => t = -S * ln(0.9)
    days_until_90_percent = -record.stability * math.log(0.9)
    record.next_optimal_review = now + timedelta(days=days_until_90_percent)
    record.predicted_retention = 1.0  # Just reviewed

    record.updated_at = now
    db.commit()

    return record


def get_concepts_needing_review(
    db: Session,
    user_id: str,
    min_retention: float = 0.7,
    limit: int = 20
) -> List[Dict]:
    """
    Get concepts whose predicted retention has dropped below threshold.

    Returns concepts sorted by urgency (lowest retention first).
    """
    concepts = db.query(ConceptRetention).filter_by(user_id=user_id).all()

    needing_review = []
    now = datetime.utcnow()

    for c in concepts:
        if c.last_reviewed:
            days_since = (now - c.last_reviewed).total_seconds() / 86400
            current_retention = calculate_memory_strength(c.stability, days_since)

            if current_retention < min_retention:
                needing_review.append({
                    "concept": c.concept,
                    "specialty": c.specialty,
                    "current_retention": current_retention,
                    "stability": c.stability,
                    "days_since_review": days_since,
                    "total_exposures": c.total_exposures,
                    "question_ids": c.question_ids
                })

    # Sort by retention (lowest first = most urgent)
    needing_review.sort(key=lambda x: x["current_retention"])

    return needing_review[:limit]


def update_all_concept_retentions(db: Session, user_id: str) -> int:
    """
    Batch update all concept retentions for a user (decay calculation).
    Called periodically or on session start.

    Returns number of concepts updated.
    """
    concepts = db.query(ConceptRetention).filter_by(user_id=user_id).all()
    now = datetime.utcnow()
    updated = 0

    for c in concepts:
        if c.last_reviewed:
            days_since = (now - c.last_reviewed).total_seconds() / 86400
            c.predicted_retention = calculate_memory_strength(c.stability, days_since)
            c.memory_strength = c.predicted_retention
            c.updated_at = now
            updated += 1

    db.commit()
    return updated


# =============================================================================
# GAP 5: CONFIDENCE-WEIGHTED QUESTION SELECTION
# =============================================================================

def calculate_confidence_calibration(db: Session, user_id: str) -> Dict:
    """
    Calculate how well-calibrated user's confidence is.

    Returns:
        {
            "calibration_score": float (0-100, higher = better calibrated),
            "overconfident_rate": float (% of high confidence wrong),
            "underconfident_rate": float (% of low confidence correct),
            "by_confidence": {1: {total, correct, accuracy}, ...}
        }
    """
    attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.confidence_level.isnot(None)
    ).all()

    if not attempts:
        return {
            "calibration_score": 50.0,
            "overconfident_rate": 0.0,
            "underconfident_rate": 0.0,
            "by_confidence": {}
        }

    by_confidence = {}
    for level in range(1, 6):
        level_attempts = [a for a in attempts if a.confidence_level == level]
        if level_attempts:
            correct = sum(1 for a in level_attempts if a.is_correct)
            by_confidence[level] = {
                "total": len(level_attempts),
                "correct": correct,
                "accuracy": correct / len(level_attempts)
            }

    # Calculate calibration score
    # Perfect calibration: confidence 1 = 20% correct, 5 = 100% correct
    expected = {1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 1.0}
    total_error = 0
    weights = 0

    for level, data in by_confidence.items():
        error = abs(data["accuracy"] - expected.get(level, 0.5))
        total_error += error * data["total"]
        weights += data["total"]

    avg_error = total_error / weights if weights > 0 else 0.5
    calibration_score = (1 - avg_error) * 100

    # Calculate over/under confidence rates
    high_conf_wrong = sum(
        1 for a in attempts
        if a.confidence_level >= 4 and not a.is_correct
    )
    high_conf_total = sum(
        1 for a in attempts if a.confidence_level >= 4
    )

    low_conf_correct = sum(
        1 for a in attempts
        if a.confidence_level <= 2 and a.is_correct
    )
    low_conf_total = sum(
        1 for a in attempts if a.confidence_level <= 2
    )

    return {
        "calibration_score": round(calibration_score, 1),
        "overconfident_rate": high_conf_wrong / high_conf_total if high_conf_total > 0 else 0.0,
        "underconfident_rate": low_conf_correct / low_conf_total if low_conf_total > 0 else 0.0,
        "by_confidence": by_confidence
    }


def select_confidence_weighted_question(
    db: Session,
    user_id: str,
    candidates: List[Question]
) -> Optional[Question]:
    """
    Select a question from candidates, weighted by user's confidence patterns.

    Prioritizes questions that:
    1. Match the difficulty level where user is overconfident (needs humbling)
    2. Come from specialties where user lacks confidence but performs well (needs encouragement)
    """
    if not candidates:
        return None

    calibration = calculate_confidence_calibration(db, user_id)

    # Get user's specialty performance
    specialty_data = {
        s["specialty"]: s
        for s in get_all_specialty_difficulties(db, user_id)
    }

    # Score each candidate
    scored_candidates = []
    for q in candidates:
        score = 1.0  # Base score

        # If user is overconfident, prioritize harder questions
        if calibration["overconfident_rate"] > 0.3:
            if q.difficulty_level == "hard":
                score *= 1.5

        # If user is underconfident, prioritize their strong areas
        if calibration["underconfident_rate"] > 0.3:
            spec_data = specialty_data.get(q.specialty, {})
            if spec_data.get("accuracy", 0) > 0.7:
                score *= 1.3  # Boost questions from strong areas

        # Slight randomization to avoid predictability
        score *= random.uniform(0.8, 1.2)

        scored_candidates.append((q, score))

    # Sort by score and pick from top candidates
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = scored_candidates[:max(1, len(scored_candidates) // 3)]

    return random.choice(top_candidates)[0]


# =============================================================================
# UNIFIED QUESTION SELECTION (COMBINES ALL GAPS)
# =============================================================================

def select_next_question_advanced(
    db: Session,
    user_id: str,
    session_questions: List[str] = None,
    use_interleaving: bool = True,
    use_confidence_weighting: bool = True
) -> Tuple[Optional[Question], Dict]:
    """
    Advanced question selection combining all 5 gap implementations.

    Returns:
        (Question, metadata) where metadata includes selection reasoning
    """
    session_questions = session_questions or []
    metadata = {
        "selection_type": None,
        "specialty": None,
        "difficulty": None,
        "algorithms_used": []
    }

    # Update concept retentions (decay calculation)
    update_all_concept_retentions(db, user_id)
    metadata["algorithms_used"].append("forgetting_curve_decay")

    # Check for urgent concept reviews (Gap 4)
    urgent_concepts = get_concepts_needing_review(db, user_id, min_retention=0.5, limit=5)
    if urgent_concepts and random.random() < 0.3:  # 30% chance to prioritize urgent concepts
        # Try to find a question for an urgent concept
        for concept_data in urgent_concepts:
            if concept_data.get("question_ids"):
                for qid in concept_data["question_ids"]:
                    if qid not in session_questions:
                        question = db.query(Question).get(qid)
                        if question and not question.rejected:
                            metadata["selection_type"] = "concept_review"
                            metadata["specialty"] = question.specialty
                            metadata["difficulty"] = question.difficulty_level
                            metadata["algorithms_used"].append("forgetting_curve_priority")
                            return question, metadata

    # Use interleaving strategy (Gap 3)
    if use_interleaving:
        question, selection_type = select_interleaved_question(db, user_id, session_questions)
        metadata["algorithms_used"].append("interleaving")

        if question:
            metadata["selection_type"] = selection_type
            metadata["specialty"] = question.specialty
            metadata["difficulty"] = question.difficulty_level

            # Apply confidence weighting if we have multiple candidates (Gap 5)
            if use_confidence_weighting and selection_type == "new":
                # Get similar candidates for confidence-weighted selection
                similar = db.query(Question).filter(
                    Question.specialty == question.specialty,
                    Question.difficulty_level == question.difficulty_level,
                    Question.id.notin_(session_questions),
                    Question.rejected == False
                ).limit(10).all()

                if len(similar) > 1:
                    question = select_confidence_weighted_question(db, user_id, similar)
                    metadata["algorithms_used"].append("confidence_weighting")

            return question, metadata

    return None, metadata


def process_answer_advanced(
    db: Session,
    user_id: str,
    question_id: str,
    is_correct: bool,
    confidence_level: Optional[int] = None,
    specialty: Optional[str] = None,
    concepts: Optional[List[str]] = None
) -> Dict:
    """
    Process an answer using all advanced algorithms.

    Updates:
    - Per-specialty difficulty (Gap 1)
    - Personalized SM-2 intervals (Gap 2)
    - Concept retention/forgetting curve (Gap 4)

    Returns processing results.
    """
    results = {
        "specialty_difficulty": None,
        "scheduled_review": None,
        "concept_retentions": []
    }

    # Get question for specialty if not provided
    if not specialty:
        question = db.query(Question).get(question_id)
        if question:
            specialty = question.specialty

    # Gap 1: Update specialty difficulty
    if specialty:
        spec_diff = update_specialty_difficulty(db, user_id, specialty, is_correct)
        results["specialty_difficulty"] = {
            "specialty": specialty,
            "new_difficulty": spec_diff.difficulty_level,
            "accuracy": spec_diff.accuracy,
            "trend": spec_diff.trend
        }

    # Gap 2: Schedule personalized review
    review = schedule_personalized_review(
        db, user_id, question_id, is_correct,
        specialty=specialty,
        confidence_level=confidence_level
    )
    results["scheduled_review"] = {
        "interval": review.review_interval,
        "scheduled_for": review.scheduled_for.isoformat(),
        "learning_stage": review.learning_stage
    }

    # Gap 4: Update concept retention
    if concepts:
        for concept in concepts:
            retention = update_concept_retention(
                db, user_id, concept, is_correct,
                specialty=specialty,
                question_id=question_id
            )
            results["concept_retentions"].append({
                "concept": concept,
                "stability": retention.stability,
                "next_review": retention.next_optimal_review.isoformat() if retention.next_optimal_review else None
            })

    return results
