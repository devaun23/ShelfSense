"""
AI Question Generation Service for ShelfSense
Generates novel USMLE Step 2 CK questions using OpenAI
"""

import os
import json
import random
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.models.models import Question
from app.models.models import generate_uuid
from app.services.step2ck_content_outline import (
    get_weighted_specialty,
    get_high_yield_topic,
    get_question_type,
    CLINICAL_SETTINGS,
    COMMON_DISTRACTORS
)
from app.services.nbme_gold_book_principles import get_generation_principles
from app.services.openai_service import openai_service, CircuitBreakerOpenError
from app.services.cache_service import question_cache
from sqlalchemy import func

SPECIALTIES = [
    "Internal Medicine",
    "Surgery",
    "Pediatrics",
    "Psychiatry",
    "Obstetrics and Gynecology",
    "Family Medicine",
    "Emergency Medicine",
    "Preventive Medicine"
]


def get_training_statistics(db: Session, specialty: Optional[str] = None) -> Dict:
    """Get statistics from the entire question database for AI training"""
    # Get only original questions (not AI-generated ones)
    query = db.query(Question).filter(
        ~Question.source.like('%AI Generated%')
    )

    if specialty:
        query = query.filter(Question.source.like(f"%{specialty}%"))

    all_questions = query.all()

    # Analyze the entire database
    total_questions = len(all_questions)
    avg_vignette_length = sum(len(q.vignette) for q in all_questions) / max(total_questions, 1)

    return {
        "total_questions": total_questions,
        "avg_vignette_length": int(avg_vignette_length)
    }


