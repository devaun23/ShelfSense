#!/usr/bin/env python3
"""
Content Generation Pipeline Orchestrator

Ties together the full content pipeline:
1. Load curriculum gaps (from gap analysis)
2. Generate questions with Ollama (FREE)
3. Validate with Claude Haiku / GPT-3.5 (LOW COST)
4. Check originality (FREE)
5. Save to database

Usage:
    # Generate 10 questions for top priority gaps
    python scripts/generate_content_pipeline.py --count 10

    # Generate for specific system/task
    python scripts/generate_content_pipeline.py --system cardiovascular --task diagnosis --count 5

    # Dry run (no DB save)
    python scripts/generate_content_pipeline.py --count 5 --dry-run

    # Skip validation (faster, for testing)
    python scripts/generate_content_pipeline.py --count 10 --skip-validation

Cost Estimate:
    - Ollama generation: $0 (local)
    - Haiku validation: ~$0.003 per question (~$0.30 per 100)
    - Originality check: $0 (local)
    - Total: ~$0.003 per accepted question
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Load environment variables from backend/.env
from dotenv import load_dotenv
env_file = backend_path / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded environment from {env_file}")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentPipeline:
    """
    Orchestrates the full content generation pipeline.
    """

    # Compute absolute paths based on script location
    _script_dir = Path(__file__).parent.resolve()
    _project_root = _script_dir.parent
    _db_path = (_project_root / 'backend' / 'shelfsense.db').resolve()
    _default_db = f"sqlite:///{_db_path}"
    _default_gaps = str((_project_root / "backend" / "curriculum_gaps.json").resolve())

    def __init__(
        self,
        db_url: str = None,
        gaps_file: str = None,
        skip_validation: bool = False,
        dry_run: bool = False,
        model: str = "llama3.2:3b",
        use_cloud: bool = False
    ):
        self.db_url = db_url or self._default_db
        self.gaps_file = gaps_file or self._default_gaps
        self.skip_validation = skip_validation
        self.dry_run = dry_run
        self.model = model
        self.use_cloud = use_cloud

        # Initialize database
        logger.info(f"Using database: {self.db_url}")
        engine = create_engine(self.db_url)
        Session = sessionmaker(bind=engine)
        self.db = Session()

        # Stats tracking
        self.stats = {
            "generated": 0,
            "validated": 0,
            "accepted": 0,
            "rejected": 0,
            "duplicates": 0,
            "saved": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }

    async def run(
        self,
        count: int = 10,
        system: Optional[str] = None,
        task: Optional[str] = None,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Run the full content generation pipeline.

        Args:
            count: Number of questions to generate
            system: Specific body system (or None for priority gaps)
            task: Specific physician task (or None for priority gaps)
            difficulty: Question difficulty level

        Returns:
            Pipeline run statistics
        """
        self.stats["start_time"] = datetime.utcnow()
        logger.info(f"Starting content pipeline: target {count} questions")

        # Initialize generator based on mode
        if self.use_cloud:
            from app.services.cloud_question_generator import (
                CloudQuestionGenerator,
                get_available_providers
            )
            try:
                generator = CloudQuestionGenerator(self.db, provider="auto")
                logger.info(f"Using CLOUD generation ({generator.provider}) - ~$0.01/question")
            except ValueError as e:
                logger.error(f"Cloud provider error: {e}")
                available = get_available_providers()
                if not available:
                    logger.info("Set OPENAI_API_KEY or ANTHROPIC_API_KEY to use cloud generation")
                return self.stats
        else:
            from app.services.ollama_question_generator import OllamaQuestionGenerator
            from app.services.ollama_service import OllamaNotAvailableError
            try:
                generator = OllamaQuestionGenerator(self.db, model=self.model)
                logger.info(f"Using LOCAL Ollama model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama: {e}")
                logger.info("TIP: Use --use-cloud for faster cloud-based generation")
                return self.stats

        # Determine what to generate
        if system and task:
            # Specific gap
            gaps = [{"system": system, "task": task, "gap": count}]
        else:
            # Load priority gaps
            gaps = self._load_priority_gaps(count)

        if not gaps:
            logger.warning("No gaps to fill")
            return self.stats

        logger.info(f"Will generate for {len(gaps)} gap(s)")

        # Process each gap
        questions_remaining = count
        all_accepted = []

        for gap in gaps:
            if questions_remaining <= 0:
                break

            gap_system = gap["system"]
            gap_task = gap["task"]
            gap_count = min(gap.get("gap", 5), questions_remaining, 10)  # Max 10 per gap

            logger.info(f"\n{'='*60}")
            logger.info(f"Generating for: {gap_system} x {gap_task} ({gap_count} questions)")
            logger.info(f"{'='*60}")

            try:
                # Step 1: Generate with Ollama
                questions = await self._generate_questions(
                    generator, gap_system, gap_task, gap_count, difficulty
                )

                if not questions:
                    logger.warning(f"No questions generated for {gap_system} x {gap_task}")
                    continue

                # Step 2: Validate quality
                if not self.skip_validation:
                    questions = await self._validate_questions(questions)

                if not questions:
                    logger.warning("All questions rejected by validation")
                    continue

                # Step 3: Check originality
                questions = await self._check_originality(questions)

                if not questions:
                    logger.warning("All questions flagged as duplicates")
                    continue

                # Step 4: Save to database
                if not self.dry_run:
                    saved = self._save_questions(questions, generator)
                    self.stats["saved"] += saved
                else:
                    logger.info(f"[DRY RUN] Would save {len(questions)} questions")

                all_accepted.extend(questions)
                questions_remaining -= len(questions)

            except OllamaNotAvailableError as e:
                logger.error(f"Ollama not available: {e}")
                logger.info("Start Ollama with: ollama serve")
                break

            except Exception as e:
                logger.error(f"Error processing gap {gap_system} x {gap_task}: {e}")
                self.stats["errors"] += 1
                continue

        self.stats["end_time"] = datetime.utcnow()
        self.stats["accepted"] = len(all_accepted)

        # Print summary
        self._print_summary()

        return self.stats

    def _load_priority_gaps(self, target_count: int) -> List[Dict[str, Any]]:
        """Load priority gaps from gap analysis file."""
        gaps_path = Path(self.gaps_file)

        if not gaps_path.exists():
            logger.warning(f"Gaps file not found: {self.gaps_file}")
            logger.info("Run curriculum_gap_analysis.py first to generate gaps")
            return []

        with open(gaps_path) as f:
            data = json.load(f)

        matrix_gaps = data.get("matrix_gaps", [])

        # Filter to gaps that actually need questions
        priority_gaps = [g for g in matrix_gaps if g.get("gap", 0) > 0]

        # Sort by gap size (largest gaps first)
        priority_gaps.sort(key=lambda x: x.get("gap", 0), reverse=True)

        logger.info(f"Loaded {len(priority_gaps)} priority gaps from analysis")

        return priority_gaps

    async def _generate_questions(
        self,
        generator,
        system: str,
        task: str,
        count: int,
        difficulty: str
    ) -> List[Dict[str, Any]]:
        """Generate questions using Ollama."""
        logger.info(f"[GENERATE] Creating {count} questions with Ollama...")

        try:
            questions = await generator.generate_for_gap(
                system=system,
                task=task,
                count=count,
                difficulty=difficulty
            )

            self.stats["generated"] += len(questions)
            logger.info(f"[GENERATE] Created {len(questions)} questions")

            return questions

        except Exception as e:
            logger.error(f"[GENERATE] Error: {e}")
            raise

    async def _validate_questions(
        self,
        questions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate questions with Claude Haiku / GPT-3.5."""
        from app.services.multi_model_validator import (
            MultiModelValidator,
            ValidationStatus
        )

        logger.info(f"[VALIDATE] Checking {len(questions)} questions...")

        validator = MultiModelValidator()
        accepted = []

        for i, question in enumerate(questions):
            try:
                result = await validator.validate_question(question)
                self.stats["validated"] += 1

                if result.status == ValidationStatus.ACCEPT:
                    accepted.append(question)
                    logger.info(
                        f"  [{i+1}] ACCEPT (score: {result.score:.0f}, "
                        f"accuracy: {result.medical_accuracy:.0f})"
                    )
                elif result.status == ValidationStatus.REVISE:
                    # For now, skip REVISE questions (could add revision logic later)
                    logger.info(
                        f"  [{i+1}] REVISE - skipping (score: {result.score:.0f})"
                    )
                    logger.info(f"       Issues: {', '.join(result.issues[:2])}")
                else:
                    self.stats["rejected"] += 1
                    logger.info(
                        f"  [{i+1}] REJECT (score: {result.score:.0f})"
                    )
                    logger.info(f"       Issues: {', '.join(result.issues[:2])}")

            except Exception as e:
                logger.warning(f"  [{i+1}] Validation error: {e}")
                # On validation error, accept anyway (will need manual review)
                accepted.append(question)

        logger.info(f"[VALIDATE] {len(accepted)}/{len(questions)} accepted")
        return accepted

    async def _check_originality(
        self,
        questions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check questions for originality."""
        from app.services.originality_checker import OriginalityChecker

        logger.info(f"[ORIGINALITY] Checking {len(questions)} questions...")

        checker = OriginalityChecker(self.db)
        await checker.load_corpus()

        original, results = await checker.check_batch(questions)

        duplicates = len(questions) - len(original)
        self.stats["duplicates"] += duplicates

        if duplicates > 0:
            logger.warning(f"[ORIGINALITY] {duplicates} duplicates filtered")

        logger.info(f"[ORIGINALITY] {len(original)}/{len(questions)} are original")
        return original

    def _save_questions(
        self,
        questions: List[Dict[str, Any]],
        generator
    ) -> int:
        """Save questions to database."""
        logger.info(f"[SAVE] Saving {len(questions)} questions to database...")

        try:
            saved = generator.save_questions_to_db(
                questions,
                status="pending_review"  # New questions need review
            )
            logger.info(f"[SAVE] Successfully saved {saved} questions")
            return saved

        except Exception as e:
            logger.error(f"[SAVE] Error: {e}")
            return 0

    def _print_summary(self):
        """Print pipeline run summary."""
        duration = (
            (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            if self.stats["end_time"] and self.stats["start_time"]
            else 0
        )

        print("\n" + "=" * 60)
        print("CONTENT PIPELINE SUMMARY")
        print("=" * 60)
        print(f"  Generated:  {self.stats['generated']} questions")
        print(f"  Validated:  {self.stats['validated']} questions")
        print(f"  Accepted:   {self.stats['accepted']} questions")
        print(f"  Rejected:   {self.stats['rejected']} questions")
        print(f"  Duplicates: {self.stats['duplicates']} filtered")
        print(f"  Saved:      {self.stats['saved']} questions")
        print(f"  Errors:     {self.stats['errors']}")
        print(f"  Duration:   {duration:.1f} seconds")

        if self.stats["generated"] > 0:
            accept_rate = self.stats["accepted"] / self.stats["generated"] * 100
            print(f"  Accept Rate: {accept_rate:.1f}%")

        # Cost estimate (Haiku validation only)
        if self.stats["validated"] > 0:
            estimated_cost = self.stats["validated"] * 0.003  # ~$0.003 per validation
            print(f"  Est. Cost:  ${estimated_cost:.3f}")

        print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="Generate USMLE questions using the content pipeline"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=10,
        help="Number of questions to generate (default: 10)"
    )
    parser.add_argument(
        "--system", "-s",
        type=str,
        help="Specific body system (e.g., cardiovascular)"
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="Specific physician task (e.g., diagnosis)"
    )
    parser.add_argument(
        "--difficulty", "-d",
        type=str,
        default="medium",
        choices=["easy", "medium", "hard"],
        help="Question difficulty (default: medium)"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip quality validation (faster, for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save to database (preview only)"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,  # Use class default (absolute path)
        help="Database URL (default: auto-detected absolute path)"
    )
    parser.add_argument(
        "--gaps-file",
        type=str,
        default=None,  # Use class default (absolute path)
        help="Path to curriculum gaps JSON (default: auto-detected absolute path)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="llama3.2:3b",
        help="Ollama model to use (default: llama3.2:3b)"
    )
    parser.add_argument(
        "--use-cloud",
        action="store_true",
        help="Use Claude/GPT instead of local Ollama (faster but costs money)"
    )

    args = parser.parse_args()

    # Validate system/task pairing
    if bool(args.system) != bool(args.task):
        parser.error("--system and --task must be used together")

    # Create and run pipeline
    pipeline = ContentPipeline(
        db_url=args.db_url,
        gaps_file=args.gaps_file,
        skip_validation=args.skip_validation,
        dry_run=args.dry_run,
        model=args.model,
        use_cloud=args.use_cloud
    )

    try:
        await pipeline.run(
            count=args.count,
            system=args.system,
            task=args.task,
            difficulty=args.difficulty
        )
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
    finally:
        pipeline.db.close()


if __name__ == "__main__":
    asyncio.run(main())
