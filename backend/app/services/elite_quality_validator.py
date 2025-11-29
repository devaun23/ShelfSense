"""
Rule-Based Elite Quality Validator for 285+ Caliber Explanations.

ZERO API COST - Pure Python logic using regex and string matching.

This validator checks explanations against criteria that differentiate
252 scorers from 285+ scorers:

1. Pattern Recognition - First-sentence diagnosis teaching
2. Mechanism Depth - Explicit causal chains with arrows
3. Distractor Psychology - Why wrong answers are TEMPTING
4. Threshold Explicitness - Numbers with normal ranges
5. Brevity - Concise, memorable core message

Usage:
    from app.services.elite_quality_validator import elite_validator

    result = elite_validator.validate(question_dict)
    print(f"Elite Score: {result['score']}")
    print(f"Issues: {result['issues']}")
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EliteQualityResult:
    """Result of elite quality validation."""
    score: float  # 0-100
    dimensions: Dict[str, float]  # Individual dimension scores (0-1)
    issues: List[str]  # Specific problems found
    strengths: List[str]  # What's good
    is_elite: bool  # Score >= 85
    recommendations: List[str]  # How to improve


class EliteQualityValidator:
    """
    Rule-based validator for 285+ caliber USMLE explanations.

    This validator uses no AI - it's pure Python pattern matching.
    It checks for the structural and stylistic elements that
    differentiate elite-level explanations from average ones.

    The 285+ Difference:
    - A 252 scorer knows the answer
    - A 285 scorer knows WHY each wrong answer is tempting

    This validator ensures explanations teach at the 285+ level.
    """

    # Thresholds
    ELITE_THRESHOLD = 85.0
    ACCEPTABLE_THRESHOLD = 70.0

    # Maximum words for quick_answer
    MAX_QUICK_ANSWER_WORDS = 30

    # Minimum mechanism arrows expected
    MIN_MECHANISM_ARROWS = 2

    # Pattern for normal range notation: (normal X-Y) or (nl X-Y)
    NORMAL_RANGE_PATTERN = re.compile(
        r'\((?:normal|nl|ref|range)[:\s]*[\d\.<>\-\s]+[^)]*\)',
        re.IGNORECASE
    )

    # Pattern for clinical values (numbers followed by units or context)
    CLINICAL_VALUE_PATTERN = re.compile(
        r'\b\d+\.?\d*\s*(?:mg|mL|g|L|mmHg|bpm|%|mEq|mmol|U|IU|ng|pg|mcg|kg|cm|mm|sec|min|hr|days?|weeks?|months?|years?|°[CF])\b',
        re.IGNORECASE
    )

    # Patterns indicating distractor psychology ("tempting because", "commonly confused")
    DISTRACTOR_PSYCHOLOGY_PATTERNS = [
        re.compile(r'tempting\s+because', re.IGNORECASE),
        re.compile(r'commonly\s+(?:confused|mistaken)', re.IGNORECASE),
        re.compile(r'students?\s+(?:often|commonly|frequently)\s+(?:choose|pick|select)', re.IGNORECASE),
        re.compile(r'trap\s+(?:answer|choice)', re.IGNORECASE),
        re.compile(r'might\s+(?:seem|appear|look)\s+(?:correct|right)', re.IGNORECASE),
        re.compile(r'if\s+(?:you|one)\s+(?:forgot|missed|overlooked)', re.IGNORECASE),
    ]

    # Arrow patterns for mechanism chains
    ARROW_PATTERNS = ['→', '->', '➔', '➜', '⟶', '⇒', 'leads to', 'causes', 'results in']

    def validate(self, question: Dict[str, Any]) -> EliteQualityResult:
        """
        Validate a question's explanation against 285+ caliber criteria.

        Args:
            question: Dict with 'vignette', 'explanation', 'choices', etc.

        Returns:
            EliteQualityResult with score, dimensions, issues, and recommendations
        """
        explanation = question.get("explanation", {})

        # Handle string explanations (legacy format)
        if isinstance(explanation, str):
            explanation = {"raw_text": explanation}

        dimensions = {}
        issues = []
        strengths = []
        recommendations = []

        # 1. Pattern Recognition (20%)
        score, issue, strength = self._check_pattern_recognition(
            question.get("vignette", ""),
            explanation.get("quick_answer", "")
        )
        dimensions["pattern_recognition"] = score
        if issue:
            issues.append(issue)
        if strength:
            strengths.append(strength)

        # 2. Mechanism Depth (25%)
        score, issue, strength = self._check_mechanism_chains(explanation)
        dimensions["mechanism_depth"] = score
        if issue:
            issues.append(issue)
        if strength:
            strengths.append(strength)

        # 3. Distractor Coverage (20%)
        score, issue_list = self._check_distractor_coverage(explanation)
        dimensions["distractor_coverage"] = score
        issues.extend(issue_list)

        # 4. Distractor Psychology (15%)
        score, issue, strength = self._check_distractor_psychology(explanation)
        dimensions["distractor_psychology"] = score
        if issue:
            issues.append(issue)
        if strength:
            strengths.append(strength)

        # 5. Threshold Explicitness (10%)
        score, issue, strength = self._check_threshold_explicitness(explanation)
        dimensions["threshold_explicitness"] = score
        if issue:
            issues.append(issue)
        if strength:
            strengths.append(strength)

        # 6. Brevity (10%)
        score, issue = self._check_brevity(explanation)
        dimensions["brevity"] = score
        if issue:
            issues.append(issue)

        # Calculate weighted overall score
        weights = {
            "pattern_recognition": 0.20,
            "mechanism_depth": 0.25,
            "distractor_coverage": 0.20,
            "distractor_psychology": 0.15,
            "threshold_explicitness": 0.10,
            "brevity": 0.10
        }

        overall_score = sum(
            dimensions[dim] * weight
            for dim, weight in weights.items()
        ) * 100

        # Generate recommendations based on issues
        recommendations = self._generate_recommendations(dimensions, issues)

        return EliteQualityResult(
            score=round(overall_score, 1),
            dimensions=dimensions,
            issues=issues,
            strengths=strengths,
            is_elite=overall_score >= self.ELITE_THRESHOLD,
            recommendations=recommendations
        )

    def _check_pattern_recognition(
        self,
        vignette: str,
        quick_answer: str
    ) -> Tuple[float, Optional[str], Optional[str]]:
        """
        Check if quick_answer teaches first-sentence pattern recognition.

        A 285+ explanation tells you what to notice in the FIRST sentence
        of the vignette that points to the diagnosis.
        """
        if not quick_answer:
            return 0.0, "Missing quick_answer field", None

        # Extract key terms from first sentence of vignette
        first_sentence = vignette.split('.')[0] if vignette else ""
        first_sentence_lower = first_sentence.lower()

        # Check if quick_answer references key clinical terms from vignette
        quick_answer_lower = quick_answer.lower()

        # Look for overlap in clinical terms
        clinical_terms = re.findall(r'\b[a-z]+(?:emia|itis|osis|pathy|algia|uria|pnea|trophy|plasia|oma)\b', first_sentence_lower)
        symptom_terms = re.findall(r'\b(?:pain|fever|cough|swelling|weakness|fatigue|rash|bleeding|vomiting|diarrhea|dyspnea|chest|abdominal)\b', first_sentence_lower)

        relevant_terms = clinical_terms + symptom_terms

        matches = sum(1 for term in relevant_terms if term in quick_answer_lower)

        if matches >= 2:
            return 1.0, None, "Quick answer references key presenting symptoms"
        elif matches >= 1:
            return 0.7, None, "Quick answer mentions some presenting features"
        elif len(quick_answer) > 20:
            return 0.4, "Quick answer doesn't reference first-sentence cues", None
        else:
            return 0.2, "Quick answer lacks pattern recognition teaching", None

    def _check_mechanism_chains(
        self,
        explanation: Dict[str, Any]
    ) -> Tuple[float, Optional[str], Optional[str]]:
        """
        Check for explicit mechanism chains with arrows.

        285+ explanations use: cause → pathology → finding → management
        """
        # Combine relevant text fields
        text_fields = [
            explanation.get("clinical_reasoning", ""),
            explanation.get("correct_answer_explanation", ""),
            explanation.get("principle", ""),
            str(explanation.get("deep_dive", ""))
        ]
        combined_text = " ".join(str(t) for t in text_fields)

        # Count arrows
        arrow_count = 0
        for pattern in self.ARROW_PATTERNS:
            arrow_count += combined_text.count(pattern)

        if arrow_count >= 4:
            return 1.0, None, f"Excellent mechanism chains ({arrow_count} arrows)"
        elif arrow_count >= self.MIN_MECHANISM_ARROWS:
            return 0.7, None, f"Good mechanism chains ({arrow_count} arrows)"
        elif arrow_count >= 1:
            return 0.4, "Limited mechanism chain notation", None
        else:
            return 0.1, "Missing mechanism chains (use → for cause-effect)", None

    def _check_distractor_coverage(
        self,
        explanation: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Check that all 5 answer choices have explanations.
        """
        distractor_explanations = explanation.get("distractor_explanations", {})
        issues = []

        if not distractor_explanations:
            return 0.0, ["Missing distractor_explanations field"]

        # Check for each choice A-E
        expected_choices = ['A', 'B', 'C', 'D', 'E']
        present_choices = set()

        for choice in expected_choices:
            # Check various key formats
            if (choice in distractor_explanations or
                f"choice_{choice}" in distractor_explanations or
                choice.lower() in distractor_explanations):
                present_choices.add(choice)

        missing = set(expected_choices) - present_choices

        if not missing:
            return 1.0, []
        elif len(missing) <= 1:
            return 0.8, [f"Missing explanation for choice {', '.join(missing)}"]
        elif len(missing) <= 2:
            return 0.5, [f"Missing explanations for choices {', '.join(missing)}"]
        else:
            return 0.2, [f"Missing explanations for {len(missing)} choices"]

    def _check_distractor_psychology(
        self,
        explanation: Dict[str, Any]
    ) -> Tuple[float, Optional[str], Optional[str]]:
        """
        Check if wrong answers explain WHY they're tempting.

        This is the 285+ secret: understanding NBME's distractor logic.
        """
        distractor_explanations = explanation.get("distractor_explanations", {})

        if not distractor_explanations:
            return 0.0, "No distractor explanations to check", None

        # Combine all distractor text
        distractor_text = " ".join(
            str(v) for v in distractor_explanations.values()
            if isinstance(v, str)
        )

        # Count psychology patterns
        psychology_matches = 0
        for pattern in self.DISTRACTOR_PSYCHOLOGY_PATTERNS:
            if pattern.search(distractor_text):
                psychology_matches += 1

        if psychology_matches >= 3:
            return 1.0, None, "Excellent distractor psychology analysis"
        elif psychology_matches >= 2:
            return 0.8, None, "Good distractor psychology coverage"
        elif psychology_matches >= 1:
            return 0.5, "Limited distractor psychology explanation", None
        else:
            return 0.2, "Missing 'tempting because' analysis for wrong answers", None

    def _check_threshold_explicitness(
        self,
        explanation: Dict[str, Any]
    ) -> Tuple[float, Optional[str], Optional[str]]:
        """
        Check that clinical values include normal ranges.

        285+ explanations: "BP 80/50 (normal >90/60)"
        Not: "hypotensive"
        """
        # Combine relevant text
        text_fields = [
            explanation.get("clinical_reasoning", ""),
            explanation.get("correct_answer_explanation", ""),
            explanation.get("quick_answer", "")
        ]
        combined_text = " ".join(str(t) for t in text_fields)

        # Count clinical values
        clinical_values = self.CLINICAL_VALUE_PATTERN.findall(combined_text)

        # Count normal range notations
        normal_ranges = self.NORMAL_RANGE_PATTERN.findall(combined_text)

        if not clinical_values:
            # No clinical values to check - neutral
            return 0.7, None, None

        ratio = len(normal_ranges) / len(clinical_values) if clinical_values else 0

        if ratio >= 0.5:
            return 1.0, None, f"Good threshold context ({len(normal_ranges)} ranges defined)"
        elif ratio >= 0.25:
            return 0.6, "Some values lack (normal X-Y) context", None
        elif normal_ranges:
            return 0.4, "Most values lack normal range context", None
        else:
            return 0.2, "No normal ranges defined (use 'value (normal X-Y)')", None

    def _check_brevity(
        self,
        explanation: Dict[str, Any]
    ) -> Tuple[float, Optional[str]]:
        """
        Check quick_answer brevity (<=30 words).
        """
        quick_answer = explanation.get("quick_answer", "")

        if not quick_answer:
            return 0.0, "Missing quick_answer"

        word_count = len(quick_answer.split())

        if word_count <= self.MAX_QUICK_ANSWER_WORDS:
            return 1.0, None
        elif word_count <= 40:
            return 0.7, f"Quick answer slightly long ({word_count} words, max {self.MAX_QUICK_ANSWER_WORDS})"
        elif word_count <= 50:
            return 0.4, f"Quick answer too long ({word_count} words)"
        else:
            return 0.1, f"Quick answer way too long ({word_count} words, needs condensing)"

    def _generate_recommendations(
        self,
        dimensions: Dict[str, float],
        issues: List[str]
    ) -> List[str]:
        """Generate actionable recommendations based on low-scoring dimensions."""
        recommendations = []

        if dimensions.get("mechanism_depth", 1) < 0.7:
            recommendations.append(
                "Add explicit mechanism chains using arrow notation: "
                "'risk factor → pathology → clinical finding → management'"
            )

        if dimensions.get("distractor_psychology", 1) < 0.7:
            recommendations.append(
                "For each wrong answer, explain why it's TEMPTING: "
                "'Choice A is tempting because it's the classic teaching, "
                "but wrong here because...'"
            )

        if dimensions.get("threshold_explicitness", 1) < 0.6:
            recommendations.append(
                "Add normal ranges after clinical values: "
                "'BP 80/50 (normal >90/60)' not just 'hypotensive'"
            )

        if dimensions.get("pattern_recognition", 1) < 0.6:
            recommendations.append(
                "Quick answer should teach first-sentence recognition: "
                "'When you see [key finding], think [diagnosis]'"
            )

        if dimensions.get("brevity", 1) < 0.7:
            recommendations.append(
                "Condense quick_answer to <=30 words. "
                "Move details to clinical_reasoning."
            )

        return recommendations

    def batch_validate(
        self,
        questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate multiple questions and return summary statistics.

        Args:
            questions: List of question dicts

        Returns:
            Dict with overall stats and per-question results
        """
        results = []
        for q in questions:
            result = self.validate(q)
            results.append({
                "id": q.get("id"),
                "score": result.score,
                "is_elite": result.is_elite,
                "issues": result.issues
            })

        elite_count = sum(1 for r in results if r["is_elite"])
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0

        return {
            "total_questions": len(questions),
            "elite_questions": elite_count,
            "elite_percentage": f"{(elite_count / len(questions) * 100):.1f}%" if questions else "0%",
            "average_score": round(avg_score, 1),
            "questions": results
        }


# Global singleton instance
elite_validator = EliteQualityValidator()
