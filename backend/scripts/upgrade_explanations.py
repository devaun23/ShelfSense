"""
Explanation Quality Upgrade Script for ShelfSense

This script upgrades all existing question explanations to meet the full
EXPLANATION_FRAMEWORK.md standard, adding:
- quick_answer (30-word summary)
- deep_dive (pathophysiology, differential_comparison, clinical_pearls)
- memory_hooks (analogy, mnemonic, clinical_story)
- step_by_step (numbered decision steps)
- common_traps (what students get wrong)
- Arrow notation (→) in reasoning
- Explicit thresholds with units

Usage:
    python scripts/upgrade_explanations.py --dry-run  # Preview changes
    python scripts/upgrade_explanations.py --batch 50  # Process 50 questions
    python scripts/upgrade_explanations.py --all       # Process all questions
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI


def get_openai_client():
    """Get OpenAI client"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def analyze_current_state(db_path: str) -> Dict:
    """Analyze current explanation quality across all questions"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM questions
        WHERE rejected = 0 OR rejected IS NULL
    """)
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT id, explanation FROM questions
        WHERE (rejected = 0 OR rejected IS NULL) AND explanation IS NOT NULL
    """)
    questions = cursor.fetchall()

    stats = {
        "total_questions": total,
        "with_explanation": len(questions),
        "has_quick_answer": 0,
        "has_deep_dive": 0,
        "has_memory_hooks": 0,
        "has_step_by_step": 0,
        "has_common_traps": 0,
        "has_arrow_notation": 0,
        "has_explicit_thresholds": 0,
        "needs_upgrade": 0,
        "fully_compliant": 0
    }

    import re

    for q_id, expl_json in questions:
        if not expl_json:
            continue

        try:
            expl = json.loads(expl_json) if isinstance(expl_json, str) else expl_json
            if not isinstance(expl, dict):
                stats["needs_upgrade"] += 1
                continue

            # Check each enhanced element
            if expl.get("quick_answer"):
                stats["has_quick_answer"] += 1
            if expl.get("deep_dive"):
                stats["has_deep_dive"] += 1
            if expl.get("memory_hooks"):
                stats["has_memory_hooks"] += 1
            if expl.get("step_by_step"):
                stats["has_step_by_step"] += 1
            if expl.get("common_traps"):
                stats["has_common_traps"] += 1

            # Check for arrow notation
            combined = str(expl.get("principle", "")) + str(expl.get("clinical_reasoning", ""))
            if "→" in combined:
                stats["has_arrow_notation"] += 1

            # Check for explicit thresholds
            if re.search(r'[<>≥≤]\s*\d+', combined) or re.search(r'\d+\s*(mg|mcg|mL|mmHg|bpm|%)', combined):
                stats["has_explicit_thresholds"] += 1

            # Determine if fully compliant
            is_compliant = all([
                expl.get("quick_answer"),
                expl.get("deep_dive"),
                expl.get("memory_hooks"),
                "→" in combined
            ])

            if is_compliant:
                stats["fully_compliant"] += 1
            else:
                stats["needs_upgrade"] += 1

        except json.JSONDecodeError:
            stats["needs_upgrade"] += 1

    conn.close()
    return stats


def get_questions_needing_upgrade(db_path: str, limit: int = 100) -> List[Dict]:
    """Get questions that need explanation upgrades"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, vignette, answer_key, choices, explanation, specialty
        FROM questions
        WHERE (rejected = 0 OR rejected IS NULL) AND explanation IS NOT NULL
        ORDER BY RANDOM()
        LIMIT ?
    """, (limit * 2,))  # Get more to filter

    questions = cursor.fetchall()
    conn.close()

    needs_upgrade = []

    for q in questions:
        q_id, vignette, answer_key, choices_json, expl_json, specialty = q

        if not expl_json:
            continue

        try:
            expl = json.loads(expl_json)

            # Check if needs upgrade (missing any enhanced element)
            missing = []
            if not expl.get("quick_answer"):
                missing.append("quick_answer")
            if not expl.get("deep_dive"):
                missing.append("deep_dive")
            if not expl.get("memory_hooks"):
                missing.append("memory_hooks")
            if not expl.get("step_by_step"):
                missing.append("step_by_step")

            combined = str(expl.get("principle", "")) + str(expl.get("clinical_reasoning", ""))
            if "→" not in combined:
                missing.append("arrow_notation")

            if missing and len(needs_upgrade) < limit:
                needs_upgrade.append({
                    "id": q_id,
                    "vignette": vignette,
                    "answer_key": answer_key,
                    "choices": json.loads(choices_json) if choices_json else [],
                    "current_explanation": expl,
                    "specialty": specialty,
                    "missing_elements": missing
                })

        except json.JSONDecodeError:
            continue

    return needs_upgrade


def generate_enhanced_explanation(client: OpenAI, question: Dict, model: str = "gpt-4o") -> Optional[Dict]:
    """Generate enhanced explanation with all framework elements"""

    current = question["current_explanation"]
    choices = question["choices"]

    # Format choices
    if isinstance(choices, list):
        choices_text = "\n".join([f"{chr(65+i)}. {c}" for i, c in enumerate(choices)])
    else:
        choices_text = "\n".join([f"{k}. {v}" for k, v in sorted(choices.items())])

    prompt = f"""Enhance this USMLE question explanation to meet ShelfSense quality standards.

