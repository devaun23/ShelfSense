"""
Clean question database - fix duplicates, typos, and data quality issues
"""

import json
import re
from pathlib import Path
from collections import Counter

def clean_vignette(vignette):
    """Remove duplicate question stems and clean formatting"""
    if isinstance(vignette, dict):
        # Extract text from dict structure
        text = f"{vignette.get('demographics', '')} {vignette.get('presentation', '')}".strip()
        if vignette.get('question_stem'):
            text = f"{text}\n\n{vignette['question_stem']}"
    else:
        text = str(vignette)

    # Remove duplicate lines (common extraction issue)
    lines = text.split('\n')
    seen = set()
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            seen.add(line_stripped)
            cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # Fix common OCR/extraction typos
    replacements = {
        'treatme nt': 'treatment',
        'supplemeta l': 'supplemental',
        'abnorma l': 'abnormal',
        'hospita l': 'hospital',
        'critica l': 'critical',
        'additiona l': 'additional',
        'interna l': 'internal',
        'mg/d L': 'mg/dL',
        'mEq/ L': 'mEq/L',
        'mm/ min': 'mm/min',
        'µmol/ L': 'µmol/L',
        'μmol/ L': 'μmol/L',
        'ities': 'ities',
        'litiies': 'lities',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    return text.strip()


def deduplicate_choices(choices):
    """Remove duplicate answer choices"""
    if not isinstance(choices, list):
        return choices

    # Extract text from choice objects or strings
    seen_texts = set()
    unique_choices = []

    for choice in choices:
        if isinstance(choice, dict):
            text = choice.get('text', str(choice))
        else:
            text = str(choice)

        # Normalize text for comparison
        normalized = text.strip().lower()

        if normalized and normalized not in seen_texts:
            seen_texts.add(normalized)
            unique_choices.append(text)

    return unique_choices


def clean_question_database():
    """Clean the entire question database"""

    db_path = Path(__file__).parent.parent / "data" / "extracted_questions" / "shelfsense_master_database.json"

    print(f"Loading database from: {db_path}")
    with open(db_path, 'r') as f:
        data = json.load(f)

    questions = data['questions']
    print(f"Total questions: {len(questions)}")

    cleaned_count = 0
    duplicate_choices_fixed = 0
    vignettes_cleaned = 0

    for q in questions:
        # Clean vignette
        original_vignette = q.get('vignette', '')
        cleaned_vignette = clean_vignette(original_vignette)
        if cleaned_vignette != original_vignette:
            q['vignette'] = cleaned_vignette
            vignettes_cleaned += 1

        # Deduplicate choices
        if 'choices' in q and isinstance(q['choices'], list):
            original_count = len(q['choices'])
            q['choices'] = deduplicate_choices(q['choices'])
            new_count = len(q['choices'])

            if new_count < original_count:
                duplicate_choices_fixed += 1
                cleaned_count += 1

    print(f"\nCleaning results:")
    print(f"  Vignettes cleaned: {vignettes_cleaned}")
    print(f"  Questions with duplicate choices fixed: {duplicate_choices_fixed}")
    print(f"  Total questions cleaned: {cleaned_count}")

    # Save cleaned database
    output_path = db_path.parent / "shelfsense_master_database_cleaned.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nCleaned database saved to: {output_path}")

    # Generate statistics
    choice_counts = Counter()
    for q in questions:
        if 'choices' in q:
            choice_counts[len(q['choices'])] += 1

    print(f"\nAnswer choice distribution after cleaning:")
    for count in sorted(choice_counts.keys()):
        print(f"  {count} choices: {choice_counts[count]} questions")

    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("ShelfSense - Question Database Cleaner")
    print("=" * 60)

    clean_question_database()

    print("\n" + "=" * 60)
    print("Cleaning complete!")
    print("=" * 60)
