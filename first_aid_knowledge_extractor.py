#!/usr/bin/env python3
"""
First Aid for Step 2 CK Knowledge Base Extractor

Extracts high-yield facts, concepts, and structured knowledge from First Aid.
This knowledge will be used to enhance question explanations and create concept maps.

Strategy:
1. Extract chapter structure and topics
2. Identify high-yield facts (marked with ★ or bold)
3. Extract clinical pearls and mnemonics
4. Build topic-to-content mapping
5. Create searchable knowledge base
"""

import pdfplumber
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

class FirstAidKnowledgeExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.knowledge_base = {
            "chapters": [],
            "topics": {},
            "high_yield_facts": [],
            "mnemonics": [],
            "clinical_pearls": [],
            "metadata": {
                "source": "First Aid for USMLE Step 2 CK, 11th Edition",
                "total_pages": 0,
                "extraction_date": "2025-11-19"
            }
        }

    def extract_table_of_contents(self, pdf) -> Dict[str, List]:
        """Extract chapter structure from TOC."""
        print("Extracting table of contents...")
        chapters = []

        # First 20 pages usually contain TOC
        for page_num in range(min(20, len(pdf.pages))):
            page = pdf.pages[page_num]
            text = page.extract_text()

            if text:
                # Look for chapter headings (all caps or numbered)
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()

                    # Chapter pattern: "CHAPTER 1: CARDIOVASCULAR" or "1. Cardiovascular"
                    chapter_match = re.match(r'(?:CHAPTER\s+)?(\d+)[:\.\s]+([A-Z][A-Za-z\s&]+)', line)
                    if chapter_match:
                        chapter_num = chapter_match.group(1)
                        chapter_name = chapter_match.group(2).strip()
                        chapters.append({
                            "number": int(chapter_num),
                            "name": chapter_name,
                            "topics": []
                        })

        return chapters

    def extract_high_yield_markers(self, text: str) -> List[str]:
        """Extract facts marked as high-yield (★, bold, or boxed)."""
        high_yield = []

        # Pattern 1: Lines with ★ or •
        for line in text.split('\n'):
            if '★' in line or '•' in line:
                clean_line = line.replace('★', '').replace('•', '').strip()
                if len(clean_line) > 10:  # Filter out too-short snippets
                    high_yield.append(clean_line)

        # Pattern 2: Text in ALL CAPS (likely important headings)
        caps_pattern = re.findall(r'\b[A-Z][A-Z\s]{3,}[A-Z]\b', text)
        high_yield.extend([cap.strip() for cap in caps_pattern if len(cap.strip()) > 5])

        return high_yield

    def extract_mnemonics(self, text: str) -> List[Dict[str, str]]:
        """Extract mnemonics (e.g., MUDPILES, SIGECAPS)."""
        mnemonics = []

        # Pattern: All caps acronym followed by explanation
        # Example: "MUDPILES: Methanol, Uremia, DKA, Propylene glycol..."
        mnemonic_pattern = re.findall(
            r'\b([A-Z]{3,})\s*[:=]\s*([A-Z][^\n]{20,200})',
            text
        )

        for acronym, explanation in mnemonic_pattern:
            # Filter out common false positives
            if acronym not in ['PDF', 'USMLE', 'NBME', 'USA', 'FDA', 'CDC']:
                mnemonics.append({
                    "acronym": acronym,
                    "explanation": explanation.strip(),
                    "length": len(acronym)
                })

        return mnemonics

    def extract_clinical_pearls(self, text: str) -> List[str]:
        """Extract clinical pearls and key teaching points."""
        pearls = []

        # Pattern 1: Sentences starting with "Always", "Never", "Most common"
        pearl_starters = [
            r'Always [^\.]{10,}[\.\!]',
            r'Never [^\.]{10,}[\.\!]',
            r'Most common [^\.]{10,}[\.\!]',
            r'First-line [^\.]{10,}[\.\!]',
            r'Gold standard [^\.]{10,}[\.\!]',
            r'Classic presentation [^\.]{10,}[\.\!]'
        ]

        for pattern in pearl_starters:
            matches = re.findall(pattern, text, re.IGNORECASE)
            pearls.extend([m.strip() for m in matches])

        return pearls

    def extract_by_specialty(self, text: str, specialty: str) -> Dict:
        """Extract specialty-specific content."""
        specialty_content = {
            "specialty": specialty,
            "facts": [],
            "diseases": [],
            "treatments": [],
            "diagnostics": []
        }

        # Extract disease names (capitalized, often followed by description)
        disease_pattern = re.findall(
            r'([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)\s+(?:is|presents with|characterized by)',
            text
        )
        specialty_content["diseases"] = list(set(disease_pattern))[:50]  # Top 50

        # Extract treatment mentions
        treatment_pattern = re.findall(
            r'(?:treat(?:ment)?|therapy|manage(?:ment)?)\s+(?:with|is|includes)\s+([A-Z][a-z]+(?:\s+[a-z]+)?)',
            text,
            re.IGNORECASE
        )
        specialty_content["treatments"] = list(set(treatment_pattern))[:50]

        # Extract diagnostic tests
        diagnostic_pattern = re.findall(
            r'(?:diagnos(?:ed|is)|confirm(?:ed)?|test(?:ing)?)\s+(?:with|by|using)\s+([A-Z][A-Z\s]+|[A-Z][a-z]+(?:\s+[a-z]+)?)',
            text,
            re.IGNORECASE
        )
        specialty_content["diagnostics"] = list(set(diagnostic_pattern))[:50]

        return specialty_content

    def process_pdf(self) -> Dict:
        """Main extraction process."""
        print(f"\n{'='*60}")
        print("First Aid for Step 2 CK Knowledge Extractor")
        print(f"{'='*60}\n")
        print(f"Processing: {self.pdf_path.name}")

        with pdfplumber.open(self.pdf_path) as pdf:
            self.knowledge_base["metadata"]["total_pages"] = len(pdf.pages)
            print(f"Total pages: {len(pdf.pages)}")

            # Extract TOC
            self.knowledge_base["chapters"] = self.extract_table_of_contents(pdf)
            print(f"Chapters found: {len(self.knowledge_base['chapters'])}")

            # Process all pages
            all_text = ""
            specialty_sections = defaultdict(str)
            current_specialty = None

            # Common specialty keywords to identify sections
            specialties = [
                "Cardiovascular", "Pulmonary", "Gastroenterology", "Hepatology",
                "Nephrology", "Hematology", "Oncology", "Endocrinology",
                "Rheumatology", "Neurology", "Psychiatry", "Dermatology",
                "Ophthalmology", "Otolaryngology", "Infectious Disease",
                "Obstetrics", "Gynecology", "Pediatrics", "Surgery",
                "Emergency Medicine", "Critical Care"
            ]

            print("\nExtracting content from all pages...")
            for page_num, page in enumerate(pdf.pages, 1):
                if page_num % 50 == 0:
                    print(f"  Processing page {page_num}/{len(pdf.pages)}...")

                text = page.extract_text()
                if text:
                    all_text += text + "\n\n"

                    # Detect specialty transitions
                    for specialty in specialties:
                        if specialty.upper() in text.upper():
                            current_specialty = specialty

                    if current_specialty:
                        specialty_sections[current_specialty] += text + "\n\n"

            print(f"\nProcessing extracted text ({len(all_text)} characters)...")

            # Extract knowledge components
            print("  - Extracting high-yield facts...")
            self.knowledge_base["high_yield_facts"] = self.extract_high_yield_markers(all_text)

            print("  - Extracting mnemonics...")
            self.knowledge_base["mnemonics"] = self.extract_mnemonics(all_text)

            print("  - Extracting clinical pearls...")
            self.knowledge_base["clinical_pearls"] = self.extract_clinical_pearls(all_text)

            # Extract specialty-specific content
            print("  - Processing specialty sections...")
            specialty_knowledge = {}
            for specialty, text in specialty_sections.items():
                if len(text) > 500:  # Only process substantial sections
                    specialty_knowledge[specialty] = self.extract_by_specialty(text, specialty)

            self.knowledge_base["specialty_knowledge"] = specialty_knowledge

            # Add full text for search purposes (chunked)
            print("  - Creating searchable text chunks...")
            chunk_size = 2000
            chunks = []
            for i in range(0, len(all_text), chunk_size):
                chunk = all_text[i:i+chunk_size]
                chunks.append({
                    "chunk_id": i // chunk_size,
                    "text": chunk,
                    "char_start": i,
                    "char_end": min(i + chunk_size, len(all_text))
                })

            self.knowledge_base["searchable_chunks"] = chunks[:1000]  # Limit to 1000 chunks

        return self.knowledge_base

    def save_knowledge_base(self, output_dir: str = "data/knowledge_base"):
        """Save extracted knowledge to JSON files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save complete knowledge base
        complete_path = output_path / "first_aid_complete.json"
        with open(complete_path, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved complete knowledge base: {complete_path}")

        # Save summary
        summary = {
            "metadata": self.knowledge_base["metadata"],
            "stats": {
                "chapters": len(self.knowledge_base.get("chapters", [])),
                "high_yield_facts": len(self.knowledge_base.get("high_yield_facts", [])),
                "mnemonics": len(self.knowledge_base.get("mnemonics", [])),
                "clinical_pearls": len(self.knowledge_base.get("clinical_pearls", [])),
                "specialties_covered": len(self.knowledge_base.get("specialty_knowledge", {})),
                "searchable_chunks": len(self.knowledge_base.get("searchable_chunks", []))
            }
        }

        summary_path = output_path / "first_aid_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"✓ Saved summary: {summary_path}")

        # Print extraction summary
        print(f"\n{'='*60}")
        print("EXTRACTION SUMMARY")
        print(f"{'='*60}")
        for key, value in summary["stats"].items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        print(f"{'='*60}\n")

def main():
    # First Aid PDF path
    import glob
    pdf_files = glob.glob("/Users/devaun/Desktop/*First Aid*.pdf")
    if not pdf_files:
        print("Error: First Aid PDF not found on Desktop")
        return
    pdf_path = pdf_files[0]

    # Create extractor
    extractor = FirstAidKnowledgeExtractor(pdf_path)

    # Extract knowledge
    knowledge_base = extractor.process_pdf()

    # Save to files
    extractor.save_knowledge_base()

    print("✓ First Aid knowledge extraction complete!")
    print("\nReady for integration with ShelfSense question explanations.")

if __name__ == "__main__":
    main()
