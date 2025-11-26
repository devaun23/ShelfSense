"""
Adaptive Learning Algorithm

Selects next question based on:
1. User's weak areas (< 60% accuracy)
2. Recency weighting (newer = more accurate)
3. Questions not yet answered
4. AI-generated questions for weak specialties
5. Difficulty adaptation based on user overall accuracy
"""

import random
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, Integer
from app.models.models import Question, QuestionAttempt
from app.services.question_generator import generate_and_save_question


def get_user_difficulty_target(db: Session, user_id: str) -> Dict:
    """
    Calculate difficulty target based on user's OVERALL accuracy.

    This determines what difficulty level of questions to serve.

    Returns:
        {
            "difficulty_level": "easy" | "medium" | "hard",
            "target_correct_rate": float (0.60-0.70),
            "vignette_complexity": "simple" | "moderate" | "complex",
            "distractor_plausibility": "obvious" | "moderate" | "subtle",
            "accuracy": float (user's actual accuracy),
            "total_questions": int (questions answered)
        }

    Algorithm:
    - User accuracy >= 80%: Generate harder questions
    - User accuracy 60-80%: Generate medium questions
    - User accuracy < 60%: Generate easier questions
    - New users (< 10 questions): Default to medium
    """
    # Get user's overall accuracy
    attempts = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).filter(
        QuestionAttempt.user_id == user_id
    ).first()

    total = attempts.total or 0
    correct = attempts.correct or 0

    # Default for new users
    if total < 10:
        return {
            "difficulty_level": "medium",
            "target_correct_rate": 0.65,
            "vignette_complexity": "moderate",
            "distractor_plausibility": "moderate",
            "accuracy": correct / total if total > 0 else 0.0,
            "total_questions": total
        }

    accuracy = correct / total

    # Determine difficulty based on accuracy
    if accuracy >= 0.80:
        # High performer - challenge them
        return {
            "difficulty_level": "hard",
            "target_correct_rate": 0.55,
            "vignette_complexity": "complex",
            "distractor_plausibility": "subtle",
            "accuracy": accuracy,
            "total_questions": total
        }
    elif accuracy >= 0.60:
        # Average performer - standard difficulty
        return {
            "difficulty_level": "medium",
            "target_correct_rate": 0.65,
            "vignette_complexity": "moderate",
            "distractor_plausibility": "moderate",
            "accuracy": accuracy,
            "total_questions": total
        }
    else:
        # Struggling - build confidence with easier questions
        return {
            "difficulty_level": "easy",
            "target_correct_rate": 0.75,
            "vignette_complexity": "simple",
            "distractor_plausibility": "obvious",
            "accuracy": accuracy,
            "total_questions": total
        }

def get_weak_areas(db: Session, user_id: str, threshold: float = 0.6) -> List[str]:
    """
    Identify sources where user has < 60% accuracy
    Returns list of source names
    """
    # Get all attempts with their questions
    attempts_by_source = db.query(
        Question.source,
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).group_by(
        Question.source
    ).all()

    weak_sources = []
    for source, total, correct in attempts_by_source:
        if total > 0:
            accuracy = (correct or 0) / total
            if accuracy < threshold:
                weak_sources.append(source)

    return weak_sources


def get_unanswered_questions(
    db: Session,
    user_id: str,
    sources: Optional[List[str]] = None,
    limit: int = None
) -> List[Question]:
    """
    Get questions user hasn't answered yet
    Optionally filter by sources (for weak areas)
    Optimized with SQL-based sorting and limiting
    """
    # Get all question IDs user has attempted
    attempted_ids = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id
    ).all()
    attempted_ids = [q[0] for q in attempted_ids]

    # Get unanswered questions sorted by recency_weight (SQL-based)
    query = db.query(Question).filter(
        Question.id.notin_(attempted_ids) if attempted_ids else True
    )

    if sources:
        query = query.filter(Question.source.in_(sources))

    # Sort by recency_weight descending in SQL (much faster than Python)
    query = query.order_by(Question.recency_weight.desc())

    # Limit results if specified (for performance)
    if limit:
        query = query.limit(limit)

    return query.all()


