#!/usr/bin/env python3
"""
Run OCR extraction on all 8 image-based PDFs with FIXED pattern
This uses the corrected nbme_ocr_extractor.py
"""

from nbme_ocr_extractor import NBMEOCRExtractor
from pathlib import Path

def main():
    pdf_directory = "/Users/devaun/Desktop/Compressed_PDFs"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    # ALL 8 image-based PDFs
    target_pdfs = [
        "Medicine 7 - Answers.pdf",
        "Medicine 8 - Answers.pdf",
        "Neuro 7 - Answers.pdf",
        "Neuro 8 - Answers.pdf",
        "Pediatrics 7 - Answers.pdf",
        "Pediatrics 8 - Answers.pdf",
        "Surgery 7 - Answers.pdf",
        "Surgery 8 - Answers.pdf"
    ]

    print("="*60)
    print("OCR EXTRACTION - ALL 8 IMAGE PDFs WITH FIXED PATTERN")
    print("="*60)
    print(f"Processing {len(target_pdfs)} PDFs...")
    print("="*60)

    extractor = NBMEOCRExtractor(pdf_directory)
    questions = extractor.process_specific_pdfs(target_pdfs)
    extractor.save_to_json(questions, output_directory)

    print("\n✓ OCR extraction complete!")

if __name__ == "__main__":
    main()
