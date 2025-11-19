#!/usr/bin/env python3
"""
NBME PDF Question Extractor for ShelfSense
Extracts questions from compressed NBME PDFs and converts to ShelfSense JSON format
"""

import pdfplumber
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
import sys

class NBMEExtractor:
    """Extract NBME questions from PDFs into structured format"""

    def __init__(self, pdf_directory: str):
        self.pdf_dir = Path(pdf_directory)
        self.questions = []

        # Reasoning pattern keywords for automatic tagging
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
        """Extract a single question from page text"""

        # Match question number at start: "Item N of 50"
        item_match = re.search(r'Item (\d+) of \d+', page_text)
        if not item_match:
            return None

        question_num = item_match.group(1)

        # Extract the vignette - everything between question number and first answer choice
        # Look for pattern: number. [vignette text] followed by answer choices starting with 0 \n A)
        vignette_match = re.search(
            r'\d+\.\s+(.+?)(?=\n0\s*\n[A-I]\))',
            page_text,
            re.DOTALL
        )

        if not vignette_match:
            return None

        vignette = vignette_match.group(1).strip()

        # Extract answer choices - format is:
        # 0
        # A) Choice text
        # 0
        # B) Choice text
        choices = []
        choice_pattern = r'0\s*\n([A-I])\)\s*([^\n]+(?:\n(?!0\s*\n[A-I]\))[^\n]+)*)'

        for match in re.finditer(choice_pattern, page_text):
            choice_id = match.group(1)
            choice_text = match.group(2).strip()
            # Clean up choice text
            choice_text = re.sub(r'\s+', ' ', choice_text)
            choices.append({
                "id": choice_id,
                "text": choice_text
            })

        if not choices:
            return None

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
            "choices": choices
        }

    def _extract_demographics(self, text: str) -> str:
        """Extract patient demographics from vignette"""
        demo_match = re.match(r'(A\s+\d+-year-old\s+(?:man|woman|boy|girl))', text)
        return demo_match.group(1) if demo_match else ""

    def _extract_vitals(self, text: str) -> Dict:
        """Extract vital signs from vignette"""
        vitals = {}

        # Temperature
        temp_match = re.search(r'temperature is ([\d.]+)°C \(([\d.]+)°F\)', text)
        if temp_match:
            vitals["temp_c"] = temp_match.group(1)
            vitals["temp_f"] = temp_match.group(2)

        # Pulse
        pulse_match = re.search(r'pulse is (\d+)/min', text)
        if pulse_match:
            vitals["pulse"] = pulse_match.group(1)

        # Respirations
        resp_match = re.search(r'respirations are (\d+)/min', text)
        if resp_match:
            vitals["respirations"] = resp_match.group(1)

        # Blood pressure
        bp_match = re.search(r'blood pressure is (\d+/\d+) mm Hg', text)
        if bp_match:
            vitals["blood_pressure"] = bp_match.group(1)

        # O2 sat
        o2_match = re.search(r'oxygen saturation of (\d+)%', text)
        if o2_match:
            vitals["o2_sat"] = o2_match.group(1)

        return vitals

    def _extract_labs(self, text: str) -> Dict:
        """Extract laboratory values from vignette"""
        labs = {}

        # Common lab patterns
        lab_patterns = {
            "hemoglobin": r'Hemoglobin\s+([\d.]+)\s*g/dL',
            "hematocrit": r'Hematocrit\s+([\d.]+)%',
            "wbc": r'(?:Leukocyte count|WBC)\s+([\d,]+)/mm',
            "platelets": r'Platelet count\s+([\d,]+)/mm',
            "sodium": r'Na\+?\s+([\d]+)\s*mEq/L',
            "potassium": r'K\+?\s+([\d.]+)\s*mEq/L',
            "chloride": r'Cl-?\s+([\d]+)\s*mEq/L',
            "bicarbonate": r'HCO3?-?\s+([\d]+)\s*mEq/L',
            "glucose": r'Glucose\s+([\d]+)\s*mg/dL',
            "creatinine": r'Creatinine\s+([\d.]+)\s*mg/dL',
        }

        for lab_name, pattern in lab_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                labs[lab_name] = match.group(1)

        return labs

    def _extract_question_stem(self, text: str) -> str:
        """Extract the actual question being asked"""
        # Usually the last sentence with a question mark
        question_match = re.search(r'([^.!?]+\?)\s*$', text)
        if question_match:
            return question_match.group(1).strip()

        # Or starts with "Which of the following"
        which_match = re.search(r'(Which of the following.+?)(?=\n|$)', text, re.DOTALL)
        if which_match:
            return which_match.group(1).strip()

        return ""

    def tag_reasoning_patterns(self, question: Dict) -> List[str]:
        """Automatically tag question with likely reasoning patterns"""
        patterns = []
        full_text = question.get("vignette", "") + question.get("question_stem", "")
        full_text_lower = full_text.lower()

        for pattern_name, keywords in self.pattern_keywords.items():
            for keyword in keywords:
                if keyword.lower() in full_text_lower:
                    patterns.append(pattern_name)
                    break

        return list(set(patterns))  # Remove duplicates

    def determine_difficulty(self, question: Dict) -> int:
        """Estimate difficulty (1-5) based on complexity"""
        vignette = question.get("vignette", "")

        # Simple heuristic based on vignette length and complexity
        word_count = len(vignette.split())
        num_labs = len(question.get("labs", {}))
        num_choices = len(question.get("choices", []))

        if word_count < 100 and num_labs < 3:
            return 2  # Easy
        elif word_count < 200 and num_labs < 6:
            return 3  # Medium
        else:
            return 4  # Hard

    def classify_tier(self, question: Dict) -> int:
        """Classify question tier (1-5) based on topic importance"""
        # This would ideally use First Aid high-yield topics
        # For now, default to tier 2 (high yield but not critical)
        return 2

    def convert_to_shelfsense_format(self, question: Dict, specialty: str, source_file: str) -> Dict:
        """Convert extracted question to ShelfSense JSON format"""

        question_id = f"{specialty.lower().replace(' ', '_')}_{int(question['question_num']):03d}"

        shelfsense_question = {
            "id": question_id,
            "specialty": specialty,
            "source": f"NBME {source_file}",
            "topic": "TBD",  # Would need topic extraction
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
            "correct_answer": "TBD",  # Needs answer key
            "reasoning_patterns": self.tag_reasoning_patterns(question),
            "explanation": {
                "concept": "TBD",
                "pattern": "TBD",
                "distractors": {}
            }
        }

        return shelfsense_question

    def extract_from_pdf(self, pdf_path: Path, specialty: str) -> List[Dict]:
        """Extract all questions from a single PDF"""
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
                        print(f"  ✓ Extracted Q{question['question_num']} from page {page_num}")

        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")

        return questions

    def extract_all_questions(self) -> Dict[str, List[Dict]]:
        """Extract questions from all PDFs in directory"""
        all_questions = {
            "Emergency Medicine": [],
            "Internal Medicine": [],
            "Neurology": [],
            "Pediatrics": [],
            "Surgery": []
        }

        # Map filename patterns to specialties
        specialty_map = {
            "Emergency": "Emergency Medicine",
            "Internal": "Internal Medicine",
            "Medicine": "Internal Medicine",
            "Neuro": "Neurology",
            "Pediatric": "Pediatrics",
            "Surgery": "Surgery"
        }

        # Process only question PDFs (not answer PDFs)
        question_pdfs = [p for p in self.pdf_dir.glob("*.pdf") if "Question" in p.name]

        for pdf_path in sorted(question_pdfs):
            # Determine specialty from filename
            specialty = None
            for key, value in specialty_map.items():
                if key in pdf_path.name:
                    specialty = value
                    break

            if specialty:
                questions = self.extract_from_pdf(pdf_path, specialty)
                all_questions[specialty].extend(questions)

        return all_questions

    def save_to_json(self, questions: Dict[str, List[Dict]], output_dir: Path):
        """Save extracted questions to JSON files"""
        output_dir.mkdir(exist_ok=True)

        for specialty, question_list in questions.items():
            if question_list:
                filename = f"{specialty.lower().replace(' ', '_')}_questions.json"
                output_path = output_dir / filename

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(question_list, f, indent=2, ensure_ascii=False)

                print(f"\n✓ Saved {len(question_list)} {specialty} questions to {output_path}")

        # Also save combined file
        all_questions_flat = []
        for question_list in questions.values():
            all_questions_flat.extend(question_list)

        combined_path = output_dir / "all_nbme_questions.json"
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(all_questions_flat, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved {len(all_questions_flat)} total questions to {combined_path}")

        # Generate summary statistics
        self._generate_summary(questions, output_dir)

    def _generate_summary(self, questions: Dict[str, List[Dict]], output_dir: Path):
        """Generate extraction summary report"""
        summary = {
            "total_questions": sum(len(q) for q in questions.values()),
            "by_specialty": {k: len(v) for k, v in questions.items()},
            "status": "Extracted from compressed NBME PDFs",
            "next_steps": [
                "Add correct answers from answer PDFs",
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

    # Configure paths
    pdf_directory = "/Users/devaun/Desktop/Compressed_PDFs"
    output_directory = Path("/Users/devaun/ShelfSense/data/extracted_questions")

    print("="*60)
    print("NBME Question Extractor for ShelfSense")
    print("="*60)
    print(f"Source: {pdf_directory}")
    print(f"Output: {output_directory}")
    print("="*60 + "\n")

    # Initialize extractor
    extractor = NBMEExtractor(pdf_directory)

    # Extract all questions
    questions = extractor.extract_all_questions()

    # Save to JSON files
    extractor.save_to_json(questions, output_directory)

    print("\n✓ Ready for integration into ShelfSense database!")


if __name__ == "__main__":
    main()
