"""
Massive Question Pool Service for INSTANT Question Delivery

This service maintains a large pool of 5,000+ pre-generated AI questions
organized by specialty and difficulty, ensuring every user request is
served instantly (<100ms) without any API latency.

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    QUESTION POOL (5,000+ questions)             │
├─────────────────────────────────────────────────────────────────┤
│  Per Specialty (8 specialties × 400 questions each):            │
│    - Easy: 100 questions                                        │
│    - Medium: 200 questions                                      │
│    - Hard: 100 questions                                        │
│                                                                 │
│  Adaptive Serving:                                              │
│    1. Get user's weakness profile (weak specialties)            │
│    2. Get user's difficulty target (based on accuracy)          │
│    3. Serve from matching pool bucket                           │
│    4. Exclude already-answered questions                        │
│                                                                 │
│  Background Replenishment:                                      │
│    - Runs continuously (every 5 minutes)                        │
│    - Generates 10-20 questions per cycle                        │
│    - Prioritizes low-stock specialty/difficulty combos          │
│    - Never blocks user requests                                 │
└─────────────────────────────────────────────────────────────────┘
"""

import os
import threading
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.models.models import Question, QuestionAttempt, generate_uuid
from app.database import SessionLocal

# =============================================================================
# POOL CONFIGURATION - SCALED UP FOR INSTANT DELIVERY
# =============================================================================

# Target pool sizes per specialty per difficulty
POOL_TARGETS = {
    "easy": 100,
    "medium": 200,
    "hard": 100,
}

# Minimum before triggering emergency replenishment
POOL_MINIMUMS = {
    "easy": 20,
    "medium": 50,
    "hard": 20,
}

# Replenishment batch sizes
REPLENISH_BATCH = {
    "easy": 10,
    "medium": 20,
    "hard": 10,
}

# All specialties following USMLE distribution
SPECIALTIES = [
    "Internal Medicine",
    "Surgery",
    "Pediatrics",
    "Psychiatry",
    "Obstetrics and Gynecology",
    "Family Medicine",
    "Emergency Medicine",
    "Preventive Medicine",
]

# USMLE specialty weights (for prioritizing generation)
SPECIALTY_WEIGHTS = {
    "Internal Medicine": 0.25,      # 25% of questions
    "Surgery": 0.15,                # 15%
    "Pediatrics": 0.13,             # 13%
    "Obstetrics and Gynecology": 0.12,  # 12%
    "Psychiatry": 0.10,             # 10%
    "Emergency Medicine": 0.10,     # 10%
    "Family Medicine": 0.08,        # 8%
    "Preventive Medicine": 0.07,    # 7%
}

# Pool source prefix for identification
POOL_SOURCE_PREFIX = "AI Pool"


def get_pool_source(specialty: str, difficulty: str) -> str:
    """Get the source string for pool questions."""
    return f"{POOL_SOURCE_PREFIX} - {specialty} - {difficulty}"


# =============================================================================
# POOL STATISTICS
# =============================================================================

def get_detailed_pool_stats(db: Session) -> Dict:
    """
    Get comprehensive pool statistics by specialty and difficulty.

    Returns:
        {
            "total": 1234,
            "by_specialty": {
                "Internal Medicine": {"easy": 50, "medium": 100, "hard": 40, "total": 190},
                ...
            },
            "low_stock": [("Surgery", "hard"), ...],
            "health": "healthy" | "warning" | "critical"
        }
    """
    stats = {
        "total": 0,
        "by_specialty": {},
        "low_stock": [],
        "health": "healthy"
    }

    for specialty in SPECIALTIES:
        specialty_stats = {"total": 0}

        for difficulty in ["easy", "medium", "hard"]:
            source_pattern = get_pool_source(specialty, difficulty)
            count = db.query(Question).filter(
                Question.source == source_pattern,
                Question.rejected == False
            ).count()

            specialty_stats[difficulty] = count
            specialty_stats["total"] += count
            stats["total"] += count

            # Check if below minimum
            if count < POOL_MINIMUMS[difficulty]:
                stats["low_stock"].append((specialty, difficulty, count))

        stats["by_specialty"][specialty] = specialty_stats

    # Determine overall health
    if len(stats["low_stock"]) == 0:
        stats["health"] = "healthy"
    elif len(stats["low_stock"]) < 5:
        stats["health"] = "warning"
    else:
        stats["health"] = "critical"

    return stats


