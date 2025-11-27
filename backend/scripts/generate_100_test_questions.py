#!/usr/bin/env python3
"""
Generate 100 Test Questions for AI Quality Validation

This script generates 100 diverse questions matching the USMLE Step 2 CK blueprint,
validates them using the quality validation service, and exports a report for review.

Distribution:
- Internal Medicine: 45 questions (45%)
- Surgery: 20 questions (20%)
- Pediatrics: 15 questions (15%)
- OB/GYN: 10 questions (10%)
- Psychiatry: 10 questions (10%)

Difficulty: 20% easy, 60% medium, 20% hard

Usage:
    cd backend
    python -m scripts.generate_100_test_questions

    # Or with options:
    python -m scripts.generate_100_test_questions --dry-run  # Validate only
    python -m scripts.generate_100_test_questions --save     # Save to database
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.models import Question, GenerationJob
from app.services.question_agent import generate_question_fast
from app.services.quality_validation_service import (
    QuestionValidator,
    validate_batch,
    export_validation_report,
    ValidationResult
)
from app.services.step2ck_content_outline import get_high_yield_topic

# Ensure tables exist
Base.metadata.create_all(bind=engine)


# Target distribution matching USMLE Step 2 CK blueprint
SPECIALTY_DISTRIBUTION = {
    "Internal Medicine": 45,
    "Surgery": 20,
    "Pediatrics": 15,
    "Obstetrics and Gynecology": 10,
    "Psychiatry": 10,
}

DIFFICULTY_DISTRIBUTION = {
    "easy": 20,
    "medium": 60,
    "hard": 20,
}

MAX_REGENERATION_ATTEMPTS = 3


def get_difficulty_for_index(index: int, total: int = 100) -> str:
    """Determine difficulty level based on question index."""
    # First 20% easy, next 60% medium, last 20% hard
    if index < total * 0.20:
        return "easy"
    elif index < total * 0.80:
        return "medium"
    else:
        return "hard"


async def generate_single_question(
    db: Session,
    specialty: str,
    difficulty: str,
    index: int,
    validator: QuestionValidator
) -> dict:
    """
    Generate a single question with validation and retry logic.

    Returns dict with question data and validation result.
    """
    result = {
        "index": index,
        "specialty": specialty,
        "difficulty": difficulty,
        "success": False,
        "attempts": 0,
        "question_data": None,
        "validation": None,
        "error": None,
    }

    for attempt in range(MAX_REGENERATION_ATTEMPTS):
        result["attempts"] = attempt + 1

        try:
            # Get high-yield topic for this specialty
            topic = get_high_yield_topic(specialty)

            print(f"  [{index+1}/100] Generating {specialty} ({difficulty}) - {topic} (attempt {attempt+1})")

            # Generate question using fine-tuned model
            question = await asyncio.to_thread(
                generate_question_fast,
                db,
                specialty,
                topic
            )

            if not question:
                result["error"] = "Generation returned None"
                continue

            # Prepare data for validation
            question_data = {
                "id": question.id if hasattr(question, 'id') else None,
                "vignette": question.vignette,
                "choices": question.choices,
                "answer_key": question.answer_key,
                "explanation": question.explanation,
                "specialty": specialty,
                "difficulty": difficulty,
            }

            # Validate
            validation = validator.validate_question(question_data)

            result["question_data"] = question_data
            result["validation"] = {
                "is_valid": validation.is_valid,
                "quality_score": validation.quality_score,
                "structural_score": validation.structural_score,
                "nbme_score": validation.nbme_score,
                "content_score": validation.content_score,
                "recommendation": validation.recommendation,
                "issues": validation.issues,
                "warnings": validation.warnings,
            }

            # Check if we should retry
            if validation.recommendation == "regenerate":
                print(f"    -> Quality {validation.quality_score}% - regenerating...")
                continue

            # Success!
            result["success"] = True
            status = "PASS" if validation.recommendation == "auto_pass" else "REVIEW"
            print(f"    -> [{status}] Quality: {validation.quality_score}%")
            break

        except Exception as e:
            result["error"] = str(e)
            print(f"    -> Error: {e}")

    return result


async def generate_batch(
    db: Session,
    save_to_db: bool = False,
    output_dir: str = "validation_reports"
) -> dict:
    """
    Generate 100 questions with proper distribution and validation.

    Args:
        db: Database session
        save_to_db: If True, save passing questions to database
        output_dir: Directory for validation reports

    Returns:
        Summary statistics
    """
    print("\n" + "="*60)
    print("ShelfSense AI Question Quality Validation")
    print("Generating 100 test questions...")
    print("="*60 + "\n")

    validator = QuestionValidator()
    results = []
    questions_generated = []

    # Build generation queue
    queue = []
    idx = 0
    for specialty, count in SPECIALTY_DISTRIBUTION.items():
        for i in range(count):
            difficulty = get_difficulty_for_index(idx)
            queue.append((specialty, difficulty, idx))
            idx += 1

    print(f"Generation queue: {len(queue)} questions")
    print(f"Distribution: {SPECIALTY_DISTRIBUTION}")
    print(f"Difficulties: {DIFFICULTY_DISTRIBUTION}")
    print("-" * 60)

    # Generate questions
    start_time = datetime.utcnow()

    for specialty, difficulty, index in queue:
        result = await generate_single_question(
            db, specialty, difficulty, index, validator
        )
        results.append(result)

        if result["success"] and result["question_data"]:
            questions_generated.append(result["question_data"])

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    # Calculate statistics
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    auto_pass = sum(
        1 for r in results
        if r["validation"] and r["validation"]["recommendation"] == "auto_pass"
    )
    review = sum(
        1 for r in results
        if r["validation"] and r["validation"]["recommendation"] == "review"
    )
    failed = sum(1 for r in results if not r["success"])

    avg_quality = sum(
        r["validation"]["quality_score"]
        for r in results if r["validation"]
    ) / successful if successful > 0 else 0

    avg_attempts = sum(r["attempts"] for r in results) / total if total > 0 else 0

    # Print summary
    print("\n" + "="*60)
    print("GENERATION SUMMARY")
    print("="*60)
    print(f"Total attempted:     {total}")
    print(f"Successful:          {successful} ({successful/total*100:.1f}%)")
    print(f"  - Auto-pass:       {auto_pass} ({auto_pass/total*100:.1f}%)")
    print(f"  - Needs review:    {review} ({review/total*100:.1f}%)")
    print(f"Failed:              {failed} ({failed/total*100:.1f}%)")
    print(f"Average quality:     {avg_quality:.1f}%")
    print(f"Average attempts:    {avg_attempts:.2f}")
    print(f"Duration:            {duration:.1f}s ({duration/total:.2f}s/question)")
    print("="*60 + "\n")

    # Export validation report
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # CSV report
    csv_path = os.path.join(output_dir, f"validation_report_{timestamp}.csv")
    csv_content = export_validation_results_csv(results)
    with open(csv_path, "w") as f:
        f.write(csv_content)
    print(f"CSV report saved to: {csv_path}")

    # JSON report
    json_path = os.path.join(output_dir, f"validation_report_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump({
            "summary": {
                "total": total,
                "successful": successful,
                "auto_pass": auto_pass,
                "review": review,
                "failed": failed,
                "average_quality": round(avg_quality, 1),
                "duration_seconds": round(duration, 1),
                "generated_at": timestamp,
            },
            "results": results,
        }, f, indent=2, default=str)
    print(f"JSON report saved to: {json_path}")

    # Save to database if requested
    if save_to_db and questions_generated:
        print(f"\nSaving {len(questions_generated)} questions to database...")
        # Questions are already saved by generate_question_fast
        print("Questions saved.")

    return {
        "total": total,
        "successful": successful,
        "auto_pass": auto_pass,
        "review": review,
        "failed": failed,
        "average_quality": round(avg_quality, 1),
        "csv_report": csv_path,
        "json_report": json_path,
    }


def export_validation_results_csv(results: list) -> str:
    """Export results to CSV format."""
    lines = [
        "index,specialty,difficulty,success,attempts,quality_score,structural_score,nbme_score,content_score,recommendation,issues"
    ]

    for r in results:
        v = r.get("validation", {}) or {}
        issues_str = "; ".join(v.get("issues", []) if v else [r.get("error", "")])
        lines.append(
            f"{r['index']},"
            f"{r['specialty']},"
            f"{r['difficulty']},"
            f"{r['success']},"
            f"{r['attempts']},"
            f"{v.get('quality_score', '')},"
            f"{v.get('structural_score', '')},"
            f"{v.get('nbme_score', '')},"
            f"{v.get('content_score', '')},"
            f"{v.get('recommendation', '')},"
            f"\"{issues_str}\""
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate 100 test questions for AI quality validation"
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Save passing questions to database"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="validation_reports",
        help="Directory for validation reports (default: validation_reports)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate existing questions, don't generate new ones"
    )

    args = parser.parse_args()

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    db = SessionLocal()
    try:
        if args.dry_run:
            print("Dry run mode - validating existing questions only")
            # Get recent AI-generated questions
            questions = db.query(Question).filter(
                Question.source_type == "ai_generated"
            ).order_by(Question.created_at.desc()).limit(100).all()

            if not questions:
                print("No AI-generated questions found to validate")
                return

            question_dicts = [{
                "id": q.id,
                "vignette": q.vignette,
                "choices": q.choices,
                "answer_key": q.answer_key,
                "explanation": q.explanation,
                "specialty": q.specialty,
            } for q in questions]

            results = validate_batch(question_dicts)
            print(f"Validated {results['total']} questions")
            print(f"Auto-pass: {results['auto_pass']} ({results['auto_pass_rate']}%)")
            print(f"Average quality: {results['average_quality_score']}%")

            # Export report
            os.makedirs(args.output_dir, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(args.output_dir, f"validation_{timestamp}.csv")
            with open(report_path, "w") as f:
                f.write(export_validation_report(results, "csv"))
            print(f"Report saved to: {report_path}")

        else:
            # Generate new questions
            asyncio.run(generate_batch(
                db,
                save_to_db=args.save,
                output_dir=args.output_dir
            ))

    finally:
        db.close()


if __name__ == "__main__":
    main()
