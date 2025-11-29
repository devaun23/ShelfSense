"""
Validation Script for 2,500 AI-Generated Internal Medicine Questions

Usage:
    python scripts/validate_2500_questions.py --input questions.json --output validation_report.json

Features:
- Multi-stage validation pipeline
- Quality gates with auto-pause
- Human review sampling
- Comprehensive reporting
- Statistical confidence intervals
"""

import asyncio
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.services.batch_validation_pipeline import (
    BatchValidationPipeline,
    detect_plagiarism
)


def load_questions(filepath: str) -> List[Dict]:
    """Load questions from JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Handle different JSON formats
    if isinstance(data, list):
        questions = data
    elif isinstance(data, dict) and "questions" in data:
        questions = data["questions"]
    else:
        raise ValueError("JSON must be list of questions or dict with 'questions' key")

    print(f"Loaded {len(questions)} questions from {filepath}")
    return questions


def save_report(report: Dict, filepath: str):
    """Save validation report to JSON"""
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Saved validation report to {filepath}")


def print_summary(report: Dict):
    """Print validation summary to console"""
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    print(f"\nTotal Questions: {report['total_questions']}")
    print(f"Accepted: {report['accepted']} ({report['acceptance_rate']:.1%})")
    print(f"Rejected: {report['rejected']}")
    print(f"Needs Review: {report['needs_review']}")

    print(f"\nElite Questions: {report['elite_count']} ({report['elite_rate']:.1%})")
    print(f"Average Score: {report['avg_score']:.1f}/100")
    print(f"Median Score: {report['median_score']:.1f}/100")

    print(f"\nStage Breakdown:")
    for stage, count in report['stage_breakdown'].items():
        print(f"  {stage}: {count}")

    print(f"\nCritical Issues: {report['critical_issues_count']}")

    if report['quality_gate_failures']:
        print(f"\nQuality Gate Failures: {len(report['quality_gate_failures'])}")
        for failure in report['quality_gate_failures']:
            print(f"  - {failure['gate']} at question {failure['at_question']}: {failure['action']}")

    print(f"\nEstimated Cost: ${report['estimated_cost']:.2f}")
    print(f"Total Time: {report['total_time_seconds']:.1f} seconds")

    print("\nTop Issues:")
    issue_items = sorted(
        report['issue_breakdown'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    for issue_type, count in issue_items:
        print(f"  {issue_type}: {count}")

    print("="*60 + "\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Validate batch of AI-generated questions"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file with questions"
    )
    parser.add_argument(
        "--output",
        default="validation_report.json",
        help="Output JSON file for report (default: validation_report.json)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        help="Sample size for human review (default: auto-calculated)"
    )
    parser.add_argument(
        "--disable-gates",
        action="store_true",
        help="Disable quality gates (process all questions)"
    )
    parser.add_argument(
        "--check-plagiarism",
        help="Path to known questions JSON for plagiarism checking"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Load questions
    questions = load_questions(args.input)

    # Initialize database session
    db = SessionLocal()

    try:
        # Initialize pipeline
        pipeline = BatchValidationPipeline(db)

        print(f"\nStarting validation of {len(questions)} questions...")
        print(f"Quality gates: {'DISABLED' if args.disable_gates else 'ENABLED'}")

        # Run validation
        report = await pipeline.validate_batch(
            questions=questions,
            enable_gates=not args.disable_gates,
            human_review_sample_size=args.sample_size
        )

        # Convert report to dict
        report_dict = {
            "validated_at": datetime.utcnow().isoformat(),
            "input_file": args.input,
            "total_questions": report.total_questions,
            "accepted": report.accepted,
            "rejected": report.rejected,
            "needs_review": report.needs_review,
            "acceptance_rate": report.acceptance_rate,
            "elite_count": report.elite_count,
            "elite_rate": report.elite_rate,
            "avg_score": report.avg_score,
            "median_score": report.median_score,
            "critical_issues_count": report.critical_issues_count,
            "quality_gate_failures": report.quality_gate_failures,
            "stage_breakdown": report.stage_breakdown,
            "issue_breakdown": report.issue_breakdown,
            "estimated_cost": report.estimated_cost,
            "total_time_seconds": report.total_time_seconds
        }

        # Plagiarism check (optional)
        if args.check_plagiarism:
            print(f"\nRunning plagiarism check against {args.check_plagiarism}...")
            known_questions = load_questions(args.check_plagiarism)

            plagiarism_results = []
            for q in questions:
                plag_result = detect_plagiarism(q, known_questions)
                if plag_result["is_plagiarism"]:
                    plagiarism_results.append({
                        "question_id": q.get("id"),
                        "similarity": plag_result["max_similarity"],
                        "source": plag_result["similar_source"]
                    })

            report_dict["plagiarism_check"] = {
                "checked_against": args.check_plagiarism,
                "flagged_count": len(plagiarism_results),
                "flagged_questions": plagiarism_results
            }

            print(f"Plagiarism check complete: {len(plagiarism_results)} questions flagged")

        # Human review sample
        print(f"\nGenerating human review sample...")
        accepted_questions = [
            q for q in questions
            if q.get("validation_status") == "ACCEPTED"
        ]

        sample = pipeline.select_human_review_sample(
            accepted_questions,
            sample_size=args.sample_size
        )

        report_dict["human_review_sample"] = {
            "sample_size": len(sample),
            "question_ids": [q.get("id") for q in sample],
            "sampling_method": "stratified",
            "confidence_level": pipeline.SAMPLE_CONFIDENCE_LEVEL,
            "margin_of_error": pipeline.SAMPLE_MARGIN_OF_ERROR
        }

        # Save report
        save_report(report_dict, args.output)

        # Print summary
        print_summary(report_dict)

        # Exit code based on acceptance rate
        if report.acceptance_rate < pipeline.OVERALL_ACCEPT_THRESHOLD:
            print(f"WARNING: Acceptance rate {report.acceptance_rate:.1%} below threshold {pipeline.OVERALL_ACCEPT_THRESHOLD:.1%}")
            sys.exit(1)

        if report.quality_gate_failures:
            critical_failures = [
                f for f in report.quality_gate_failures
                if f["action"] == "STOP_GENERATION"
            ]
            if critical_failures:
                print("ERROR: Critical quality gate failures detected")
                sys.exit(2)

        print("Validation complete - all quality gates passed!")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