def get_pool_gaps(db: Session) -> List[Tuple[str, str, int]]:
    """
    Find specialty/difficulty combinations that need more questions.

    Returns list of (specialty, difficulty, needed_count) sorted by priority.
    """
    gaps = []

    for specialty in SPECIALTIES:
        weight = SPECIALTY_WEIGHTS.get(specialty, 0.1)

        for difficulty in ["easy", "medium", "hard"]:
            source_pattern = get_pool_source(specialty, difficulty)
            current = db.query(Question).filter(
                Question.source == source_pattern,
                Question.rejected == False
            ).count()

            target = POOL_TARGETS[difficulty]
            needed = max(0, target - current)

            if needed > 0:
                # Priority based on specialty weight and how far below target
                priority = weight * (needed / target)
                gaps.append((specialty, difficulty, needed, priority))

    # Sort by priority (highest first)
    gaps.sort(key=lambda x: x[3], reverse=True)

    return [(g[0], g[1], g[2]) for g in gaps]


# =============================================================================
# INSTANT QUESTION SERVING
# =============================================================================

def get_instant_question_adaptive(
    db: Session,
    user_id: str,
    preferred_specialty: Optional[str] = None
) -> Optional[Question]:
    """
    Get a question instantly from pool, adaptively matched to user.

    This is the main entry point for instant question delivery.
    It considers:
    1. User's weak specialties (prioritize weak areas)
    2. User's current accuracy (determine difficulty)
    3. Questions user hasn't answered yet

    Args:
        db: Database session
        user_id: User ID for personalization
        preferred_specialty: Optional override for specialty

    Returns:
        Question matched to user's needs, or None if pool empty
    """
    from app.services.adaptive import get_user_difficulty_target, get_user_weakness_profile

    # Get user's weakness profile
    weakness_profile = get_user_weakness_profile(db, user_id)
    weak_specialties = weakness_profile.get("weak_specialties", [])

    # Get user's difficulty target
    difficulty_info = get_user_difficulty_target(db, user_id)
    target_difficulty = difficulty_info.get("difficulty_level", "medium")

    # Map difficulty levels
    difficulty_map = {
        "easy": "easy",
        "medium": "medium",
        "hard": "hard",
        "very_hard": "hard"  # Map very_hard to hard
    }
    difficulty = difficulty_map.get(target_difficulty, "medium")

    # Determine specialty to use
    if preferred_specialty:
        specialty = preferred_specialty
    elif weak_specialties:
        # 70% chance to target weak specialty
        if random.random() < 0.7:
            specialty = random.choice(weak_specialties)
        else:
            specialty = random.choice(SPECIALTIES)
    else:
        specialty = random.choice(SPECIALTIES)

    # Get question from pool
    question = _get_from_pool(db, user_id, specialty, difficulty)

    if question:
        return question

    # Fallback 1: Try same specialty, different difficulty
    for alt_difficulty in ["medium", "easy", "hard"]:
        if alt_difficulty != difficulty:
            question = _get_from_pool(db, user_id, specialty, alt_difficulty)
            if question:
                return question

    # Fallback 2: Try any specialty with target difficulty
    for alt_specialty in SPECIALTIES:
        if alt_specialty != specialty:
            question = _get_from_pool(db, user_id, alt_specialty, difficulty)
            if question:
                return question

    # Fallback 3: Get any available question
    return _get_any_from_pool(db, user_id)