def get_example_questions(db: Session, specialty: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """Retrieve diverse example questions from database to guide AI generation
    Samples from across the ENTIRE 1,994-question database to maximize learning"""

    # Get only original questions (exclude AI-generated)
    query = db.query(Question).filter(
        ~Question.source.like('%AI Generated%')
    )

    if specialty:
        query = query.filter(Question.source.like(f"%{specialty}%"))

    # Get total count for this specialty
    total = query.count()

    if total == 0:
        # Fallback to any original questions
        query = db.query(Question).filter(
            ~Question.source.like('%AI Generated%')
        )
        total = query.count()

    # Sample diverse questions from across different recency tiers
    # This ensures AI learns from newest (most accurate) AND established questions
    examples = []

    # Tier 1: Highest recency (newest, most predictive)
    tier1 = query.filter(Question.recency_weight >= 0.8).order_by(Question.recency_weight.desc()).limit(2).all()
    examples.extend(tier1)

    # Tier 2: Mid-high recency
    tier2 = query.filter(Question.recency_weight >= 0.6, Question.recency_weight < 0.8).order_by(Question.recency_weight.desc()).limit(2).all()
    examples.extend(tier2)

    # Tier 3: Any remaining to reach limit (for variety)
    remaining = limit - len(examples)
    if remaining > 0:
        tier3 = query.limit(remaining).all()
        examples.extend(tier3)

    return [{
        "vignette": q.vignette,
        "choices": q.choices,
        "answer": q.answer_key,
        "explanation": q.explanation,
        "source": q.source
    } for q in examples[:limit]]


def get_fallback_question(db: Session, specialty: Optional[str] = None) -> Optional[Dict]:
    """
    Get a random question from the database when OpenAI is unavailable.
    Used for graceful degradation when circuit breaker is open.

    Args:
        db: Database session
        specialty: Optional specialty filter

    Returns:
        Dictionary containing question data, or None if no questions available
    """
    # Prefer non-AI-generated questions for fallback
    query = db.query(Question).filter(
        ~Question.source.like('%AI Generated%')
    )

    if specialty:
        query = query.filter(Question.source.like(f"%{specialty}%"))

    # Get random question
    question = query.order_by(func.random()).first()

    if not question:
        # Fallback to any question if specialty filter returns nothing
        question = db.query(Question).filter(
            ~Question.source.like('%AI Generated%')
        ).order_by(func.random()).first()

    if not question:
        return None

    return {
        "vignette": question.vignette,
        "choices": question.choices,
        "answer_key": question.answer_key,
        "explanation": question.explanation,
        "source": f"{question.source} (Fallback)",
        "specialty": specialty or "General",
        "recency_weight": question.recency_weight,
        "metadata": {
            "fallback": True,
            "original_id": question.id,
            "reason": "circuit_breaker_open"
        }
    }


def generate_question(
    db: Session,
    specialty: Optional[str] = None,
    topic: Optional[str] = None,
    use_cache: bool = True
) -> Dict:
    """
    Generate a novel USMLE Step 2 CK question using OpenAI
    Follows official USMLE content distribution and targets high-yield topics

    Args:
        db: Database session
        specialty: Medical specialty (if None, weighted by USMLE distribution)
        topic: Specific topic within specialty (if None, selects high-yield topic)
        use_cache: Whether to check/use cache (default: True)

    Returns:
        Dictionary containing generated question data

    Raises:
        CircuitBreakerOpenError: If OpenAI is unavailable (circuit breaker open)
        ValueError: If response validation fails
    """

    # Use USMLE-weighted specialty selection
    if not specialty:
        specialty = get_weighted_specialty()

    # Select high-yield topic if not provided
    if not topic:
        topic = get_high_yield_topic(specialty)

    # Check cache first for faster response (target: <3s)
    if use_cache:
        cached = question_cache.get_cached_question(specialty, topic)
        if cached:
            # Add cache metadata and return
            cached["metadata"] = cached.get("metadata", {})
            cached["metadata"]["from_cache"] = True
            logger.info("Cache HIT for specialty=%s", specialty)
            return cached

    # Select question type based on NBME distribution
    question_type = get_question_type()

    # Select clinical setting
    clinical_setting = random.choice(CLINICAL_SETTINGS)

    # Get NBME Gold Book principles
    gold_book_principles = get_generation_principles()

    # Get training statistics from ENTIRE database
    stats = get_training_statistics(db, specialty)

    # Get diverse example questions from across the database
    examples = get_example_questions(db, specialty, limit=5)

    # Build comprehensive training context from your FULL database
    example_context = f"\n\nTRAINING DATA CONTEXT:\n"
    example_context += f"- You are learning from {stats['total_questions']} real NBME/Shelf exam questions\n"
    example_context += f"- Average vignette length: ~{stats['avg_vignette_length']} characters\n"
    example_context += f"- These examples represent the quality and style you must match\n\n"

    if examples:
        example_context += "═══ STUDY THESE EXAMPLES CAREFULLY ═══\n\n"
        for i, ex in enumerate(examples, 1):
            example_context += f"Training Example {i}:\n"
            example_context += f"VIGNETTE:\n{ex['vignette']}\n\n"
            example_context += f"ANSWER CHOICES:\n"
            for j, choice in enumerate(ex['choices'][:5], 65):  # A-E
                example_context += f"{chr(j)}. {choice}\n"
            example_context += f"\nCORRECT ANSWER: {ex['answer']}\n"
            if ex.get('explanation'):
                example_context += f"EXPLANATION: {ex['explanation']}\n"
            example_context += f"SOURCE: {ex['source']}\n"
            example_context += "─" * 60 + "\n\n"

    # Construct enhanced generation prompt with training data and high-yield focus
    prompt = f"""You are an expert USMLE Step 2 CK question writer creating exam-quality questions for a medical student targeting a 280+ Step 2 CK score and 99th percentile shelf exams.

QUESTION SPECIFICATIONS (USMLE Official Blueprint):
- DISCIPLINE: {specialty} (Following USMLE distribution: Medicine 55-65%, Surgery 20-30%, Pediatrics 17-27%, OB/GYN 10-20%, Psychiatry 10-15%)
- HIGH-YIELD TOPIC: {topic} (From First Aid Step 2 CK high-yield material)
- COMPETENCY TESTED: {question_type} (Following USMLE task distribution)
- CLINICAL SETTING: {clinical_setting}

CRITICAL REQUIREMENTS FOR HIGH-QUALITY QUESTIONS:
1. Study the training examples carefully - match their clinical depth, writing style, and format
2. Create a completely NEW question (do not copy examples, but learn from their structure)
3. Vignette structure (3-5 sentences):
   - Patient demographics (age, gender, relevant history)
   - Chief complaint with timeline
   - Pertinent positives AND negatives from history
   - Physical examination findings (vital signs, specific exam findings)
   - Laboratory/imaging results if applicable
4. Answer choices MUST be:
   - Exactly 5 DISTINCT options (A-E)
   - Each medically plausible (no obviously wrong choices)
   - Testing clinical reasoning at Step 2 CK level (60-70% difficulty)
   - Following current evidence-based guidelines
5. Quality standards:
   - NO DUPLICATES - verify all 5 choices are completely different
   - NO TYPOS - triple-check spelling, grammar, and medical terminology
   - Use proper medical units WITHOUT spaces: mg/dL, mEq/L, mmHg, mm Hg, beats/min
   - Realistic lab values and vital signs
   - Current treatment guidelines (not outdated practices)
6. Explanation must:
   - Cite pathophysiology or clinical guidelines
   - Explain why the correct answer is right
   - Briefly mention why key distractors are wrong
   - Be educational and clinically accurate

{f'SPECIFIC TOPIC: {topic}' if topic else 'TOPIC: High-yield clinical scenario for this specialty'}

{example_context}

NBME GOLD BOOK PRINCIPLES (CRITICAL - FOLLOW EXACTLY):
1. COVER THE OPTIONS RULE: Question MUST be answerable from stem + lead-in ALONE, WITHOUT looking at options
2. VIGNETTE TEMPLATE:
   First sentence: Age, gender, setting, presenting complaint, duration
   Subsequent: History, physical exam, labs/imaging, treatment
   Lead-in: Focused question allowing single best answer without seeing options
3. SINGLE BEST ANSWER: Options homogeneous, evaluated on single dimension, ONE clearly best answer
4. ALL RELEVANT FACTS: All facts needed to answer are in stem (not in options)
5. PATIENTS DO NOT LIE: All patient-reported information is accurate
6. CLASSIC CASES: Use classic presentations (not "zebras"), no red herrings, avoid tricks
7. NO TRIVIA: Test important concepts, not obscure facts
8. HOMOGENEOUS OPTIONS: All options same category (all diagnoses OR all treatments, etc.)

DIFFICULTY TARGET: 60-70% of examinees should answer correctly (Step 2 CK standard)

NOW GENERATE A COMPLETELY NEW, EXAM-QUALITY QUESTION that:
- Matches the clinical depth and realism of the training examples
- Tests important diagnostic or management knowledge
- Has 5 unique, plausible answer choices (no "gimmies")
- Uses current evidence-based medicine
- Contains ZERO typos, spacing errors, or formatting issues
- Would appear on an actual USMLE Step 2 CK exam

Return ONLY valid JSON (no additional text):
{{
  "vignette": "A [age]-year-old [gender] with a history of [relevant conditions] presents to [setting] with [chief complaint and timeline]. [Additional history]. On examination, temperature is [X]°C ([X]°F), pulse is [X]/min, respirations are [X]/min, and blood pressure is [X]/[X] mm Hg. [Physical exam findings]. Laboratory studies show [relevant labs with units].",
  "choices": ["Specific management/diagnosis A", "Specific management/diagnosis B", "Specific management/diagnosis C", "Specific management/diagnosis D", "Specific management/diagnosis E"],
  "answer_key": "B",
  "explanation": {{
    "type": "One of: TYPE_A_STABILITY (patient stability assessment), TYPE_B_TIME (time-sensitive decisions), TYPE_C_DIAGNOSTIC (diagnostic workup sequence), TYPE_D_RISK (risk stratification), TYPE_E_TREATMENT (treatment selection/hierarchy), TYPE_F_DIFFERENTIAL (differential diagnosis)",
    "quick_answer": "A 1-2 sentence direct answer explaining why the correct choice is right. This is the first thing students see - make it clear and memorable.",
    "principle": "State the core medical principle concisely using clinical language",
    "clinical_reasoning": "Use structured format with arrows (→) to show diagnostic/therapeutic pathway. Example: 'History + exam → provisional diagnosis → confirm with test → treatment'. Keep it clear and flowing with logical progression.",
    "correct_answer_explanation": "Explain why this is correct using clear clinical logic. Use arrow notation (→) to show cause-effect or step-progression when relevant.",
    "distractor_explanations": {{
      "A": "Concise reason why wrong",
      "B": "Concise reason why wrong (skip if this is the correct answer)",
      "C": "Concise reason why wrong",
      "D": "Concise reason why wrong",
      "E": "Concise reason why wrong"
    }},
    "concept": "The main medical concept being tested (e.g., 'Acute Coronary Syndrome Management', 'Diabetic Ketoacidosis')",
    "educational_objective": "What the student should learn from this question - a clear learning takeaway",
    "deep_dive": {{
      "pathophysiology": "Explain the underlying pathophysiology relevant to this case",
      "differential_comparison": "Compare key differentials and how to distinguish them",
      "clinical_pearls": ["High-yield clinical pearl 1", "High-yield clinical pearl 2", "High-yield clinical pearl 3"]
    }},
    "step_by_step": [
      {{"step": 1, "action": "First clinical action", "rationale": "Why this step comes first"}},
      {{"step": 2, "action": "Second clinical action", "rationale": "Why this follows"}},
      {{"step": 3, "action": "Third clinical action", "rationale": "Final reasoning step"}}
    ],
    "memory_hooks": {{
      "mnemonic": "A helpful mnemonic if applicable (or null)",
      "analogy": "A relatable analogy to remember this concept (or null)",
      "clinical_story": null
    }},
    "common_traps": [
      {{
        "trap": "A common mistake students make",
        "why_wrong": "Why this thinking is incorrect",
        "correct_thinking": "The right way to approach it"
      }}
    ],
    "related_topics": ["Related topic 1", "Related topic 2", "Related topic 3"],
    "difficulty_factors": {{
      "content_difficulty": "basic OR intermediate OR advanced",
      "reasoning_complexity": "single_step OR multi_step OR integration",
      "common_error_rate": 0.3
    }}
  }},
  "specialty": "{specialty}"
}}"""

    try:
        # Call OpenAI API with circuit breaker protection
        response = openai_service.chat_completion(
            messages=[
                {"role": "system", "content": "You are an expert USMLE Step 2 CK question writer. You create exam-quality clinical vignettes that test medical knowledge at the level of a third-year medical student. Generate only valid JSON responses with clinically accurate content following current evidence-based guidelines."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            temperature=0.7,  # Balanced: creative but consistent
            max_tokens=2500,  # Increased for comprehensive explanations
            response_format={"type": "json_object"}
        )

        # Parse response
        generated_data = json.loads(response.choices[0].message.content)

        # Validate structure
        required_fields = ["vignette", "choices", "answer_key", "explanation"]
        for field in required_fields:
            if field not in generated_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate choices
        if len(generated_data["choices"]) != 5:
            raise ValueError(f"Expected 5 choices, got {len(generated_data['choices'])}")

        # Validate answer key
        if generated_data["answer_key"] not in ["A", "B", "C", "D", "E"]:
            raise ValueError(f"Invalid answer key: {generated_data['answer_key']}")

        # Check for duplicate choices
        unique_choices = set([c.strip().lower() for c in generated_data["choices"]])
        if len(unique_choices) != 5:
            raise ValueError("Duplicate choices detected")

        # Add metadata
        generated_data["source"] = f"AI Generated - {specialty}"
        generated_data["specialty"] = specialty
        generated_data["recency_weight"] = 1.0  # AI-generated questions get highest weight

        # Cache the generated question for future requests
        if use_cache:
            question_cache.cache_question(generated_data, specialty, topic)
            logger.info("Cached new question for specialty=%s, topic=%s", specialty, topic)

        return generated_data

    except CircuitBreakerOpenError:
        # Circuit breaker is open - try cache first, then database fallback
        logger.warning("Circuit breaker open, attempting fallback for specialty=%s", specialty)

        # Try any cached question first
        cached_fallback = question_cache.get_any_cached_question(specialty)
        if cached_fallback:
            cached_fallback["metadata"] = cached_fallback.get("metadata", {})
            cached_fallback["metadata"]["fallback"] = True
            cached_fallback["metadata"]["reason"] = "circuit_breaker_open"
            logger.info("Serving cached fallback question for specialty=%s", specialty)
            return cached_fallback

        # Then try database
        fallback = get_fallback_question(db, specialty)
        if fallback:
            logger.info("Serving database fallback question for specialty=%s", specialty)
            return fallback

        # No fallback available, re-raise
        raise

    except Exception as e:
        logger.error("Error generating question: %s", str(e), exc_info=True)
        raise


def validate_explanation_quality(explanation: Dict, answer_key: str) -> Dict:
    """
    Validate explanation quality and return validation results.

    Checks:
    - All 5 distractor_explanations are present (A-E)
    - Correct answer is excluded from distractor_explanations
    - Arrow notation (→) is used in clinical_reasoning and principle
    - Threshold patterns with units are present where applicable

    Returns:
        Dict with 'valid' bool and 'warnings' list
    """
    warnings = []
    all_choices = ["A", "B", "C", "D", "E"]
    expected_distractors = [c for c in all_choices if c != answer_key]

    # Check distractor_explanations
    distractor_explanations = explanation.get("distractor_explanations", {})

    if not distractor_explanations:
        warnings.append("Missing distractor_explanations entirely")
    else:
        # Check all 4 wrong answers have explanations
        for choice in expected_distractors:
            if choice not in distractor_explanations:
                warnings.append(f"Missing distractor explanation for choice {choice}")
            elif not distractor_explanations[choice] or distractor_explanations[choice].strip() == "":
                warnings.append(f"Empty distractor explanation for choice {choice}")

        # Check correct answer is not in distractors (or has meaningful "correct" indicator)
        if answer_key in distractor_explanations:
            distractor_text = distractor_explanations[answer_key].lower()
            if "correct" not in distractor_text and "right answer" not in distractor_text:
                warnings.append(f"Correct answer {answer_key} should not have a 'why wrong' distractor explanation")

    # Check arrow notation in clinical_reasoning
    clinical_reasoning = explanation.get("clinical_reasoning", "")
    if clinical_reasoning and "→" not in clinical_reasoning:
        warnings.append("clinical_reasoning missing arrow notation (→) for logical flow")

    # Check principle has clear structure
    principle = explanation.get("principle", "")
    if not principle or len(principle) < 10:
        warnings.append("principle is missing or too short")

    # Check for educational_objective
    if not explanation.get("educational_objective"):
        warnings.append("Missing educational_objective")

    # Check deep_dive has required subfields
    deep_dive = explanation.get("deep_dive", {})
    if deep_dive:
        if not deep_dive.get("pathophysiology"):
            warnings.append("deep_dive missing pathophysiology")
        if not deep_dive.get("clinical_pearls"):
            warnings.append("deep_dive missing clinical_pearls")
    else:
        warnings.append("Missing deep_dive section")

    # Log warnings for monitoring
    if warnings:
        logger.warning(
            "Explanation quality warnings for answer_key=%s: %s",
            answer_key,
            "; ".join(warnings)
        )

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "distractor_count": len([c for c in expected_distractors if c in distractor_explanations]),
        "has_arrow_notation": "→" in clinical_reasoning,
        "has_deep_dive": bool(deep_dive and deep_dive.get("pathophysiology"))
    }


def save_generated_question(db: Session, question_data: Dict) -> Question:
    """Save a generated question to the database with validation"""

    import json

    # Convert explanation dict to JSON string for storage
    explanation_data = question_data.get("explanation")

    # Validate explanation quality before saving
    if isinstance(explanation_data, dict):
        answer_key = question_data.get("answer_key", "")
        validation_result = validate_explanation_quality(explanation_data, answer_key)

        # Store validation metadata
        if "metadata" not in question_data:
            question_data["metadata"] = {}
        question_data["metadata"]["explanation_validation"] = validation_result

        explanation_json = json.dumps(explanation_data)
    else:
        explanation_json = explanation_data

    question = Question(
        id=generate_uuid(),
        vignette=question_data["vignette"],
        choices=question_data["choices"],
        answer_key=question_data["answer_key"],
        explanation=explanation_json,
        source=question_data.get("source", "AI Generated"),
        recency_weight=question_data.get("recency_weight", 1.0),
        recency_tier=1,  # AI-generated questions are tier 1 (most recent/accurate)
        extra_data={"specialty": question_data.get("specialty"), "ai_generated": True}
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return question


def generate_and_save_question(db: Session, specialty: Optional[str] = None, topic: Optional[str] = None) -> Question:
    """Generate a question and save it to the database"""
    question_data = generate_question(db, specialty, topic)
    return save_generated_question(db, question_data)
