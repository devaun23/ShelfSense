#!/usr/bin/env python3
"""
Batch Question Generation for Internal Medicine
Implements the IM_QUESTION_GENERATION_MANIFEST.md strategy

Usage:
    python scripts/batch_generate_im.py --phase 1 --batch 1
    python scripts/batch_generate_im.py --phase 2 --subspecialty cardiology
    python scripts/batch_generate_im.py --custom --count 50 --subspecialty endocrinology --task pharmacotherapy
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.models import Question, generate_uuid
from app.services.question_generator import generate_question, validate_explanation_quality
from app.services.question_validators import QuestionQualityValidator, ValidationReport

# ============================================================================
# GENERATION MANIFEST CONFIGURATION
# ============================================================================

SUBSPECIALTY_TARGETS = {
    "Cardiology": 325,
    "Pulmonology": 250,
    "Gastroenterology": 250,
    "Infectious Disease": 250,
    "Renal": 200,
    "Endocrinology": 200,
    "Hematology/Oncology": 200,
    "Rheumatology": 150,
    "Neurology": 150,
    "Immunology/Allergy": 100,
    "Ethics/Professionalism": 250,
    "Biostatistics/Epidemiology": 125,
    "Multisystem": 50,
}

TASK_TYPE_PERCENTAGES = {
    "diagnosis": 18,
    "lab_diagnostic": 15,
    "mixed_management": 14,
    "pharmacotherapy": 10,
    "clinical_interventions": 8,
    "prognosis": 7,
    "health_maintenance": 7,
    "professionalism": 6,
    "systems_practice": 6,
    "practice_learning": 4,
    "mechanism": 5,
}

DIFFICULTY_PERCENTAGES = {
    "easy": 20,
    "medium": 50,
    "hard": 25,
    "very_hard": 5,
}

# Phase definitions from manifest
PHASE_1_SPECIALTIES = {
    "Ethics/Professionalism": 250,
    "Biostatistics/Epidemiology": 125,
    "Endocrinology": 125,
    "Hematology/Oncology": 125,
    "Renal": 100,
    "Neurology": 75,
}

PHASE_2_SPECIALTIES = {
    "Cardiology": 325,
    "Pulmonology": 250,
    "Gastroenterology": 250,
    "Infectious Disease": 75,  # Complete to 250
}

PHASE_3_SPECIALTIES = {
    "Infectious Disease": 175,  # Complete to 250 total
    "Rheumatology": 150,
    "Immunology/Allergy": 100,
    "Renal": 100,  # Additional to reach 200
    "Endocrinology": 75,  # Complete to 200
    "Hematology/Oncology": 75,  # Complete to 200
    "Multisystem": 50,
}

# High-yield topics by subspecialty (from manifest)
HIGH_YIELD_TOPICS = {
    "Cardiology": [
        "Acute coronary syndrome (STEMI, NSTEMI, unstable angina)",
        "Heart failure (systolic vs diastolic, acute decompensation)",
        "Atrial fibrillation management",
        "Hypertension management",
        "Valvular heart disease",
        "Aortic dissection",
        "Pericarditis and cardiac tamponade",
        "Infective endocarditis",
    ],
    "Pulmonology": [
        "COPD exacerbation management",
        "Asthma (step therapy, acute exacerbation)",
        "Pneumonia (CAP, HAP, VAP)",
        "Pulmonary embolism",
        "Pleural effusion",
        "Lung cancer screening and diagnosis",
    ],
    "Gastroenterology": [
        "GI bleeding (upper vs lower)",
        "Inflammatory bowel disease",
        "Cirrhosis complications",
        "Acute pancreatitis",
        "Cholecystitis and choledocholithiasis",
        "Colorectal cancer screening",
    ],
    "Infectious Disease": [
        "HIV/AIDS (opportunistic infections)",
        "Sepsis and septic shock",
        "Meningitis (bacterial, viral, fungal)",
        "Endocarditis",
        "Skin and soft tissue infections",
        "Tuberculosis",
    ],
    "Renal": [
        "Acute kidney injury",
        "Chronic kidney disease",
        "Electrolyte disorders",
        "Acid-base disorders",
        "Nephrotic vs nephritic syndrome",
    ],
    "Endocrinology": [
        "Diabetes mellitus",
        "Diabetic ketoacidosis and HHS",
        "Thyroid disorders",
        "Adrenal disorders",
        "Hypoglycemia evaluation",
    ],
    "Hematology/Oncology": [
        "Anemia workup",
        "Transfusion medicine",
        "Anticoagulation",
        "Thrombocytopenia",
        "Venous thromboembolism",
    ],
    "Rheumatology": [
        "Rheumatoid arthritis",
        "Systemic lupus erythematosus",
        "Gout and pseudogout",
        "Giant cell arteritis",
    ],
    "Neurology": [
        "Stroke (ischemic vs hemorrhagic)",
        "Seizures and status epilepticus",
        "Headache (migraine, cluster, temporal arteritis)",
        "Dementia workup",
    ],
    "Ethics/Professionalism": [
        "Informed consent and capacity",
        "Confidentiality and HIPAA",
        "End-of-life care",
        "Difficult conversations",
        "Professional boundaries",
    ],
    "Biostatistics/Epidemiology": [
        "Study design (RCT, cohort, case-control)",
        "Diagnostic statistics (sensitivity, specificity)",
        "Clinical significance (p-value, CI, NNT)",
    ],
    "Immunology/Allergy": [
        "Allergic reactions and anaphylaxis",
        "Immunodeficiency disorders",
        "Autoimmune diseases",
    ],
    "Multisystem": [
        "Complex integration cases",
        "Multi-organ system involvement",
    ],
}


# ============================================================================
# BATCH GENERATION ENGINE
# ============================================================================

class BatchGenerator:
    """Manages batch question generation with validation"""

    def __init__(self, db: Session, validate: bool = True, verbose: bool = True):
        self.db = db
        self.validate = validate
        self.verbose = verbose
        self.validator = QuestionQualityValidator() if validate else None

        # Statistics
        self.generated = 0
        self.passed = 0
        self.failed = 0
        self.validation_failures = []

    def generate_batch(
        self,
        subspecialty: str,
        count: int,
        task_distribution: Optional[Dict[str, int]] = None,
        difficulty_distribution: Optional[Dict[str, int]] = None,
        batch_id: Optional[str] = None,
    ) -> List[Question]:
        """
        Generate a batch of questions for a subspecialty.

        Args:
            subspecialty: IM subspecialty (e.g., "Cardiology")
            count: Number of questions to generate
            task_distribution: Optional task type distribution (defaults to manifest)
            difficulty_distribution: Optional difficulty distribution (defaults to manifest)
            batch_id: Optional batch identifier for tracking

        Returns:
            List of generated Question objects
        """
        if batch_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_id = f"IM_{subspecialty.replace('/', '_')}_{timestamp}"

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"BATCH GENERATION: {batch_id}")
            print(f"Subspecialty: {subspecialty}")
            print(f"Target Count: {count}")
            print(f"{'='*80}\n")

        # Calculate task and difficulty distributions
        if task_distribution is None:
            task_distribution = self._calculate_task_distribution(count)

        if difficulty_distribution is None:
            difficulty_distribution = self._calculate_difficulty_distribution(count)

        # Get high-yield topics for this subspecialty
        topics = HIGH_YIELD_TOPICS.get(subspecialty, [])
        if not topics:
            print(f"WARNING: No high-yield topics defined for {subspecialty}")
            topics = [None]  # Generate without specific topic

        # Generate questions
        questions = []
        attempts = 0
        max_attempts = count * 3  # Allow 3x attempts for failures

        while len(questions) < count and attempts < max_attempts:
            attempts += 1

            # Select task type and difficulty from distributions
            task_type = self._select_from_distribution(task_distribution)
            difficulty = self._select_from_distribution(difficulty_distribution)
            topic = self._select_topic(topics)

            try:
                # Generate question
                if self.verbose and len(questions) % 10 == 0:
                    print(f"Progress: {len(questions)}/{count} questions generated...")

                question_data = generate_question(
                    db=self.db,
                    specialty=f"Internal Medicine - {subspecialty}",
                    topic=topic,
                    use_cache=False  # Don't use cache for batch generation
                )

                # Validate if enabled
                if self.validate:
                    validation_result = self._validate_question(question_data)
                    if not validation_result.passed:
                        self.failed += 1
                        self.validation_failures.append({
                            "subspecialty": subspecialty,
                            "topic": topic,
                            "task": task_type,
                            "difficulty": difficulty,
                            "issues": [f.issue for f in validation_result.findings]
                        })
                        continue  # Skip this question

                # Save to database
                question = self._save_question(
                    question_data,
                    subspecialty=subspecialty,
                    task_type=task_type,
                    difficulty=difficulty,
                    batch_id=batch_id
                )

                questions.append(question)
                self.generated += 1
                self.passed += 1

                # Decrement from distributions
                task_distribution[task_type] = max(0, task_distribution[task_type] - 1)
                difficulty_distribution[difficulty] = max(0, difficulty_distribution[difficulty] - 1)

                # Rate limiting (20 questions/min max)
                time.sleep(3)  # 3 seconds between questions

            except Exception as e:
                print(f"ERROR generating question: {str(e)}")
                self.failed += 1
                continue

        if self.verbose:
            self._print_batch_summary(batch_id, questions)

        return questions

    def _calculate_task_distribution(self, count: int) -> Dict[str, int]:
        """Calculate task type distribution for given count"""
        distribution = {}
        for task, percentage in TASK_TYPE_PERCENTAGES.items():
            distribution[task] = int(count * percentage / 100)

        # Adjust for rounding errors
        diff = count - sum(distribution.values())
        if diff > 0:
            # Add to most common task
            distribution["diagnosis"] += diff

        return distribution

    def _calculate_difficulty_distribution(self, count: int) -> Dict[str, int]:
        """Calculate difficulty distribution for given count"""
        distribution = {}
        for difficulty, percentage in DIFFICULTY_PERCENTAGES.items():
            distribution[difficulty] = int(count * percentage / 100)

        # Adjust for rounding errors
        diff = count - sum(distribution.values())
        if diff > 0:
            distribution["medium"] += diff

        return distribution

    def _select_from_distribution(self, distribution: Dict[str, int]) -> str:
        """Select item from distribution (round-robin to ensure balance)"""
        # Find item with highest remaining count
        available = {k: v for k, v in distribution.items() if v > 0}
        if not available:
            # All exhausted, return most common
            return max(distribution.keys(), key=lambda k: TASK_TYPE_PERCENTAGES.get(k, 0))

        return max(available.keys(), key=lambda k: available[k])

    def _select_topic(self, topics: List[str]) -> Optional[str]:
        """Select topic from list (round-robin)"""
        import random
        return random.choice(topics) if topics else None

    def _validate_question(self, question_data: Dict) -> ValidationReport:
        """Validate generated question"""
        return self.validator.validate_question(
            vignette=question_data["vignette"],
            choices=question_data["choices"],
            correct_key=question_data["answer_key"]
        )

    def _save_question(
        self,
        question_data: Dict,
        subspecialty: str,
        task_type: str,
        difficulty: str,
        batch_id: str
    ) -> Question:
        """Save question to database with metadata"""
        # Add custom metadata
        extra_data = question_data.get("extra_data", {})
        extra_data.update({
            "subspecialty": subspecialty,
            "task_type": task_type,
            "difficulty_target": difficulty,
            "generation_batch": batch_id,
            "generated_at": datetime.now().isoformat(),
        })

        question = Question(
            id=generate_uuid(),
            vignette=question_data["vignette"],
            choices=question_data["choices"],
            answer_key=question_data["answer_key"],
            explanation=json.dumps(question_data["explanation"]) if isinstance(question_data["explanation"], dict) else question_data["explanation"],
            source=question_data.get("source", f"AI Generated - Internal Medicine - {subspecialty}"),
            specialty="internal_medicine",
            difficulty_level=difficulty,
            recency_weight=1.0,
            recency_tier=1,
            extra_data=extra_data,
            content_status="active",
            source_type="ai_generated",
            validation_passed=True,  # Already validated
        )

        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)

        return question

    def _print_batch_summary(self, batch_id: str, questions: List[Question]):
        """Print batch generation summary"""
        print(f"\n{'='*80}")
        print(f"BATCH COMPLETE: {batch_id}")
        print(f"{'='*80}")
        print(f"✓ Generated: {len(questions)} questions")
        print(f"✓ Passed Validation: {self.passed}")
        print(f"✗ Failed Validation: {self.failed}")

        if self.validation_failures:
            print(f"\nValidation Failures by Issue:")
            issue_counts = {}
            for failure in self.validation_failures:
                for issue in failure["issues"]:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1

            for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"  - {issue}: {count}x")

        print(f"{'='*80}\n")


# ============================================================================
# PHASE EXECUTORS
# ============================================================================

def execute_phase(phase_num: int, batch_num: int, db: Session):
    """Execute a specific phase and batch from the manifest"""

    if phase_num == 1:
        specialties = PHASE_1_SPECIALTIES
        phase_name = "Critical Gaps"
    elif phase_num == 2:
        specialties = PHASE_2_SPECIALTIES
        phase_name = "High-Yield Core"
    elif phase_num == 3:
        specialties = PHASE_3_SPECIALTIES
        phase_name = "Completion"
    else:
        raise ValueError(f"Invalid phase: {phase_num}")

    print(f"\n{'='*80}")
    print(f"PHASE {phase_num}: {phase_name}")
    print(f"Batch {batch_num}")
    print(f"{'='*80}\n")

    generator = BatchGenerator(db, validate=True, verbose=True)

    # Generate 50 questions per batch (optimal batch size from manifest)
    batch_size = 50

    # Distribute across specialties in phase
    specialty_list = list(specialties.keys())
    specialty_idx = (batch_num - 1) % len(specialty_list)
    subspecialty = specialty_list[specialty_idx]

    print(f"Generating {batch_size} questions for {subspecialty}")

    batch_id = f"Phase{phase_num}_Batch{batch_num:03d}_{subspecialty.replace('/', '_')}"

    questions = generator.generate_batch(
        subspecialty=subspecialty,
        count=batch_size,
        batch_id=batch_id
    )

    return questions


def execute_custom(
    subspecialty: str,
    count: int,
    task_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = None
):
    """Execute custom batch generation"""

    print(f"\n{'='*80}")
    print(f"CUSTOM BATCH GENERATION")
    print(f"{'='*80}\n")

    generator = BatchGenerator(db, validate=True, verbose=True)

    # Custom task/difficulty distributions
    task_dist = None
    diff_dist = None

    if task_type:
        task_dist = {task_type: count}

    if difficulty:
        diff_dist = {difficulty: count}

    batch_id = f"Custom_{subspecialty.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    questions = generator.generate_batch(
        subspecialty=subspecialty,
        count=count,
        task_distribution=task_dist,
        difficulty_distribution=diff_dist,
        batch_id=batch_id
    )

    return questions


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Batch question generation for Internal Medicine"
    )

    subparsers = parser.add_subparsers(dest="command", help="Generation mode")

    # Phase command
    phase_parser = subparsers.add_parser("phase", help="Execute phase from manifest")
    phase_parser.add_argument("--phase", type=int, required=True, choices=[1, 2, 3])
    phase_parser.add_argument("--batch", type=int, required=True)

    # Custom command
    custom_parser = subparsers.add_parser("custom", help="Custom batch generation")
    custom_parser.add_argument("--subspecialty", required=True, choices=list(SUBSPECIALTY_TARGETS.keys()))
    custom_parser.add_argument("--count", type=int, required=True)
    custom_parser.add_argument("--task", choices=list(TASK_TYPE_PERCENTAGES.keys()))
    custom_parser.add_argument("--difficulty", choices=list(DIFFICULTY_PERCENTAGES.keys()))

    args = parser.parse_args()

    # Create database session
    db = SessionLocal()

    try:
        if args.command == "phase":
            execute_phase(args.phase, args.batch, db)
        elif args.command == "custom":
            execute_custom(
                subspecialty=args.subspecialty,
                count=args.count,
                task_type=args.task,
                difficulty=args.difficulty,
                db=db
            )
        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == "__main__":
    main()