def _get_from_pool(
    db: Session,
    user_id: str,
    specialty: str,
    difficulty: str
) -> Optional[Question]:
    """Get a specific question from pool bucket."""
    source_pattern = get_pool_source(specialty, difficulty)

    # Get IDs of questions user has already answered
    answered_ids = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id
    ).subquery()

    # Query for available question
    question = db.query(Question).filter(
        Question.source == source_pattern,
        Question.rejected == False,
        ~Question.id.in_(answered_ids)
    ).order_by(func.random()).first()

    if question:
        # Mark as served (update source to show it's been used)
        question.source = f"AI Generated - {specialty} - {difficulty}"
        db.commit()

        print(f"[MassivePool] Served {specialty}/{difficulty} question to user {user_id[:8]}")

        # Trigger background replenishment check
        _trigger_replenish_check(specialty, difficulty)

    return question


def _get_any_from_pool(db: Session, user_id: str) -> Optional[Question]:
    """Get any available question from pool (last resort fallback)."""
    answered_ids = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id
    ).subquery()

    question = db.query(Question).filter(
        Question.source.like(f"{POOL_SOURCE_PREFIX}%"),
        Question.rejected == False,
        ~Question.id.in_(answered_ids)
    ).order_by(func.random()).first()

    if question:
        # Parse specialty and difficulty from source
        parts = question.source.split(" - ")
        if len(parts) >= 3:
            specialty = parts[1]
            difficulty = parts[2]
            question.source = f"AI Generated - {specialty} - {difficulty}"
            db.commit()
            print(f"[MassivePool] Served fallback question to user {user_id[:8]}")

    return question


# =============================================================================
# POOL REPLENISHMENT (Background)
# =============================================================================

_replenish_lock = threading.Lock()
_is_replenishing = False
_replenish_queue = []


def _trigger_replenish_check(specialty: str, difficulty: str):
    """Add to replenishment queue if not already there."""
    global _replenish_queue

    item = (specialty, difficulty)
    if item not in _replenish_queue:
        _replenish_queue.append(item)


def replenish_pool_batch(
    db: Session,
    specialty: str,
    difficulty: str,
    count: int
) -> int:
    """
    Generate a batch of questions for the pool.

    Args:
        db: Database session
        specialty: Target specialty
        difficulty: Target difficulty
        count: Number to generate

    Returns:
        Number successfully generated
    """
    from app.services.question_agent import QuestionGenerationAgent
    from app.services.step2ck_content_outline import get_high_yield_topic

    agent = QuestionGenerationAgent(db)
    generated = 0

    for i in range(count):
        try:
            topic = get_high_yield_topic(specialty)

            if topic is None:
                print(f"[MassivePool] WARNING: No topic found for specialty '{specialty}', skipping question {i+1}/{count}")
                continue

            question_data = agent.generate_question(
                specialty=specialty,
                topic=topic,
                difficulty=difficulty,
                max_retries=2
            )

            if question_data:
                # Add to pool with proper tagging
                question = Question(
                    id=generate_uuid(),
                    vignette=question_data["vignette"],
                    answer_key=question_data["answer_key"],
                    choices=question_data["choices"],
                    explanation=question_data.get("explanation"),
                    source=get_pool_source(specialty, difficulty),
                    specialty=specialty.lower().replace(" ", "_"),
                    difficulty_level=difficulty,
                    source_type="ai_generated",
                    recency_weight=1.0,
                    recency_tier=1,
                    content_status="active",
                    extra_data={
                        "ai_generated": True,
                        "topic": topic,
                        "pooled_at": datetime.utcnow().isoformat()
                    }
                )
                db.add(question)
                db.commit()
                generated += 1

                print(f"[MassivePool] Generated {specialty}/{difficulty} question {generated}/{count}")

        except Exception as e:
            print(f"[MassivePool] Failed to generate question: {e}")
            continue

    return generated


