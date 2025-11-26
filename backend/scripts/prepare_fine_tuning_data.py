"""
Fine-Tuning Data Preparation Script for ShelfSense

This script prepares training data for OpenAI fine-tuning by:
1. Extracting all questions from the database
2. Converting to OpenAI's JSONL fine-tuning format
3. Creating a comprehensive system prompt with quality standards
4. Splitting into training (90%) and validation (10%) sets

Usage:
    python scripts/prepare_fine_tuning_data.py                    # Export all questions
    python scripts/prepare_fine_tuning_data.py --validate         # Validate before export
    python scripts/prepare_fine_tuning_data.py --output custom.jsonl  # Custom output file

Output:
    - training_data.jsonl (90% of questions)
    - validation_data.jsonl (10% of questions)
"""

import os
import sys
import json
import argparse
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# SYSTEM PROMPT - Embeds all ShelfSense quality standards
# ============================================================================

SYSTEM_PROMPT = """You are an expert USMLE Step 2 CK question writer following ShelfSense standards. Generate questions that are clinically authentic, educationally valuable, and match NBME format exactly.

## NBME GOLD BOOK PRINCIPLES (Must Follow All 10)

1. START WITH IMPORTANT CONCEPT - Begin with a clinically significant concept students must know
2. VIGNETTE TEMPLATE - Format: Age/Gender → Site → Chief Complaint → Duration → History → Physical Exam → Labs → Question
3. SINGLE BEST ANSWER - One clearly correct answer among plausible alternatives
4. COVER THE OPTIONS - Question answerable without seeing answer choices
5. ALL RELEVANT FACTS IN STEM - No hidden information, everything needed is provided
6. PATIENTS DON'T LIE - Clinical findings presented are accurate and reliable
7. CLASSIC PRESENTATIONS - Use typical cases, not zebras or rare presentations
8. NO TRIVIA - Test clinically relevant knowledge, not obscure facts
9. NO TEST-TAKING TRICKS - Avoid "always/never" or pattern-based answering
10. HOMOGENEOUS OPTIONS - All choices same category (all diagnoses, all treatments, etc.)

## EXPLANATION STRUCTURE (Required Format)

Every explanation must include:

1. **type**: One of TYPE_A_STABILITY, TYPE_B_TIME_SENSITIVE, TYPE_C_DIAGNOSTIC_SEQUENCE, TYPE_D_RISK_STRATIFICATION, TYPE_E_TREATMENT_HIERARCHY, TYPE_F_DIFFERENTIAL

2. **quick_answer**: 30-word MAX summary for rapid review
   Example: "Septic shock from cholecystitis needs urgent surgery, not just antibiotics."

3. **principle**: One sentence with EXACT decision rule using arrow notation (→)
   Example: "BP <90 with lactate >4 → septic shock → immediate source control required"

4. **clinical_reasoning**: 2-5 sentences with explicit thresholds
   Example: "BP 76/50 (systolic <90) and HR 128 (>100) → hemodynamic instability → septic shock. Low CVP (2 mmHg, normal 3-8) after fluids → vasodilation, not hypovolemia."

5. **correct_answer_explanation**: Why the correct answer is right with pathophysiology

6. **distractor_explanations**: Object with keys A-E (excluding correct answer)
   Each: 15-20 words explaining why wrong for THIS specific patient

7. **deep_dive**: Object with:
   - pathophysiology: Why this happens biologically (2-3 sentences)
   - differential_comparison: How to distinguish from similar conditions
   - clinical_pearls: Array of 2-3 high-yield facts

8. **step_by_step**: Array of decision steps
   Each: {step: 1, action: "What to do", rationale: "Why"}

9. **memory_hooks**: Object with:
   - analogy: Relatable comparison ("You can't put out fire while fuel burns")
   - mnemonic: If applicable (e.g., "MUDPILES for anion gap")
   - clinical_story: Brief memorable pattern

10. **common_traps**: Array of common mistakes
    Each: {trap: "What wrong", why_wrong: "Why fails", correct_thinking: "Right approach"}

## QUALITY RULES

- Use → for ALL causal relationships
- EVERY number must have context: "BP 80/50 (systolic <90)" not "hypotensive"
- quick_answer MUST be ≤30 words
- Principle must be clear, actionable decision rule
- Core explanation under 200 words
- Distractor explanations specific to THIS patient

## OUTPUT FORMAT

Return valid JSON with this exact structure:
{
    "vignette": "Full clinical vignette with demographics, presentation, exam, labs",
    "choices": ["A. Option text", "B. Option text", "C. Option text", "D. Option text", "E. Option text"],
    "answer_key": "B",
    "explanation": {
        "type": "TYPE_X_...",
        "quick_answer": "...",
        "principle": "...",
        "clinical_reasoning": "...",
        "correct_answer_explanation": "...",
        "distractor_explanations": {"A": "...", "C": "...", "D": "...", "E": "..."},
        "deep_dive": {...},
        "step_by_step": [...],
        "memory_hooks": {...},
        "common_traps": [...]
    },
    "specialty": "Internal Medicine|Surgery|Pediatrics|etc.",
    "topic": "High-yield topic name",
    "difficulty": 3
}"""


