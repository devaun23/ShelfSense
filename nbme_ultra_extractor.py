#!/usr/bin/env python3
"""
ULTRA-ROBUST NBME Extractor
Uses multiple strategies to ensure we get EVERY question from each PDF
"""

import pdfplumber
import re
import json
from pathlib import Path
from nbme_complete_extractor import NBMECompleteExtractor

class UltraExtractor(NBMECompleteExtractor):
    """Ultra-robust extractor that gets ALL questions"""

    def extract_all_questions_from_pdf(self, pdf_path: Path):
        """Extract using multiple strategies and combine results"""

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"\nProcessing: {pdf_path.name} ({total_pages} pages)")

            # Collect all text
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += "\n" + text

            # Strategy 1: Original pattern
            questions_v1 = self._extract_with_pattern(all_text, r'(?:^|\n|\)\()\s*(\d+)\.\s+([A-Z])')

            # Strategy 2: More flexible - just number + period + any char
            questions_v2 = self._extract_with_pattern(all_text, r'(?:^|\n|\s)(\d+)\.\s+([A-Za-z])')

            # Strategy 3: Page-by-page extraction for stubborn cases
            questions_v3 = self._extract_page_by_page(pdf)

            # Merge all results, keeping best version of each question
            merged = self._merge_questions([questions_v1, questions_v2, questions_v3])

            print(f"  Strategy 1: {len(questions_v1)} questions")
            print(f"  Strategy 2: {len(questions_v2)} questions")
            print(f"  Strategy 3: {len(questions_v3)} questions")
            print(f"  Merged total: {len(merged)} questions")

            return merged

    def _extract_with_pattern(self, all_text: str, pattern: str):
        """Extract using a specific regex pattern"""
        questions = []
        question_splits = re.split(pattern, all_text)

        i = 1
        while i < len(question_splits):
            if i + 2 >= len(question_splits):
                break

            question_num = question_splits[i]
            first_char = question_splits[i+1]
            question_text = question_splits[i+2]

            # Only process if question number is 1-50
            try:
                num_int = int(question_num)
                if 1 <= num_int <= 50:
                    full_question_text = f"{question_num}. {first_char}{question_text}"
                    question = self.extract_single_question(full_question_text, question_num)
                    if question:
                        questions.append(question)
            except ValueError:
                pass

            i += 3

        return questions

    def _extract_page_by_page(self, pdf):
        """Extract by processing each page individually"""
        questions = []

        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            # Look for question starts on this page
            matches = list(re.finditer(r'(?:^|\n)(\d+)\.\s+([A-Za-z])', text, re.MULTILINE))

            for match in matches:
                question_num = match.group(1)
                try:
                    num_int = int(question_num)
                    if 1 <= num_int <= 50:
                        # Get text from this match to end of page
                        start = match.start()
                        page_text = text[start:]

                        # Try to extract
                        question = self.extract_single_question(page_text, question_num)
                        if question:
                            questions.append(question)
                except ValueError:
                    pass

        return questions

    def _merge_questions(self, question_lists):
        """Merge multiple question lists, keeping best version of each"""
        merged = {}

        for question_list in question_lists:
            for q in question_list:
                q_num = q['question_num']

                # Keep this version if:
                # 1. We don't have this question yet, OR
                # 2. This version has a better answer (not TBD)
                if q_num not in merged:
                    merged[q_num] = q
                elif q['correct_answer'] != 'TBD' and merged[q_num]['correct_answer'] == 'TBD':
                    merged[q_num] = q
                elif len(q.get('correct_explanation', '')) > len(merged[q_num].get('correct_explanation', '')):
                    # This version has a longer explanation
                    merged[q_num] = q

        # Return sorted by question number
        return [merged[k] for k in sorted(merged.keys(), key=lambda x: int(x))]

def main():
    from pathlib import Path
    import json

    pdf_directory = "/Users/devaun/Desktop/Compressed_PDFs"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    # PDFs that need ultra extraction (missing questions)
    problem_pdfs = [
        ("Internal Medicine 3 - Answers.pdf", "Internal Medicine"),
        ("Internal Medicine 4 - Answers v1 [wide].pdf", "Internal Medicine"),
        ("Internal Medicine 5 - Answers.pdf", "Internal Medicine"),
        ("Internal Medicine 6 - Answers.pdf", "Internal Medicine"),
        ("Neuro 3 - Answers.pdf", "Neurology"),
        ("Neuro 5 - Answers.pdf", "Neurology"),
        ("Neuro 6 - Answers.pdf", "Neurology"),
        ("Pediatric 3 - Answers v1 [wide].pdf", "Pediatrics"),
        ("Pediatrics 4 - Answers v1 [wide].pdf", "Pediatrics"),
        ("Pediatrics 5 - Answers v1 [wide].pdf", "Pediatrics"),
        ("Pediatrics 6 - Answers v1 [wide].pdf", "Pediatrics"),
        ("Surgery 3 - Answers v1 [wide].pdf", "Surgery"),
        ("Surgery 4 - Answers v1 [wide].pdf", "Surgery"),
        ("Surgery 5 - Answers v1 [wide].pdf", "Surgery"),
        ("Surgery 6 - Answers v1 [wide].pdf", "Surgery"),
    ]

    print("="*60)
    print("ULTRA-ROBUST NBME Extractor")
    print("="*60)

    extractor = UltraExtractor(pdf_directory)

    # Process each PDF
    additional_questions = {
        "Internal Medicine": [],
        "Neurology": [],
        "Pediatrics": [],
        "Surgery": []
    }

    for pdf_name, specialty in problem_pdfs:
        pdf_path = Path(pdf_directory) / pdf_name
        if not pdf_path.exists():
            print(f"Skipping {pdf_name} (not found)")
            continue

        questions = extractor.extract_all_questions_from_pdf(pdf_path)

        # Convert to ShelfSense format
        for q in questions:
            shelfsense_q = extractor.convert_to_shelfsense_format(q, specialty, pdf_path.stem)
            additional_questions[specialty].append(shelfsense_q)

    # Load existing questions and replace
    for specialty in additional_questions.keys():
        if additional_questions[specialty]:
            filename = f"{specialty.lower().replace(' ', '_')}_questions.json"
            filepath = output_directory / filename

            # Load existing
            existing = []
            if filepath.exists():
                with open(filepath, 'r') as f:
                    existing = json.load(f)

            # Remove old versions from these PDFs
            old_ids = {q['id'] for q in additional_questions[specialty]}
            filtered_existing = [q for q in existing if q['id'] not in old_ids]

            # Add new versions
            updated = filtered_existing + additional_questions[specialty]

            # Save
            with open(filepath, 'w') as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Updated {specialty}: now {len(updated)} questions")

    # Update all_nbme_questions.json
    all_questions = []
    for specialty in ["Emergency Medicine", "Internal Medicine", "Neurology", "Pediatrics", "Surgery"]:
        filename = f"{specialty.lower().replace(' ', '_')}_questions.json"
        filepath = output_directory / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                all_questions.extend(json.load(f))

    with open(output_directory / "all_nbme_questions.json", 'w') as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"ULTRA EXTRACTION COMPLETE")
    print(f"Total questions: {len(all_questions)}")
    print(f"={'='*60}")

if __name__ == "__main__":
    main()
