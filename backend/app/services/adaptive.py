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


def select_next_question(db: Session, user_id: str, use_ai: bool = True,
                         use_targeted: bool = True) -> Optional[Question]:
    """
    ADAPTIVE algorithm with weakness-targeted AI generation:
    1. Identify weak areas
    2. 40% chance to generate weakness-targeted AI question
    3. Get top-weighted unanswered questions using SQL (faster)
    4. Select randomly from top candidates

    Args:
        db: Database session
        user_id: User ID
        use_ai: Whether to use AI generation
        use_targeted: Whether to use weakness-targeted generation (recommended)
    """
    # Get weak areas
    weak_sources = get_weak_areas(db, user_id)

    # AI Integration: 40% chance to generate targeted question for weak areas
    if use_ai and use_targeted and random.random() < 0.4:
        try:
            # Get weakness profile to decide if targeted generation is valuable
            weakness_profile = get_user_weakness_profile(db, user_id)

            has_weaknesses = (
                weakness_profile.get("weak_specialties") or
                weakness_profile.get("most_common_error") or
                weakness_profile.get("missed_concepts")
            )

            if has_weaknesses:
                print(f"[Adaptive] Generating targeted question for {weakness_profile.get('recommended_focus')}")

                from app.services.question_agent import generate_weakness_targeted_question
                from app.services.question_generator import save_generated_question

                question_data = generate_weakness_targeted_question(db, user_id)
                ai_question = save_generated_question(db, question_data)
                return ai_question
            else:
                print(f"[Adaptive] No weakness data, using standard selection")

        except Exception as e:
            print(f"[Adaptive] Targeted generation failed: {str(e)}, falling back to pool")
            # Fall through to normal selection

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


def get_user_weakness_profile(db: Session, user_id: str) -> Dict:
    """
    Build a comprehensive weakness profile for targeted question generation.

    Aggregates:
    1. Weak specialties (< 60% accuracy)
    2. Error patterns (from error_analyses table)
    3. Specific topics/concepts missed
    4. Recent wrong answers for context

    Returns:
        {
            "user_id": str,
            "weak_specialties": [{"specialty": str, "accuracy": float, "total": int}],
            "error_patterns": {"knowledge_gap": 5, "premature_closure": 3, ...},
            "most_common_error": str,
            "missed_concepts": [str],  # Specific concepts from error analyses
            "recent_wrong_topics": [str],  # Topics from recent wrong answers
            "recommended_focus": str,  # AI-suggested focus area
            "difficulty_target": str,  # easy/medium/hard
        }
    """
    from app.models.models import ErrorAnalysis

    profile = {
        "user_id": user_id,
        "weak_specialties": [],
        "error_patterns": {},
        "most_common_error": None,
        "missed_concepts": [],
        "recent_wrong_topics": [],
        "recommended_focus": None,
        "difficulty_target": "medium"
    }

    # 1. Get weak specialties with performance data
    performance = get_performance_by_source(db, user_id)
    for source, data in performance.items():
        if data['total'] >= 3 and data['accuracy'] < 0.6:  # At least 3 questions attempted
            # Extract specialty from source
            specialty = None
            if "Medicine" in source:
                specialty = "Medicine"
            elif "Surgery" in source:
                specialty = "Surgery"
            elif "Pediatrics" in source:
                specialty = "Pediatrics"
            elif "Psychiatry" in source:
                specialty = "Psychiatry"
            elif "OB" in source or "Gyn" in source:
                specialty = "Obstetrics & Gynecology"
            elif "Emergency" in source:
                specialty = "Emergency Medicine"

            if specialty:
                profile["weak_specialties"].append({
                    "specialty": specialty,
                    "source": source,
                    "accuracy": data['accuracy'],
                    "total": data['total'],
                    "correct": data['correct']
                })

    # Sort by accuracy (worst first)
    profile["weak_specialties"].sort(key=lambda x: x['accuracy'])

    # 2. Get error patterns from error_analyses
    error_counts = db.query(
        ErrorAnalysis.error_type,
        func.count(ErrorAnalysis.id).label('count')
    ).filter(
        ErrorAnalysis.user_id == user_id
    ).group_by(
        ErrorAnalysis.error_type
    ).all()

    for error_type, count in error_counts:
        profile["error_patterns"][error_type] = count

    if profile["error_patterns"]:
        profile["most_common_error"] = max(
            profile["error_patterns"].items(),
            key=lambda x: x[1]
        )[0]

    # 3. Get missed concepts from recent error analyses
    recent_errors = db.query(ErrorAnalysis).filter(
        ErrorAnalysis.user_id == user_id
    ).order_by(
        ErrorAnalysis.created_at.desc()
    ).limit(20).all()

    missed_concepts = set()
    for error in recent_errors:
        if error.missed_detail:
            missed_concepts.add(error.missed_detail)

    profile["missed_concepts"] = list(missed_concepts)[:10]  # Top 10

    # 4. Get recent wrong answer topics
    recent_wrong = db.query(
        Question.source,
        Question.extra_data
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.is_correct == False
    ).order_by(
        QuestionAttempt.attempted_at.desc()
    ).limit(10).all()

    topics = set()
    for source, extra_data in recent_wrong:
        if extra_data and isinstance(extra_data, dict):
            topic = extra_data.get('topic')
            if topic:
                topics.add(topic)
        # Also add specialty from source
        if source:
            topics.add(source.split(' - ')[-1] if ' - ' in source else source)

    profile["recent_wrong_topics"] = list(topics)[:10]

    # 5. Determine difficulty target
    difficulty_info = get_user_difficulty_target(db, user_id)
    profile["difficulty_target"] = difficulty_info["difficulty_level"]

    # 6. Generate recommended focus
    if profile["weak_specialties"]:
        weakest = profile["weak_specialties"][0]
        profile["recommended_focus"] = f"{weakest['specialty']} ({weakest['accuracy']:.0%} accuracy)"
    elif profile["most_common_error"]:
        error_names = {
            "knowledge_gap": "foundational knowledge review",
            "premature_closure": "differential diagnosis practice",
            "misread_stem": "clinical detail attention",
            "faulty_reasoning": "clinical reasoning pathways",
            "test_taking_error": "test-taking strategy",
            "time_pressure": "pacing and time management"
        }
        profile["recommended_focus"] = error_names.get(
            profile["most_common_error"],
            "general practice"
        )
    else:
        profile["recommended_focus"] = "balanced practice across all specialties"

    return profile


