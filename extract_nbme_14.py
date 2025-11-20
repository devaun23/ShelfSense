#!/usr/bin/env python3
"""Quick extractor for NBME 14"""

import sys
sys.path.append('/Users/devaun/ShelfSense')

from nbme_comprehensive_extractor import NBMEComprehensiveExtractor
from pathlib import Path
import json

pdf_path = Path("/Users/devaun/Desktop/NBMEs-selected/NBME 14 - ANSWERS.pdf")
output_dir = Path("/Users/devaun/ShelfSense/data/extracted_questions")
pdf_dir = Path("/Users/devaun/Desktop/NBMEs-selected")

print("Extracting NBME 14...")
extractor = NBMEComprehensiveExtractor(pdf_directory=str(pdf_dir))
questions = extractor.extract_all_questions_from_pdf(pdf_path)

print(f"\n✓ Extracted {len(questions)} questions from NBME 14")

# Save
output_file = output_dir / "nbme_14_questions.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(questions, f, indent=2, ensure_ascii=False)

print(f"✓ Saved to {output_file}")
print(f"\nNBME 14 extraction complete!")