QUESTION:
{question['vignette']}

CHOICES:
{choices_text}

CORRECT ANSWER: {question['answer_key']}

CURRENT EXPLANATION:
Type: {current.get('type', 'Unknown')}
Principle: {current.get('principle', '')}
Clinical Reasoning: {current.get('clinical_reasoning', '')}

MISSING ELEMENTS: {question['missing_elements']}

Generate ONLY the missing/weak elements. Keep existing good content.

Return JSON with these fields (only include fields that need improvement):

{{
    "quick_answer": "30-word max rapid review summary. Example: 'Septic shock from cholecystitis needs urgent surgery, not just antibiotics.'",

    "principle": "Enhanced principle with arrow notation (→). Pattern: [Finding] with [marker] → [action]. Example: 'BP <90 with lactate >4 → septic shock → source control required'",

    "clinical_reasoning": "Enhanced reasoning with explicit thresholds. Example: 'BP 76/50 (systolic <90) and HR 128 (>100) indicate hemodynamic instability → septic shock. Low CVP (2 mmHg, normal 3-8) after fluids → vasodilation, not hypovolemia.'",

    "deep_dive": {{
        "pathophysiology": "Why this happens at biological/mechanistic level (2-3 sentences)",
        "differential_comparison": "How to distinguish from similar conditions",
        "clinical_pearls": ["High-yield fact 1", "Board-relevant detail 2"]
    }},

    "memory_hooks": {{
        "analogy": "Relatable comparison. Example: 'You can't put out a fire while fuel is still burning'",
        "mnemonic": "If applicable (e.g., MUDPILES for anion gap)",
        "clinical_story": "Brief memorable case pattern"
    }},

    "step_by_step": [
        {{"step": 1, "action": "What to do first", "rationale": "Why"}},
        {{"step": 2, "action": "Next step", "rationale": "Why"}},
        {{"step": 3, "action": "Final step", "rationale": "Why"}}
    ],

    "common_traps": [
        {{
            "trap": "What students commonly do wrong",
            "why_wrong": "Why this thinking fails",
            "correct_thinking": "The right approach"
        }}
    ]
}}

QUALITY RULES:
1. Use → for ALL causal relationships and decision paths
2. EVERY number must have context (e.g., "BP 80/50 (systolic <90)" not just "hypotensive")
3. quick_answer must be ≤30 words
4. Principle must be one clear decision rule
5. Distractor explanations must be specific to THIS patient"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert medical educator creating USMLE explanations following the ShelfSense framework."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )

        enhanced = json.loads(response.choices[0].message.content)
        return enhanced

    except Exception as e:
        print(f"  Error generating enhancement: {e}")
        return None


def merge_explanations(current: Dict, enhanced: Dict) -> Dict:
    """Merge enhanced elements into current explanation"""
    merged = current.copy()

    # Update principle and clinical_reasoning if enhanced versions have arrow notation
    if enhanced.get("principle") and "→" in enhanced["principle"]:
        merged["principle"] = enhanced["principle"]

    if enhanced.get("clinical_reasoning") and "→" in enhanced["clinical_reasoning"]:
        merged["clinical_reasoning"] = enhanced["clinical_reasoning"]

    # Add new elements
    for key in ["quick_answer", "deep_dive", "memory_hooks", "step_by_step", "common_traps"]:
        if enhanced.get(key):
            merged[key] = enhanced[key]

    return merged


