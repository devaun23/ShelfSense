"""
Enhanced Framework-Based Explanation Generator for USMLE Questions

Generates structured explanations following the 6-type ShelfSense framework with:
- Progressive disclosure (quick answer, core, deep dive)
- Step-by-step breakdowns
- Visual aid suggestions
- Memory hooks and analogies
- Common trap identification

Types:
- TYPE A: Stable/Unstable Bifurcation
- TYPE B: Time-Sensitive Decisions
- TYPE C: Diagnostic Sequence
- TYPE D: Risk Stratification
- TYPE E: Treatment Hierarchy
- TYPE F: Differential Narrowing

Usage:
    python generate_explanations.py --batch-size 50 --start 0
    python generate_explanations.py --continue  # Resume from last checkpoint
    python generate_explanations.py --enhanced   # Generate with all enhanced fields
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


def generate_explanation(question, enhanced=True):
    """
    Generate framework-based explanation for a question
    Returns structured JSON explanation with optional enhanced fields
    """

    # Convert choices to lettered format
    lettered_choices = {chr(65 + i): choice for i, choice in enumerate(question.choices)}
    choices_text = "\n".join([f"{letter}. {text}" for letter, text in lettered_choices.items()])

    # Build the prompt based on whether we want enhanced fields
    if enhanced:
        prompt = f"""You are a USMLE Step 2 CK expert creating comprehensive explanations using the ShelfSense framework.

{FRAMEWORK}

Your task:
1. Classify this question into one of the 6 types (A-F)
2. Generate a COMPLETE structured explanation with ALL enhanced fields
3. Return JSON with all required fields

Question:
{question.vignette}

Answer Choices:
{choices_text}

Correct Answer: {question.answer_key}

Source: {question.source or 'NBME'}

Return JSON with this EXACT structure:
{{
  "type": "TYPE_A_STABILITY",

  "quick_answer": "Maximum 30 words summarizing the key teaching point",

  "principle": "One-sentence principle statement with exact decision rule and thresholds",

  "clinical_reasoning": "2-5 sentences explaining why this rule applies here, with explicit values like BP 82/48 (systolic <90)",

  "correct_answer_explanation": "Why the correct answer is right for THIS specific patient",

  "distractor_explanations": {{
    "A": "Why A is wrong for THIS patient (15-20 words, skip if A is correct)",
    "B": "Why B is wrong for THIS patient",
    "C": "Why C is wrong for THIS patient",
    "D": "Why D is wrong for THIS patient",
    "E": "Why E is wrong for THIS patient (if exists)"
  }},

  "deep_dive": {{
    "pathophysiology": "The biological/mechanistic explanation of why this happens",
    "differential_comparison": "How to distinguish this from similar conditions",
    "clinical_pearls": ["High-yield fact 1", "High-yield fact 2", "Board-relevant detail"]
  }},

  "step_by_step": [
    {{"step": 1, "action": "First thing to do/recognize", "rationale": "Why this step matters"}},
    {{"step": 2, "action": "Second step", "rationale": "Why"}},
    {{"step": 3, "action": "Third step if applicable", "rationale": "Why"}}
  ],

  "visual_aid": {{
    "type": "decision_tree OR flowchart OR comparison_table OR timeline",
    "description": "Brief description of what visual would help understand this",
    "key_elements": ["Key branch point or comparison 1", "Key element 2"]
  }},

  "memory_hooks": {{
    "analogy": "A memorable comparison to help remember this concept",
    "mnemonic": "Mnemonic if one exists for this topic (or null)",
    "clinical_story": "Brief memorable pattern like 'elderly patient with...' "
  }},

  "common_traps": [
    {{
      "trap": "What students commonly do wrong on this type of question",
      "why_wrong": "Why this thinking fails",
      "correct_thinking": "The right mental approach"
    }}
  ],

  "educational_objective": "What decision-making pattern or clinical reasoning this question teaches",

  "concept": "Primary medical concept (e.g., 'Acute Care Surgery', 'Cardiology')",

  "related_topics": ["Related topic 1", "Related topic 2"],

  "difficulty_factors": {{
    "content_difficulty": "basic OR intermediate OR advanced",
    "reasoning_complexity": "single_step OR multi_step OR integration",
    "common_error_rate": 0.30
  }}
}}