def run_continuous_replenishment():
    """
    Continuous background thread that keeps the pool filled.

    Runs every 5 minutes, checks for gaps, and generates questions.
    This ensures the pool is always ready for instant serving.
    """
    global _is_replenishing

    print("[MassivePool] Starting continuous replenishment...")

    while True:
        try:
            if _is_replenishing:
                time.sleep(60)
                continue

            _is_replenishing = True
            db = SessionLocal()

            try:
                # Get current gaps
                gaps = get_pool_gaps(db)

                if not gaps:
                    print("[MassivePool] Pool is fully stocked!")
                    time.sleep(300)  # Check again in 5 minutes
                    continue

                # Process top priority gaps (up to 3 per cycle)
                for specialty, difficulty, needed in gaps[:3]:
                    batch_size = min(needed, REPLENISH_BATCH[difficulty])

                    print(f"[MassivePool] Replenishing {specialty}/{difficulty} "
                          f"(need {needed}, generating {batch_size})")

                    generated = replenish_pool_batch(db, specialty, difficulty, batch_size)
                    print(f"[MassivePool] Generated {generated}/{batch_size} questions")

                    # Small delay between batches to avoid rate limits
                    time.sleep(5)

            finally:
                db.close()
                _is_replenishing = False

            # Wait before next cycle
            time.sleep(300)  # 5 minutes

        except Exception as e:
            print(f"[MassivePool] Replenishment error: {e}")
            _is_replenishing = False
            time.sleep(60)


def start_background_replenishment():
    """Start the background replenishment thread."""
    thread = threading.Thread(target=run_continuous_replenishment, daemon=True)
    thread.start()
    print("[MassivePool] Background replenishment thread started")


# =============================================================================
# INITIAL POOL WARMING
# =============================================================================

def warm_pool_initial(target_total: int = 1000) -> Dict:
    """
    Warm up the pool with initial questions.

    Call this at application startup or via management command.
    Distributes questions across specialties and difficulties based on weights.

    Args:
        target_total: Total number of questions to generate (default 1000)

    Returns:
        Summary of generation results
    """
    print(f"[MassivePool] Warming pool with {target_total} questions...")

    db = SessionLocal()
    results = {"generated": 0, "failed": 0, "by_specialty": {}}

    try:
        stats = get_detailed_pool_stats(db)

        # Calculate how many each specialty/difficulty needs
        for specialty in SPECIALTIES:
            weight = SPECIALTY_WEIGHTS[specialty]
            specialty_target = int(target_total * weight)

            results["by_specialty"][specialty] = {}

            for difficulty in ["easy", "medium", "hard"]:
                diff_weight = {"easy": 0.25, "medium": 0.5, "hard": 0.25}[difficulty]
                bucket_target = int(specialty_target * diff_weight)

                current = stats["by_specialty"].get(specialty, {}).get(difficulty, 0)
                needed = max(0, bucket_target - current)

                if needed > 0:
                    print(f"[MassivePool] Warming {specialty}/{difficulty}: "
                          f"need {needed} (current: {current}, target: {bucket_target})")

                    generated = replenish_pool_batch(db, specialty, difficulty, needed)
                    results["generated"] += generated
                    results["failed"] += (needed - generated)
                    results["by_specialty"][specialty][difficulty] = generated

        print(f"[MassivePool] Pool warming complete: "
              f"{results['generated']} generated, {results['failed']} failed")

    finally:
        db.close()

    return results


def warm_pool_async(target_total: int = 1000):
    """Warm pool in background thread."""
    def warm():
        warm_pool_initial(target_total)

    thread = threading.Thread(target=warm, daemon=True)
    thread.start()
    print(f"[MassivePool] Pool warming started in background (target: {target_total})")


# =============================================================================
# STARTUP INITIALIZATION
# =============================================================================

def initialize_massive_pool():
    """
    Initialize the massive pool system.

    Call this at application startup. It will:
    1. Check current pool status
    2. Start background replenishment if pool is low
    3. Begin continuous replenishment thread
    """
    db = SessionLocal()
    try:
        stats = get_detailed_pool_stats(db)
        print(f"[MassivePool] Current pool status: {stats['total']} questions, health: {stats['health']}")

        if stats["health"] == "critical":
            print("[MassivePool] Pool critically low! Starting emergency warm-up...")
            warm_pool_async(500)  # Generate 500 questions in background
        elif stats["health"] == "warning":
            print("[MassivePool] Pool below target, starting background warm-up...")
            warm_pool_async(200)  # Generate 200 questions in background

        # Start continuous replenishment
        start_background_replenishment()

    finally:
        db.close()
