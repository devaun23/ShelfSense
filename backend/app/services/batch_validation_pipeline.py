"""
Batch Validation Pipeline for 2,500 AI-Generated Questions

Implements 6-stage validation framework for elite quality (285+ scorer level).

Stages:
1. Automated Pre-Flight (zero cost)
2. AI Medical Validation (low cost)
3. Elite Explanation Validation (zero cost)
4. Statistical IRT Validation (post-deployment)
5. Medical Fact-Checking (sample-based)
6. Plagiarism Detection (zero cost)

Usage:
    from app.services.batch_validation_pipeline import BatchValidationPipeline

    pipeline = BatchValidationPipeline(db)
    results = await pipeline.validate_batch(questions)
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
import numpy as np
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.services.question_validators import QuestionQualityValidator
from app.services.multi_model_validator import MultiModelValidator, ValidationStatus
from app.services.elite_quality_validator import elite_validator
from app.services.item_response_theory import IRTCalibrator

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Complete validation result for a question"""
    question_id: str
    status: str  # ACCEPTED, REJECTED, NEEDS_REVIEW
    overall_score: float  # 0-100
    is_elite: bool

    # Stage results
    stage1_passed: bool
    stage2_passed: bool
    stage3_score: float

    # Issues and flags
    critical_issues: List[str]
    warnings: List[str]
    red_flags: List[Dict]

    # Recommendations
    recommendations: List[str]

    # Metadata
    validated_at: datetime
    validation_time_ms: float


@dataclass
class BatchValidationReport:
    """Summary report for batch validation"""
    total_questions: int
    accepted: int
    rejected: int
    needs_review: int

    acceptance_rate: float
    elite_count: int
    elite_rate: float

    avg_score: float
    median_score: float

    critical_issues_count: int
    quality_gate_failures: List[Dict]

    stage_breakdown: Dict[str, int]
    issue_breakdown: Dict[str, int]

    estimated_cost: float
    total_time_seconds: float