def select_next_question(db: Session, user_id: str, use_ai: bool = True) -> Optional[Question]:
    """
    OPTIMIZED Adaptive algorithm with SQL-based selection:
    1. Identify weak areas
    2. Get top-weighted unanswered questions using SQL (faster)
    3. Select randomly from top candidates
    4. Optional: 30% chance to generate AI question for weak specialty
    """
    # Get weak areas
    weak_sources = get_weak_areas(db, user_id)

    # Get top 50 unanswered questions using SQL sorting (much faster)
    if weak_sources:
        pool = get_unanswered_questions(db, user_id, weak_sources, limit=50)
    else:
        # No weak areas yet, use all unanswered questions (top 50 by weight)
        pool = get_unanswered_questions(db, user_id, limit=50)

    if not pool:
        # User has answered all questions, get top 50 from entire database
        pool = db.query(Question).order_by(Question.recency_weight.desc()).limit(50).all()

    if not pool:
        return None

    # AI Integration: 30% chance to generate new question for weak specialty
    if use_ai and weak_sources and random.random() < 0.3:
        try:
            # Extract specialty from weak source
            specialty = None
            for source in weak_sources:
                if "Internal Medicine" in source:
                    specialty = "Internal Medicine"
                elif "Surgery" in source:
                    specialty = "Surgery"
                elif "Pediatrics" in source:
                    specialty = "Pediatrics"
                elif "Psychiatry" in source:
                    specialty = "Psychiatry"
                elif "OB" in source or "Gynecology" in source:
                    specialty = "Obstetrics and Gynecology"
                elif "Family Medicine" in source:
                    specialty = "Family Medicine"
                elif "Emergency" in source:
                    specialty = "Emergency Medicine"
                elif "Preventive" in source:
                    specialty = "Preventive Medicine"

                if specialty:
                    break

            # Generate AI question for weak area
            ai_question = generate_and_save_question(db, specialty=specialty)
            return ai_question

        except Exception as e:
            print(f"AI generation failed, falling back to database: {str(e)}")
            # Fall through to normal selection

    # Optimized selection: Pool is already sorted by SQL, just pick randomly from top 20%
    top_20_percent = max(1, int(len(pool) * 0.2))
    selected = random.choice(pool[:top_20_percent])

    return selected


def calculate_predicted_score(db: Session, user_id: str) -> Optional[int]:
    """
    Calculate predicted Step 2 CK score based on recency-weighted accuracy

    Formula:
    - Weighted accuracy = sum(correct * weight) / sum(weight)
    - Score = 194 + (weighted_accuracy - 0.6) * 265
    - 60% = 194 (fail), 75% = 245 (average), 90% = 270+
    """
    # Get all attempts with question weights
    attempts = db.query(
        QuestionAttempt.is_correct,
        Question.recency_weight
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).all()

    if not attempts:
        return None

    # Calculate weighted accuracy
    total_weight = 0.0
    weighted_correct = 0.0

    for is_correct, weight in attempts:
        weight = weight or 0.5  # Default weight if missing
        total_weight += weight
        if is_correct:
            weighted_correct += weight

    if total_weight == 0:
        return None

    weighted_accuracy = weighted_correct / total_weight

    # Map to Step 2 CK score (194-300 range)
    # 60% = 194, 75% = 245, 90% = 270
    predicted_score = 194 + (weighted_accuracy - 0.6) * 265

    return round(max(194, min(300, predicted_score)))


def get_performance_by_source(db: Session, user_id: str) -> Dict[str, Dict]:
    """
    Get accuracy breakdown by source
    Returns dict of {source: {total, correct, accuracy}}
    """
    results = db.query(
        Question.source,
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).group_by(
        Question.source
    ).all()

    performance = {}
    for source, total, correct in results:
        accuracy = (correct or 0) / total if total > 0 else 0.0
        performance[source] = {
            'total': total,
            'correct': correct or 0,
            'accuracy': round(accuracy, 3)
        }

    return performance
