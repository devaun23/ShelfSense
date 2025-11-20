"""
AI Question Generation Service for ShelfSense
Generates novel USMLE Step 2 CK questions using OpenAI
"""

import os
import json
import random
from typing import Optional, Dict, List
from openai import OpenAI
from sqlalchemy.orm import Session
from app.models.models import Question
from app.models.models import generate_uuid

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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


def generate_question(db: Session, specialty: Optional[str] = None, topic: Optional[str] = None) -> Dict:
    """
    Generate a novel USMLE Step 2 CK question using OpenAI
    Learns from your existing question database to maintain quality and style

    Args:
        db: Database session
        specialty: Medical specialty (e.g., "Internal Medicine", "Surgery")
        topic: Specific topic within specialty (optional)

    Returns:
        Dictionary containing generated question data
    """

    # Select random specialty if not provided
    if not specialty:
        specialty = random.choice(SPECIALTIES)

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

    # Construct enhanced generation prompt with training data
    prompt = f"""You are an expert USMLE Step 2 CK question writer. You will generate a NOVEL, high-quality clinical vignette question for {specialty}.

CRITICAL REQUIREMENTS:
1. Study the training examples carefully - match their clinical depth, writing style, and format
2. Create a completely NEW question (do not copy examples, but learn from their structure)
3. Vignette: 3-5 sentences with patient demographics, chief complaint, relevant history, physical exam, and diagnostics
4. Provide exactly 5 DISTINCT answer choices (A-E) - each must be medically plausible
5. NO DUPLICATES - verify all 5 choices are completely different
6. NO TYPOS - triple-check spelling, grammar, and medical terminology
7. Use proper medical units WITHOUT spaces: mg/dL, mEq/L, mmHg (not "mg/d L" or "mEq/ L")
8. Answer choices should test clinical reasoning and diagnostic ability
9. Explanation must be educational and cite pathophysiology or clinical guidelines
10. Match the difficulty level and style of the training examples

{f'SPECIFIC FOCUS: {topic}' if topic else 'FOCUS: Generate a question on a high-yield topic for this specialty'}

{example_context}

NOW GENERATE A COMPLETELY NEW QUESTION that:
- Is as clinically accurate as the examples
- Uses similar writing style and detail level
- Tests important clinical knowledge
- Has 5 unique, plausible answer choices
- Contains ZERO typos or formatting errors

Return ONLY valid JSON:
{{
  "vignette": "A [age]-year-old [gender] with a history of... presents with... On examination... Laboratory studies show...",
  "choices": ["Choice A (unique)", "Choice B (unique)", "Choice C (unique)", "Choice D (unique)", "Choice E (unique)"],
  "answer_key": "B",
  "explanation": "The correct answer is B because [pathophysiology/clinical reasoning]...",
  "specialty": "{specialty}"
}}"""

    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert medical educator specializing in USMLE Step 2 CK question writing. Generate only valid JSON responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1500,
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

        return generated_data

    except Exception as e:
        print(f"Error generating question: {str(e)}")
        raise


def save_generated_question(db: Session, question_data: Dict) -> Question:
    """Save a generated question to the database"""

    question = Question(
        id=generate_uuid(),
        vignette=question_data["vignette"],
        choices=question_data["choices"],
        answer_key=question_data["answer_key"],
        explanation=question_data.get("explanation"),
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