CRITICAL REQUIREMENTS:
- Define ALL thresholds explicitly (e.g., "BP 82/48 (systolic <90)" not "hypotensive")
- Quick answer MUST be ≤30 words
- Core explanation (clinical_reasoning) should be 2-5 sentences
- Distractor explanations should be 15-20 words each, specific to THIS patient
- Remove the correct answer letter from distractor_explanations
- step_by_step should have 2-4 steps maximum
- Be medically accurate for NBME standards
- Memory hooks should be genuinely memorable and clinically relevant"""

    else:
        # Basic prompt without enhanced fields
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
  "quick_answer": "30-word maximum summary",
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
                {"role": "system", "content": "You are a USMLE expert creating framework-based explanations. Be precise, concise, and medically accurate. Always use explicit thresholds and values."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        explanation = json.loads(response.choices[0].message.content)

        # Validate required structure
        required_fields = ['type', 'principle', 'clinical_reasoning', 'correct_answer_explanation', 'distractor_explanations', 'educational_objective', 'concept']
        for field in required_fields:
            if field not in explanation:
                raise ValueError(f"Missing required field: {field}")

        # Validate quick_answer length
        if 'quick_answer' in explanation:
            word_count = len(explanation['quick_answer'].split())
            if word_count > 35:  # Allow slight flexibility
                print(f"  ⚠️ Quick answer is {word_count} words (target: ≤30)")

        return explanation

    except Exception as e:
        print(f"  ❌ Error generating explanation: {e}")
        return None


def validate_explanation(explanation):
    """Validate explanation meets quality standards"""
    issues = []

    # Check quick answer length
    if 'quick_answer' in explanation:
        word_count = len(explanation['quick_answer'].split())
        if word_count > 35:
            issues.append(f"quick_answer too long ({word_count} words)")

    # Check for explicit thresholds in clinical_reasoning
    vague_terms = ['hypotensive', 'tachycardic', 'elevated', 'abnormal', 'low', 'high']
    reasoning = explanation.get('clinical_reasoning', '').lower()
    for term in vague_terms:
        if term in reasoning and not any(c.isdigit() for c in reasoning):
            issues.append(f"May have vague term '{term}' without explicit threshold")

    # Check distractor explanations exist
    distractors = explanation.get('distractor_explanations', {})
    if len(distractors) < 3:
        issues.append(f"Only {len(distractors)} distractor explanations (expected 3-4)")

    return issues


def save_checkpoint(question_id, index, total, stats):
    """Save progress checkpoint with stats"""
    checkpoint_path = Path(__file__).parent / "explanation_checkpoint.json"
    checkpoint = {
        'last_question_id': question_id,
        'last_index': index,
        'total_questions': total,
        'timestamp': datetime.now().isoformat(),
        'stats': stats
    }
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint, f, indent=2)


def load_checkpoint():
    """Load progress checkpoint"""
    checkpoint_path = Path(__file__).parent / "explanation_checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r') as f:
            return json.load(f)
    return None


def main(batch_size=50, start_index=0, continue_from_checkpoint=False, enhanced=True):
    """Main explanation generation process"""

    print("=" * 80)
    print("ShelfSense - Enhanced Explanation Generator")
    print("=" * 80)
    print()
    print(f"Mode: {'Enhanced (all fields)' if enhanced else 'Basic'}")
    print()

    # Load checkpoint if continuing
    if continue_from_checkpoint:
        checkpoint = load_checkpoint()
        if checkpoint:
            start_index = checkpoint['last_index'] + 1
            print(f"📂 Resuming from checkpoint: question {start_index}/{checkpoint['total_questions']}")
            if 'stats' in checkpoint:
                print(f"   Previous stats: {checkpoint['stats']}")
            print()

    # Connect to database
    db = SessionLocal()

    # Stats tracking
    stats = {
        'processed': 0,
        'errors': 0,
        'type_distribution': {},
        'validation_warnings': 0
    }

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
            needs_update = False

            if isinstance(q.explanation, str):
                # Old string explanation, needs conversion
                needs_update = True
            elif isinstance(q.explanation, dict):
                # Check if it has framework structure
                if 'type' not in q.explanation or 'principle' not in q.explanation:
                    needs_update = True
                # Check if it needs enhanced fields
                elif enhanced and 'quick_answer' not in q.explanation:
                    needs_update = True
            else:
                # No explanation at all
                needs_update = True

            if needs_update:
                questions_to_process.append(q)

        print(f"Questions needing {'enhanced ' if enhanced else ''}explanations: {len(questions_to_process)}")
        print()

        if not questions_to_process:
            print("✅ All questions already have framework-based explanations!")
            return

        # Process questions
        start_time = time.time()

        for i, question in enumerate(questions_to_process):
            current_index = start_index + i
            print(f"[{current_index+1}/{total_questions}] Processing: {question.id[:8]}... ({question.source or 'Unknown'})")

            # Generate explanation
            explanation = generate_explanation(question, enhanced=enhanced)

            if explanation:
                # Validate
                issues = validate_explanation(explanation)
                if issues:
                    stats['validation_warnings'] += 1
                    for issue in issues:
                        print(f"  ⚠️ {issue}")

                # Track type distribution
                exp_type = explanation.get('type', 'UNKNOWN')
                stats['type_distribution'][exp_type] = stats['type_distribution'].get(exp_type, 0) + 1

                # Store
                question.explanation = explanation
                stats['processed'] += 1

                # Show summary
                quick = explanation.get('quick_answer', explanation.get('principle', ''))[:60]
                print(f"  ✅ {exp_type}: {quick}...")
            else:
                stats['errors'] += 1
                print(f"  ❌ Failed to generate explanation")

            # Commit and checkpoint every batch_size questions
            if (i + 1) % batch_size == 0:
                db.commit()
                save_checkpoint(question.id, current_index, total_questions, stats)

                elapsed = time.time() - start_time
                rate = stats['processed'] / elapsed if elapsed > 0 else 0
                remaining = len(questions_to_process) - i - 1
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60

                print()
                print(f"💾 Checkpoint saved: {stats['processed']} processed, {stats['errors']} errors")
                print(f"⏱️  Rate: {rate:.2f} questions/sec")
                print(f"⏰ ETA: {eta_minutes:.1f} minutes")
                print(f"📊 Types: {stats['type_distribution']}")
                print()

        # Final commit
        db.commit()

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Questions processed: {stats['processed']}")
        print(f"Errors: {stats['errors']}")
        print(f"Validation warnings: {stats['validation_warnings']}")
        print(f"Total time: {(time.time() - start_time) / 60:.1f} minutes")
        print()
        print("Type Distribution:")
        for exp_type, count in sorted(stats['type_distribution'].items()):
            print(f"  {exp_type}: {count}")
        print()
        print("✅ Explanation generation complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user. Progress saved to checkpoint.")
        print("Run with --continue to resume.")
        db.rollback()
        save_checkpoint(question.id if 'question' in dir() else '', start_index, total_questions, stats)

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
    parser.add_argument('--enhanced', action='store_true', default=True, help='Generate with all enhanced fields (default: True)')
    parser.add_argument('--basic', action='store_true', help='Generate basic explanations only')

    args = parser.parse_args()

    main(
        batch_size=args.batch_size,
        start_index=args.start,
        continue_from_checkpoint=args.cont,
        enhanced=not args.basic
    )
