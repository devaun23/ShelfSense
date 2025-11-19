#!/usr/bin/env python3
"""
COMPLETE NBME Answer PDF Extractor for ShelfSense
Extracts questions + answers + FULL explanations + educational objectives
Processes multi-page questions properly
"""

import pdfplumber
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

class NBMECompleteExtractor:
    """Extract complete NBME questions with full explanations from Answer PDFs"""

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

    def extract_all_questions_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """Extract all 50 questions from a single Answer PDF by processing ALL pages"""
        questions = []

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"\nProcessing: {pdf_path.name} ({total_pages} pages)")

            # Collect all text first
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += "\n" + text

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

        # Clean the text first - remove all footer artifacts
        text = self._clean_text(text)

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
            choice_text = choice_text.strip()
            if choice_text:
                choices.append({"id": choice_id, "text": choice_text})

        if not choices:
            return None

        # Extract correct answer - handle both "E." and "E. " formats
        answer_match = re.search(r'Correct Answer:\s*([A-I])\.?(?:\s|$)', text)
        correct_answer = answer_match.group(1) if answer_match else "TBD"

        # Extract correct answer explanation
        # The explanation starts after "Correct Answer: X." and continues until "Incorrect Answer"
        correct_explanation = ""
        correct_exp_match = re.search(
            r'Correct Answer:\s*[A-I]\.\s*(.+?)(?=\n\s*Incorrect Answers?:|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if correct_exp_match:
            correct_explanation = correct_exp_match.group(1).strip()
            correct_explanation = re.sub(r'\s+', ' ', correct_explanation)
            correct_explanation = correct_explanation.strip()

        # Extract distractor explanations
        distractors = {}
        incorrect_section_match = re.search(
            r'Incorrect Answers?:\s*([A-I](?:,\s*[A-I])*(?:,?\s*and\s*[A-I])?)\.\s*(.+?)(?=\n\s*Educational Objective:|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )

        if incorrect_section_match:
            incorrect_text = incorrect_section_match.group(2)

            # Extract choice name + explanation pairs
            # Pattern: "Name/phrase (Choice X) explanation text"
            # Must handle names with slashes like "Haemophilus influenza" or "Klebsiella pneumoniae"
            distractor_pattern = r'([A-Za-z/\s]+?)\s*\(Choice\s+([A-I])\)\s+(.+?)(?=\n[A-Z][a-z/]+?\s*\(Choice\s+[A-I]\)|$)'

            for match in re.finditer(distractor_pattern, incorrect_text, re.DOTALL):
                choice_name = match.group(1).strip()
                choice_id = match.group(2)
                explanation = match.group(3).strip()

                # Combine name and explanation
                full_explanation = f"{choice_name} {explanation}"
                full_explanation = re.sub(r'\s+', ' ', full_explanation)
                distractors[choice_id] = full_explanation.strip()

        # Extract educational objective
        educational_objective = ""
        obj_match = re.search(
            r'Educational\s+(?:Objective|Goal):\s*(.+?)(?=\n\s*(?:Exam Section|Previous|Next|Score Report)|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if obj_match:
            educational_objective = obj_match.group(1).strip()
            educational_objective = re.sub(r'\s+', ' ', educational_objective)
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

    def _clean_text(self, text: str) -> str:
        """Remove all footer artifacts and noise from extracted text"""
        # Remove common footer patterns
        text = re.sub(r'r ~, r,', '', text)
        text = re.sub(r'~, r,', '', text)
        text = re.sub(r'r\s*~\s*,\s*r\s*,', '', text)

        # Remove telegram links
        text = re.sub(r'https://t\.me/\S+', '', text)

        # Remove navigation elements
        text = re.sub(r'\b(Previous|Next|Score Report|Lab Values|Calculator|Help|Pause)\b', '', text)

        # Remove ellipsis artifacts
        text = re.sub(r'\.{3,}', '', text)

        # Remove "Mark" at beginning of lines (from header)
        text = re.sub(r'\nMark\s+', '\n', text)

        # Remove "Exam Section: Item X of 50"
        text = re.sub(r'Exam Section:\s*Item\s+\d+\s+of\s+\d+', '', text)

        # Remove "National Board of Medical Examiners"
        text = re.sub(r'National Board of Medical Examiners', '', text)

        # Remove specialty header (e.g., "Emergency Medicine Self-Assessment")
        text = re.sub(r'(?:Emergency Medicine|Internal Medicine|Neurology|Pediatrics|Surgery)\s+Self-Assessment', '', text)

        # Remove various dot/dash separator lines
        text = re.sub(r'[\.\-\s]{10,}', ' ', text)

        # Remove single character artifacts on their own line
        text = re.sub(r'\n[,.:;~\-]\s*\n', '\n', text)

        return text

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

    def extract_all_pdfs(self) -> Dict[str, List[Dict]]:
        all_questions = {
            "Emergency Medicine": [],
            "Internal Medicine": [],
            "Neurology": [],
            "Pediatrics": [],
            "Surgery": []
        }

        specialty_map = {
            "Emergency": "Emergency Medicine",
            "Internal": "Internal Medicine",
            "Medicine": "Internal Medicine",
            "Neuro": "Neurology",
            "Pediatric": "Pediatrics",
            "Surgery": "Surgery"
        }

        answer_pdfs = sorted([p for p in self.pdf_dir.glob("*.pdf") if "Answer" in p.name])

        for pdf_path in answer_pdfs:
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
        output_dir.mkdir(exist_ok=True)

        for specialty, question_list in questions.items():
            if question_list:
                filename = f"{specialty.lower().replace(' ', '_')}_questions.json"
                with open(output_dir / filename, 'w', encoding='utf-8') as f:
                    json.dump(question_list, f, indent=2, ensure_ascii=False)
                print(f"\n✓ Saved {len(question_list)} {specialty} questions")

        all_flat = []
        for qlist in questions.values():
            all_flat.extend(qlist)

        with open(output_dir / "all_nbme_questions.json", 'w', encoding='utf-8') as f:
            json.dump(all_flat, f, indent=2, ensure_ascii=False)

        summary = {
            "total_questions": len(all_flat),
            "by_specialty": {k: len(v) for k, v in questions.items()},
            "status": "Complete extraction with explanations",
            "includes": [
                "Question vignettes",
                "All answer choices",
                "Correct answers",
                "Correct answer explanations",
                "Distractor explanations for each wrong answer",
                "Educational objectives"
            ]
        }

        with open(output_dir / "extraction_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"\n" + "="*60)
        print(f"COMPLETE EXTRACTION FINISHED")
        print(f"="*60)
        print(f"Total: {summary['total_questions']} questions")
        for spec, count in summary['by_specialty'].items():
            print(f"  {spec}: {count}")
        print(f"="*60)

def main():
    pdf_directory = "/Users/devaun/Desktop/Compressed_PDFs"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    print("="*60)
    print("COMPLETE NBME Extractor - With Full Explanations")
    print("="*60)

    extractor = NBMECompleteExtractor(pdf_directory)
    questions = extractor.extract_all_pdfs()
    extractor.save_to_json(questions, output_directory)

    print("\n✓ Ready for ShelfSense integration!")

if __name__ == "__main__":
    main()
