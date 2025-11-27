"""
Quality Validation Service for AI-Generated Questions

Provides automated validation of USMLE Step 2 CK questions against:
- Structural requirements (format, length, completeness)
- NBME Gold Book compliance (10 principles)
- Medical content quality signals

Quality Score Thresholds:
- >= 80%: Auto-pass, add to question bank
- 60-79%: Flag for self-review
- < 60%: Auto-regenerate (max 3 attempts per topic)
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of question validation."""
    is_valid: bool
    quality_score: float
    structural_score: float
    nbme_score: float
    content_score: float
    issues: List[str]
    warnings: List[str]
    recommendation: str  # "auto_pass", "review", "regenerate"


@dataclass
class StructuralCheck:
    """Individual structural validation check."""
    name: str
    passed: bool
    message: str
    weight: float = 1.0


class QuestionValidator:
    """Validates AI-generated questions for quality and compliance."""

    # NBME compliance criteria weights (sum to 100)
    NBME_WEIGHTS = {
        "cover_options": 10,
        "vignette_template": 10,
        "single_best_answer": 10,
        "all_facts_in_stem": 10,
        "classic_presentation": 10,
        "homogeneous_options": 10,
        "no_trivia": 10,
        "no_test_tricks": 10,
        "patients_reliable": 10,
        "important_concept": 10,
    }

    # Quality thresholds
    AUTO_PASS_THRESHOLD = 80
    REVIEW_THRESHOLD = 60

    def __init__(self):
        self.checks_run = []
        self.issues = []
        self.warnings = []

    def validate_question(self, question_data: Dict) -> ValidationResult:
        """
        Run full validation on a question.

        Args:
            question_data: Dict with vignette, choices, answer_key, explanation, etc.

        Returns:
            ValidationResult with scores and recommendation
        """
        self.checks_run = []
        self.issues = []
        self.warnings = []

        # 1. Structural validation (must pass all)
        structural_score, structural_passed = self._validate_structure(question_data)

        if not structural_passed:
            return ValidationResult(
                is_valid=False,
                quality_score=0,
                structural_score=structural_score,
                nbme_score=0,
                content_score=0,
                issues=self.issues,
                warnings=self.warnings,
                recommendation="regenerate"
            )

        # 2. NBME compliance scoring
        nbme_score = self._score_nbme_compliance(question_data)

        # 3. Content quality signals
        content_score = self._score_content_quality(question_data)

        # Calculate weighted quality score
        quality_score = (
            structural_score * 0.20 +
            nbme_score * 0.50 +
            content_score * 0.30
        )

        # Determine recommendation
        if quality_score >= self.AUTO_PASS_THRESHOLD:
            recommendation = "auto_pass"
        elif quality_score >= self.REVIEW_THRESHOLD:
            recommendation = "review"
        else:
            recommendation = "regenerate"

        return ValidationResult(
            is_valid=quality_score >= self.REVIEW_THRESHOLD,
            quality_score=round(quality_score, 1),
            structural_score=round(structural_score, 1),
            nbme_score=round(nbme_score, 1),
            content_score=round(content_score, 1),
            issues=self.issues,
            warnings=self.warnings,
            recommendation=recommendation
        )

    def _validate_structure(self, data: Dict) -> Tuple[float, bool]:
        """
        Validate structural requirements.

        Returns (score, all_passed) tuple.
        """
        checks = []

        # Check required fields
        required_fields = ["vignette", "choices", "answer_key"]
        for field in required_fields:
            if field not in data or not data[field]:
                checks.append(StructuralCheck(
                    name=f"has_{field}",
                    passed=False,
                    message=f"Missing required field: {field}",
                    weight=2.0
                ))
            else:
                checks.append(StructuralCheck(
                    name=f"has_{field}",
                    passed=True,
                    message=f"Has {field}",
                    weight=2.0
                ))

        # Check 5 answer choices
        choices = data.get("choices", [])
        has_5_choices = len(choices) == 5
        checks.append(StructuralCheck(
            name="five_choices",
            passed=has_5_choices,
            message="Has exactly 5 answer choices" if has_5_choices else f"Expected 5 choices, got {len(choices)}",
            weight=2.0
        ))

        # Check unique choices
        if choices:
            unique_choices = len(set(c.strip().lower() for c in choices))
            all_unique = unique_choices == len(choices)
            checks.append(StructuralCheck(
                name="unique_choices",
                passed=all_unique,
                message="All choices are unique" if all_unique else "Duplicate choices detected",
                weight=2.0
            ))

        # Check answer key validity
        answer_key = data.get("answer_key", "")
        valid_keys = ["A", "B", "C", "D", "E"]
        valid_answer = answer_key in valid_keys
        checks.append(StructuralCheck(
            name="valid_answer_key",
            passed=valid_answer,
            message=f"Valid answer key: {answer_key}" if valid_answer else f"Invalid answer key: {answer_key}",
            weight=2.0
        ))

        # Check vignette length (100-800 characters is ideal)
        vignette = data.get("vignette", "")
        vignette_len = len(vignette)
        good_length = 100 <= vignette_len <= 1000
        checks.append(StructuralCheck(
            name="vignette_length",
            passed=good_length,
            message=f"Vignette length: {vignette_len}" if good_length else f"Vignette length {vignette_len} outside ideal range (100-1000)",
            weight=1.0
        ))

        # Check for question mark in vignette (lead-in)
        has_question = "?" in vignette
        checks.append(StructuralCheck(
            name="has_lead_in",
            passed=has_question,
            message="Has lead-in question" if has_question else "Missing question mark in vignette",
            weight=1.5
        ))

        # Check for patient demographics at start
        has_demographics = self._check_demographics(vignette)
        checks.append(StructuralCheck(
            name="has_demographics",
            passed=has_demographics,
            message="Has patient demographics" if has_demographics else "Missing clear patient demographics",
            weight=1.0
        ))

        # Calculate score
        total_weight = sum(c.weight for c in checks)
        passed_weight = sum(c.weight for c in checks if c.passed)
        score = (passed_weight / total_weight) * 100 if total_weight > 0 else 0

        # Collect issues
        for check in checks:
            if not check.passed:
                self.issues.append(check.message)

        # Critical failures (must pass)
        critical_checks = ["has_vignette", "has_choices", "has_answer_key", "five_choices", "valid_answer_key"]
        all_critical_passed = all(
            c.passed for c in checks if c.name in critical_checks
        )

        return score, all_critical_passed

    def _check_demographics(self, vignette: str) -> bool:
        """Check if vignette starts with patient demographics."""
        # Common patterns: "A 45-year-old", "An 18-year-old", "A 3-month-old"
        age_pattern = r'\b(\d+[-\s]?(year|month|week|day)[-\s]?old)\b'
        gender_pattern = r'\b(male|female|man|woman|boy|girl)\b'

        first_100_chars = vignette[:150].lower()
        has_age = bool(re.search(age_pattern, first_100_chars, re.IGNORECASE))
        has_gender = bool(re.search(gender_pattern, first_100_chars))

        return has_age or has_gender

    def _score_nbme_compliance(self, data: Dict) -> float:
        """
        Score NBME Gold Book compliance.

        Checks 10 principles, returns 0-100 score.
        """
        vignette = data.get("vignette", "")
        choices = data.get("choices", [])
        explanation = data.get("explanation", {})

        scores = {}

        # 1. Cover the Options Rule - Question answerable without choices
        # Heuristic: vignette should end with a clear question, not depend on options
        has_clear_question = bool(re.search(r'\?\s*$', vignette.strip()))
        scores["cover_options"] = 100 if has_clear_question else 50

        # 2. Vignette Template - Age/Gender -> Setting -> Complaint -> Duration
        has_age = bool(re.search(r'\d+[-\s]?(year|month)', vignette, re.IGNORECASE))
        has_setting = any(s in vignette.lower() for s in ["emergency", "clinic", "hospital", "office", "icu"])
        has_complaint = any(c in vignette.lower() for c in ["presents with", "complains of", "brought in", "reports"])
        scores["vignette_template"] = sum([has_age * 40, has_setting * 30, has_complaint * 30])

        # 3. Single Best Answer - Check explanation mentions why one is clearly best
        if isinstance(explanation, dict):
            has_correct_explanation = bool(explanation.get("correct_answer_explanation", ""))
            scores["single_best_answer"] = 100 if has_correct_explanation else 60
        else:
            scores["single_best_answer"] = 70

        # 4. All Facts in Stem - Hard to validate automatically, give default
        # Check for explicit values (numbers, measurements)
        explicit_values = len(re.findall(r'\d+(?:\.\d+)?(?:\s*(?:mg|mL|mmHg|bpm|%|g/dL|mmol|U/L))?', vignette))
        scores["all_facts_in_stem"] = min(100, 50 + explicit_values * 5)

        # 5. Classic Presentation - No rare diseases mentioned
        rare_terms = ["rare", "unusual", "atypical", "uncommon", "zebra"]
        has_rare = any(term in vignette.lower() for term in rare_terms)
        scores["classic_presentation"] = 50 if has_rare else 100

        # 6. Homogeneous Options - All options should be same category
        # Heuristic: check if all start with similar words or patterns
        if choices:
            first_words = [c.split()[0] if c else "" for c in choices]
            # Remove letter prefix (A., B., etc.)
            cleaned = [re.sub(r'^[A-E][\.\)]\s*', '', c).split()[0].lower() if c else "" for c in choices]
            unique_starts = len(set(cleaned))
            # Fewer unique starts suggests more homogeneous options
            scores["homogeneous_options"] = 100 if unique_starts <= 3 else 70 if unique_starts == 4 else 50
        else:
            scores["homogeneous_options"] = 50

        # 7. No Trivia - Check for clinically relevant terms
        clinical_terms = ["treatment", "diagnosis", "management", "next step", "most likely", "appropriate"]
        has_clinical_focus = any(term in vignette.lower() for term in clinical_terms)
        scores["no_trivia"] = 100 if has_clinical_focus else 70

        # 8. No Test-Taking Tricks - Check for "always", "never", absolute terms
        trick_terms = [r'\balways\b', r'\bnever\b', r'\ball of the above\b', r'\bnone of the above\b']
        combined_text = vignette + " ".join(choices)
        has_tricks = any(re.search(term, combined_text, re.IGNORECASE) for term in trick_terms)
        scores["no_test_tricks"] = 50 if has_tricks else 100

        # 9. Patients Don't Lie - Clinical findings should be clear
        # Check for concrete exam findings
        exam_terms = ["temperature", "blood pressure", "heart rate", "respirator", "examination"]
        has_exam = any(term in vignette.lower() for term in exam_terms)
        scores["patients_reliable"] = 100 if has_exam else 70

        # 10. Important Concept - Check if explanation has principle
        if isinstance(explanation, dict) and explanation.get("principle"):
            scores["important_concept"] = 100
        elif isinstance(explanation, dict) and explanation.get("clinical_reasoning"):
            scores["important_concept"] = 80
        else:
            scores["important_concept"] = 60

        # Calculate weighted total
        total_score = sum(
            scores[key] * (self.NBME_WEIGHTS[key] / 100)
            for key in self.NBME_WEIGHTS
        )

        # Add warnings for low-scoring areas
        for key, score in scores.items():
            if score < 70:
                self.warnings.append(f"Low NBME compliance: {key} ({score}%)")

        return total_score

    def _score_content_quality(self, data: Dict) -> float:
        """
        Score content quality signals.

        Checks for:
        - Arrow notation (→) in explanations
        - Explicit thresholds with units
        - Distractor explanations
        - Clinical reasoning depth
        """
        explanation = data.get("explanation", {})
        vignette = data.get("vignette", "")
        scores = []

        # Check for arrow notation
        combined_text = str(explanation) + vignette
        arrow_count = combined_text.count("→") + combined_text.count("->")
        arrow_score = min(100, arrow_count * 20)  # 5 arrows = 100%
        scores.append(arrow_score)

        # Check for explicit thresholds
        threshold_pattern = r'[<>≥≤]\s*\d+|\d+\s*(?:mg|mcg|mL|mmHg|bpm|%|hours?|days?|g/dL)'
        threshold_count = len(re.findall(threshold_pattern, combined_text))
        threshold_score = min(100, threshold_count * 15)
        scores.append(threshold_score)

        # Check for distractor explanations
        if isinstance(explanation, dict):
            distractors = explanation.get("distractor_explanations", {})
            if distractors and len(distractors) >= 4:
                scores.append(100)
            elif distractors and len(distractors) >= 2:
                scores.append(70)
            else:
                scores.append(30)
        else:
            scores.append(30)

        # Check explanation completeness
        if isinstance(explanation, dict):
            expected_fields = ["type", "quick_answer", "principle", "clinical_reasoning",
                            "correct_answer_explanation"]
            present = sum(1 for f in expected_fields if explanation.get(f))
            completeness_score = (present / len(expected_fields)) * 100
            scores.append(completeness_score)
        else:
            scores.append(40)

        return sum(scores) / len(scores) if scores else 50


