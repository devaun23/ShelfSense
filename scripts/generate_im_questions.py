#!/usr/bin/env python3
"""
Internal Medicine Question Generation Script

Generates 2,500 IM questions distributed across body systems based on NBME IM Shelf weightings.
Runs with checkpointing so it can be resumed if interrupted.

Usage:
    python scripts/generate_im_questions.py --count 2500 --use-cloud
    python scripts/generate_im_questions.py --resume  # Resume from checkpoint
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
env_file = backend_path / ".env"
if env_file.exists():
    load_dotenv(env_file)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# IM Shelf Body System Distribution (based on NBME)
# Total percentages add up to 100%
IM_SYSTEMS = {
    "cardiovascular": 18,           # Heart failure, MI, arrhythmias, HTN
    "respiratory": 12,              # Pneumonia, COPD, asthma, PE
    "gastrointestinal": 14,         # GI bleed, liver disease, IBD
    "renal_urinary_reproductive": 10,  # AKI, CKD, UTI, electrolytes
    "endocrine": 12,                # Diabetes, thyroid, adrenal
    "nervous_system": 8,            # Stroke, seizure, meningitis
    "blood_lymph": 8,               # Anemia, coagulopathy, malignancy
    "musculoskeletal_skin": 6,      # Arthritis, cellulitis, rashes
    "immune": 4,                    # Autoimmune, allergies
    "multisystem": 4,               # Sepsis, shock, multi-organ
    "biostatistics_epi": 2,         # Study design, screening
    "behavioral_health": 2,         # Depression, anxiety in medical patients
}

# Physician Tasks Distribution
IM_TASKS = {
    "diagnosis": 35,                # What's the diagnosis?
    "management": 30,               # How do you treat?
    "lab_diagnostic": 15,           # Next best test?
    "pharmacotherapy": 10,          # Drug choice/mechanism
    "health_maintenance": 5,        # Screening, prevention
    "prognosis": 5,                 # Complications, outcomes
}

CHECKPOINT_FILE = Path(__file__).parent / "checkpoints" / "im_generation_checkpoint.json"


def calculate_distribution(total: int) -> List[Dict[str, Any]]:
    """Calculate question distribution across system/task combinations."""
    targets = []

    for system, system_pct in IM_SYSTEMS.items():
        system_count = int(total * system_pct / 100)

        for task, task_pct in IM_TASKS.items():
            count = max(1, int(system_count * task_pct / 100))
            targets.append({
                "system": system,
                "task": task,
                "target": count,
                "completed": 0
            })

    # Adjust to hit exact total
    current_total = sum(t["target"] for t in targets)
    if current_total < total:
        # Add extras to highest-weight items
        diff = total - current_total
        for t in targets[:diff]:
            t["target"] += 1

    return targets


def load_checkpoint() -> Dict[str, Any]:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return None


def save_checkpoint(state: Dict[str, Any]):
    """Save checkpoint for resume capability."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


