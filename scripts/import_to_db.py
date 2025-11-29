#!/usr/bin/env python3
"""
Import Extracted Questions to ShelfSense Database

Loads questions from JSON (output of burst_import.py) into the database.

Usage:
    python scripts/import_to_db.py extracted_questions.json

    # Dry run (preview without saving)
    python scripts/import_to_db.py extracted_questions.json --dry-run

    # Specify specialty
    python scripts/import_to_db.py extracted_questions.json --specialty internal_medicine
"""

import os
import sys
import json
import argparse
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Must set DATABASE_URL before importing models
if not os.getenv("DATABASE_URL"):
    # Default to local SQLite for development
    os.environ["DATABASE_URL"] = "sqlite:///./shelfsense.db"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.models import Question, Base


def load_questions_from_json(json_path: Path) -> List[Dict[str, Any]]:
    """Load questions from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def normalize_specialty(specialty: str) -> str:
    """Normalize specialty name to standard format."""
    mappings = {
        "internal medicine": "internal_medicine",
        "im": "internal_medicine",
        "medicine": "internal_medicine",
        "surgery": "surgery",
        "surg": "surgery",
        "pediatrics": "pediatrics",
        "peds": "pediatrics",
        "obgyn": "obgyn",
        "ob-gyn": "obgyn",
        "ob/gyn": "obgyn",
        "psychiatry": "psychiatry",
        "psych": "psychiatry",
        "neurology": "neurology",
        "neuro": "neurology",
        "family medicine": "family_medicine",
        "fm": "family_medicine"
    }

    normalized = specialty.lower().strip()
    return mappings.get(normalized, normalized.replace(" ", "_"))


def convert_to_db_format(
    question: Dict[str, Any],
    specialty: str,
    source: str = "NBME"
) -> Dict[str, Any]:
    """
    Convert extracted question to database model format.
    """
    # Build choices array from dict
    choices_dict = question.get("choices", {})
    choices = [
        choices_dict.get("A", ""),
        choices_dict.get("B", ""),
        choices_dict.get("C", ""),
        choices_dict.get("D", ""),
        choices_dict.get("E", "")
    ]

    # Get explanation (may be dict from enhancement or string from original)
    explanation = question.get("explanation", {})
    if isinstance(explanation, str):
        explanation = {"raw_text": explanation}

    # Determine difficulty from explanation if available
    difficulty = "medium"
    if isinstance(explanation, dict):
        q_type = explanation.get("question_type", "")
        if "STABILITY" in q_type or "TREATMENT" in q_type:
            difficulty = "medium"
        elif "DIAGNOSTIC" in q_type or "DIFFERENTIAL" in q_type:
            difficulty = "hard"

    return {
        "id": str(uuid.uuid4()),
        "vignette": question.get("vignette", "") + "\n\n" + question.get("question_stem", ""),
        "answer_key": question.get("answer_key", "A"),
        "choices": choices,
        "explanation": explanation,
        "source": source,
        "specialty": normalize_specialty(specialty),
        "difficulty_level": difficulty,
        "recency_tier": 1,  # Newly imported = most recent
        "recency_weight": 1.0,
        "source_type": "imported",
        "content_status": "active",
        "quality_score": 80.0,  # Default for imported content
        "version": 1,
        "extra_data": {
            "source_file": question.get("source_file"),
            "source_page": question.get("source_page"),
            "enhanced_at": question.get("enhanced_at"),
            "import_timestamp": datetime.utcnow().isoformat()
        }
    }


def import_questions(
    questions: List[Dict[str, Any]],
    specialty: str,
    db_url: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Import questions to database.
    """
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    # Ensure tables exist
    Base.metadata.create_all(engine)

    session = Session()

    stats = {
        "total": len(questions),
        "imported": 0,
        "skipped": 0,
        "errors": []
    }

    try:
        for i, q in enumerate(questions):
            try:
                # Convert to DB format
                db_data = convert_to_db_format(q, specialty)

                if dry_run:
                    print(f"  [{i+1}] Would import: {db_data['vignette'][:50]}...")
                    stats["imported"] += 1
                    continue

                # Check for duplicates (by vignette similarity)
                existing = session.query(Question).filter(
                    Question.vignette.contains(db_data["vignette"][:100])
                ).first()

                if existing:
                    print(f"  [{i+1}] SKIP: Similar question exists")
                    stats["skipped"] += 1
                    continue

                # Create question
                question = Question(**db_data)
                session.add(question)
                stats["imported"] += 1

                # Commit in batches
                if (i + 1) % 50 == 0:
                    session.commit()
                    print(f"  Committed {i+1} questions...")

            except Exception as e:
                stats["errors"].append({
                    "index": i,
                    "error": str(e),
                    "question": q.get("vignette", "")[:100]
                })
                print(f"  [{i+1}] ERROR: {e}")

        if not dry_run:
            session.commit()

    finally:
        session.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import extracted questions to ShelfSense database"
    )
    parser.add_argument(
        "json_path",
        type=Path,
        help="Path to JSON file with extracted questions"
    )
    parser.add_argument(
        "--specialty",
        type=str,
        default="internal_medicine",
        help="Specialty for imported questions (default: internal_medicine)"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=os.getenv("DATABASE_URL", "sqlite:///./shelfsense.db"),
        help="Database URL (default: from DATABASE_URL env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview import without saving to database"
    )

    args = parser.parse_args()

    # Check file exists
    if not args.json_path.exists():
        print(f"ERROR: File not found: {args.json_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("SHELFSENSE DATABASE IMPORT")
    print(f"{'='*60}")
    print(f"Source: {args.json_path}")
    print(f"Specialty: {normalize_specialty(args.specialty)}")
    print(f"Database: {args.database_url[:50]}...")
    print(f"Dry run: {'YES' if args.dry_run else 'NO'}")
    print(f"{'='*60}\n")

    # Load questions
    print("[1/2] Loading questions from JSON...")
    questions = load_questions_from_json(args.json_path)
    print(f"  Loaded {len(questions)} questions")

    # Validate
    has_explanations = sum(1 for q in questions if q.get("explanation"))
    print(f"  With explanations: {has_explanations}")

    if has_explanations < len(questions):
        print(f"  WARNING: {len(questions) - has_explanations} questions without explanations")

    # Import
    print(f"\n[2/2] {'Previewing' if args.dry_run else 'Importing'} to database...")
    stats = import_questions(
        questions,
        args.specialty,
        args.database_url,
        dry_run=args.dry_run
    )

    # Summary
    print(f"\n{'='*60}")
    print("IMPORT COMPLETE" if not args.dry_run else "DRY RUN COMPLETE")
    print(f"{'='*60}")
    print(f"Total questions: {stats['total']}")
    print(f"Imported: {stats['imported']}")
    print(f"Skipped (duplicates): {stats['skipped']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats["errors"]:
        print("\nErrors:")
        for err in stats["errors"][:5]:
            print(f"  - {err['error']}")
        if len(stats["errors"]) > 5:
            print(f"  ... and {len(stats['errors']) - 5} more")

    if args.dry_run:
        print("\nTo import for real, remove --dry-run flag")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
