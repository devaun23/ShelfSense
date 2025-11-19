#!/usr/bin/env python3
"""
NBME Answer PDF Extractor for ShelfSense
Extracts questions AND answers from NBME Answer PDFs
This is the authoritative source since Answer PDFs contain complete questions + answers
"""

import pdfplumber
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
import sys

class NBMEAnswerExtractor:
    """Extract NBME questions from Answer PDFs (contains everything)"""

    def __init__(self, pdf_directory: str):
        self.pdf_dir = Path(pdf_directory)
        self.questions = []

        # Reasoning pattern keywords
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

    def extract_question_from_page(self, page_text: str, page_num: int) -> Optional[Dict]:
        """Extract question AND answer from Answer PDF page"""

        # Extract question number from "N. A patient..."
        question_num_match = re.search(r'^(\d+)\.\s+[A-Z]', page_text, re.MULTILINE)
        if not question_num_match:
            return None

        question_num = question_num_match.group(1)

        # Extract vignette - from "N." until answer choices
        vignette_match = re.search(
            r'(\d+)\.\s+(.+?)(?=^[A-I]\))',
            page_text,
            re.DOTALL | re.MULTILINE
        )

        if not vignette_match:
            return None

        vignette = vignette_match.group(2).strip()

        # Extract answer choices - simpler pattern in Answer PDFs (no "0\n")
        # Format is just:
        # A) Choice text
        # B) Choice text
        choices = []
        choice_pattern = r'^([A-I])\)\s*(.+?)(?=^[A-I]\)|Correct Answer:|\Z)'

        for match in re.finditer(choice_pattern, page_text, re.DOTALL | re.MULTILINE):
            choice_id = match.group(1)
            choice_text = match.group(2).strip()
            # Clean up
            choice_text = re.sub(r'\s+', ' ', choice_text)
            choice_text = re.sub(r'(r ~, r,|https://t\.me/\S+|Next Score Report.*)', '', choice_text)
            choice_text = choice_text.strip()

            if choice_text:
                choices.append({
                    "id": choice_id,
                    "text": choice_text
                })

        if not choices:
            return None

        # Extract correct answer
        answer_match = re.search(r'Correct Answer:\s*([A-I])\b', page_text)
        correct_answer = answer_match.group(1) if answer_match else "TBD"

        # Parse vignette components
        demographics = self._extract_demographics(vignette)
        vitals = self._extract_vitals(vignette)
        labs = self._extract_labs(vignette)
        question_stem = self._extract_question_stem(vignette)

        return {
            "question_num": question_num,
            "page": page_num,
            "vignette": vignette,
            "demographics": demographics,
            "vitals": vitals,
            "labs": labs,
            "question_stem": question_stem,
            "choices": choices,
            "correct_answer": correct_answer
        }

    def _extract_demographics(self, text: str) -> str:
        """Extract patient demographics"""
        demo_match = re.search(r'(A\s+\d+-year-old\s+(?:man|woman|boy|girl))', text, re.IGNORECASE)
        return demo_match.group(1) if demo_match else ""

    def _extract_vitals(self, text: str) -> Dict:
        """Extract vital signs"""
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
        """Extract laboratory values"""
        labs = {}
        lab_patterns = {
            "hemoglobin": r'Hemoglobin\\s+([\\d.]+)\\s*g/dL',
            "hematocrit": r'(?:Hematocrit|hematocrit is)\\s+([\\d.]+)%',
            "wbc": r'(?:Leukocyte count|leukocyte count is|WBC)\\s+([\\d,]+)/mm',
            "platelets": r'Platelet count\\s+([\\d,]+)/mm',
            "sodium": r'Na\\+?\\s+([\\d]+)\\s*mEq/L',
            "potassium": r'K\\+?\\s+([\\d.]+)\\s*mEq/L',
            "chloride": r'Cl-?\\s+([\\d]+)\\s*mEq/L',
            "bicarbonate": r'HCO3?-?\\s+([\\d]+)\\s*mEq/L',
            "glucose": r'Glucose\\s+([\\d]+)\\s*mg/dL',
            "creatinine": r'Creatinine\\s+([\\d.]+)\\s*mg/dL',
        }

        for lab_name, pattern in lab_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                labs[lab_name] = match.group(1)

        return labs

    def _extract_question_stem(self, text: str) -> str:
        """Extract the actual question"""
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
        """Auto-tag reasoning patterns"""
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
        """Estimate difficulty"""
        vignette = question.get("vignette", "")
        word_count = len(vignette.split())
        num_labs = len(question.get("labs", {}))

        if word_count < 100 and num_labs < 3:
            return 2
        elif word_count < 200 and num_labs < 6:
            return 3
        else:
            return 4

    def classify_tier(self, question: Dict) -> int:
        """Classify tier"""
        return 2

    def convert_to_shelfsense_format(self, question: Dict, specialty: str, source_file: str) -> Dict:
        """Convert to ShelfSense JSON"""
        question_id = f"{specialty.lower().replace(' ', '_')}_{source_file.replace(' ', '_').replace('-', '_')}_{int(question['question_num']):03d}"

        return {
            "id": question_id,
            "specialty": specialty,
            "source": f"NBME {source_file}",
            "topic": "TBD",
            "tier": self.classify_tier(question),
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
                "concept": "TBD",
                "pattern": "TBD",
                "distractors": {}
            }
        }

    def extract_from_pdf(self, pdf_path: Path, specialty: str) -> List[Dict]:
        """Extract all questions from Answer PDF"""
        questions = []
        print(f"Processing: {pdf_path.name}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue

                    question = self.extract_question_from_page(text, page_num)
                    if question:
                        shelfsense_q = self.convert_to_shelfsense_format(
                            question,
                            specialty,
                            pdf_path.stem
                        )
                        questions.append(shelfsense_q)
                        ans = question['correct_answer']
                        print(f"  ✓ Q{question['question_num']} → Answer: {ans} (page {page_num})")

        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()

        return questions

    def extract_all_questions(self) -> Dict[str, List[Dict]]:
        """Extract from all Answer PDFs"""
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

        # Process Answer PDFs only
        answer_pdfs = [p for p in self.pdf_dir.glob("*.pdf") if "Answer" in p.name]

        for pdf_path in sorted(answer_pdfs):
            specialty = None
            for key, value in specialty_map.items():
                if key in pdf_path.name:
                    specialty = value
                    break

            if specialty:
                questions = self.extract_from_pdf(pdf_path, specialty)
                all_questions[specialty].extend(questions)
                print(f"  Total from this PDF: {len(questions)}/50")

        return all_questions

    def save_to_json(self, questions: Dict[str, List[Dict]], output_dir: Path):
        """Save to JSON"""
        output_dir.mkdir(exist_ok=True)

        for specialty, question_list in questions.items():
            if question_list:
                filename = f"{specialty.lower().replace(' ', '_')}_questions.json"
                output_path = output_dir / filename

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(question_list, f, indent=2, ensure_ascii=False)

                print(f"\n✓ Saved {len(question_list)} {specialty} questions to {output_path}")

        # Combined file
        all_questions_flat = []
        for question_list in questions.values():
            all_questions_flat.extend(question_list)

        combined_path = output_dir / "all_nbme_questions.json"
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(all_questions_flat, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved {len(all_questions_flat)} total questions to {combined_path}")

        # Summary
        self._generate_summary(questions, output_dir)

    def _generate_summary(self, questions: Dict[str, List[Dict]], output_dir: Path):
        """Generate summary"""
        summary = {
            "total_questions": sum(len(q) for q in questions.values()),
            "by_specialty": {k: len(v) for k, v in questions.items()},
            "status": "Extracted from NBME Answer PDFs with correct answers",
            "next_steps": [
                "Add detailed explanations",
                "Refine reasoning pattern tags",
                "Add topic classifications",
                "Validate all extracted data"
            ]
        }

        summary_path = output_dir / "extraction_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"\n✓ Extraction summary saved to {summary_path}")
        print(f"\n" + "="*60)
        print(f"EXTRACTION COMPLETE")
        print(f"="*60)
        print(f"Total Questions: {summary['total_questions']}")
        for specialty, count in summary['by_specialty'].items():
            print(f"  {specialty}: {count}")
        print(f"="*60)


def main():
    """Main extraction workflow"""
    pdf_directory = "/Users/devaun/Desktop/Compressed_PDFs"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    print("="*60)
    print("NBME Answer PDF Extractor for ShelfSense")
    print("Extracting questions WITH correct answers")
    print("="*60)
    print(f"Source: {pdf_directory}")
    print(f"Output: {output_directory}")
    print("="*60 + "\n")

    extractor = NBMEAnswerExtractor(pdf_directory)
    questions = extractor.extract_all_questions()
    extractor.save_to_json(questions, output_directory)

    print("\n✓ Ready for integration into ShelfSense database!")


if __name__ == "__main__":
    main()
