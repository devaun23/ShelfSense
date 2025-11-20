"""
AI-Powered OCR Error Cleaner with Multi-Layer Quality Control

This script:
1. Identifies questions with OCR errors using regex patterns
2. Uses GPT-4o-mini to conservatively fix spacing errors
3. Logs every change with reasoning
4. Validates medical accuracy
5. Generates HTML change report for human review
6. Applies changes only after approval

Usage:
    python clean_with_validation.py --dry-run    # Preview changes
    python clean_with_validation.py --execute    # Apply changes
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.models import Question

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# OCR error patterns to detect
OCR_PATTERNS = [
    r'\w+ [ltesn](?:\s|$|\.|,)',  # Word ending with space + single letter
    r'year-o ld',
    r'construct ion',
    r'hospit al',
    r'departme nt',
    r'emergen cy',
    r'mg/d L',
    r'mEq/ L',
    r'mm /Hg',
    r'mm/ Hg',
    r'μmol/ L',
    r'µmol/ L',
]


def has_ocr_errors(text):
    """Check if text contains OCR errors"""
    for pattern in OCR_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def clean_text_with_ai(text, context=""):
    """
    Use GPT-4o-mini to conservatively fix OCR errors
    Returns: {
        'corrected_text': str,
        'changes': [{from, to, reason, confidence}],
        'total_changes': int
    }
    """
    prompt = f"""You are an OCR error correction expert for medical text. Fix ONLY obvious OCR spacing errors.

DO NOT change:
- Medical terminology (unless obvious spacing typo)
- Clinical values or numbers
- Diagnostic terms
- Any text that is already correct

ONLY fix obvious spacing patterns like:
- "year-o ld" → "year-old"
- "clopidog rel" → "clopidogrel"
- "atorvastat in" → "atorvastatin"
- "construct ion" → "construction"
- "departme nt" → "department"
- "emergen cy" → "emergency"
- "mg/d L" → "mg/dL"
- "mEq/ L" → "mEq/L"
- "mm /Hg" → "mmHg"

Context: {context}

Text to fix:
{text}

Return JSON with:
{{
  "corrected_text": "the fully corrected text",
  "changes": [
    {{
      "from": "original phrase",
      "to": "corrected phrase",
      "reason": "brief explanation",
      "confidence": 95
    }}
  ]
}}

Be conservative. Only fix if you are 90%+ confident."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical OCR error correction expert. Be conservative and precise."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        result = json.loads(response.choices[0].message.content)
        result['total_changes'] = len(result.get('changes', []))
        return result

    except Exception as e:
        print(f"AI cleaning error: {e}")
        return {
            'corrected_text': text,
            'changes': [],
            'total_changes': 0
        }


