#!/usr/bin/env python3
"""
Extract NBME Question-Only PDFs (No Answers)
For algorithm training on NBME writing style and question patterns
"""

import sys
sys.path.append('/Users/devaun/ShelfSense')

from nbme_comprehensive_extractor import NBMEComprehensiveExtractor
from pathlib import Path
import json

pdf_dir = Path("/Users/devaun/Desktop/NBMEs-selected")
output_dir = Path("/Users/devaun/ShelfSense/data/extracted_questions")

# Question-only PDFs (no answers)
question_pdfs = [
    "NBME 6 - Questions.pdf",
    "NBME 7 - Questions.pdf",
    "NBME 8 - Questions.pdf",
    "NBME 9 - Questions.pdf",
    "NBME 11 - Questions.pdf",
    "NBME 12 - Questions.pdf",
    "NBME 13 - Questions.pdf"
]

print(f"\n{'='*70}")
print("Extracting NBME Question-Only PDFs (No Answers)")
print("For algorithm training on NBME writing style")
print(f"{'='*70}\n")

extractor = NBMEComprehensiveExtractor(pdf_directory=str(pdf_dir))
all_questions = []

for pdf_name in question_pdfs:
    pdf_path = pdf_dir / pdf_name
    if not pdf_path.exists():
        print(f"⚠ Skipping {pdf_name} - not found")
        continue

    nbme_num = pdf_name.replace("NBME ", "").replace(" - Questions.pdf", "")
    print(f"\nExtracting NBME {nbme_num} Questions...")

    try:
        questions = extractor.extract_all_questions_from_pdf(pdf_path)

        # Mark as question-only (no answer key)
        for q in questions:
            q['source_type'] = 'nbme_questions_only'
            q['nbme_exam'] = nbme_num
            q['has_answer_key'] = False

        all_questions.extend(questions)
        print(f"✓ Extracted {len(questions)} questions from NBME {nbme_num}")

        # Save individual file
        output_file = output_dir / f"nbme_{nbme_num}_questions_only.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        print(f"  Saved to {output_file.name}")

    except Exception as e:
        print(f"✗ Error extracting NBME {nbme_num}: {e}")

# Save consolidated questions-only file
print(f"\n{'='*70}")
print(f"Total questions extracted: {len(all_questions)}")
print(f"{'='*70}\n")

consolidated_path = output_dir / "nbme_questions_only_consolidated.json"
with open(consolidated_path, 'w', encoding='utf-8') as f:
    json.dump({
        "metadata": {
            "type": "nbme_questions_only",
            "description": "NBME questions without answer keys for writing style training",
            "total_questions": len(all_questions),
            "exams": question_pdfs
        },
        "questions": all_questions
    }, f, indent=2, ensure_ascii=False)

print(f"✓ Saved consolidated file: {consolidated_path.name}")
print(f"\nQuestion-only extraction complete!")
print("These questions will help the algorithm learn NBME writing patterns.")
