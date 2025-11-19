#!/usr/bin/env python3
"""
Consolidate All Questions - ShelfSense Master Database Builder

Combines all extracted questions from:
1. Shelf exam questions (1,149 from text + OCR)
2. NBME Step 2 CK questions (2,473)
3. Creates master database with deduplication
4. Generates comprehensive statistics
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import hashlib

def load_json(filepath: Path) -> List[Dict]:
    """Load questions from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'questions' in data:
                return data['questions']
            else:
                return []
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return []

def generate_question_hash(question: Dict) -> str:
    """Generate unique hash for question to detect duplicates."""
    # Use vignette + correct answer as unique identifier
    vignette = str(question.get('vignette', '') or question.get('question_text', '') or '')
    answer = str(question.get('correct_answer', '') or '')
    combined = f"{vignette[:200]}_{answer}"  # First 200 chars of vignette + answer
    return hashlib.md5(combined.encode()).hexdigest()

def deduplicate_questions(questions: List[Dict]) -> Tuple[List[Dict], int]:
    """Remove duplicate questions based on content hash."""
    seen_hashes = set()
    unique_questions = []
    duplicates = 0

    for q in questions:
        q_hash = generate_question_hash(q)
        if q_hash not in seen_hashes:
            seen_hashes.add(q_hash)
            unique_questions.append(q)
        else:
            duplicates += 1

    return unique_questions, duplicates

