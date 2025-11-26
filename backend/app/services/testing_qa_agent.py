"""
Testing/QA Agent Service for ShelfSense.

Provides automated test validation, coverage analysis, and quality metrics
for AI-generated questions and the overall application.
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Question, ExplanationQualityLog


class TestingQAAgent:
    """
    Agent responsible for quality assurance and testing validation.

    Capabilities:
    - Question quality validation
    - Batch validation of questions
    - Coverage report generation
    - Quality score calculation
    """

    # Quality thresholds based on NBME Gold Book principles
    QUALITY_RULES = {
        "vignette_min_words": 50,
        "vignette_max_words": 500,
        "required_choices": 5,
        "explanation_required": True,
        "distractor_explanations_required": True,
        "quality_score_minimum": 60,
        "clinical_accuracy_required": True
    }

    def __init__(self, db: Session):
        self.db = db

    def validate_question(self, question_id: str) -> Dict:
        """
        Validate a single question for quality compliance.

        Args:
            question_id: ID of the question to validate

        Returns:
            Validation result with is_valid, quality_score, issues, and suggestions
        """
        question = self.db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {
                "question_id": question_id,
                "is_valid": False,
                "quality_score": 0,
                "issues": ["Question not found"],
                "suggestions": []
            }

        issues = []
        suggestions = []
        score_deductions = 0

        # Validate vignette
        vignette_issues, vignette_suggestions, vignette_deductions = self._validate_vignette(
            question.vignette
        )
        issues.extend(vignette_issues)
        suggestions.extend(vignette_suggestions)
        score_deductions += vignette_deductions

        # Validate choices
        choices_issues, choices_suggestions, choices_deductions = self._validate_choices(
            question.choices
        )
        issues.extend(choices_issues)
        suggestions.extend(choices_suggestions)
        score_deductions += choices_deductions

        # Validate answer key
        if question.answer_key not in ["A", "B", "C", "D", "E"]:
            issues.append("Invalid answer key")
            score_deductions += 20

        # Validate explanation
        exp_issues, exp_suggestions, exp_deductions = self._validate_explanation(
            question.explanation
        )
        issues.extend(exp_issues)
        suggestions.extend(exp_suggestions)
        score_deductions += exp_deductions

        # Calculate final score
        quality_score = max(0, 100 - score_deductions)
        is_valid = quality_score >= self.QUALITY_RULES["quality_score_minimum"]

        return {
            "question_id": question_id,
            "is_valid": is_valid,
            "quality_score": quality_score,
            "issues": issues,
            "suggestions": suggestions
        }

    def _validate_vignette(self, vignette: Optional[str]) -> Tuple[List[str], List[str], int]:
        """Validate the clinical vignette."""
        issues = []
        suggestions = []
        deductions = 0

        if not vignette:
            issues.append("Missing vignette")
            return issues, suggestions, 40

        word_count = len(vignette.split())

        if word_count < self.QUALITY_RULES["vignette_min_words"]:
            issues.append(f"Vignette too short ({word_count} words, minimum {self.QUALITY_RULES['vignette_min_words']})")
            suggestions.append("Add more clinical detail to the vignette")
            deductions += 15

        if word_count > self.QUALITY_RULES["vignette_max_words"]:
            issues.append(f"Vignette too long ({word_count} words, maximum {self.QUALITY_RULES['vignette_max_words']})")
            suggestions.append("Consider condensing the vignette")
            deductions += 10

        # Check for question mark (lead-in)
        if "?" not in vignette:
            issues.append("Missing question lead-in")
            suggestions.append("Add a clear question at the end of the vignette")
            deductions += 10

        # Check for NBME format (age, gender in first sentence)
        first_sentence = vignette.split(".")[0].lower() if vignette else ""
        if not any(marker in first_sentence for marker in ["year", "month", "old", "man", "woman"]):
            suggestions.append("Consider starting with patient demographics (age, gender)")
            deductions += 5

        return issues, suggestions, deductions

    def _validate_choices(self, choices: Optional[List[str]]) -> Tuple[List[str], List[str], int]:
        """Validate answer choices."""
        issues = []
        suggestions = []
        deductions = 0

        if not choices:
            issues.append("Missing answer choices")
            return issues, suggestions, 40

        if len(choices) != self.QUALITY_RULES["required_choices"]:
            issues.append(f"Wrong number of choices ({len(choices)}, expected {self.QUALITY_RULES['required_choices']})")
            deductions += 20

        # Check for duplicates
        unique_choices = set(c.lower().strip() for c in choices)
        if len(unique_choices) < len(choices):
            issues.append("Duplicate answer choices detected")
            deductions += 15

        # Check choice length
        for i, choice in enumerate(choices):
            if len(choice.strip()) < 2:
                issues.append(f"Choice {chr(65 + i)} is too short")
                deductions += 5

        return issues, suggestions, deductions

    def _validate_explanation(self, explanation: any) -> Tuple[List[str], List[str], int]:
        """Validate the explanation structure."""
        issues = []
        suggestions = []
        deductions = 0

        if not explanation:
            issues.append("Missing explanation")
            suggestions.append("Add a structured explanation with clinical reasoning")
            return issues, suggestions, 30

        # Check if it's a structured explanation (dict) vs plain text
        if isinstance(explanation, str):
            issues.append("Explanation is plain text, not structured")
            suggestions.append("Convert to structured format with principle, clinical_reasoning, etc.")
            deductions += 15
            return issues, suggestions, deductions

        if isinstance(explanation, dict):
            # Check required fields
            required_fields = ["principle", "clinical_reasoning", "correct_answer_explanation"]
            for field in required_fields:
                if field not in explanation or not explanation[field]:
                    issues.append(f"Missing explanation field: {field}")
                    deductions += 5

            # Check for distractor explanations
            if "distractor_explanations" not in explanation:
                issues.append("Missing distractor explanations")
                suggestions.append("Add explanations for why each wrong answer is incorrect")
                deductions += 10

        return issues, suggestions, deductions

    def batch_validate_questions(
        self,
        question_ids: Optional[List[str]] = None,
        sample_size: Optional[int] = None,
        log_results: bool = True
    ) -> Dict:
        """
        Validate multiple questions.

        Args:
            question_ids: Specific question IDs to validate. If None, samples from DB.
            sample_size: Number of questions to sample if question_ids is None.
            log_results: Whether to log results to the quality log table.

        Returns:
            Summary of validation results
        """
        # Get questions to validate
        if question_ids:
            questions = self.db.query(Question).filter(Question.id.in_(question_ids)).all()
        else:
            query = self.db.query(Question).filter(Question.rejected == False)
            if sample_size:
                questions = query.order_by(func.random()).limit(sample_size).all()
            else:
                questions = query.limit(100).all()  # Default limit

        results = {
            "validated": 0,
            "passed": 0,
            "failed": 0,
            "needs_improvement": 0,
            "average_score": 0,
            "details": []
        }

        total_score = 0

        for question in questions:
            validation = self.validate_question(question.id)
            results["validated"] += 1
            total_score += validation["quality_score"]

            if validation["is_valid"]:
                results["passed"] += 1
            else:
                results["failed"] += 1

            if validation["quality_score"] < 80:
                results["needs_improvement"] += 1

            results["details"].append(validation)

            # Log results if requested
            if log_results:
                self._log_quality_result(question.id, validation)

        if results["validated"] > 0:
            results["average_score"] = round(total_score / results["validated"], 2)

        return results

    def _log_quality_result(self, question_id: str, validation: Dict):
        """Log quality validation result to database."""
        log = ExplanationQualityLog(
            question_id=question_id,
            quality_score=validation["quality_score"],
            issues_found=validation["issues"],
            validated_at=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()

    def get_coverage_report(self) -> Dict:
        """
        Generate a test coverage report.

        Returns:
            Coverage report with overall stats and per-module breakdown
        """
        try:
            # Run pytest with coverage
            result = subprocess.run(
                ["pytest", "tests/", "--cov=app", "--cov-report=json", "-q"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/
            )

            # Try to parse coverage.json
            coverage_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "coverage.json"
            )

            if os.path.exists(coverage_file):
                with open(coverage_file, "r") as f:
                    coverage_data = json.load(f)

                return {
                    "status": "success",
                    "overall_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                    "files": coverage_data.get("files", {}),
                    "generated_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "no_report",
                    "message": "Coverage report not generated",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }

        except FileNotFoundError:
            return {
                "status": "error",
                "message": "pytest not found. Make sure pytest and pytest-cov are installed."
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_quality_overview(self) -> Dict:
        """
        Get an overview of question quality across the database.

        Returns:
            Quality overview with counts and scores
        """
        # Total questions
        total = self.db.query(Question).count()
        active = self.db.query(Question).filter(Question.rejected == False).count()

        # Questions with structured explanations
        structured = 0
        with_distractors = 0
        without_explanation = 0

        questions = self.db.query(Question).filter(Question.rejected == False).all()

        for q in questions:
            if q.explanation is None:
                without_explanation += 1
            elif isinstance(q.explanation, dict):
                structured += 1
                if "distractor_explanations" in q.explanation:
                    with_distractors += 1
            elif isinstance(q.explanation, str):
                # Plain text explanation
                pass

        # Recent quality logs
        recent_logs = self.db.query(ExplanationQualityLog).order_by(
            ExplanationQualityLog.validated_at.desc()
        ).limit(100).all()

        avg_recent_score = 0
        if recent_logs:
            avg_recent_score = sum(log.quality_score or 0 for log in recent_logs) / len(recent_logs)

        # Calculate overall quality score
        quality_score = self._calculate_overall_quality_score(
            total=active,
            structured=structured,
            with_distractors=with_distractors
        )

        return {
            "total_questions": total,
            "active_questions": active,
            "with_explanation": active - without_explanation,
            "without_explanation": without_explanation,
            "structured_explanations": structured,
            "with_distractor_explanations": with_distractors,
            "quality_score": round(quality_score, 1),
            "average_recent_validation_score": round(avg_recent_score, 1),
            "recent_validations": len(recent_logs),
            "generated_at": datetime.utcnow().isoformat()
        }

    def _calculate_overall_quality_score(
        self,
        total: int,
        structured: int,
        with_distractors: int
    ) -> float:
        """Calculate overall quality score (0-100)."""
        if total == 0:
            return 0

        # Weights: 40% structured, 40% distractors, 20% coverage
        structured_score = (structured / total) * 40
        distractor_score = (with_distractors / total) * 40
        coverage_score = (min(structured, total) / total) * 20

        return structured_score + distractor_score + coverage_score

    def run_test_suite(self, test_path: Optional[str] = None) -> Dict:
        """
        Run the test suite and return results.

        Args:
            test_path: Optional path to specific test file or directory

        Returns:
            Test suite results
        """
        try:
            cmd = ["pytest", "-v", "--tb=short"]
            if test_path:
                cmd.append(test_path)
            else:
                cmd.append("tests/")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                timeout=300  # 5 minute timeout
            )

            # Parse output
            lines = result.stdout.split("\n")
            passed = sum(1 for line in lines if " PASSED" in line)
            failed = sum(1 for line in lines if " FAILED" in line)
            errors = sum(1 for line in lines if " ERROR" in line)

            return {
                "status": "completed",
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "exit_code": result.returncode,
                "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
                "stderr": result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr,
                "ran_at": datetime.utcnow().isoformat()
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "Test suite timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_untested_modules(self) -> Dict:
        """
        Identify modules that lack test coverage.

        Returns:
            List of modules without corresponding tests
        """
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        app_dir = os.path.join(backend_dir, "app")
        tests_dir = os.path.join(backend_dir, "tests")

        untested = {
            "routers": [],
            "services": [],
            "models": []
        }

        # Check routers
        routers_dir = os.path.join(app_dir, "routers")
        if os.path.exists(routers_dir):
            for filename in os.listdir(routers_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    module_name = filename[:-3]
                    test_file = f"test_{module_name}.py"
                    if not os.path.exists(os.path.join(tests_dir, test_file)):
                        untested["routers"].append(module_name)

        # Check services
        services_dir = os.path.join(app_dir, "services")
        if os.path.exists(services_dir):
            for filename in os.listdir(services_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    module_name = filename[:-3]
                    test_file = f"test_{module_name}.py"
                    if not os.path.exists(os.path.join(tests_dir, test_file)):
                        untested["services"].append(module_name)

        return {
            "untested_modules": untested,
            "total_untested": (
                len(untested["routers"]) +
                len(untested["services"]) +
                len(untested["models"])
            ),
            "generated_at": datetime.utcnow().isoformat()
        }