def get_targeting_prompt_context(weakness_profile: Dict) -> str:
    """
    Convert weakness profile into prompt context for targeted question generation.

    Returns a formatted string to inject into the question generation prompt.
    """
    context_parts = []

    # Add weak specialty context
    if weakness_profile.get("weak_specialties"):
        weak_specs = weakness_profile["weak_specialties"][:3]
        spec_str = ", ".join([
            f"{w['specialty']} ({w['accuracy']:.0%})"
            for w in weak_specs
        ])
        context_parts.append(f"USER'S WEAK SPECIALTIES: {spec_str}")

    # Add error pattern context
    if weakness_profile.get("most_common_error"):
        error_guidance = {
            "knowledge_gap": "Test foundational concepts the user is missing. Include clear teaching points.",
            "premature_closure": "Create a scenario where multiple diagnoses fit initially. Test differential diagnosis.",
            "misread_stem": "Include subtle but critical clinical details. Test attention to specifics.",
            "faulty_reasoning": "Test clinical reasoning pathways. Include multi-step diagnostic logic.",
            "test_taking_error": "Create clear, unambiguous questions to build confidence.",
            "time_pressure": "Keep vignette focused and efficient to read."
        }
        error_type = weakness_profile["most_common_error"]
        context_parts.append(f"USER'S ERROR PATTERN: {error_type}")
        context_parts.append(f"GENERATION GUIDANCE: {error_guidance.get(error_type, '')}")

    # Add missed concepts
    if weakness_profile.get("missed_concepts"):
        concepts = ", ".join(weakness_profile["missed_concepts"][:5])
        context_parts.append(f"CONCEPTS USER HAS MISSED: {concepts}")

    # Add recent wrong topics
    if weakness_profile.get("recent_wrong_topics"):
        topics = ", ".join(weakness_profile["recent_wrong_topics"][:5])
        context_parts.append(f"RECENT WRONG ANSWER TOPICS: {topics}")

    # Add difficulty
    context_parts.append(f"TARGET DIFFICULTY: {weakness_profile.get('difficulty_target', 'medium')}")

    return "\n".join(context_parts)
