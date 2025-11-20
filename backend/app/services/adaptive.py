"""
Adaptive Learning Algorithm

Selects next question based on:
1. User's weak areas (< 60% accuracy)
2. Recency weighting (newer = more accurate)
3. Questions not yet answered
4. AI-generated questions for weak specialties
"""

import random
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.models import Question, QuestionAttempt
from app.services.question_generator import generate_and_save_question

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
    sources: Optional[List[str]] = None
) -> List[Question]:
    """
    Get questions user hasn't answered yet
    Optionally filter by sources (for weak areas)
    """
    # Get all question IDs user has attempted
    attempted_ids = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id
    ).all()
    attempted_ids = [q[0] for q in attempted_ids]

    # Get unanswered questions
    query = db.query(Question).filter(
        Question.id.notin_(attempted_ids) if attempted_ids else True
    )

    if sources:
        query = query.filter(Question.source.in_(sources))

    return query.all()


def select_next_question(db: Session, user_id: str, use_ai: bool = True) -> Optional[Question]:
    """
    ENHANCED Adaptive algorithm with AI generation:
    1. Identify weak areas
    2. Get unanswered questions in weak areas
    3. Apply recency weighting
    4. 30% chance: Generate NEW AI question for weak specialty
    5. 70% chance: Select from top 20% weighted pool (randomized)
    """
    # Get weak areas
    weak_sources = get_weak_areas(db, user_id)

    # Get unanswered questions in weak areas
    if weak_sources:
        pool = get_unanswered_questions(db, user_id, weak_sources)
    else:
        # No weak areas yet, use all unanswered questions
        pool = get_unanswered_questions(db, user_id)

    if not pool:
        # User has answered all questions, restart pool
        pool = db.query(Question).all()

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

    # Normal selection: Apply recency weighting and sort
    weighted_pool = sorted(
        pool,
        key=lambda q: (q.recency_weight or 0.0) * random.uniform(0.8, 1.2),  # Add randomness
        reverse=True
    )

    # Select from top 20% (prevents always showing same questions)
    top_20_percent = max(1, int(len(weighted_pool) * 0.2))
    selected = random.choice(weighted_pool[:top_20_percent])

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