def upgrade_question(db_path: str, question_id: str, enhanced_explanation: Dict):
    """Save upgraded explanation to database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE questions
        SET explanation = ?
        WHERE id = ?
    """, (json.dumps(enhanced_explanation), question_id))

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Upgrade ShelfSense question explanations")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    parser.add_argument("--batch", type=int, default=10, help="Number of questions to process")
    parser.add_argument("--all", action="store_true", help="Process all questions needing upgrade")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--db", default="shelfsense.db", help="Database path")
    args = parser.parse_args()

    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), args.db)

    print("=" * 70)
    print("ShelfSense Explanation Quality Upgrade")
    print("=" * 70)

    # Analyze current state
    print("\nAnalyzing current explanation quality...")
    stats = analyze_current_state(db_path)

    print(f"\nCurrent State:")
    print(f"  Total Questions: {stats['total_questions']}")
    print(f"  With Explanation: {stats['with_explanation']}")
    print(f"  Has quick_answer: {stats['has_quick_answer']} ({stats['has_quick_answer']/stats['with_explanation']*100:.1f}%)")
    print(f"  Has deep_dive: {stats['has_deep_dive']} ({stats['has_deep_dive']/stats['with_explanation']*100:.1f}%)")
    print(f"  Has memory_hooks: {stats['has_memory_hooks']} ({stats['has_memory_hooks']/stats['with_explanation']*100:.1f}%)")
    print(f"  Has step_by_step: {stats['has_step_by_step']} ({stats['has_step_by_step']/stats['with_explanation']*100:.1f}%)")
    print(f"  Has arrow notation: {stats['has_arrow_notation']} ({stats['has_arrow_notation']/stats['with_explanation']*100:.1f}%)")
    print(f"  Fully Compliant: {stats['fully_compliant']} ({stats['fully_compliant']/stats['with_explanation']*100:.1f}%)")
    print(f"  Needs Upgrade: {stats['needs_upgrade']}")

    if args.dry_run:
        print("\n[DRY RUN] Would process questions but not save changes")

    # Get questions to upgrade
    limit = stats['needs_upgrade'] if args.all else args.batch
    print(f"\nFetching {limit} questions needing upgrade...")

    questions = get_questions_needing_upgrade(db_path, limit=limit)
    print(f"Found {len(questions)} questions to upgrade")

    if not questions:
        print("No questions need upgrading!")
        return

    # Initialize OpenAI client
    try:
        client = get_openai_client()
    except ValueError as e:
        print(f"\nError: {e}")
        print("Set OPENAI_API_KEY environment variable and retry.")
        return

    # Process questions
    print(f"\nProcessing {len(questions)} questions...")
    print("-" * 70)

    results = {
        "processed": 0,
        "upgraded": 0,
        "failed": 0,
        "skipped": 0
    }

    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] Question: {q['id'][:30]}...")
        print(f"  Specialty: {q['specialty']}")
        print(f"  Missing: {', '.join(q['missing_elements'])}")

        # Generate enhanced explanation
        enhanced = generate_enhanced_explanation(client, q, model=args.model)

        if not enhanced:
            print(f"  ❌ Failed to generate enhancement")
            results["failed"] += 1
            continue

        # Merge with current
        merged = merge_explanations(q["current_explanation"], enhanced)

        # Show what changed
        new_elements = [k for k in ["quick_answer", "deep_dive", "memory_hooks", "step_by_step", "common_traps"]
                       if k in enhanced and enhanced[k]]
        print(f"  ✓ Enhanced with: {', '.join(new_elements)}")

        if enhanced.get("quick_answer"):
            print(f"  Quick: {enhanced['quick_answer'][:60]}...")

        if not args.dry_run:
            upgrade_question(db_path, q["id"], merged)
            print(f"  ✓ Saved to database")
            results["upgraded"] += 1
        else:
            print(f"  [DRY RUN] Would save changes")
            results["upgraded"] += 1

        results["processed"] += 1

        # Rate limiting
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("UPGRADE SUMMARY")
    print("=" * 70)
    print(f"  Processed: {results['processed']}")
    print(f"  Upgraded: {results['upgraded']}")
    print(f"  Failed: {results['failed']}")

    if not args.dry_run:
        print(f"\n✓ Changes saved to database")
        print(f"  Run again with --batch {args.batch} to continue upgrading")
    else:
        print(f"\n[DRY RUN] No changes were saved")
        print(f"  Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
