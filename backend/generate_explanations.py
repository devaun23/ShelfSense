"""
Framework-Based Explanation Generator for USMLE Questions

Generates structured explanations following the 6-type ShelfSense framework:
- TYPE A: Stable/Unstable Bifurcation
- TYPE B: Time-Sensitive Decisions
- TYPE C: Diagnostic Sequence
- TYPE D: Risk Stratification
- TYPE E: Treatment Hierarchy
- TYPE F: Differential Narrowing

Usage:
    python generate_explanations.py --batch-size 50 --start 0
    python generate_explanations.py --continue  # Resume from last checkpoint
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import sqlite3
from openai import OpenAI
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.models import Question

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Load explanation framework
FRAMEWORK_PATH = Path(__file__).parent.parent / "EXPLANATION_FRAMEWORK.md"
with open(FRAMEWORK_PATH, 'r') as f:
    FRAMEWORK = f.read()


def generate_explanation(question):
    """
    Generate framework-based explanation for a question
    Returns structured JSON explanation
    """

    # Convert choices to lettered format
    lettered_choices = {chr(65 + i): choice for i, choice in enumerate(question.choices)}
    choices_text = "\n".join([f"{letter}. {text}" for letter, text in lettered_choices.items()])

    prompt = f"""You are a USMLE Step 2 CK expert creating explanations using the ShelfSense framework.

{FRAMEWORK}

Your task:
1. Classify this question into one of the 6 types (A-F)
2. Generate a structured explanation following that type's template
3. Return JSON with all required fields

Question:
{question.vignette}

Answer Choices:
{choices_text}

Correct Answer: {question.answer_key}

Source: {question.source or 'NBME'}

Return JSON:
{{
  "type": "TYPE_A_STABILITY",  // or B, C, D, E, F
  "principle": "One-sentence principle statement with exact decision rule",
  "clinical_reasoning": "2-5 sentences explaining why this rule applies here, with explicit thresholds and values",
  "correct_answer_explanation": "Why the correct answer is right for THIS patient",
  "distractor_explanations": {{
    "A": "Why A is wrong for THIS specific patient (if A is not correct)",
    "B": "Why B is wrong for THIS specific patient (if B is not correct)",
    "C": "Why C is wrong for THIS specific patient (if C is not correct)",
    "D": "Why D is wrong for THIS specific patient (if D is not correct)",
    "E": "Why E is wrong for THIS specific patient (if E is not correct)"
  }},
  "educational_objective": "What decision-making pattern this question teaches",
  "concept": "Primary medical concept (e.g., 'Acute Care Surgery', 'Cardiology', 'Pediatrics')"
}}

IMPORTANT:
- Define all thresholds explicitly (e.g., "BP 82/48 (systolic <90)" not "hypotensive")
- Keep total explanation under 200 words
- Distractor explanations should be 15-20 words each
- Be medically accurate for NBME standards
- Remove the correct answer from distractor_explanations"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a USMLE expert creating framework-based explanations. Be precise, concise, and medically accurate."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        explanation = json.loads(response.choices[0].message.content)

        # Validate structure
        required_fields = ['type', 'principle', 'clinical_reasoning', 'correct_answer_explanation', 'distractor_explanations', 'educational_objective', 'concept']
        for field in required_fields:
            if field not in explanation:
                raise ValueError(f"Missing required field: {field}")

        return explanation

    except Exception as e:
        print(f"  ❌ Error generating explanation: {e}")
        return None


def save_checkpoint(question_id, index, total):
    """Save progress checkpoint"""
    checkpoint_path = Path(__file__).parent / "explanation_checkpoint.json"
    checkpoint = {
        'last_question_id': question_id,
        'last_index': index,
        'total_questions': total,
        'timestamp': datetime.now().isoformat()
    }
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint, f)


def load_checkpoint():
    """Load progress checkpoint"""
    checkpoint_path = Path(__file__).parent / "explanation_checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r') as f:
            return json.load(f)
    return None


def main(batch_size=50, start_index=0, continue_from_checkpoint=False):
    """Main explanation generation process"""

    print("=" * 80)
    print("ShelfSense - Framework-Based Explanation Generator")
    print("=" * 80)
    print()

    # Load checkpoint if continuing
    if continue_from_checkpoint:
        checkpoint = load_checkpoint()
        if checkpoint:
            start_index = checkpoint['last_index'] + 1
            print(f"📂 Resuming from checkpoint: question {start_index}/{checkpoint['total_questions']}")
            print()

    # Connect to database
    db = SessionLocal()

    try:
        # Get all questions
        all_questions = db.query(Question).all()
        total_questions = len(all_questions)

        print(f"Total questions in database: {total_questions}")
        print(f"Starting from index: {start_index}")
        print(f"Batch size: {batch_size}")
        print()

        # Filter questions that need explanations
        questions_to_process = []
        for q in all_questions[start_index:]:
            # Check if explanation exists and is framework-based
            if isinstance(q.explanation, str):
                # Old string explanation, needs conversion
                questions_to_process.append(q)
            elif isinstance(q.explanation, dict):
                # Check if it has framework structure
                if 'type' not in q.explanation or 'principle' not in q.explanation:
                    questions_to_process.append(q)
            else:
                # No explanation at all
                questions_to_process.append(q)

        print(f"Questions needing framework explanations: {len(questions_to_process)}")
        print()

        if not questions_to_process:
            print("✅ All questions already have framework-based explanations!")
            return

        # Process questions in batches
        processed = 0
        errors = 0
        start_time = time.time()

        for i, question in enumerate(questions_to_process, start=start_index):
            print(f"[{i+1}/{total_questions}] Processing: {question.id[:8]}... ({question.source or 'Unknown'})")

            # Generate explanation
            explanation = generate_explanation(question)

            if explanation:
                # Store as JSON
                question.explanation = explanation
                processed += 1
                print(f"  ✅ Generated {explanation['type']}: {explanation['principle'][:60]}...")
            else:
                errors += 1
                print(f"  ❌ Failed to generate explanation")

            # Commit every batch_size questions
            if (i + 1) % batch_size == 0:
                db.commit()
                save_checkpoint(question.id, i, total_questions)

                elapsed = time.time() - start_time
                rate = processed / elapsed
                remaining = len(questions_to_process) - processed
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60

                print()
                print(f"💾 Checkpoint saved: {processed} processed, {errors} errors")
                print(f"⏱️  Rate: {rate:.2f} questions/sec")
                print(f"⏰ ETA: {eta_minutes:.1f} minutes")
                print()

        # Final commit
        db.commit()
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Questions processed: {processed}")
        print(f"Errors: {errors}")
        print(f"Total time: {(time.time() - start_time) / 60:.1f} minutes")
        print()
        print("✅ Explanation generation complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user. Progress saved to checkpoint.")
        print("Run with --continue to resume.")
        db.rollback()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate framework-based explanations')
    parser.add_argument('--batch-size', type=int, default=50, help='Save checkpoint every N questions')
    parser.add_argument('--start', type=int, default=0, help='Start from question index')
    parser.add_argument('--continue', dest='cont', action='store_true', help='Continue from last checkpoint')

    args = parser.parse_args()

    main(
        batch_size=args.batch_size,
        start_index=args.start,
        continue_from_checkpoint=args.cont
    )