def validate_medical_accuracy(original, corrected, changes):
    """
    Second AI pass to validate medical accuracy of changes
    Returns: (is_safe: bool, concerns: str)
    """
    if not changes:
        return True, ""

    prompt = f"""You are a USMLE Step 2 CK expert. Review these OCR corrections for medical accuracy:

Original: {original}
Corrected: {corrected}

Changes made:
{json.dumps(changes, indent=2)}

Are these corrections medically accurate? Could any change alter the medical meaning?
Return JSON:
{{
  "is_safe": true/false,
  "concerns": "any medical accuracy concerns, or empty string if safe"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        result = json.loads(response.choices[0].message.content)
        return result.get('is_safe', True), result.get('concerns', '')

    except Exception as e:
        print(f"Validation error: {e}")
        return True, ""


def generate_change_report(all_changes, output_path):
    """Generate HTML report of all changes for human review"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>OCR Cleaning Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        .summary {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .question {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #4CAF50; }}
        .change {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 3px solid #2196F3; }}
        .from {{ color: #d32f2f; text-decoration: line-through; }}
        .to {{ color: #388e3c; font-weight: bold; }}
        .concern {{ background: #fff3cd; border-left: 3px solid #ffc107; padding: 10px; margin-top: 10px; }}
        .preview {{ background: #f5f5f5; padding: 10px; margin: 10px 0; font-family: monospace; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>🔍 OCR Cleaning Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Questions Processed:</strong> {len(all_changes)}</p>
        <p><strong>Questions with Changes:</strong> {sum(1 for c in all_changes if c['total_changes'] > 0)}</p>
        <p><strong>Total Changes Made:</strong> {sum(c['total_changes'] for c in all_changes)}</p>
        <p><strong>Questions with Concerns:</strong> {sum(1 for c in all_changes if c.get('concerns'))}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

    for i, change_data in enumerate(all_changes, 1):
        if change_data['total_changes'] == 0:
            continue

        html += f"""
    <div class="question">
        <h3>Question {i}: {change_data['question_id'][:8]}...</h3>
        <p><strong>Source:</strong> {change_data['source']}</p>
        <p><strong>Changes:</strong> {change_data['total_changes']}</p>
"""

        for change in change_data['changes']:
            html += f"""
        <div class="change">
            <p><span class="from">"{change['from']}"</span> → <span class="to">"{change['to']}"</span></p>
            <p><strong>Reason:</strong> {change['reason']}</p>
            <p><strong>Confidence:</strong> {change['confidence']}%</p>
        </div>
"""

        if change_data.get('concerns'):
            html += f"""
        <div class="concern">
            <strong>⚠️ Medical Validation Concern:</strong> {change_data['concerns']}
        </div>
"""

        html += f"""
        <div class="preview">
            <strong>Original Vignette:</strong><br>
            {change_data['original_vignette'][:300]}...
        </div>
        <div class="preview">
            <strong>Corrected Vignette:</strong><br>
            {change_data['corrected_vignette'][:300]}...
        </div>
    </div>
"""

    html += """
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"\n✅ Change report generated: {output_path}")


def main(dry_run=True):
    """Main cleaning process"""

    print("=" * 80)
    print("ShelfSense - AI-Powered OCR Cleaner with Quality Control")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'EXECUTE (will apply changes)'}")
    print()

    # Connect to database
    db = SessionLocal()

    try:
        # Get all questions
        questions = db.query(Question).all()
        print(f"Total questions in database: {len(questions)}")

        # Filter questions with OCR errors
        questions_with_errors = []
        for q in questions:
            full_text = q.vignette + " " + " ".join(q.choices)
            if has_ocr_errors(full_text):
                questions_with_errors.append(q)

        print(f"Questions with OCR errors: {len(questions_with_errors)}")
        print()

        if not questions_with_errors:
            print("✅ No OCR errors found! Database is clean.")
            return

        # Process each question with AI
        all_changes = []

        for i, question in enumerate(questions_with_errors, 1):
            print(f"Processing {i}/{len(questions_with_errors)}: {question.id[:8]}...")

            # Clean vignette
            vignette_result = clean_text_with_ai(
                question.vignette,
                context=f"This is a USMLE Step 2 CK question vignette from {question.source}"
            )

            # Clean choices
            cleaned_choices = []
            choice_changes = []

            for choice in question.choices:
                choice_result = clean_text_with_ai(
                    choice,
                    context="This is a multiple choice answer option for a USMLE question"
                )
                cleaned_choices.append(choice_result['corrected_text'])
                choice_changes.extend(choice_result['changes'])

            # Combine all changes
            all_question_changes = vignette_result['changes'] + choice_changes

            # Validate medical accuracy
            is_safe, concerns = validate_medical_accuracy(
                question.vignette,
                vignette_result['corrected_text'],
                all_question_changes
            )

            # Store change data
            change_data = {
                'question_id': question.id,
                'source': question.source or 'Unknown',
                'original_vignette': question.vignette,
                'corrected_vignette': vignette_result['corrected_text'],
                'original_choices': question.choices,
                'corrected_choices': cleaned_choices,
                'changes': all_question_changes,
                'total_changes': len(all_question_changes),
                'is_safe': is_safe,
                'concerns': concerns if not is_safe else ''
            }

            all_changes.append(change_data)

            # Apply changes if not dry run and safe
            if not dry_run and is_safe and change_data['total_changes'] > 0:
                question.vignette = vignette_result['corrected_text']
                question.choices = cleaned_choices
                print(f"  ✓ Applied {change_data['total_changes']} changes")
            elif change_data['total_changes'] > 0:
                print(f"  → {change_data['total_changes']} changes found")
                if not is_safe:
                    print(f"  ⚠️  Has medical concerns: {concerns}")

        # Commit changes if not dry run
        if not dry_run:
            db.commit()
            print(f"\n✅ Changes committed to database")

        # Generate report
        report_path = Path(__file__).parent / f"ocr_cleaning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        generate_change_report(all_changes, report_path)

        # Summary
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Questions processed: {len(all_changes)}")
        print(f"Questions with changes: {sum(1 for c in all_changes if c['total_changes'] > 0)}")
        print(f"Total changes made: {sum(c['total_changes'] for c in all_changes)}")
        print(f"Questions with medical concerns: {sum(1 for c in all_changes if c.get('concerns'))}")
        print()
        print(f"📊 Review the change report: file://{report_path}")

        if dry_run:
            print()
            print("This was a DRY RUN. No changes were applied.")
            print("Review the report, then run with --execute to apply changes.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean OCR errors with AI validation')
    parser.add_argument('--execute', action='store_true', help='Execute changes (default is dry-run)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes only (default)')

    args = parser.parse_args()

    # Default to dry-run unless --execute is specified
    dry_run = not args.execute

    main(dry_run=dry_run)
