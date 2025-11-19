#!/usr/bin/env python3
"""
Extract Medicine 7 and Medicine 8 PDFs only
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
import sys
import io

class NBMEOCRExtractor:
    """Extract NBME questions from image-based PDFs using OCR"""

    def __init__(self, pdf_directory: str):
        self.pdf_dir = Path(pdf_directory)
        self.pattern_keywords = {
            "urgency_assessment": ["emergency", "most appropriate immediate", "acute", "stabilize first"],
            "treatment_prioritization": ["most appropriate next step", "initial management"],
            "diagnosis_recognition": ["most likely diagnosis", "most consistent with"],
            "vital_sign_interpretation": ["blood pressure", "pulse", "temperature", "respiratory"],
            "lab_interpretation": ["laboratory studies show", "serum", "hemoglobin"],
            "timeline_errors": ["history of", "days ago", "weeks ago", "months ago"],
            "missed_qualifiers": ["most", "least", "except", "not"],
            "anchoring": ["patient says", "concerned that"],
            "test_selection": ["most appropriate next step in diagnosis", "confirm the diagnosis"],
        }

    def extract_text_with_ocr(self, pdf_path: Path) -> str:
        """Extract text from image-based PDF using OCR"""
        print(f"  Using OCR to extract text from {pdf_path.name}...")

        all_text = ""
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # First try standard text extraction
            print(f"  Attempting standard text extraction...")
            for page in doc:
                text = page.get_text()
                if text and len(text.strip()) > 100:
                    all_text += "\n" + text

            # If we got reasonable text, return it
            if len(all_text.strip()) > 500:
                print(f"  Standard extraction successful ({len(all_text)} chars)")
                doc.close()
                return all_text

            # Otherwise, use OCR
            print(f"  Standard extraction failed, using OCR...")
            all_text = ""

            for page_num in range(total_pages):
                print(f"    OCR processing page {page_num + 1}/{total_pages}...", end='\r')

                # Render page as image with 2x zoom for better quality
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

                # Convert to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # Extract text using Tesseract
                text = pytesseract.image_to_string(img, config='--psm 6')
                all_text += "\n" + text

            print(f"\n  OCR extraction complete ({len(all_text)} chars)")
            doc.close()

        except Exception as e:
            print(f"  Error during OCR: {e}")
            import traceback
            traceback.print_exc()
            return ""

        return all_text

    def extract_all_questions_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """Extract all 50 questions from a single Answer PDF using OCR if needed"""
        questions = []

        print(f"\nProcessing: {pdf_path.name}")

        # Extract text (with OCR fallback)
        all_text = self.extract_text_with_ocr(pdf_path)

        if not all_text:
            print(f"  ERROR: No text extracted from {pdf_path.name}")
            return []

        # Split by question number pattern to get each complete question
        # Pattern: "N. A patient..." or "N. A N-year-old..."
        question_splits = re.split(r'\n(\d+)\.\s+([A-Z])', all_text)

        # Process splits: [text_before, num1, first_char1, text1, num2, first_char2, text2, ...]
        i = 1  # Skip the text before first question
        while i < len(question_splits):
            if i + 2 >= len(question_splits):
                break

            question_num = question_splits[i]
            first_char = question_splits[i+1]
            question_text = question_splits[i+2]

            # Reconstruct the question
            full_question_text = f"{question_num}. {first_char}{question_text}"

            # Extract the question
            question = self.extract_single_question(full_question_text, question_num)
            if question:
                questions.append(question)
                ans = question.get('correct_answer', 'TBD')
                print(f"  ✓ Q{question_num} → Answer: {ans}")

            i += 3

        print(f"  Total extracted: {len(questions)}/50")

        return questions

    def extract_single_question(self, text: str, question_num: str) -> Optional[Dict]:
        """Extract a single complete question with all explanations"""

        # Extract vignette (before answer choices)
        vignette_match = re.search(r'^(.+?)(?=^[A-I]\))', text, re.MULTILINE | re.DOTALL)
        if not vignette_match:
            return None
        vignette = vignette_match.group(1).strip()

        # Extract answer choices
        choices = []
        choice_pattern = r'^([A-I])\)\s*(.+?)(?=^[A-I]\)|Correct Answer:|$)'
        for match in re.finditer(choice_pattern, text, re.MULTILINE | re.DOTALL):
            choice_id = match.group(1)
            choice_text = match.group(2).strip()
            choice_text = re.sub(r'\s+', ' ', choice_text)
            choice_text = re.sub(r'(r ~, r,|https://t\.me/\S+|Previous|Next|Score Report|Lab Values|Calculator|Help|Pause)', '', choice_text)
            choice_text = choice_text.strip()
            if choice_text:
                choices.append({"id": choice_id, "text": choice_text})

        if not choices:
            return None

        # Extract correct answer
        answer_match = re.search(r'Correct Answer:\s*([A-I])\b', text)
        correct_answer = answer_match.group(1) if answer_match else "TBD"

        # Extract correct answer explanation
        correct_explanation = ""
        correct_exp_match = re.search(
            r'Correct Answer:\s*[A-I]\.\s*(.+?)(?=Incorrect Answers?:|Educational Objective:|Previous|Next|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if correct_exp_match:
            correct_explanation = correct_exp_match.group(1).strip()
            correct_explanation = re.sub(r'\s+', ' ', correct_explanation)
            correct_explanation = re.sub(r'(r ~, r,|https://t\.me/\S+|\.{3,})', '', correct_explanation)
            correct_explanation = correct_explanation.strip()

        # Extract distractor explanations
        distractors = {}
        incorrect_section_match = re.search(
            r'Incorrect Answers?:\s*([A-I](?:,\s*[A-I])*(?:,?\s*and\s*[A-I])?)\.\s*(.+?)(?=Educational Objective:|Previous|Next|Exam Section:|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )

        if incorrect_section_match:
            incorrect_text = incorrect_section_match.group(2)
            # Split by choice pattern: "Choice X) explanation"
            distractor_pattern = r'(?:Choice\s+)?([A-I])\)\s*(.+?)(?=(?:Choice\s+)?[A-I]\)|$)'
            for match in re.finditer(distractor_pattern, incorrect_text, re.DOTALL):
                choice_id = match.group(1)
                explanation = match.group(2).strip()
                explanation = re.sub(r'\s+', ' ', explanation)
                explanation = re.sub(r'(r ~, r,|https://t\.me/\S+)', '', explanation)
                distractors[choice_id] = explanation.strip()

        # Extract educational objective
        educational_objective = ""
        obj_match = re.search(
            r'Educational\s+(?:Objective|Goal):\s*(.+?)(?=Previous|Next|Exam Section:|\.\.\.|r ~, r,|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if obj_match:
            educational_objective = obj_match.group(1).strip()
            educational_objective = re.sub(r'\s+', ' ', educational_objective)
            educational_objective = re.sub(r'(r ~, r,|https://t\.me/\S+|\.{3,})', '', educational_objective)
            educational_objective = educational_objective.strip()

        # Parse vignette components
        demographics = self._extract_demographics(vignette)
        vitals = self._extract_vitals(vignette)
        labs = self._extract_labs(vignette)
        question_stem = self._extract_question_stem(vignette)

        return {
            "question_num": question_num,
            "vignette": vignette,
            "demographics": demographics,
            "vitals": vitals,
            "labs": labs,
            "question_stem": question_stem,
            "choices": choices,
            "correct_answer": correct_answer,
            "correct_explanation": correct_explanation,
            "distractor_explanations": distractors,
            "educational_objective": educational_objective
        }

    def _extract_demographics(self, text: str) -> str:
        demo_match = re.search(r'(A\s+\d+-year-old\s+(?:man|woman|boy|girl))', text, re.IGNORECASE)
        return demo_match.group(1) if demo_match else ""

    def _extract_vitals(self, text: str) -> Dict:
        vitals = {}
        temp_match = re.search(r'temperature is ([\\d.]+)°C \\(([\\d.]+)\\s*°F\\)', text)
        if temp_match:
            vitals["temp_c"] = temp_match.group(1)
            vitals["temp_f"] = temp_match.group(2)
        pulse_match = re.search(r'pulse is (\\d+)/min', text)
        if pulse_match:
            vitals["pulse"] = pulse_match.group(1)
        resp_match = re.search(r'respirations are (\\d+)/min', text)
        if resp_match:
            vitals["respirations"] = resp_match.group(1)
        bp_match = re.search(r'blood pressure is (\\d+/\\d+) mm Hg', text)
        if bp_match:
            vitals["blood_pressure"] = bp_match.group(1)
        o2_match = re.search(r'oxygen saturation of (\\d+)%', text)
        if o2_match:
            vitals["o2_sat"] = o2_match.group(1)
        return vitals

    def _extract_labs(self, text: str) -> Dict:
        labs = {}
        lab_patterns = {
            "hemoglobin": r'Hemoglobin\\s+([\\d.]+)\\s*g/dL',
            "hematocrit": r'(?:Hematocrit|hematocrit is)\\s+([\\d.]+)%',
            "wbc": r'(?:Leukocyte count|leukocyte count is|WBC)\\s+([\\d,]+)/mm',
            "platelets": r'Platelet count\\s+([\\d,]+)/mm',
            "sodium": r'Na\\+?\\s+([\\d]+)\\s*mEq/L',
            "potassium": r'K\\+?\\s+([\\d.]+)\\s*mEq/L',
        }
        for lab_name, pattern in lab_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                labs[lab_name] = match.group(1)
        return labs

    def _extract_question_stem(self, text: str) -> str:
        question_match = re.search(r'([^.!?]+\\?)\\s*$', text)
        if question_match:
            return question_match.group(1).strip()
        which_match = re.search(r'((?:Which|What)\\s+(?:of the following|is the).+?)(?=\\n|$)', text, re.DOTALL)
        if which_match:
            return which_match.group(1).strip()
        most_match = re.search(r'((?:The )?most (?:appropriate|likely).+?)(?=\\n|$)', text, re.IGNORECASE | re.DOTALL)
        if most_match:
            return most_match.group(1).strip()
        return ""

    def tag_reasoning_patterns(self, question: Dict) -> List[str]:
        patterns = []
        full_text = question.get("vignette", "") + " " + question.get("question_stem", "")
        full_text_lower = full_text.lower()
        for pattern_name, keywords in self.pattern_keywords.items():
            for keyword in keywords:
                if keyword.lower() in full_text_lower:
                    patterns.append(pattern_name)
                    break
        return list(set(patterns))

    def determine_difficulty(self, question: Dict) -> int:
        vignette = question.get("vignette", "")
        word_count = len(vignette.split())
        num_labs = len(question.get("labs", {}))
        if word_count < 100 and num_labs < 3:
            return 2
        elif word_count < 200 and num_labs < 6:
            return 3
        else:
            return 4

    def convert_to_shelfsense_format(self, question: Dict, specialty: str, source_file: str) -> Dict:
        question_id = f"{specialty.lower().replace(' ', '_')}_{source_file.replace(' ', '_').replace('-', '_')}_{int(question['question_num']):03d}"

        return {
            "id": question_id,
            "specialty": specialty,
            "source": f"NBME {source_file}",
            "topic": "TBD",
            "tier": 2,
            "difficulty": self.determine_difficulty(question),
            "vignette": {
                "demographics": question.get("demographics", ""),
                "presentation": question.get("vignette", ""),
                "vitals": question.get("vitals", {}),
                "labs": question.get("labs", {})
            },
            "question_stem": question.get("question_stem", ""),
            "choices": question.get("choices", []),
            "correct_answer": question.get("correct_answer", "TBD"),
            "reasoning_patterns": self.tag_reasoning_patterns(question),
            "explanation": {
                "correct_answer_explanation": question.get("correct_explanation", ""),
                "distractor_explanations": question.get("distractor_explanations", {}),
                "educational_objective": question.get("educational_objective", ""),
                "concept": question.get("educational_objective", "")[:200] if question.get("educational_objective") else "TBD"
            }
        }

    def process_specific_pdfs(self, pdf_names: List[str]) -> Dict[str, List[Dict]]:
        """Process specific PDFs by name"""
        all_questions = {
            "Internal Medicine": [],
        }

        specialty_map = {
            "Medicine": "Internal Medicine",
        }

        for pdf_name in pdf_names:
            pdf_path = self.pdf_dir / pdf_name
            if not pdf_path.exists():
                print(f"ERROR: {pdf_name} not found!")
                continue

            # Determine specialty
            specialty = None
            for key, value in specialty_map.items():
                if key in pdf_path.name:
                    specialty = value
                    break

            if specialty:
                questions = self.extract_all_questions_from_pdf(pdf_path)
                for q in questions:
                    shelfsense_q = self.convert_to_shelfsense_format(q, specialty, pdf_path.stem)
                    all_questions[specialty].append(shelfsense_q)

        return all_questions

    def save_to_json(self, questions: Dict[str, List[Dict]], output_dir: Path):
        """Save extracted questions to JSON files"""
        output_dir.mkdir(exist_ok=True)

        # Load existing questions if they exist
        existing_questions = {
            "Internal Medicine": [],
        }

        # Read existing files
        for specialty in existing_questions.keys():
            filename = f"{specialty.lower().replace(' ', '_')}_questions.json"
            filepath = output_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_questions[specialty] = json.load(f)

        # Merge new questions with existing ones (avoiding duplicates by ID)
        for specialty, new_question_list in questions.items():
            if new_question_list:
                existing_ids = {q['id'] for q in existing_questions[specialty]}
                for new_q in new_question_list:
                    if new_q['id'] not in existing_ids:
                        existing_questions[specialty].append(new_q)

                # Save updated list
                filename = f"{specialty.lower().replace(' ', '_')}_questions.json"
                with open(output_dir / filename, 'w', encoding='utf-8') as f:
                    json.dump(existing_questions[specialty], f, indent=2, ensure_ascii=False)
                print(f"\n✓ Saved {len(existing_questions[specialty])} total {specialty} questions")

        # Update all_nbme_questions.json
        all_flat = []
        for qlist in existing_questions.values():
            all_flat.extend(qlist)

        with open(output_dir / "all_nbme_questions.json", 'w', encoding='utf-8') as f:
            json.dump(all_flat, f, indent=2, ensure_ascii=False)

        # Print per-file results
        print("\n" + "="*60)
        print("EXTRACTION RESULTS PER PDF:")
        print("="*60)
        for specialty, question_list in questions.items():
            if question_list:
                # Count questions by source file
                med7_count = sum(1 for q in question_list if "medicine_7" in q['id'])
                med8_count = sum(1 for q in question_list if "medicine_8" in q['id'])
                if med7_count > 0:
                    print(f"Medicine 7 - Answers.pdf: {med7_count} questions")
                if med8_count > 0:
                    print(f"Medicine 8 - Answers.pdf: {med8_count} questions")
        print("="*60)


def main():
    pdf_directory = "/Users/devaun/Desktop/Compressed_PDFs"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    # PDFs to process with OCR - Only Medicine 7 and Medicine 8
    target_pdfs = [
        "Medicine 7 - Answers.pdf",
        "Medicine 8 - Answers.pdf"
    ]

    print("="*60)
    print("OCR-Enhanced NBME Extractor - Medicine 7 & 8")
    print("="*60)
    print(f"Processing {len(target_pdfs)} image-based PDFs...")
    print("="*60)

    extractor = NBMEOCRExtractor(pdf_directory)
    questions = extractor.process_specific_pdfs(target_pdfs)
    extractor.save_to_json(questions, output_directory)

    print("\n✓ Extraction complete!")

if __name__ == "__main__":
    main()
