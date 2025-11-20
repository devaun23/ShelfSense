#!/usr/bin/env python3
"""
Verification Script - Maximum Extraction Check
Confirms all available questions have been extracted from all PDFs
"""

import pdfplumber
from pathlib import Path
import json
import re
from collections import defaultdict

def count_questions_in_pdf(pdf_path: Path, max_questions: int = 250) -> dict:
    """Count actual question numbers present in a PDF"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ''
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += text + '\n'

            # Find unique question numbers
            found_questions = set()
            for num in range(1, max_questions + 1):
                # Multiple patterns to catch different formats
                patterns = [
                    rf'\b{num}\.\s+[A-Z]',  # "1. A"
                    rf'\n{num}\)\s+',        # "1) "
                    rf'\({num}\)',           # "(1)"
                    rf'Question\s+{num}',    # "Question 1"
                ]
                for pattern in patterns:
                    if re.search(pattern, all_text):
                        found_questions.add(num)
                        break

            return {
                'pdf_name': pdf_path.name,
                'question_count': len(found_questions),
                'question_numbers': sorted(list(found_questions)),
                'file_size_mb': pdf_path.stat().st_size / 1024 / 1024,
                'page_count': len(pdf.pages)
            }
    except Exception as e:
        return {
            'pdf_name': pdf_path.name,
            'error': str(e),
            'question_count': 0
        }

def verify_all_pdfs():
    """Verify extraction from all available PDFs"""
    print(f"\n{'='*80}")
    print("MAXIMUM EXTRACTION VERIFICATION")
    print(f"{'='*80}\n")

    results = {
        'shelf_exams': {},
        'nbme_answers': {},
        'nbme_questions_only': {},
        'summary': {}
    }

    # 1. Shelf Exam PDFs
    print("Checking Shelf Exam PDFs...")
    shelf_dir = Path("/Users/devaun/Desktop/Compressed_PDFs")
    shelf_pdfs = list(shelf_dir.glob("*.pdf"))

    shelf_total = 0
    for pdf_path in sorted(shelf_pdfs):
        result = count_questions_in_pdf(pdf_path, max_questions=50)
        results['shelf_exams'][pdf_path.name] = result
        shelf_total += result.get('question_count', 0)
        print(f"  {pdf_path.name}: {result.get('question_count', 0)} questions")

    print(f"\nShelf Exams Total: {shelf_total} questions from {len(shelf_pdfs)} PDFs")

    # 2. NBME Answer PDFs
    print("\nChecking NBME Answer PDFs...")
    nbme_dir = Path("/Users/devaun/Desktop/NBMEs-selected")
    nbme_answer_pdfs = list(nbme_dir.glob("*ANSWERS*.pdf"))

    nbme_answer_total = 0
    for pdf_path in sorted(nbme_answer_pdfs):
        result = count_questions_in_pdf(pdf_path, max_questions=250)
        results['nbme_answers'][pdf_path.name] = result
        nbme_answer_total += result.get('question_count', 0)
        print(f"  {pdf_path.name}: {result.get('question_count', 0)} questions")

    print(f"\nNBME Answers Total: {nbme_answer_total} questions from {len(nbme_answer_pdfs)} PDFs")

    # 3. NBME Question-Only PDFs
    print("\nChecking NBME Question-Only PDFs...")
    nbme_question_pdfs = list(nbme_dir.glob("*Questions*.pdf"))

    nbme_question_total = 0
    for pdf_path in sorted(nbme_question_pdfs):
        result = count_questions_in_pdf(pdf_path, max_questions=250)
        results['nbme_questions_only'][pdf_path.name] = result
        nbme_question_total += result.get('question_count', 0)
        print(f"  {pdf_path.name}: {result.get('question_count', 0)} questions")

    print(f"\nNBME Questions-Only Total: {nbme_question_total} questions from {len(nbme_question_pdfs)} PDFs")

    # 4. Compare with Extracted Database
    print("\n" + "="*80)
    print("COMPARING WITH EXTRACTED DATABASE")
    print("="*80 + "\n")

    db_path = Path("/Users/devaun/ShelfSense/data/extracted_questions/shelfsense_master_database.json")
    if db_path.exists():
        with open(db_path, 'r') as f:
            master_db = json.load(f)
            extracted_count = master_db['metadata']['total_questions']
            print(f"Current Master Database: {extracted_count} unique questions")
    else:
        extracted_count = 0
        print("Master database not found yet")

    # Summary
    available_total = shelf_total + nbme_answer_total
    results['summary'] = {
        'shelf_exams_available': shelf_total,
        'nbme_answers_available': nbme_answer_total,
        'nbme_questions_only_available': nbme_question_total,
        'total_available_with_answers': available_total,
        'currently_extracted': extracted_count,
        'extraction_percentage': round((extracted_count / available_total * 100), 2) if available_total > 0 else 0
    }

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Shelf Exams Available: {shelf_total} questions")
    print(f"NBME Answers Available: {nbme_answer_total} questions")
    print(f"NBME Questions-Only: {nbme_question_total} questions (for training)")
    print(f"\nTotal Available (with answers): {available_total} questions")
    print(f"Currently Extracted: {extracted_count} unique questions")
    print(f"Extraction Rate: {results['summary']['extraction_percentage']}%")

    if extracted_count < available_total:
        missing = available_total - extracted_count
        print(f"\n⚠️  Potential missing questions: {missing}")
        print("Note: After deduplication, this is expected. Check individual PDFs for gaps.")
    else:
        print(f"\n✓ Extraction appears complete (accounting for deduplication)")

    print(f"{'='*80}\n")

    # Save verification report
    output_path = Path("/Users/devaun/ShelfSense/data/extracted_questions/verification_report.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"✓ Verification report saved: {output_path}")

    return results

if __name__ == "__main__":
    verify_all_pdfs()