async def main():
    parser = argparse.ArgumentParser(description="Generate IM questions")
    parser.add_argument("--count", "-n", type=int, default=2500, help="Total questions to generate")
    parser.add_argument("--use-cloud", action="store_true", help="Use cloud API (OpenAI/Anthropic)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--batch-size", type=int, default=10, help="Questions per batch (default: 10)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip quality validation")
    args = parser.parse_args()

    # Setup database
    db_path = (backend_path / 'shelfsense.db').resolve()
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    logger.info(f"Database: {db_url}")

    # Initialize generator
    if args.use_cloud:
        from app.services.cloud_question_generator import CloudQuestionGenerator
        generator = CloudQuestionGenerator(db, provider="auto")
        logger.info(f"Using CLOUD generation ({generator.provider})")
    else:
        from app.services.ollama_question_generator import OllamaQuestionGenerator
        generator = OllamaQuestionGenerator(db)
        logger.info("Using LOCAL Ollama generation")

    # Load or create state
    if args.resume:
        state = load_checkpoint()
        if not state:
            logger.error("No checkpoint found. Start fresh without --resume")
            return
        logger.info(f"Resuming from checkpoint: {state['completed_total']}/{state['target_total']} completed")
    else:
        targets = calculate_distribution(args.count)
        state = {
            "target_total": args.count,
            "completed_total": 0,
            "targets": targets,
            "started_at": datetime.now().isoformat(),
            "errors": 0
        }
        save_checkpoint(state)

    # Stats
    start_time = datetime.now()
    questions_generated = 0

    print("\n" + "=" * 60)
    print("INTERNAL MEDICINE QUESTION GENERATION")
    print("=" * 60)
    print(f"  Target: {state['target_total']} questions")
    print(f"  Completed: {state['completed_total']} questions")
    print(f"  Remaining: {state['target_total'] - state['completed_total']} questions")
    print(f"  Estimated time: ~{(state['target_total'] - state['completed_total']) * 10 // 60} minutes")
    print("=" * 60 + "\n")

    try:
        for i, target in enumerate(state["targets"]):
            # Check if we've reached the total target
            if state["completed_total"] >= state["target_total"]:
                logger.info(f"Reached target of {state['target_total']} questions. Stopping.")
                break

            remaining = target["target"] - target["completed"]
            if remaining <= 0:
                continue

            # Cap remaining to not exceed total target
            max_to_generate = state["target_total"] - state["completed_total"]
            remaining = min(remaining, max_to_generate)

            system = target["system"]
            task = target["task"]

            logger.info(f"\n[{i+1}/{len(state['targets'])}] {system} x {task}: {remaining} questions")

            # Generate in batches
            while remaining > 0:
                batch_size = min(args.batch_size, remaining)

                try:
                    questions = await generator.generate_for_gap(
                        system=system,
                        task=task,
                        discipline="internal_medicine",
                        count=batch_size,
                        difficulty="medium"
                    )

                    if questions:
                        # Save to database
                        saved = generator.save_questions_to_db(questions, status="pending_review")
                        target["completed"] += saved
                        state["completed_total"] += saved
                        questions_generated += saved
                        remaining -= saved

                        # Progress update
                        pct = state["completed_total"] / state["target_total"] * 100
                        elapsed = (datetime.now() - start_time).total_seconds() / 60
                        rate = questions_generated / elapsed if elapsed > 0 else 0
                        eta = (state["target_total"] - state["completed_total"]) / rate if rate > 0 else 0

                        logger.info(
                            f"  Progress: {state['completed_total']}/{state['target_total']} "
                            f"({pct:.1f}%) | Rate: {rate:.1f}/min | ETA: {eta:.0f}min"
                        )

                        # Save checkpoint after each batch
                        save_checkpoint(state)
                    else:
                        state["errors"] += 1
                        logger.warning(f"  No questions generated for this batch")
                        break  # Move to next system/task

                except Exception as e:
                    state["errors"] += 1
                    logger.error(f"  Error: {e}")
                    save_checkpoint(state)
                    continue

    except KeyboardInterrupt:
        logger.info("\n\nInterrupted! Saving checkpoint...")
        save_checkpoint(state)
        print(f"\nProgress saved. Resume with: python scripts/generate_im_questions.py --resume --use-cloud")

    finally:
        db.close()

    # Final summary
    elapsed = (datetime.now() - start_time).total_seconds() / 60
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Total Generated: {questions_generated}")
    print(f"  Total in DB: {state['completed_total']}")
    print(f"  Errors: {state['errors']}")
    print(f"  Duration: {elapsed:.1f} minutes")
    if questions_generated > 0:
        print(f"  Rate: {questions_generated / elapsed:.1f} questions/minute")
        cost = questions_generated * 0.017
        print(f"  Est. Cost: ${cost:.2f}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
