"""
AI Question Generation Service for ShelfSense
Generates novel USMLE Step 2 CK questions using OpenAI
"""

import os
import json
import random
import time
from typing import Optional, Dict, List
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError
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

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 10.0  # seconds

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


def retry_with_exponential_backoff(
    func,
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_RETRY_DELAY,
    max_delay: float = MAX_RETRY_DELAY
):
    """
    Retry a function with exponential backoff

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries

    Returns:
        Function result if successful

    Raises:
        Exception: Last exception if all retries fail
    """
    def wrapper(*args, **kwargs):
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except (RateLimitError, APIConnectionError, APIError) as e:
                last_exception = e

                if attempt == max_retries:
                    # Last attempt failed, raise the exception
                    print(f"All {max_retries} retry attempts failed")
                    raise

                # Calculate delay with exponential backoff
                delay = min(delay * 2, max_delay)

                print(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                print(f"Retrying in {delay:.1f} seconds...")

                time.sleep(delay)

            except Exception as e:
                # Non-retryable exception (e.g., validation error)
                print(f"Non-retryable error: {str(e)}")
                raise

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

    return wrapper


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


def generate_question(db: Session, specialty: Optional[str] = None, topic: Optional[str] = None) -> Dict:
    """
    Generate a novel USMLE Step 2 CK question using OpenAI
    Follows official USMLE content distribution and targets high-yield topics

    Args:
        db: Database session
        specialty: Medical specialty (if None, weighted by USMLE distribution)
        topic: Specific topic within specialty (if None, selects high-yield topic)

    Returns:
        Dictionary containing generated question data
    """

    # Use USMLE-weighted specialty selection
    if not specialty:
        specialty = get_weighted_specialty()

    # Select high-yield topic if not provided
    if not topic:
        topic = get_high_yield_topic(specialty)

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
    "principle": "State the core medical principle concisely using clinical language",
    "clinical_reasoning": "Use structured format with arrows (→) to show diagnostic/therapeutic pathway. Example: 'History + exam → provisional diagnosis → confirm with test → treatment'. Keep it clear and flowing with logical progression.",
    "correct_answer_explanation": "Explain why this is correct using clear clinical logic. Use arrow notation (→) to show cause-effect or step-progression when relevant. Example: 'Risk factors → pathophysiology → clinical presentation → indicated management'",
    "distractor_explanations": {{
      "A": "Concise reason why wrong. Use arrows if showing why pathway leads elsewhere. Example: 'This would be used if patient had X → leading to Y, but patient has Z instead'",
      "C": "Concise reason why wrong. Focus on key differentiating factor",
      "D": "Concise reason why wrong. Mention when this would be appropriate instead",
      "E": "Concise reason why wrong. State the critical difference"
    }}
  }},

EXPLANATION FORMATTING RULES:
- Use arrows (→) to show progression, causation, or logical flow
- Keep each explanation focused and clear without unnecessary words
- Use line breaks naturally (no bullet points or numbered lists)
- Example good format: "Patient presents with X → suggesting Y → confirmed by Z → therefore treatment is A"
- Make explanations educational but concise
- Use clinical reasoning flow rather than paragraph style
  "specialty": "{specialty}"
}}"""

    try:
        # Call OpenAI API with retry logic
        def make_api_call():
            return client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert USMLE Step 2 CK question writer. You create exam-quality clinical vignettes that test medical knowledge at the level of a third-year medical student. Generate only valid JSON responses with clinically accurate content following current evidence-based guidelines."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Balanced: creative but consistent
                max_tokens=1500,
                response_format={"type": "json_object"}
            )

        # Wrap with retry logic
        response = retry_with_exponential_backoff(make_api_call)()

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

        return generated_data

    except Exception as e:
        print(f"Error generating question: {str(e)}")
        raise


def save_generated_question(db: Session, question_data: Dict) -> Question:
    """Save a generated question to the database"""

    import json

    # Convert explanation dict to JSON string for storage
    explanation_data = question_data.get("explanation")
    if isinstance(explanation_data, dict):
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
