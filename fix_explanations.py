#!/usr/bin/env python3
"""
Fix explanation extraction for already-extracted NBME questions
Re-extracts clean explanations from the source PDFs
"""

import pdfplumber
import re
import json
from pathlib import Path
from typing import Dict, Optional

class ExplanationFixer:
    """Fix corrupted explanations in extracted questions"""

    def __init__(self, pdf_directory: str):
        self.pdf_dir = Path(pdf_directory)

    def extract_clean_explanation(self, pdf_path: Path, question_num: str) -> Dict[str, any]:
        """Extract clean explanation for a specific question"""

        with pdfplumber.open(pdf_path) as pdf:
            # Read all pages into one text block
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += "\n" + text

            # Find this question's section
            # Pattern: question number followed by explanation
            pattern = rf'\n{question_num}\.\s+.*?Correct Answer:\s*([A-I])\.'

            # Find all occurrences of "Correct Answer: X."
            answer_matches = list(re.finditer(r'Correct Answer:\s*([A-I])\.', all_text))

            if not answer_matches:
                return {"correct_answer": "TBD", "correct_explanation": "", "distractor_explanations": {}, "educational_objective": ""}

            # Find the right occurrence for this question
            # Get text around each match and look for substantial content
            correct_answer = None
            explanation_text = None

            for match in answer_matches:
                start = match.start()
                # Get substantial chunk of text after this match
                chunk = all_text[start:start+3000]

                # Skip if it's just dots/garbage
                if re.match(r'Correct Answer:\s*[A-I]\.\s*\.{3,}', chunk):
                    continue

                # Check if this has actual explanation text (at least 100 chars of real content)
                clean_chunk = re.sub(r'(~, r,|https://t\.me/\S+|Previous|Next|Score Report)', '', chunk)
                if len(clean_chunk.strip()) > 150:
                    correct_answer = match.group(1)
                    explanation_text = chunk
                    break

            if not explanation_text:
                return {"correct_answer": "TBD", "correct_explanation": "", "distractor_explanations": {}, "educational_objective": ""}

            # Extract correct answer explanation
            correct_exp_match = re.search(
                r'Correct Answer:\s*[A-I]\.\s*(.+?)(?=Incorrect Answers?:|Educational Objective:|Previous|Next|Exam Section:|$)',
                explanation_text,
                re.DOTALL | re.IGNORECASE
            )

            correct_explanation = ""
            if correct_exp_match:
                correct_explanation = correct_exp_match.group(1).strip()
                # Clean up
                correct_explanation = re.sub(r'\s+', ' ', correct_explanation)
                correct_explanation = re.sub(r'(r ~, r,|https://t\.me/\S+|\.{3,}|~,\s*r,)', '', correct_explanation)
                correct_explanation = re.sub(r'Previous|Next|Score Report|Lab Values|Calculator|Help|Pause', '', correct_explanation)
                correct_explanation = correct_explanation.strip()

            # Extract distractor explanations
            distractors = {}
            incorrect_section_match = re.search(
                r'Incorrect Answers?:\s*([A-I](?:,\s*[A-I])*(?:,?\s*and\s*[A-I])?)\.\s*(.+?)(?=Educational Objective:|Previous|Next|Exam Section:|$)',
                explanation_text,
                re.DOTALL | re.IGNORECASE
            )

            if incorrect_section_match:
                incorrect_text = incorrect_section_match.group(2)
                # Split by choice pattern
                distractor_pattern = r'(?:Choice\s+)?([A-I])\)\s*(.+?)(?=(?:Choice\s+)?[A-I]\)|Educational Objective:|$)'
                for match in re.finditer(distractor_pattern, incorrect_text, re.DOTALL):
                    choice_id = match.group(1)
                    explanation = match.group(2).strip()
                    explanation = re.sub(r'\s+', ' ', explanation)
                    explanation = re.sub(r'(r ~, r,|https://t\.me/\S+|~,\s*r,)', '', explanation)
                    explanation = explanation.strip()
                    if explanation and len(explanation) > 20:
                        distractors[choice_id] = explanation

            # Extract educational objective
            educational_objective = ""
            obj_match = re.search(
                r'Educational\s+(?:Objective|Goal):\s*(.+?)(?=Previous|Next|Exam Section:|\.\.\.|r ~, r,|$)',
                explanation_text,
                re.DOTALL | re.IGNORECASE
            )
            if obj_match:
                educational_objective = obj_match.group(1).strip()
                educational_objective = re.sub(r'\s+', ' ', educational_objective)
                educational_objective = re.sub(r'(r ~, r,|https://t\.me/\S+|\.{3,}|~,\s*r,)', '', educational_objective)
                educational_objective = educational_objective.strip()

            return {
                "correct_answer": correct_answer,
                "correct_explanation": correct_explanation,
                "distractor_explanations": distractors,
                "educational_objective": educational_objective
            }

    def fix_questions_file(self, json_path: Path, pdf_mapping: Dict[str, str]):
        """Fix explanations in a single JSON file"""

        print(f"\nProcessing {json_path.name}...")

        with open(json_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        fixed_count = 0
        for question in questions:
            # Determine source PDF
            source = question.get('source', '')
            pdf_name = None
            for key in pdf_mapping:
                if key in source:
                    pdf_name = pdf_mapping[key]
                    break

            if not pdf_name:
                continue

            pdf_path = self.pdf_dir / pdf_name
            if not pdf_path.exists():
                continue

            # Check if explanation needs fixing
            current_exp = question['explanation']['correct_answer_explanation']
            if not current_exp or len(current_exp) < 50 or '~, r,' in current_exp or current_exp.strip().startswith('.'):
                # Extract question number from ID
                match = re.search(r'_(\d+)$', question['id'])
                if match:
                    question_num = str(int(match.group(1)))

                    # Get clean explanation
                    clean_exp = self.extract_clean_explanation(pdf_path, question_num)

                    if clean_exp['correct_explanation'] and len(clean_exp['correct_explanation']) > 50:
                        question['explanation']['correct_answer_explanation'] = clean_exp['correct_explanation']
                        question['explanation']['distractor_explanations'] = clean_exp['distractor_explanations']
                        question['explanation']['educational_objective'] = clean_exp['educational_objective']
                        question['explanation']['concept'] = clean_exp['educational_objective'][:200] if clean_exp['educational_objective'] else "TBD"

                        if clean_exp['correct_answer'] != "TBD":
                            question['correct_answer'] = clean_exp['correct_answer']

                        fixed_count += 1
                        print(f"  ✓ Fixed Q{question_num}")

        # Save updated questions
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

        print(f"  Fixed {fixed_count} explanations")
        return fixed_count

def main():
    pdf_directory = "/Users/devaun/Desktop/Compressed_PDFs"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    fixer = ExplanationFixer(pdf_directory)

    # Map specialty files to their PDFs
    specialty_pdfs = {
        'emergency_medicine_questions.json': {
            'Emergency Medicine 1': 'Emergency Medicine 1 - Answers.pdf',
            'Emergency Medicine 2': 'Emergency Medicine 2 - Answers.pdf'
        },
        'internal_medicine_questions.json': {
            'Internal Medicine 3': 'Internal Medicine 3 - Answers.pdf',
            'Internal Medicine 4': 'Internal Medicine 4 - Answers v1 [wide].pdf',
            'Internal Medicine 5': 'Internal Medicine 5 - Answers.pdf',
            'Internal Medicine 6': 'Internal Medicine 6 - Answers.pdf'
        },
        'neurology_questions.json': {
            'Neuro 3': 'Neuro 3 - Answers.pdf',
            'Neuro 4': 'Neuro 4 - Answers.pdf',
            'Neuro 5': 'Neuro 5 - Answers.pdf',
            'Neuro 6': 'Neuro 6 - Answers.pdf'
        },
        'pediatrics_questions.json': {
            'Pediatric 3': 'Pediatric 3 - Answers v1 [wide].pdf',
            'Pediatrics 4': 'Pediatrics 4 - Answers v1 [wide].pdf',
            'Pediatrics 5': 'Pediatrics 5 - Answers v1 [wide].pdf',
            'Pediatrics 6': 'Pediatrics 6 - Answers v1 [wide].pdf'
        },
        'surgery_questions.json': {
            'Surgery 3': 'Surgery 3 - Answers v1 [wide].pdf',
            'Surgery 4': 'Surgery 4 - Answers v1 [wide].pdf',
            'Surgery 5': 'Surgery 5 - Answers v1 [wide].pdf',
            'Surgery 6': 'Surgery 6 - Answers v1 [wide].pdf'
        }
    }

    print("="*60)
    print("Fixing Explanation Extraction")
    print("="*60)

    total_fixed = 0
    for json_file, pdf_map in specialty_pdfs.items():
        json_path = output_directory / json_file
        if json_path.exists():
            fixed = fixer.fix_questions_file(json_path, pdf_map)
            total_fixed += fixed

    print(f"\n" + "="*60)
    print(f"TOTAL FIXED: {total_fixed} explanations")
    print(f"="*60)

if __name__ == "__main__":
    main()