def get_db_connection(db_path: str):
    """Get database connection"""
    return sqlite3.connect(db_path)


def extract_questions(db_path: str) -> List[Dict]:
    """Extract all questions from database"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, vignette, answer_key, choices, explanation, specialty, source
        FROM questions
        WHERE (rejected = 0 OR rejected IS NULL)
        AND explanation IS NOT NULL
    """)

    questions = []
    for row in cursor.fetchall():
        q_id, vignette, answer_key, choices_json, expl_json, specialty, source = row

        # Parse JSON fields
        try:
            choices = json.loads(choices_json) if choices_json else []
            explanation = json.loads(expl_json) if expl_json else {}
        except json.JSONDecodeError:
            continue

        # Skip if explanation is not a dict
        if not isinstance(explanation, dict):
            continue

        questions.append({
            "id": q_id,
            "vignette": vignette,
            "answer_key": answer_key,
            "choices": choices,
            "explanation": explanation,
            "specialty": specialty or "general",
            "source": source
        })

    conn.close()
    return questions


def validate_question(question: Dict) -> Tuple[bool, List[str]]:
    """Validate a question has all required fields for fine-tuning"""
    issues = []

    # Check vignette
    if not question.get("vignette") or len(question["vignette"]) < 50:
        issues.append("Vignette too short or missing")

    # Check choices
    choices = question.get("choices", [])
    if len(choices) < 4:
        issues.append(f"Only {len(choices)} choices (need 4-5)")

    # Check answer key
    if question.get("answer_key") not in ["A", "B", "C", "D", "E"]:
        issues.append(f"Invalid answer_key: {question.get('answer_key')}")

    # Check explanation structure
    expl = question.get("explanation", {})
    required_fields = ["type", "principle", "clinical_reasoning", "distractor_explanations"]

    for field in required_fields:
        if not expl.get(field):
            issues.append(f"Missing explanation.{field}")

    # Check enhanced fields (warn but don't fail)
    enhanced_fields = ["quick_answer", "deep_dive", "memory_hooks", "step_by_step"]
    missing_enhanced = [f for f in enhanced_fields if not expl.get(f)]

    if missing_enhanced:
        issues.append(f"Missing enhanced fields: {missing_enhanced}")

    return len(issues) == 0, issues


def format_choices(choices: List[str]) -> List[str]:
    """Format choices with letter prefixes if missing"""
    formatted = []
    letters = ["A", "B", "C", "D", "E"]

    for i, choice in enumerate(choices[:5]):
        if isinstance(choice, str):
            # Check if already has letter prefix
            if not choice.strip().startswith(f"{letters[i]}."):
                choice = f"{letters[i]}. {choice}"
            formatted.append(choice)

    return formatted


def create_training_example(question: Dict) -> Dict:
    """Create a single training example in OpenAI fine-tuning format"""

    # Format the user prompt (what we'd ask to generate this question)
    specialty = question.get("specialty", "general")
    topic = question.get("explanation", {}).get("concept", "clinical medicine")

    user_prompt = f"Generate a USMLE Step 2 CK question about {topic} for {specialty}."

    # Format the assistant response (the question we want the model to learn)
    choices = format_choices(question.get("choices", []))

    assistant_response = {
        "vignette": question.get("vignette", ""),
        "choices": choices,
        "answer_key": question.get("answer_key", ""),
        "explanation": question.get("explanation", {}),
        "specialty": specialty,
        "topic": topic,
        "difficulty": question.get("difficulty", 3)
    }

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": json.dumps(assistant_response, ensure_ascii=False)}
        ]
    }


def split_data(examples: List[Dict], validation_ratio: float = 0.1) -> Tuple[List[Dict], List[Dict]]:
    """Split examples into training and validation sets"""
    random.shuffle(examples)

    split_idx = int(len(examples) * (1 - validation_ratio))
    training = examples[:split_idx]
    validation = examples[split_idx:]

    return training, validation


