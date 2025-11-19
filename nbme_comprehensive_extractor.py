#!/usr/bin/env python3
"""
Comprehensive NBME Extractor for Step 2 CK Practice Exams
Handles both image-based and text-based formats
Extracts questions 1-200+ (full NBME exams, not just 50)
"""

import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

class NBMEComprehensiveExtractor:
    """Extract questions from NBME Step 2 CK practice exams"""

    def __init__(self, pdf_directory: str):
        self.pdf_directory = Path(pdf_directory)

    def extract_text_with_ocr(self, pdf_path: Path) -> str:
        """Extract text using OCR if needed"""
        all_text = ""

        try:
            # First try standard text extraction
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and len(text.strip()) > 100:
                        all_text += "\n" + text

                # If we got reasonable text, return it
                if len(all_text.strip()) > 500:
                    return all_text

            # Otherwise, use OCR
            print(f"  Using OCR for {pdf_path.name}...")
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            for page_num in range(min(total_pages, 300)):  # Cap at 300 pages for safety
                if page_num % 20 == 0:
                    print(f"    OCR progress: {page_num}/{total_pages} pages...")

                page = doc[page_num]
                # Render at 2x resolution for better OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(img, config='--psm 6')
                all_text += "\n" + text

            doc.close()

        except Exception as e:
            print(f"  Error extracting from {pdf_path.name}: {e}")

        return all_text

    def extract_single_question(self, text: str, question_num: str) -> Optional[Dict]:
        """Extract a single complete question with explanation"""

        # Extract vignette (before answer choices)
        vignette_match = re.search(
            r'^(.+?)(?=^[A-I]\))',
            text,
            re.MULTILINE | re.DOTALL
        )
        vignette = vignette_match.group(1).strip() if vignette_match else "TBD"

        # Extract answer choices (A-I)
        choices = []
        choice_pattern = r'^([A-I])\)\s*(.+?)(?=^[A-I]\)|$)'
        choice_matches = re.finditer(choice_pattern, text, re.MULTILINE | re.DOTALL)

        for match in choice_matches:
            choice_id = match.group(1)
            choice_text = match.group(2).strip()
            # Stop at "Correct Answer" or other metadata
            choice_text = re.split(r'Correct Answer:|Educational Objective:|Incorrect Answer', choice_text)[0].strip()
            choices.append({"id": choice_id, "text": choice_text})

        # Extract correct answer
        answer_match = re.search(r'Correct Answer:\s*([A-I])\b', text)
        correct_answer = answer_match.group(1) if answer_match else "TBD"

        # Extract explanations
        correct_exp_match = re.search(
            r'Correct Answer:\s*[A-I]\.?\s*(.+?)(?=Incorrect Answer|Educational Objective:|Key idea:|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        correct_explanation = correct_exp_match.group(1).strip() if correct_exp_match else ""

        # Extract "Key idea" explanations (common in Step Prep format)
        key_ideas = []
        key_idea_matches = re.finditer(r'Key idea:\s*(.+?)(?=Key idea:|Exam section|https://|$)', text, re.DOTALL | re.IGNORECASE)
        for match in key_idea_matches:
            key_ideas.append(match.group(1).strip())

        if key_ideas:
            correct_explanation += "\n\nKey concepts:\n" + "\n".join(f"- {idea}" for idea in key_ideas)

        # Extract educational objective
        obj_match = re.search(
            r'Educational\s+(?:Objective|Goal):\s*(.+?)(?=Previous|Next|Exam [Ss]ection:|\n\d+\.|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        educational_objective = obj_match.group(1).strip() if obj_match else ""

        return {
            "question_num": question_num,
            "vignette": vignette,
            "choices": choices,
            "correct_answer": correct_answer,
            "correct_explanation": correct_explanation,
            "educational_objective": educational_objective
        }

    def extract_all_questions_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """Extract all questions from a PDF (1-200+)"""

        print(f"\nProcessing: {pdf_path.name}")

        # Extract text (with OCR if needed)
        all_text = self.extract_text_with_ocr(pdf_path)

        if not all_text or len(all_text.strip()) < 500:
            print(f"  Failed to extract text from {pdf_path.name}")
            return []

        print(f"  Extracted {len(all_text)} characters of text")

        # Split by question numbers - NBME exams have 1-200+ questions
        # More flexible pattern to handle various formats
        question_pattern = r'(?:^|[\n\sv])\s*(\d+)[\.\)]\s*([A-Za-z])'
        question_splits = re.split(question_pattern, all_text)

        questions = []
        i = 1
        while i < len(question_splits):
            if i + 2 >= len(question_splits):
                break

            question_num = question_splits[i]
            first_char = question_splits[i+1]
            question_text = question_splits[i+2]

            # NBME Step 2 CK exams can have up to 200+ questions
            try:
                num_int = int(question_num)
                if 1 <= num_int <= 250:  # Support up to 250 questions
                    full_question_text = f"{question_num}. {first_char}{question_text}"
                    question = self.extract_single_question(full_question_text, question_num)
                    if question:
                        questions.append(question)
            except ValueError:
                pass

            i += 3

        print(f"  Extracted {len(questions)} questions")
        return questions

    def convert_to_shelfsense_format(self, question: Dict, exam_name: str) -> Dict:
        """Convert NBME format to ShelfSense format"""

        question_id = f"nbme_{exam_name.lower().replace(' ', '_').replace('-', '_')}_{int(question['question_num']):03d}"

        return {
            "id": question_id,
            "specialty": "Step 2 CK",
            "source": f"NBME {exam_name}",
            "topic": "TBD",
            "tier": 2,
            "difficulty": 3,
            "vignette": {
                "demographics": "TBD",
                "presentation": question['vignette'],
                "vitals": {},
                "labs": {}
            },
            "question_stem": "",
            "choices": question['choices'],
            "correct_answer": question['correct_answer'],
            "reasoning_patterns": ["TBD"],
            "explanation": {
                "correct_answer_explanation": question['correct_explanation'],
                "distractor_explanations": {},
                "educational_objective": question['educational_objective'],
                "concept": "TBD"
            }
        }

    def process_all_nbmes(self) -> Dict[str, List[Dict]]:
        """Process all NBME PDFs in directory"""

        # Find all answer PDFs
        answer_pdfs = list(self.pdf_directory.glob("NBME*Answer*.pdf"))
        answer_pdfs += list(self.pdf_directory.glob("NBME*Explanations*.pdf"))

        all_questions = {}

        for pdf_path in sorted(answer_pdfs):
            # Extract exam number from filename
            exam_match = re.search(r'NBME\s+(\d+)', pdf_path.name)
            if not exam_match:
                continue

            exam_num = exam_match.group(1)
            exam_name = f"NBME {exam_num}"

            questions = self.extract_all_questions_from_pdf(pdf_path)

            if questions:
                # Convert to ShelfSense format
                shelfsense_questions = [
                    self.convert_to_shelfsense_format(q, exam_name)
                    for q in questions
                ]

                if exam_name not in all_questions:
                    all_questions[exam_name] = []
                all_questions[exam_name].extend(shelfsense_questions)

        return all_questions

    def save_to_json(self, all_questions: Dict[str, List[Dict]], output_directory: Path):
        """Save questions to JSON files"""

        output_directory.mkdir(parents=True, exist_ok=True)

        # Save by exam
        for exam_name, questions in all_questions.items():
            filename = f"{exam_name.lower().replace(' ', '_')}_questions.json"
            filepath = output_directory / filename

            with open(filepath, 'w') as f:
                json.dump(questions, f, indent=2, ensure_ascii=False)

            print(f"✓ Saved {len(questions)} questions to {filename}")

        # Save combined file
        all_combined = []
        for questions in all_questions.values():
            all_combined.extend(questions)

        combined_path = output_directory / "all_nbme_step2_questions.json"
        with open(combined_path, 'w') as f:
            json.dump(all_combined, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Total: {len(all_combined)} NBME Step 2 CK questions extracted")

        # Save summary
        summary = {
            "total_questions": len(all_combined),
            "by_exam": {exam: len(questions) for exam, questions in all_questions.items()}
        }

        summary_path = output_directory / "nbme_step2_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

def main():
    pdf_directory = "/Users/devaun/Desktop/NBMEs-selected"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    print("="*60)
    print("NBME Step 2 CK Comprehensive Extractor")
    print("="*60)

    extractor = NBMEComprehensiveExtractor(pdf_directory)
    all_questions = extractor.process_all_nbmes()
    extractor.save_to_json(all_questions, output_directory)

    print("\n✓ NBME extraction complete!")

if __name__ == "__main__":
    main()