def consolidate_all_questions():
    """Main consolidation function."""
    print(f"\n{'='*70}")
    print("ShelfSense Master Database Consolidation")
    print(f"{'='*70}\n")

    data_dir = Path("/Users/devaun/ShelfSense/data/extracted_questions")
    all_questions = []
    stats = {
        "sources": {},
        "by_specialty": defaultdict(int),
        "by_source_type": defaultdict(int),
        "total_before_dedup": 0,
        "total_after_dedup": 0,
        "duplicates_removed": 0
    }

    # 1. Load Shelf Exam Questions
    print("Loading Shelf Exam Questions...")
    shelf_files = {
        "Emergency Medicine": "emergency_medicine_questions.json",
        "Internal Medicine": "internal_medicine_questions.json",
        "Neurology": "neurology_questions.json",
        "Pediatrics": "pediatrics_questions.json",
        "Surgery": "surgery_questions.json"
    }

    for specialty, filename in shelf_files.items():
        filepath = data_dir / filename
        if filepath.exists():
            questions = load_json(filepath)
            # Add metadata
            for q in questions:
                q['source_type'] = 'shelf_exam'
                q['specialty'] = specialty
            all_questions.extend(questions)
            stats["sources"][f"Shelf - {specialty}"] = len(questions)
            stats["by_specialty"][specialty] += len(questions)
            stats["by_source_type"]["Shelf Exams"] += len(questions)
            print(f"  ✓ {specialty}: {len(questions)} questions")

    # 2. Load NBME Step 2 CK Questions
    print("\nLoading NBME Step 2 CK Questions...")
    nbme_files = list(data_dir.glob("nbme_*_questions.json"))

    for filepath in nbme_files:
        nbme_num = filepath.stem.replace('nbme_', '').replace('_questions', '')
        questions = load_json(filepath)

        # Add metadata
        for q in questions:
            q['source_type'] = 'nbme_step2ck'
            q['nbme_exam'] = nbme_num

        all_questions.extend(questions)
        stats["sources"][f"NBME {nbme_num}"] = len(questions)
        stats["by_source_type"]["NBME Step 2 CK"] += len(questions)
        print(f"  ✓ NBME {nbme_num}: {len(questions)} questions")

    stats["total_before_dedup"] = len(all_questions)
    print(f"\n{'='*70}")
    print(f"Total questions loaded: {len(all_questions)}")
    print(f"{'='*70}\n")

    # 3. Deduplicate
    print("Deduplicating questions...")
    unique_questions, duplicates = deduplicate_questions(all_questions)
    stats["total_after_dedup"] = len(unique_questions)
    stats["duplicates_removed"] = duplicates
    print(f"  Duplicates found and removed: {duplicates}")
    print(f"  Unique questions remaining: {len(unique_questions)}")

    # 4. Categorize by specialty (infer from content if not tagged)
    print("\nCategorizing questions...")
    specialty_keywords = {
        "Cardiovascular": ["heart", "cardiac", "MI", "ECG", "arrhythmia", "hypertension"],
        "Pulmonary": ["lung", "pulmonary", "respiratory", "asthma", "COPD", "pneumonia"],
        "Gastroenterology": ["GI", "abdom", "liver", "colon", "gastric", "intestin"],
        "Neurology": ["neuro", "brain", "stroke", "seizure", "headache", "CNS"],
        "Psychiatry": ["psych", "depression", "anxiety", "schizophrenia", "mental"],
        "Endocrinology": ["diabetes", "thyroid", "hormone", "endocrine", "glucose"],
        "Infectious Disease": ["infection", "bacteria", "virus", "antibiotic", "fever"],
        "Obstetrics": ["pregnant", "prenatal", "obstetric", "fetal", "delivery"],
        "Pediatrics": ["child", "infant", "pediatric", "newborn", "developmental"],
        "Surgery": ["surgical", "operation", "appendic", "trauma", "fracture"]
    }

    for q in unique_questions:
        if 'specialty' not in q or not q['specialty']:
            # Infer specialty from content
            vignette = (q.get('vignette', '') or q.get('question_text', '')).lower()
            for specialty, keywords in specialty_keywords.items():
                if any(keyword.lower() in vignette for keyword in keywords):
                    q['specialty'] = specialty
                    break
            if 'specialty' not in q:
                q['specialty'] = 'General'

    # 5. Save consolidated database
    print("\nSaving consolidated database...")
    output_path = data_dir / "shelfsense_master_database.json"

    master_db = {
        "metadata": {
            "version": "1.0",
            "created": "2025-11-19",
            "total_questions": len(unique_questions),
            "sources": ["Shelf Exams", "NBME Step 2 CK"],
            "extraction_tools": [
                "nbme_complete_extractor.py",
                "run_all_ocr.py",
                "nbme_comprehensive_extractor.py"
            ]
        },
        "statistics": {
            "total_before_dedup": stats["total_before_dedup"],
            "total_after_dedup": stats["total_after_dedup"],
            "duplicates_removed": stats["duplicates_removed"],
            "by_source_type": dict(stats["by_source_type"]),
            "by_source": dict(stats["sources"]),
            "by_specialty": dict(stats["by_specialty"])
        },
        "questions": unique_questions
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(master_db, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved master database: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

    # 6. Save summary statistics
    summary_path = data_dir / "database_summary.json"
    summary = {
        "metadata": master_db["metadata"],
        "statistics": master_db["statistics"]
    }

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"✓ Saved summary: {summary_path}")

    # 7. Print final report
    print(f"\n{'='*70}")
    print("CONSOLIDATION COMPLETE")
    print(f"{'='*70}")
    print(f"\nTotal Questions in Master Database: {len(unique_questions)}")
    print(f"\nBy Source Type:")
    for source_type, count in stats["by_source_type"].items():
        print(f"  {source_type}: {count}")
    print(f"\nBy Specialty:")
    for specialty, count in sorted(stats["by_specialty"].items(), key=lambda x: -x[1])[:10]:
        print(f"  {specialty}: {count}")
    print(f"\nDuplication Stats:")
    print(f"  Before deduplication: {stats['total_before_dedup']}")
    print(f"  After deduplication: {stats['total_after_dedup']}")
    print(f"  Duplicates removed: {stats['duplicates_removed']}")
    print(f"{'='*70}\n")

    print("✓ Master database ready for ShelfSense platform!")

    return master_db

if __name__ == "__main__":
    consolidate_all_questions()