def validate_batch(questions: List[Dict]) -> Dict:
    """
    Validate a batch of questions and return summary statistics.

    Args:
        questions: List of question dicts to validate

    Returns:
        Dict with validation results and statistics
    """
    validator = QuestionValidator()
    results = []

    for i, q in enumerate(questions):
        try:
            result = validator.validate_question(q)
            results.append({
                "index": i,
                "question_id": q.get("id"),
                **asdict(result)
            })
        except Exception as e:
            logger.error(f"Validation error for question {i}: {e}")
            results.append({
                "index": i,
                "question_id": q.get("id"),
                "is_valid": False,
                "quality_score": 0,
                "issues": [str(e)],
                "recommendation": "regenerate"
            })

    # Calculate statistics
    total = len(results)
    auto_pass = sum(1 for r in results if r.get("recommendation") == "auto_pass")
    review = sum(1 for r in results if r.get("recommendation") == "review")
    regenerate = sum(1 for r in results if r.get("recommendation") == "regenerate")

    avg_score = sum(r.get("quality_score", 0) for r in results) / total if total else 0

    return {
        "total": total,
        "auto_pass": auto_pass,
        "review": review,
        "regenerate": regenerate,
        "auto_pass_rate": round(auto_pass / total * 100, 1) if total else 0,
        "average_quality_score": round(avg_score, 1),
        "results": results,
        "validated_at": datetime.utcnow().isoformat()
    }


def export_validation_report(results: Dict, format: str = "csv") -> str:
    """
    Export validation results to CSV or JSON for review.

    Args:
        results: Output from validate_batch()
        format: "csv" or "json"

    Returns:
        Formatted string
    """
    if format == "json":
        return json.dumps(results, indent=2, default=str)

    # CSV format
    lines = [
        "index,question_id,is_valid,quality_score,structural_score,nbme_score,content_score,recommendation,issues"
    ]

    for r in results.get("results", []):
        issues_str = "; ".join(r.get("issues", []))
        lines.append(
            f"{r.get('index', '')},{r.get('question_id', '')},"
            f"{r.get('is_valid', '')},"
            f"{r.get('quality_score', '')},"
            f"{r.get('structural_score', '')},"
            f"{r.get('nbme_score', '')},"
            f"{r.get('content_score', '')},"
            f"{r.get('recommendation', '')},"
            f"\"{issues_str}\""
        )

    return "\n".join(lines)
