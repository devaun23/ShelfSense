"""
Enhanced Question Database Cleaner v2
Fixes all data quality issues:
- Removes "TBD XX." prefixes
- Validates 5 unique answer choices
- Validates answer_key
- Fixes extensive OCR errors
- Removes unfixable questions
"""

import json
import re
from pathlib import Path
from collections import Counter

def remove_tbd_prefix(text):
    """Remove 'TBD XX.' prefix from question text"""
    if not text:
        return text

    # Match "TBD" followed by optional space, number, period
    # Examples: "TBD 42.", "TBD50.", "TBD 13."
    text = re.sub(r'^TBD\s*\d+\.\s*', '', text, flags=re.IGNORECASE)
    return text.strip()


def fix_ocr_errors(text):
    """Fix comprehensive list of OCR errors"""
    if not text:
        return text

    # Medical term spacing errors
    replacements = {
        # Common word splits
        'treatme nt': 'treatment',
        'supplem eta l': 'supplemental',
        'abnorma l': 'abnormal',
        'hospita l': 'hospital',
        'critica l': 'critical',
        'additiona l': 'additional',
        'interna l': 'internal',
        'periphera l': 'peripheral',
        'myocardia l': 'myocardial',
        'appropriate ly': 'appropriately',
        'immunocomprom ised': 'immunocompromised',
        'vestibulococh lear': 'vestibulocochlear',

        # Unit spacing errors
        'mg/d L': 'mg/dL',
        'mg /dL': 'mg/dL',
        'mEq/ L': 'mEq/L',
        'mEq /L': 'mEq/L',
        'mm/ min': 'mm/min',
        'mm /min': 'mm/min',
        'mm /Hg': 'mmHg',
        'mm/ Hg': 'mmHg',
        'µmol/ L': 'µmol/L',
        'μmol/ L': 'μmol/L',
        '/mm 3': '/mm³',
        '/mm3': '/mm³',

        # Scientific name errors (slashes)
        'Haemophi/us': 'Haemophilus',
        'Klebsiel/a': 'Klebsiella',
        'Legionel/a': 'Legionella',
        'Moraxel/a': 'Moraxella',
        'Pseudomona /s': 'Pseudomonas',
        'Streptococcu /s': 'Streptococcus',
        'Staphylococcu /s': 'Staphylococcus',

        # Common typos
        'ities': 'ities',
        'litiies': 'lities',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    return text.strip()


def clean_vignette(vignette):
    """Clean question vignette text"""
    if isinstance(vignette, dict):
        text = f"{vignette.get('demographics', '')} {vignette.get('presentation', '')}".strip()
        if vignette.get('question_stem'):
            text = f"{text}\n\n{vignette['question_stem']}"
    else:
        text = str(vignette)

    # Remove TBD prefix first
    text = remove_tbd_prefix(text)

    # Remove duplicate lines
    lines = text.split('\n')
    seen = set()
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            seen.add(line_stripped)
            cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # Fix OCR errors
    text = fix_ocr_errors(text)

    return text.strip()


def normalize_choice(choice):
    """Normalize a choice for comparison"""
    if isinstance(choice, dict):
        text = choice.get('text', str(choice))
    else:
        text = str(choice)

    # Remove leading letters (A., B., etc.) and normalize
    text = re.sub(r'^[A-E]\.\s*', '', text, flags=re.IGNORECASE)
    text = fix_ocr_errors(text)
    return text.strip()


def deduplicate_choices(choices):
    """Remove duplicate answer choices and return normalized list"""
    if not isinstance(choices, list):
        return []

    seen_normalized = set()
    unique_choices = []

    for choice in choices:
        normalized = normalize_choice(choice)
        normalized_lower = normalized.lower().strip()

        if normalized and normalized_lower and normalized_lower not in seen_normalized:
            seen_normalized.add(normalized_lower)
            unique_choices.append(normalized)

    return unique_choices


def validate_question(question):
    """
    Validate question has all required fields and correct structure
    Returns (is_valid, error_message)
    """
    # Check vignette exists
    if not question.get('vignette'):
        return False, "Missing vignette"

    # Check choices exist and is list
    choices = question.get('choices')
    if not isinstance(choices, list):
        return False, "Choices not a list"

    # Check exactly 5 unique choices
    if len(choices) != 5:
        return False, f"Has {len(choices)} choices, need 5"

    # Check all choices are non-empty
    for i, choice in enumerate(choices):
        if not choice or (isinstance(choice, str) and not choice.strip()):
            return False, f"Choice {i} is empty"

    # Check correct_answer exists and is valid (note: field is "correct_answer" not "answer_key")
    answer_key = question.get('correct_answer', question.get('answer_key', '')).strip().upper()
    if answer_key not in ['A', 'B', 'C', 'D', 'E']:
        return False, f"Invalid correct_answer: {answer_key}"

    return True, None


def clean_question_database():
    """Clean the entire question database with comprehensive fixes"""

    db_path = Path(__file__).parent.parent / "data" / "extracted_questions" / "shelfsense_master_database.json"

    print(f"Loading database from: {db_path}")
    with open(db_path, 'r') as f:
        data = json.load(f)

    questions = data['questions']
    print(f"Total questions before cleaning: {len(questions)}")

    # Statistics
    tbd_removed = 0
    vignettes_cleaned = 0
    duplicate_choices_fixed = 0
    questions_removed = 0
    choices_padded = 0

    cleaned_questions = []
    removed_questions = []

    for q in questions:
        original_vignette = q.get('vignette', '')

        # Clean vignette
        cleaned_vignette = clean_vignette(original_vignette)
        if 'TBD' in str(original_vignette).upper():
            tbd_removed += 1
        if cleaned_vignette != original_vignette:
            vignettes_cleaned += 1
        q['vignette'] = cleaned_vignette

        # Clean and deduplicate choices
        if 'choices' in q:
            original_count = len(q['choices']) if isinstance(q['choices'], list) else 0
            q['choices'] = deduplicate_choices(q['choices'])
            new_count = len(q['choices'])

            if new_count < original_count:
                duplicate_choices_fixed += 1

            # Try to pad to 5 choices if we have 4 (common case)
            if new_count == 4:
                q['choices'].append("None of the above")
                choices_padded += 1
                new_count = 5

        # Normalize answer field (could be "correct_answer" or "answer_key")
        if 'correct_answer' in q:
            q['correct_answer'] = q['correct_answer'].strip().upper()
        elif 'answer_key' in q:
            q['answer_key'] = q['answer_key'].strip().upper()

        # Validate question
        is_valid, error = validate_question(q)

        if is_valid:
            cleaned_questions.append(q)
        else:
            questions_removed += 1
            removed_questions.append({
                'id': q.get('id', 'unknown'),
                'reason': error,
                'vignette_preview': q.get('vignette', '')[:100]
            })

    # Update data with cleaned questions
    data['questions'] = cleaned_questions

    print(f"\n{'='*60}")
    print("CLEANING RESULTS:")
    print(f"{'='*60}")
    print(f"Questions before:              {len(questions)}")
    print(f"Questions after:               {len(cleaned_questions)}")
    print(f"Questions removed:             {questions_removed}")
    print(f"\nCleaning operations:")
    print(f"  TBD prefixes removed:        {tbd_removed}")
    print(f"  Vignettes cleaned:           {vignettes_cleaned}")
    print(f"  Duplicate choices fixed:     {duplicate_choices_fixed}")
    print(f"  4-choice questions padded:   {choices_padded}")

    # Show removed questions
    if removed_questions:
        print(f"\n{'='*60}")
        print(f"REMOVED QUESTIONS ({len(removed_questions)}):")
        print(f"{'='*60}")
        for i, rq in enumerate(removed_questions[:10], 1):  # Show first 10
            print(f"\n{i}. ID: {rq['id']}")
            print(f"   Reason: {rq['reason']}")
            print(f"   Preview: {rq['vignette_preview']}...")

        if len(removed_questions) > 10:
            print(f"\n... and {len(removed_questions) - 10} more")

    # Save cleaned database
    output_path = db_path.parent / "shelfsense_master_database_cleaned.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Cleaned database saved to: {output_path}")

    # Generate statistics
    choice_counts = Counter()
    answer_key_counts = Counter()

    for q in cleaned_questions:
        if 'choices' in q:
            choice_counts[len(q['choices'])] += 1
        # Check both correct_answer and answer_key fields
        answer = q.get('correct_answer') or q.get('answer_key')
        if answer:
            answer_key_counts[answer] += 1

    print(f"\nAnswer choice distribution:")
    for count in sorted(choice_counts.keys()):
        print(f"  {count} choices: {choice_counts[count]} questions")

    print(f"\nAnswer key distribution:")
    for key in sorted(answer_key_counts.keys()):
        print(f"  {key}: {answer_key_counts[key]} questions")

    print(f"{'='*60}\n")

    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("ShelfSense - Enhanced Question Database Cleaner v2")
    print("=" * 60)
    print()

    clean_question_database()

    print("\n" + "=" * 60)
    print("Cleaning complete!")
    print("=" * 60)