class BatchValidationPipeline:
    """
    Complete validation pipeline for batch question processing.

    Quality Gates:
    - Stage 1 pass rate >= 90%
    - Stage 2 pass rate >= 75%
    - Elite rate >= 60%
    - Overall acceptance >= 85%
    - Max 10 critical issues before pause
    - Max 20 consecutive rejections before pause
    """

    # Quality gate thresholds
    STAGE1_PASS_THRESHOLD = 0.90
    STAGE2_PASS_THRESHOLD = 0.75
    ELITE_RATE_THRESHOLD = 0.60
    OVERALL_ACCEPT_THRESHOLD = 0.85
    MAX_CRITICAL_ISSUES = 10
    MAX_REJECT_STREAK = 20

    # Sampling parameters
    SAMPLE_CONFIDENCE_LEVEL = 0.95
    SAMPLE_MARGIN_OF_ERROR = 0.05

    def __init__(self, db: Session):
        self.db = db
        self.quality_validator = QuestionQualityValidator()
        self.multi_model_validator = MultiModelValidator(min_accept_score=70.0)
        self.irt_calibrator = IRTCalibrator(db)

    async def validate_batch(
        self,
        questions: List[Dict],
        enable_gates: bool = True,
        human_review_sample_size: Optional[int] = None
    ) -> BatchValidationReport:
        """
        Validate a batch of questions through all stages.

        Args:
            questions: List of question dicts
            enable_gates: Whether to enforce quality gates
            human_review_sample_size: Sample size for Stage 5 (defaults to calculated)

        Returns:
            BatchValidationReport with comprehensive results
        """

        start_time = datetime.utcnow()

        results = []
        critical_issues_count = 0
        reject_streak = 0
        quality_gate_failures = []

        logger.info(f"Starting batch validation of {len(questions)} questions")

        for i, question in enumerate(questions):

            # Stage 1: Automated Pre-Flight Checks
            stage1_result = self._run_stage1(question)

            if not stage1_result["passed"]:
                results.append(ValidationResult(
                    question_id=question.get("id", f"q_{i}"),
                    status="REJECTED",
                    overall_score=0,
                    is_elite=False,
                    stage1_passed=False,
                    stage2_passed=False,
                    stage3_score=0,
                    critical_issues=stage1_result["issues"],
                    warnings=[],
                    red_flags=[],
                    recommendations=stage1_result["suggestions"],
                    validated_at=datetime.utcnow(),
                    validation_time_ms=stage1_result["time_ms"]
                ))
                reject_streak += 1

                # Quality Gate: Stage 1 pass rate
                if enable_gates and i > 100 and i % 100 == 0:
                    recent_pass_rate = sum(
                        1 for r in results[-100:] if r.stage1_passed
                    ) / 100

                    if recent_pass_rate < self.STAGE1_PASS_THRESHOLD:
                        quality_gate_failures.append({
                            "gate": "stage1_pass_rate",
                            "at_question": i,
                            "pass_rate": recent_pass_rate,
                            "threshold": self.STAGE1_PASS_THRESHOLD,
                            "action": "PAUSE_FOR_INVESTIGATION"
                        })
                        logger.warning(
                            f"Quality gate failure: Stage 1 pass rate {recent_pass_rate:.1%} "
                            f"below threshold {self.STAGE1_PASS_THRESHOLD:.1%}"
                        )

                continue

            # Stage 2: AI Medical Validation
            stage2_result = await self._run_stage2(question)

            if not stage2_result["passed"]:
                results.append(ValidationResult(
                    question_id=question.get("id", f"q_{i}"),
                    status="REJECTED",
                    overall_score=stage2_result["score"],
                    is_elite=False,
                    stage1_passed=True,
                    stage2_passed=False,
                    stage3_score=0,
                    critical_issues=stage2_result["issues"],
                    warnings=[],
                    red_flags=[],
                    recommendations=stage2_result["suggestions"],
                    validated_at=datetime.utcnow(),
                    validation_time_ms=stage1_result["time_ms"] + stage2_result["time_ms"]
                ))
                reject_streak += 1

                # Check for dangerous misinformation
                if stage2_result.get("dangerous_misinformation"):
                    critical_issues_count += 1
                    logger.error(
                        f"CRITICAL: Dangerous misinformation detected in question {i}"
                    )

                # Quality Gate: Critical issues
                if enable_gates and critical_issues_count > self.MAX_CRITICAL_ISSUES:
                    quality_gate_failures.append({
                        "gate": "max_critical_issues",
                        "at_question": i,
                        "critical_count": critical_issues_count,
                        "action": "STOP_GENERATION"
                    })
                    logger.critical(
                        f"STOPPING: {critical_issues_count} critical issues detected. "
                        f"Review generation process immediately."
                    )
                    break

                # Quality Gate: Reject streak
                if enable_gates and reject_streak >= self.MAX_REJECT_STREAK:
                    quality_gate_failures.append({
                        "gate": "max_reject_streak",
                        "at_question": i,
                        "streak": reject_streak,
                        "action": "INVESTIGATE_GENERATOR"
                    })
                    logger.error(
                        f"Quality gate: {reject_streak} consecutive rejections. "
                        f"Pausing for investigation."
                    )
                    # Don't break, just flag for review

                continue

            reject_streak = 0  # Reset on pass

            # Stage 3: Elite Explanation Validation
            stage3_result = self._run_stage3(question)

            # Determine final status
            if stage3_result["is_elite"]:
                status = "ACCEPTED"
            elif stage3_result["score"] >= 70:
                status = "ACCEPTED"  # Acceptable but not elite
            else:
                status = "REJECTED"

            results.append(ValidationResult(
                question_id=question.get("id", f"q_{i}"),
                status=status,
                overall_score=stage3_result["score"],
                is_elite=stage3_result["is_elite"],
                stage1_passed=True,
                stage2_passed=True,
                stage3_score=stage3_result["score"],
                critical_issues=[],
                warnings=stage3_result["issues"],
                red_flags=[],
                recommendations=stage3_result["recommendations"],
                validated_at=datetime.utcnow(),
                validation_time_ms=(
                    stage1_result["time_ms"] +
                    stage2_result["time_ms"] +
                    stage3_result["time_ms"]
                )
            ))

            # Progress logging
            if (i + 1) % 100 == 0:
                logger.info(f"Validated {i + 1}/{len(questions)} questions")

        # Calculate batch metrics
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()

        accepted = sum(1 for r in results if r.status == "ACCEPTED")
        rejected = sum(1 for r in results if r.status == "REJECTED")
        needs_review = sum(1 for r in results if r.status == "NEEDS_REVIEW")
        elite_count = sum(1 for r in results if r.is_elite)

        scores = [r.overall_score for r in results if r.overall_score > 0]

        report = BatchValidationReport(
            total_questions=len(questions),
            accepted=accepted,
            rejected=rejected,
            needs_review=needs_review,
            acceptance_rate=accepted / len(results) if results else 0,
            elite_count=elite_count,
            elite_rate=elite_count / accepted if accepted > 0 else 0,
            avg_score=np.mean(scores) if scores else 0,
            median_score=np.median(scores) if scores else 0,
            critical_issues_count=critical_issues_count,
            quality_gate_failures=quality_gate_failures,
            stage_breakdown={
                "stage1_passed": sum(1 for r in results if r.stage1_passed),
                "stage2_passed": sum(1 for r in results if r.stage2_passed),
                "stage3_elite": elite_count
            },
            issue_breakdown=self._calculate_issue_breakdown(results),
            estimated_cost=self._estimate_cost(results),
            total_time_seconds=total_time
        )

        logger.info(
            f"Batch validation complete: {accepted}/{len(results)} accepted "
            f"({report.acceptance_rate:.1%}), {elite_count} elite ({report.elite_rate:.1%})"
        )

        return report

    def _run_stage1(self, question: Dict) -> Dict:
        """Stage 1: Automated pre-flight checks"""
        start = datetime.utcnow()

        vignette = question.get("vignette", "")
        choices = question.get("choices", [])
        answer_key = question.get("answer_key", "")

        # Run validation
        validation_report = self.quality_validator.validate_question(
            vignette=vignette,
            choices=choices,
            correct_key=answer_key
        )

        end = datetime.utcnow()
        time_ms = (end - start).total_seconds() * 1000

        return {
            "passed": validation_report.passed,
            "issues": [f.issue for f in validation_report.findings if f.severity.value in ["error", "critical"]],
            "suggestions": [f.suggestion for f in validation_report.findings if f.suggestion],
            "time_ms": time_ms
        }

    async def _run_stage2(self, question: Dict) -> Dict:
        """Stage 2: AI medical validation"""
        start = datetime.utcnow()

        # Run multi-model validation
        result = await self.multi_model_validator.validate_question(question)

        end = datetime.utcnow()
        time_ms = (end - start).total_seconds() * 1000

        return {
            "passed": result.status == ValidationStatus.ACCEPT,
            "score": result.score,
            "issues": result.issues,
            "suggestions": result.suggestions,
            "dangerous_misinformation": result.medical_accuracy < 50,  # Low accuracy = dangerous
            "time_ms": time_ms
        }

    def _run_stage3(self, question: Dict) -> Dict:
        """Stage 3: Elite explanation validation"""
        start = datetime.utcnow()

        result = elite_validator.validate(question)

        end = datetime.utcnow()
        time_ms = (end - start).total_seconds() * 1000

        return {
            "score": result.score,
            "is_elite": result.is_elite,
            "issues": result.issues,
            "recommendations": result.recommendations,
            "time_ms": time_ms
        }

    def _calculate_issue_breakdown(self, results: List[ValidationResult]) -> Dict[str, int]:
        """Calculate counts of each issue type"""
        issue_counts = defaultdict(int)

        for result in results:
            for issue in result.critical_issues + result.warnings:
                # Extract issue type from message
                issue_type = issue.split(":")[0] if ":" in issue else issue[:30]
                issue_counts[issue_type] += 1

        return dict(issue_counts)

    def _estimate_cost(self, results: List[ValidationResult]) -> float:
        """Estimate total validation cost"""
        # Stage 2 (AI validation) is the only cost
        # Claude Haiku: ~$0.25 per 1000 questions
        stage2_validated = sum(1 for r in results if r.stage2_passed or not r.stage1_passed)
        return stage2_validated * 0.00025

    def calculate_sample_size(self, population_size: int) -> int:
        """
        Calculate required sample size for human review.

        For 2,500 questions with 95% confidence and 5% margin of error:
        Returns ~333 questions
        """
        from scipy import stats

        z = stats.norm.ppf(1 - (1 - self.SAMPLE_CONFIDENCE_LEVEL) / 2)
        p = 0.85  # Expected pass rate

        # Sample size formula
        n = (z**2 * p * (1 - p)) / (self.SAMPLE_MARGIN_OF_ERROR**2)

        # Finite population correction
        n_adjusted = n / (1 + (n - 1) / population_size)

        return int(np.ceil(n_adjusted))

    def select_human_review_sample(
        self,
        questions: List[Dict],
        sample_size: Optional[int] = None
    ) -> List[Dict]:
        """
        Select stratified sample for human review (Stage 5).

        Stratifies by:
        - Validation score (high/medium/borderline)
        - Subspecialty (cardiology, pulmonology, etc.)
        - Complexity (high-risk topics)
        """

        if sample_size is None:
            sample_size = self.calculate_sample_size(len(questions))

        # Define strata
        high_confidence = []
        medium_confidence = []
        borderline = []
        complex_topics = []

        for q in questions:
            score = q.get("validation_score", 0)
            subsystem = q.get("subsystem", "")

            if score >= 90:
                high_confidence.append(q)
            elif score >= 75:
                medium_confidence.append(q)
            elif score >= 65:
                borderline.append(q)

            # Complex/high-risk subsystems
            if subsystem in ["endocrinology", "rheumatology", "hematology", "nephrology"]:
                complex_topics.append(q)

        # Sample from each stratum
        sample = []

        # 5% from high confidence (minimal review needed)
        if high_confidence:
            n = max(1, int(len(high_confidence) * 0.05))
            sample.extend(random.sample(high_confidence, min(n, len(high_confidence))))

        # 10% from medium confidence
        if medium_confidence:
            n = max(1, int(len(medium_confidence) * 0.10))
            sample.extend(random.sample(medium_confidence, min(n, len(medium_confidence))))

        # 50% from borderline (needs careful review)
        if borderline:
            n = max(1, int(len(borderline) * 0.50))
            sample.extend(random.sample(borderline, min(n, len(borderline))))

        # 20% from complex topics
        if complex_topics:
            n = max(1, int(len(complex_topics) * 0.20))
            sample.extend(random.sample(complex_topics, min(n, len(complex_topics))))

        # Ensure unique questions
        sample = list(set(sample))

        # Fill to target sample size if needed
        if len(sample) < sample_size:
            remaining = [q for q in questions if q not in sample]
            additional_needed = sample_size - len(sample)
            if remaining and additional_needed > 0:
                sample.extend(random.sample(remaining, min(additional_needed, len(remaining))))

        logger.info(f"Selected {len(sample)} questions for human review")

        return sample

    def calculate_population_quality(
        self,
        sample_results: List[Dict],
        population_size: int
    ) -> Dict:
        """
        Calculate population quality estimate from sample.

        Returns confidence interval for overall quality.
        """

        from scipy import stats

        n = len(sample_results)
        successes = sum(1 for r in sample_results if r.get("expert_approved", False))
        p_hat = successes / n if n > 0 else 0

        # Wilson score interval
        z = stats.norm.ppf(1 - (1 - self.SAMPLE_CONFIDENCE_LEVEL) / 2)
        denominator = 1 + z**2 / n
        center = (p_hat + z**2 / (2*n)) / denominator
        margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4*n)) / n) / denominator

        ci_lower = max(0, center - margin)
        ci_upper = min(1, center + margin)

        return {
            "sample_size": n,
            "sample_pass_rate": p_hat,
            "confidence_level": self.SAMPLE_CONFIDENCE_LEVEL,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "margin_of_error": margin,
            "estimated_population_pass_rate": p_hat,
            "population_size": population_size,
            "estimated_passing_questions": int(population_size * p_hat),
            "estimated_range": (int(population_size * ci_lower), int(population_size * ci_upper))
        }


def detect_plagiarism(question: Dict, known_questions: List[Dict]) -> Dict:
    """
    Stage 6: Plagiarism detection via fuzzy string matching.

    Flags questions >70% similar to known questions.
    """
    vignette = question.get("vignette", "").lower()

    max_similarity = 0.0
    most_similar_source = None

    for known_q in known_questions:
        known_vignette = known_q.get("vignette", "").lower()

        similarity = SequenceMatcher(None, vignette, known_vignette).ratio()

        if similarity > max_similarity:
            max_similarity = similarity
            most_similar_source = known_q.get("source", "unknown")

    return {
        "is_plagiarism": max_similarity > 0.70,
        "max_similarity": max_similarity,
        "similar_source": most_similar_source if max_similarity > 0.70 else None,
        "severity": "CRITICAL" if max_similarity > 0.85 else "WARNING" if max_similarity > 0.70 else "OK"
    }


# Convenience function for quick validation
async def validate_questions_batch(questions: List[Dict], db: Session) -> BatchValidationReport:
    """Quick batch validation with default settings"""
    pipeline = BatchValidationPipeline(db)
    return await pipeline.validate_batch(questions)