def write_jsonl(examples: List[Dict], output_path: str):
    """Write examples to JSONL file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')


def estimate_tokens(examples: List[Dict]) -> int:
    """Rough estimate of total tokens (4 chars = ~1 token)"""
    total_chars = 0
    for ex in examples:
        for msg in ex["messages"]:
            total_chars += len(msg["content"])
    return total_chars // 4


def estimate_cost(num_examples: int, tokens_per_example: int) -> float:
    """Estimate fine-tuning cost for GPT-3.5-turbo"""
    # GPT-3.5-turbo fine-tuning: $0.008 per 1K tokens
    total_tokens = num_examples * tokens_per_example * 3  # 3 epochs
    return (total_tokens / 1000) * 0.008


def main():
    parser = argparse.ArgumentParser(description="Prepare fine-tuning data for ShelfSense")
    parser.add_argument("--db", default="shelfsense.db", help="Database path")
    parser.add_argument("--output", default="training_data.jsonl", help="Output file name")
    parser.add_argument("--validate", action="store_true", help="Validate questions before export")
    parser.add_argument("--min-quality", action="store_true", help="Only include questions with all enhanced fields")
    args = parser.parse_args()

    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), args.db)
    output_dir = os.path.dirname(os.path.dirname(__file__))

    print("=" * 70)
    print("ShelfSense Fine-Tuning Data Preparation")
    print("=" * 70)

    # Extract questions
    print("\nExtracting questions from database...")
    questions = extract_questions(db_path)
    print(f"Found {len(questions)} questions with explanations")

    # Validate if requested
    if args.validate:
        print("\nValidating questions...")
        valid_count = 0
        issues_summary = {}

        for q in questions:
            is_valid, issues = validate_question(q)
            if is_valid:
                valid_count += 1
            for issue in issues:
                issue_key = issue.split(":")[0]
                issues_summary[issue_key] = issues_summary.get(issue_key, 0) + 1

        print(f"\nValidation Results:")
        print(f"  Valid: {valid_count}/{len(questions)} ({valid_count/len(questions)*100:.1f}%)")
        print(f"\nIssue Breakdown:")
        for issue, count in sorted(issues_summary.items(), key=lambda x: -x[1]):
            print(f"  {count:4d} - {issue}")

    # Filter for min quality if requested
    if args.min_quality:
        print("\nFiltering for questions with all enhanced fields...")
        enhanced_fields = ["quick_answer", "deep_dive", "memory_hooks", "step_by_step"]
        questions = [
            q for q in questions
            if all(q.get("explanation", {}).get(f) for f in enhanced_fields)
        ]
        print(f"After filtering: {len(questions)} questions")

    if not questions:
        print("\nNo questions to export!")
        return

    # Create training examples
    print("\nCreating training examples...")
    examples = [create_training_example(q) for q in questions]

    # Split into training and validation
    print("Splitting into training (90%) and validation (10%)...")
    training, validation = split_data(examples)

    # Calculate stats
    avg_tokens = estimate_tokens(examples) // len(examples) if examples else 0
    est_cost = estimate_cost(len(training), avg_tokens)

    print(f"\nDataset Statistics:")
    print(f"  Training examples: {len(training)}")
    print(f"  Validation examples: {len(validation)}")
    print(f"  Avg tokens per example: ~{avg_tokens}")
    print(f"  Estimated fine-tuning cost: ${est_cost:.2f}")

    # Write output files
    training_path = os.path.join(output_dir, "training_data.jsonl")
    validation_path = os.path.join(output_dir, "validation_data.jsonl")

    print(f"\nWriting output files...")
    write_jsonl(training, training_path)
    write_jsonl(validation, validation_path)

    print(f"  Created: {training_path}")
    print(f"  Created: {validation_path}")

    # Show sample
    print("\n" + "=" * 70)
    print("SAMPLE TRAINING EXAMPLE")
    print("=" * 70)
    if examples:
        sample = examples[0]
        print(f"\nSystem prompt: {len(sample['messages'][0]['content'])} chars")
        print(f"User prompt: {sample['messages'][1]['content']}")
        print(f"Assistant response (first 500 chars):")
        print(sample['messages'][2]['content'][:500] + "...")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Review the generated JSONL files
2. Upload to OpenAI:
   openai api files.create -f training_data.jsonl -p fine-tune

3. Start fine-tuning:
   openai api fine_tuning.jobs.create \\
     -t <file-id> \\
     -m gpt-3.5-turbo \\
     --suffix "shelfsense-usmle-v1"

4. Monitor progress:
   openai api fine_tuning.jobs.follow -i <job-id>
""")


if __name__ == "__main__":
    main()
