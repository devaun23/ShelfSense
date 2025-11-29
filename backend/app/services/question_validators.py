"""
Question Quality Validators

Implements pre-generation and post-generation validation for:
- Vague clinical terms (#10)
- Testwiseness cues (#12)
- Distractor quality (#11)

These validators integrate into the question generation pipeline
to ensure high-quality output.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity of validation findings"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationFinding:
    """A single validation finding"""
    validator: str              # Which validator found this
    issue: str                  # Description of the issue
    severity: ValidationSeverity
    location: Optional[str]     # Where in the question (vignette, choice A, etc.)
    suggestion: Optional[str]   # How to fix


@dataclass
class ValidationReport:
    """Complete validation report"""
    passed: bool
    findings: List[ValidationFinding]
    error_count: int
    warning_count: int


# =============================================================================
# VAGUE CLINICAL TERMS VALIDATOR (#10)
# =============================================================================

class VagueTermValidator:
    """
    Detects vague clinical terms that should have explicit values.

    Medical education requires explicit values for threshold-based
    decision making. Terms like "hypotensive" without a BP value
    prevent students from practicing clinical reasoning.
    """

    # Vague terms and patterns that require explicit values
    # Format: term -> regex that SHOULD follow (if not present, flag as vague)
    VAGUE_TERM_PATTERNS = {
        # Vital sign descriptors
        "hypotensive": {
            "pattern": r"hypotensive(?!\s*\((?:BP|blood pressure)\s*\d+)",
            "requires": "BP value",
            "example": "hypotensive (BP 76/50 mmHg)"
        },
        "hypertensive": {
            "pattern": r"hypertensive(?!\s*\((?:BP|blood pressure)\s*\d+)",
            "requires": "BP value",
            "example": "hypertensive (BP 180/110 mmHg)"
        },
        "tachycardic": {
            "pattern": r"tachycardic(?!\s*\((?:HR|heart rate|pulse)\s*\d+)",
            "requires": "HR value",
            "example": "tachycardic (HR 128/min)"
        },
        "bradycardic": {
            "pattern": r"bradycardic(?!\s*\((?:HR|heart rate|pulse)\s*\d+)",
            "requires": "HR value",
            "example": "bradycardic (HR 42/min)"
        },
        "tachypneic": {
            "pattern": r"tachypneic(?!\s*\((?:RR|respiratory rate)\s*\d+)",
            "requires": "RR value",
            "example": "tachypneic (RR 28/min)"
        },
        "febrile": {
            "pattern": r"febrile(?!\s*\((?:temp|temperature)\s*\d+)",
            "requires": "temperature value",
            "example": "febrile (temperature 39.2C)"
        },
        "hypothermic": {
            "pattern": r"hypothermic(?!\s*\((?:temp|temperature)\s*\d+)",
            "requires": "temperature value",
            "example": "hypothermic (temperature 34.5C)"
        },

        # Lab value descriptors
        "elevated": {
            "pattern": r"elevated\s+(?:serum\s+)?(\w+)(?!\s*\(\d+)",
            "requires": "numeric value",
            "example": "elevated creatinine (2.8 mg/dL)"
        },
        "low": {
            "pattern": r"\blow\s+(?:serum\s+)?(\w+)(?!\s*\(\d+)",
            "requires": "numeric value",
            "example": "low hemoglobin (7.2 g/dL)"
        },
        "high": {
            "pattern": r"\bhigh\s+(?:serum\s+)?(\w+)(?!\s*\(\d+)",
            "requires": "numeric value",
            "example": "high glucose (342 mg/dL)"
        },
        "decreased": {
            "pattern": r"decreased\s+(?:serum\s+)?(\w+)(?!\s*\(\d+)",
            "requires": "numeric value",
            "example": "decreased platelets (45,000/uL)"
        },
        "increased": {
            "pattern": r"increased\s+(?:serum\s+)?(\w+)(?!\s*\(\d+)",
            "requires": "numeric value",
            "example": "increased WBC (18,500/uL)"
        },

        # Clinical state descriptors
        "hypoxic": {
            "pattern": r"hypoxic(?!\s*\((?:SpO2|O2 sat|PaO2)\s*\d+)",
            "requires": "oxygen saturation",
            "example": "hypoxic (SpO2 82% on room air)"
        },
        "anemic": {
            "pattern": r"anemic(?!\s*\((?:Hgb|hemoglobin|Hct)\s*\d+)",
            "requires": "hemoglobin value",
            "example": "anemic (Hgb 6.8 g/dL)"
        },
        "acidotic": {
            "pattern": r"acidotic(?!\s*\(pH\s*\d+)",
            "requires": "pH value",
            "example": "acidotic (pH 7.21)"
        },
        "alkalotic": {
            "pattern": r"alkalotic(?!\s*\(pH\s*\d+)",
            "requires": "pH value",
            "example": "alkalotic (pH 7.52)"
        },
    }

    # Additional phrases that suggest missing values
    VAGUE_PHRASES = [
        (r"vital signs (?:are |were )?(?:un)?stable", "Provide specific vital sign values"),
        (r"labs (?:are |were )?(?:ab)?normal", "Provide specific lab values"),
        (r"mildly abnormal", "Quantify the abnormality"),
        (r"significantly elevated", "Provide the specific value"),
        (r"slightly decreased", "Provide the specific value"),
        (r"within normal limits", "Acceptable but specific values preferred for key labs"),
    ]

    def validate(self, vignette: str) -> List[ValidationFinding]:
        """
        Check vignette for vague clinical terms.

        Args:
            vignette: The clinical vignette text

        Returns:
            List of validation findings
        """
        findings = []

        # Check each vague term pattern
        for term, config in self.VAGUE_TERM_PATTERNS.items():
            pattern = re.compile(config["pattern"], re.IGNORECASE)
            matches = pattern.finditer(vignette)

            for match in matches:
                findings.append(ValidationFinding(
                    validator="VagueTermValidator",
                    issue=f"Vague term '{term}' without explicit {config['requires']}",
                    severity=ValidationSeverity.ERROR,
                    location="vignette",
                    suggestion=f"Use explicit value, e.g., '{config['example']}'"
                ))

        # Check vague phrases
        for pattern, suggestion in self.VAGUE_PHRASES:
            if re.search(pattern, vignette, re.IGNORECASE):
                # "within normal limits" is less severe
                severity = ValidationSeverity.WARNING if "normal limits" in pattern else ValidationSeverity.ERROR

                findings.append(ValidationFinding(
                    validator="VagueTermValidator",
                    issue=f"Vague phrase detected: '{pattern}'",
                    severity=severity,
                    location="vignette",
                    suggestion=suggestion
                ))

        return findings


# =============================================================================
# TESTWISENESS VALIDATOR (#12)
# =============================================================================

class TestwisenessValidator:
    """
    Detects testwiseness cues that allow answering without clinical reasoning.

    Testwiseness cues include:
    - Length cues (correct answer is longest)
    - Specificity cues (correct answer more detailed)
    - Grammatical cues (lead-in doesn't match all choices)
    - Absolute terms ("always", "never")
    - Convergence (two choices say the same thing)
    """

    # Absolute terms that are usually wrong
    ABSOLUTE_TERMS = [
        r"\balways\b",
        r"\bnever\b",
        r"\ball\s+patients?\b",
        r"\bno\s+patients?\b",
        r"\bonly\s+(?:treatment|option|choice)\b",
        r"\bguarantee[sd]?\b",
        r"\bimpossible\b",
    ]

    # Trick patterns
    TRICK_PATTERNS = [
        r"\ball\s+of\s+the\s+above\b",
        r"\bnone\s+of\s+the\s+above\b",
        r"\bboth\s+[A-E]\s+and\s+[A-E]\b",
    ]

    def validate(
        self,
        lead_in: str,
        choices: List[str],
        correct_key: str
    ) -> List[ValidationFinding]:
        """
        Check for testwiseness cues.

        Args:
            lead_in: The question lead-in text
            choices: List of answer choices (A through E)
            correct_key: The correct answer letter (A-E)

        Returns:
            List of validation findings
        """
        findings = []

        # Parse choices into dict
        choice_dict = self._parse_choices(choices)
        if not choice_dict or correct_key not in choice_dict:
            return findings

        correct_text = choice_dict[correct_key]

        # 1. Check length cue
        findings.extend(self._check_length_cue(choice_dict, correct_key))

        # 2. Check specificity cue
        findings.extend(self._check_specificity_cue(choice_dict, correct_key))

        # 3. Check absolute terms
        findings.extend(self._check_absolute_terms(choice_dict, correct_key))

        # 4. Check trick patterns
        findings.extend(self._check_trick_patterns(choices))

        # 5. Check convergence (similar distractors)
        findings.extend(self._check_convergence(choice_dict, correct_key))

        # 6. Check grammatical agreement
        findings.extend(self._check_grammatical_agreement(lead_in, choice_dict))

        return findings

    def _parse_choices(self, choices: List[str]) -> Dict[str, str]:
        """Parse choice list into letter -> text dict"""
        result = {}
        for choice in choices:
            # Handle formats: "A. text", "A) text", "A text"
            match = re.match(r"^([A-E])[\.\)]\s*(.+)$", choice.strip())
            if match:
                result[match.group(1)] = match.group(2)
            elif len(choices) <= 5:
                # Assume A-E order if no letter prefix
                idx = choices.index(choice)
                if idx < 5:
                    result[chr(65 + idx)] = choice

        return result

    def _check_length_cue(
        self,
        choices: Dict[str, str],
        correct_key: str
    ) -> List[ValidationFinding]:
        """Check if correct answer is significantly longer than others"""
        findings = []

        lengths = {k: len(v) for k, v in choices.items()}
        correct_length = lengths[correct_key]

        # Calculate mean length of incorrect choices
        incorrect_lengths = [l for k, l in lengths.items() if k != correct_key]
        if not incorrect_lengths:
            return findings

        mean_incorrect = sum(incorrect_lengths) / len(incorrect_lengths)

        # Flag if correct is >30% longer than average incorrect
        if mean_incorrect > 0 and correct_length > mean_incorrect * 1.3:
            findings.append(ValidationFinding(
                validator="TestwisenessValidator",
                issue="Correct answer is significantly longer than distractors",
                severity=ValidationSeverity.WARNING,
                location=f"Choice {correct_key}",
                suggestion="Equalize choice lengths or add detail to distractors"
            ))

        # Also flag if correct is the longest by significant margin
        max_incorrect = max(incorrect_lengths)
        if correct_length > max_incorrect * 1.5:
            findings.append(ValidationFinding(
                validator="TestwisenessValidator",
                issue="Correct answer is much longer than all distractors",
                severity=ValidationSeverity.ERROR,
                location=f"Choice {correct_key}",
                suggestion="Shorten correct answer or lengthen distractors"
            ))

        return findings

    def _check_specificity_cue(
        self,
        choices: Dict[str, str],
        correct_key: str
    ) -> List[ValidationFinding]:
        """Check if correct answer has more specific/precise language"""
        findings = []

        # Indicators of specificity
        specificity_patterns = [
            r"\d+\s*(?:mg|g|mcg|mL|units?|hours?|days?|weeks?)",  # Dosages/times
            r"\d+(?:\.\d+)?%",  # Percentages
            r"(?:first|second|third)-line",  # Treatment order
            r"(?:immediately|urgently|stat)",  # Timing modifiers
            r"(?:IV|PO|IM|SC|topical)",  # Routes
        ]

        def count_specificity(text: str) -> int:
            return sum(
                len(re.findall(p, text, re.IGNORECASE))
                for p in specificity_patterns
            )

        correct_specificity = count_specificity(choices[correct_key])
        incorrect_specificities = [
            count_specificity(v) for k, v in choices.items() if k != correct_key
        ]

        if not incorrect_specificities:
            return findings

        max_incorrect_specificity = max(incorrect_specificities)

        # Flag if correct has notably more specific language
        if correct_specificity > max_incorrect_specificity + 2:
            findings.append(ValidationFinding(
                validator="TestwisenessValidator",
                issue="Correct answer has more precise/specific language than distractors",
                severity=ValidationSeverity.WARNING,
                location=f"Choice {correct_key}",
                suggestion="Add specific details to distractors to balance"
            ))

        return findings

    def _check_absolute_terms(
        self,
        choices: Dict[str, str],
        correct_key: str
    ) -> List[ValidationFinding]:
        """Check for absolute terms (usually indicate wrong answers)"""
        findings = []

        for letter, text in choices.items():
            for pattern in self.ABSOLUTE_TERMS:
                if re.search(pattern, text, re.IGNORECASE):
                    # Absolute terms in correct answer is unusual
                    if letter == correct_key:
                        findings.append(ValidationFinding(
                            validator="TestwisenessValidator",
                            issue=f"Correct answer contains absolute term",
                            severity=ValidationSeverity.WARNING,
                            location=f"Choice {letter}",
                            suggestion="Absolute terms are usually wrong; review if appropriate"
                        ))
                    else:
                        # Expected in distractors but note it
                        findings.append(ValidationFinding(
                            validator="TestwisenessValidator",
                            issue=f"Distractor contains absolute term (may be too obvious)",
                            severity=ValidationSeverity.INFO,
                            location=f"Choice {letter}",
                            suggestion="Consider if distractor is too obviously wrong"
                        ))

        return findings

    def _check_trick_patterns(self, choices: List[str]) -> List[ValidationFinding]:
        """Check for 'all of the above' and similar patterns"""
        findings = []

        combined = " ".join(choices)
        for pattern in self.TRICK_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                findings.append(ValidationFinding(
                    validator="TestwisenessValidator",
                    issue=f"Contains test-taking trick pattern",
                    severity=ValidationSeverity.ERROR,
                    location="choices",
                    suggestion="Remove 'all/none of the above' patterns"
                ))

        return findings

    def _check_convergence(
        self,
        choices: Dict[str, str],
        correct_key: str
    ) -> List[ValidationFinding]:
        """Check if any two distractors are semantically similar"""
        findings = []

        incorrect_choices = {k: v for k, v in choices.items() if k != correct_key}
        letters = list(incorrect_choices.keys())

        for i in range(len(letters)):
            for j in range(i + 1, len(letters)):
                letter1, letter2 = letters[i], letters[j]
                text1, text2 = incorrect_choices[letter1], incorrect_choices[letter2]

                # Calculate similarity
                similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

                if similarity > 0.7:
                    findings.append(ValidationFinding(
                        validator="TestwisenessValidator",
                        issue=f"Choices {letter1} and {letter2} are very similar ({similarity:.0%})",
                        severity=ValidationSeverity.WARNING,
                        location=f"Choices {letter1}, {letter2}",
                        suggestion="Students may eliminate both as 'same answer'; differentiate them"
                    ))

        return findings

    def _check_grammatical_agreement(
        self,
        lead_in: str,
        choices: Dict[str, str]
    ) -> List[ValidationFinding]:
        """Check if all choices grammatically fit the lead-in"""
        findings = []

        # Check for article agreement (a/an)
        if lead_in.strip().endswith(" a"):
            for letter, text in choices.items():
                if text and text[0].lower() in "aeiou":
                    findings.append(ValidationFinding(
                        validator="TestwisenessValidator",
                        issue=f"Choice {letter} starts with vowel but lead-in ends with 'a'",
                        severity=ValidationSeverity.WARNING,
                        location=f"Choice {letter}",
                        suggestion="Change lead-in to 'a/an' or rephrase"
                    ))

        # Check for singular/plural agreement
        singular_patterns = [r"\bis\s+(?:the\s+)?most\b", r"\bwhich\s+(?:one|single)\b"]
        plural_patterns = [r"\bare\s+(?:the\s+)?most\b", r"\bwhich\s+(?:ones|multiple)\b"]

        is_singular = any(re.search(p, lead_in, re.IGNORECASE) for p in singular_patterns)
        is_plural = any(re.search(p, lead_in, re.IGNORECASE) for p in plural_patterns)

        if is_singular:
            for letter, text in choices.items():
                # Check if choice appears plural (ends in 's' for simple check)
                if text.strip().endswith("s") and not text.strip().endswith("ss"):
                    findings.append(ValidationFinding(
                        validator="TestwisenessValidator",
                        issue=f"Choice {letter} may be plural but lead-in expects singular",
                        severity=ValidationSeverity.INFO,
                        location=f"Choice {letter}",
                        suggestion="Verify grammatical agreement"
                    ))

        return findings


# =============================================================================
# DISTRACTOR QUALITY VALIDATOR (#11)
# =============================================================================

class DistractorQualityValidator:
    """
    Pre-generation validator for distractor quality.

    Checks that distractors:
    - Are semantically distinct from correct answer
    - Are not obviously wrong
    - Represent plausible clinical reasoning errors
    - Are homogeneous (same type as correct answer)
    """

    # Common clinical categories for homogeneity checking
    CLINICAL_CATEGORIES = {
        "diagnoses": [
            r"(?:acute|chronic)?\s*\w+itis\b",  # inflammatory conditions
            r"\b\w+oma\b",  # tumors
            r"\b\w+osis\b",  # degenerative conditions
            r"\bsyndrome\b",
            r"\bdisease\b",
            r"\bdisorder\b",
        ],
        "treatments": [
            r"\b(?:start|begin|initiate|administer|give)\b",
            r"\b\w+(?:mab|nib|pril|olol|statin|sartan)\b",  # drug suffixes
            r"\btherapy\b",
            r"\btreatment\b",
            r"\bsurgery\b",
            r"\bprocedure\b",
        ],
        "tests": [
            r"\b(?:CT|MRI|X-ray|ultrasound|ECG|EKG)\b",
            r"\b(?:order|obtain|check|measure)\b.*\b(?:level|test|study)\b",
            r"\blab(?:oratory)?\b",
            r"\bimaging\b",
            r"\bbiopsy\b",
        ],
        "mechanisms": [
            r"\b(?:inhibit|block|activate|stimulate|suppress)\b",
            r"\b(?:increase|decrease|enhance|reduce)\b.*\b(?:production|release|synthesis)\b",
            r"\bpathway\b",
            r"\breceptor\b",
        ],
    }

    def validate(
        self,
        choices: List[str],
        correct_key: str,
        vignette: Optional[str] = None
    ) -> List[ValidationFinding]:
        """
        Validate distractor quality.

        Args:
            choices: List of answer choices
            correct_key: Correct answer letter
            vignette: Optional vignette for context

        Returns:
            List of validation findings
        """
        findings = []

        choice_dict = self._parse_choices(choices)
        if not choice_dict:
            return findings

        # 1. Check homogeneity
        findings.extend(self._check_homogeneity(choice_dict))

        # 2. Check for duplicates/near-duplicates
        findings.extend(self._check_duplicates(choice_dict))

        # 3. Check semantic distance from correct answer
        if correct_key in choice_dict:
            findings.extend(self._check_semantic_distance(choice_dict, correct_key))

        # 4. Check for obviously wrong choices
        findings.extend(self._check_obvious_wrongs(choice_dict, correct_key, vignette))

        return findings

    def _parse_choices(self, choices: List[str]) -> Dict[str, str]:
        """Parse choices into letter -> text dict"""
        result = {}
        for i, choice in enumerate(choices):
            match = re.match(r"^([A-E])[\.\)]\s*(.+)$", choice.strip())
            if match:
                result[match.group(1)] = match.group(2)
            elif i < 5:
                result[chr(65 + i)] = choice
        return result

    def _check_homogeneity(self, choices: Dict[str, str]) -> List[ValidationFinding]:
        """Check that all choices are the same category"""
        findings = []

        # Determine category for each choice
        choice_categories = {}
        for letter, text in choices.items():
            for category, patterns in self.CLINICAL_CATEGORIES.items():
                if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                    choice_categories[letter] = category
                    break
            else:
                choice_categories[letter] = "unknown"

        # Check if all categorized choices are same category
        categories = [c for c in choice_categories.values() if c != "unknown"]
        if categories and len(set(categories)) > 1:
            findings.append(ValidationFinding(
                validator="DistractorQualityValidator",
                issue="Answer choices appear to be different types (not homogeneous)",
                severity=ValidationSeverity.WARNING,
                location="choices",
                suggestion="All choices should be same type (all diagnoses, all treatments, etc.)"
            ))

        return findings

    def _check_duplicates(self, choices: Dict[str, str]) -> List[ValidationFinding]:
        """Check for duplicate or near-duplicate choices"""
        findings = []

        letters = list(choices.keys())
        for i in range(len(letters)):
            for j in range(i + 1, len(letters)):
                letter1, letter2 = letters[i], letters[j]
                text1 = choices[letter1].lower().strip()
                text2 = choices[letter2].lower().strip()

                # Check exact duplicates
                if text1 == text2:
                    findings.append(ValidationFinding(
                        validator="DistractorQualityValidator",
                        issue=f"Choices {letter1} and {letter2} are identical",
                        severity=ValidationSeverity.CRITICAL,
                        location=f"Choices {letter1}, {letter2}",
                        suggestion="Remove duplicate choice"
                    ))
                # Check near-duplicates
                elif SequenceMatcher(None, text1, text2).ratio() > 0.85:
                    findings.append(ValidationFinding(
                        validator="DistractorQualityValidator",
                        issue=f"Choices {letter1} and {letter2} are nearly identical",
                        severity=ValidationSeverity.ERROR,
                        location=f"Choices {letter1}, {letter2}",
                        suggestion="Differentiate the choices or remove one"
                    ))

        return findings

    def _check_semantic_distance(
        self,
        choices: Dict[str, str],
        correct_key: str
    ) -> List[ValidationFinding]:
        """Check semantic distance between correct answer and distractors"""
        findings = []

        correct_text = choices[correct_key].lower()

        for letter, text in choices.items():
            if letter == correct_key:
                continue

            text_lower = text.lower()
            similarity = SequenceMatcher(None, correct_text, text_lower).ratio()

            # Too similar to correct answer
            if similarity > 0.8:
                findings.append(ValidationFinding(
                    validator="DistractorQualityValidator",
                    issue=f"Choice {letter} is very similar to correct answer",
                    severity=ValidationSeverity.WARNING,
                    location=f"Choice {letter}",
                    suggestion="May create ambiguity; differentiate more clearly"
                ))

        return findings

    def _check_obvious_wrongs(
        self,
        choices: Dict[str, str],
        correct_key: str,
        vignette: Optional[str]
    ) -> List[ValidationFinding]:
        """Check for obviously wrong choices that don't test reasoning"""
        findings = []

        # Patterns that suggest obviously wrong choices
        obvious_patterns = [
            (r"do nothing", "Non-actionable distractor"),
            (r"reassure and discharge", "May be too obviously wrong in acute setting"),
            (r"watchful waiting", "May be too obviously wrong in acute setting"),
            (r"no further workup", "May be too obviously wrong"),
        ]

        for letter, text in choices.items():
            if letter == correct_key:
                continue

            for pattern, description in obvious_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Only flag if vignette suggests acute/emergent setting
                    if vignette:
                        acute_indicators = [
                            "emergency", "acute", "severe", "unstable",
                            "deteriorating", "critical", "immediate"
                        ]
                        is_acute = any(ind in vignette.lower() for ind in acute_indicators)

                        if is_acute:
                            findings.append(ValidationFinding(
                                validator="DistractorQualityValidator",
                                issue=f"Choice {letter} may be too obviously wrong: {description}",
                                severity=ValidationSeverity.WARNING,
                                location=f"Choice {letter}",
                                suggestion="Replace with more plausible distractor"
                            ))

        return findings


# =============================================================================
# COMBINED VALIDATOR
# =============================================================================

class QuestionQualityValidator:
    """
    Combined validator that runs all quality checks.

    Use this as the main entry point for question validation.
    """

    def __init__(self):
        self.vague_validator = VagueTermValidator()
        self.testwiseness_validator = TestwisenessValidator()
        self.distractor_validator = DistractorQualityValidator()

    def validate_question(
        self,
        vignette: str,
        choices: List[str],
        correct_key: str,
        lead_in: Optional[str] = None
    ) -> ValidationReport:
        """
        Run all validators on a question.

        Args:
            vignette: Clinical vignette text
            choices: List of answer choices
            correct_key: Correct answer letter
            lead_in: Question lead-in (extracted from vignette if not provided)

        Returns:
            ValidationReport with all findings
        """
        findings = []

        # Extract lead-in from vignette if not provided
        if not lead_in:
            lead_in = self._extract_lead_in(vignette)

        # Run vague term validation
        findings.extend(self.vague_validator.validate(vignette))

        # Run testwiseness validation
        findings.extend(self.testwiseness_validator.validate(lead_in, choices, correct_key))

        # Run distractor quality validation
        findings.extend(self.distractor_validator.validate(choices, correct_key, vignette))

        # Calculate summary
        error_count = sum(
            1 for f in findings
            if f.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
        )
        warning_count = sum(1 for f in findings if f.severity == ValidationSeverity.WARNING)

        # Pass if no errors (warnings are acceptable)
        passed = error_count == 0

        return ValidationReport(
            passed=passed,
            findings=findings,
            error_count=error_count,
            warning_count=warning_count
        )

    def _extract_lead_in(self, vignette: str) -> str:
        """Extract the question lead-in from vignette"""
        # Look for question pattern at end
        question_pattern = r"([^.?!]*\?)\s*$"
        match = re.search(question_pattern, vignette)
        if match:
            return match.group(1)

        # Fallback: last sentence
        sentences = re.split(r'[.!?]+', vignette)
        return sentences[-1].strip() if sentences else ""


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_question(
    vignette: str,
    choices: List[str],
    correct_key: str
) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a question.

    Returns:
        Tuple of (passed, list of issue messages)
    """
    validator = QuestionQualityValidator()
    report = validator.validate_question(vignette, choices, correct_key)

    issues = [
        f"[{f.severity.value.upper()}] {f.issue}"
        + (f" ({f.location})" if f.location else "")
        + (f" - {f.suggestion}" if f.suggestion else "")
        for f in report.findings
        if f.severity != ValidationSeverity.INFO
    ]

    return report.passed, issues


def check_vague_terms(vignette: str) -> Tuple[bool, List[str]]:
    """Check only for vague clinical terms"""
    validator = VagueTermValidator()
    findings = validator.validate(vignette)

    errors = [f for f in findings if f.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]
    messages = [f"{f.issue} - {f.suggestion}" for f in findings]

    return len(errors) == 0, messages


def check_testwiseness(lead_in: str, choices: List[str], correct_key: str) -> Tuple[bool, List[str]]:
    """Check only for testwiseness cues"""
    validator = TestwisenessValidator()
    findings = validator.validate(lead_in, choices, correct_key)

    errors = [f for f in findings if f.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]
    messages = [f"{f.issue} - {f.suggestion}" for f in findings if f.suggestion]

    return len(errors) == 0, messages


def check_distractor_quality(choices: List[str], correct_key: str, vignette: str = "") -> Tuple[bool, List[str]]:
    """Check only distractor quality"""
    validator = DistractorQualityValidator()
    findings = validator.validate(choices, correct_key, vignette)

    errors = [f for f in findings if f.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]
    messages = [f"{f.issue} - {f.suggestion}" for f in findings if f.suggestion]

    return len(errors) == 0, messages
