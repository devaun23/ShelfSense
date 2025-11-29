"""
Clinical Fact-Checker for LLM-Generated Questions

Cross-references generated content against curated medical guidelines to prevent
clinical inaccuracies from reaching students.

Issue: #8
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FactCheckSeverity(Enum):
    """Severity levels for fact-check findings"""
    INFO = "info"           # FYI, may want to review
    WARNING = "warning"     # Potentially incorrect, needs verification
    ERROR = "error"         # Likely incorrect, should block
    CRITICAL = "critical"   # Definitely incorrect, must block


@dataclass
class FactCheckResult:
    """Result of a single fact check"""
    claim: str                      # The clinical claim being checked
    is_valid: bool                  # Whether the claim passed validation
    severity: FactCheckSeverity     # Severity if invalid
    message: str                    # Explanation of finding
    guideline_source: Optional[str] # Source guideline (if applicable)
    suggested_correction: Optional[str] = None  # What the correct value should be


@dataclass
class FactCheckReport:
    """Complete fact-check report for a question"""
    passed: bool                    # Overall pass/fail
    findings: List[FactCheckResult] # All findings
    error_count: int
    warning_count: int
    confidence: float               # 0-1 confidence in the check


class ClinicalFactChecker:
    """
    Cross-reference generated content against curated medical guidelines.

    This service validates:
    - Treatment thresholds and windows
    - Drug dosages and contraindications
    - Diagnostic criteria
    - Vital sign interpretations
    """

    # Curated clinical guidelines database
    # Format: key -> {value, unit, source, tolerance (optional)}
    CLINICAL_THRESHOLDS = {
        # Stroke Management
        "tpa_window_ischemic_stroke": {
            "value": 4.5, "unit": "hours",
            "source": "AHA/ASA 2019 Guidelines",
            "description": "IV tPA administration window for ischemic stroke"
        },
        "thrombectomy_window": {
            "value": 24, "unit": "hours",
            "source": "AHA/ASA 2019 (select patients)",
            "description": "Mechanical thrombectomy window for large vessel occlusion"
        },

        # STEMI/ACS Management
        "door_to_balloon_time": {
            "value": 90, "unit": "minutes",
            "source": "ACC/AHA STEMI Guidelines",
            "description": "Target door-to-balloon time for primary PCI"
        },
        "stemi_fibrinolytic_window": {
            "value": 12, "unit": "hours",
            "source": "ACC/AHA Guidelines",
            "description": "Fibrinolytic therapy window for STEMI"
        },

        # Sepsis Management
        "sepsis_antibiotic_window": {
            "value": 1, "unit": "hour",
            "source": "Surviving Sepsis Campaign 2021",
            "description": "Time to antibiotics in sepsis/septic shock"
        },
        "sepsis_fluid_bolus": {
            "value": 30, "unit": "mL/kg",
            "source": "Surviving Sepsis Campaign 2021",
            "description": "Initial crystalloid fluid bolus for sepsis"
        },
        "map_target_sepsis": {
            "value": 65, "unit": "mmHg",
            "source": "Surviving Sepsis Campaign 2021",
            "description": "Target MAP in septic shock"
        },

        # Diabetes Management
        "hba1c_diabetes_diagnosis": {
            "value": 6.5, "unit": "%",
            "source": "ADA Standards of Care 2024",
            "description": "HbA1c threshold for diabetes diagnosis"
        },
        "fasting_glucose_diabetes": {
            "value": 126, "unit": "mg/dL",
            "source": "ADA Standards of Care 2024",
            "description": "Fasting glucose threshold for diabetes"
        },
        "dka_glucose_threshold": {
            "value": 250, "unit": "mg/dL",
            "source": "ADA Guidelines",
            "description": "Typical glucose threshold for DKA"
        },

        # Hypertension
        "hypertension_stage1_systolic": {
            "value": 130, "unit": "mmHg",
            "source": "ACC/AHA 2017 Guidelines",
            "description": "Stage 1 hypertension systolic threshold"
        },
        "hypertensive_emergency_systolic": {
            "value": 180, "unit": "mmHg",
            "source": "ACC/AHA Guidelines",
            "description": "Systolic BP suggesting hypertensive emergency"
        },

        # Shock Parameters
        "hypotension_systolic": {
            "value": 90, "unit": "mmHg",
            "source": "Clinical Standard",
            "description": "Systolic BP threshold for hypotension"
        },
        "tachycardia_threshold": {
            "value": 100, "unit": "bpm",
            "source": "Clinical Standard",
            "description": "Heart rate threshold for tachycardia"
        },
        "bradycardia_threshold": {
            "value": 60, "unit": "bpm",
            "source": "Clinical Standard",
            "description": "Heart rate threshold for bradycardia"
        },

        # Renal
        "aki_creatinine_increase": {
            "value": 0.3, "unit": "mg/dL",
            "source": "KDIGO 2012",
            "description": "Creatinine increase for AKI Stage 1 (within 48h)"
        },
        "ckd_gfr_threshold": {
            "value": 60, "unit": "mL/min/1.73m2",
            "source": "KDIGO Guidelines",
            "description": "GFR threshold for CKD Stage 3"
        },

        # Pulmonary
        "ards_pf_ratio_severe": {
            "value": 100, "unit": "mmHg",
            "source": "Berlin Definition 2012",
            "description": "P/F ratio for severe ARDS"
        },
        "ards_pf_ratio_moderate": {
            "value": 200, "unit": "mmHg",
            "source": "Berlin Definition 2012",
            "description": "P/F ratio for moderate ARDS"
        },

        # Obstetrics
        "preeclampsia_systolic": {
            "value": 140, "unit": "mmHg",
            "source": "ACOG Guidelines",
            "description": "Systolic BP threshold for preeclampsia"
        },
        "preeclampsia_severe_systolic": {
            "value": 160, "unit": "mmHg",
            "source": "ACOG Guidelines",
            "description": "Systolic BP for severe preeclampsia"
        },
        "magnesium_eclampsia_loading": {
            "value": 4, "unit": "g",
            "source": "ACOG Guidelines",
            "description": "Magnesium sulfate loading dose for eclampsia"
        },
    }

    # Common drug contraindications
    DRUG_CONTRAINDICATIONS = {
        "metformin": [
            {"condition": "eGFR < 30", "source": "FDA Label"},
            {"condition": "acute kidney injury", "source": "Clinical Standard"},
            {"condition": "metabolic acidosis", "source": "Clinical Standard"},
        ],
        "tpa": [
            {"condition": "recent surgery (< 14 days)", "source": "Package Insert"},
            {"condition": "active bleeding", "source": "AHA Guidelines"},
            {"condition": "recent intracranial hemorrhage", "source": "AHA Guidelines"},
            {"condition": "BP > 185/110 (uncontrolled)", "source": "AHA Guidelines"},
        ],
        "nsaids": [
            {"condition": "GI bleeding", "source": "Clinical Standard"},
            {"condition": "CKD stage 4-5", "source": "KDIGO Guidelines"},
            {"condition": "third trimester pregnancy", "source": "FDA"},
        ],
        "ace_inhibitors": [
            {"condition": "pregnancy", "source": "FDA Black Box"},
            {"condition": "bilateral renal artery stenosis", "source": "Clinical Standard"},
            {"condition": "angioedema history", "source": "FDA Label"},
        ],
        "warfarin": [
            {"condition": "pregnancy", "source": "FDA Black Box"},
            {"condition": "active bleeding", "source": "Clinical Standard"},
        ],
        "fluoroquinolones": [
            {"condition": "myasthenia gravis", "source": "FDA Black Box"},
            {"condition": "tendon disorders", "source": "FDA Warning"},
        ],
    }

    # Time-sensitive intervention windows (commonly tested)
    TIME_WINDOWS = {
        "tpa_stroke": {"max_hours": 4.5, "source": "AHA 2019"},
        "pci_stemi": {"max_minutes": 90, "source": "ACC/AHA"},
        "antibiotics_sepsis": {"max_hours": 1, "source": "SSC 2021"},
        "door_to_needle_stemi": {"max_minutes": 30, "source": "ACC/AHA"},
        "appendectomy_perforation": {"max_hours": 24, "source": "Surgical Standard"},
    }

    # Patterns to extract clinical claims from text
    CLAIM_PATTERNS = [
        # Time windows: "within X hours", "at X hours"
        (r"within\s+(\d+(?:\.\d+)?)\s*(hours?|minutes?|days?)", "time_window"),
        (r"at\s+(\d+(?:\.\d+)?)\s*(hours?|minutes?)", "time_point"),

        # Thresholds: "BP > 140", "glucose of 126"
        (r"(?:BP|blood pressure)\s*[<>]\s*(\d+)(?:/(\d+))?", "bp_threshold"),
        (r"(?:HR|heart rate)\s*[<>]\s*(\d+)", "hr_threshold"),
        (r"(?:glucose|blood sugar)\s*(?:of|>|<|=)?\s*(\d+)", "glucose_threshold"),
        (r"GFR\s*[<>]\s*(\d+)", "gfr_threshold"),
        (r"HbA1c\s*[<>=]\s*(\d+(?:\.\d+)?)", "hba1c_threshold"),

        # Drug dosages
        (r"(\w+)\s+(\d+(?:\.\d+)?)\s*(mg|g|mcg|mL|units?)\s*(?:IV|PO|IM|SC)?", "drug_dose"),

        # Treatment timing
        (r"tPA\s+(?:within|at|after)\s+(\d+(?:\.\d+)?)\s*(hours?)", "tpa_timing"),
    ]

    def __init__(self):
        """Initialize the fact checker"""
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), claim_type)
            for pattern, claim_type in self.CLAIM_PATTERNS
        ]

    def validate_question(
        self,
        vignette: str,
        correct_answer: str,
        explanation: Dict[str, Any]
    ) -> FactCheckReport:
        """
        Validate a generated question for clinical accuracy.

        Args:
            vignette: The clinical vignette text
            correct_answer: The correct answer choice
            explanation: The explanation dictionary

        Returns:
            FactCheckReport with all findings
        """
        findings: List[FactCheckResult] = []

        # Combine all text for analysis
        all_text = self._combine_text(vignette, correct_answer, explanation)

        # Check time-sensitive interventions
        findings.extend(self._check_time_windows(all_text))

        # Check clinical thresholds
        findings.extend(self._check_thresholds(all_text))

        # Check drug-related claims
        findings.extend(self._check_drug_claims(all_text))

        # Check for potentially outdated guidelines
        findings.extend(self._check_guideline_currency(all_text))

        # Calculate summary
        error_count = sum(1 for f in findings if f.severity == FactCheckSeverity.ERROR)
        critical_count = sum(1 for f in findings if f.severity == FactCheckSeverity.CRITICAL)
        warning_count = sum(1 for f in findings if f.severity == FactCheckSeverity.WARNING)

        # Determine overall pass/fail
        # Fail if any CRITICAL or ERROR findings
        passed = critical_count == 0 and error_count == 0

        # Calculate confidence based on how many claims we could validate
        # Higher confidence = more claims checked against guidelines
        claims_checked = len(findings)
        confidence = min(1.0, claims_checked * 0.1 + 0.5) if claims_checked > 0 else 0.3

        return FactCheckReport(
            passed=passed,
            findings=findings,
            error_count=error_count + critical_count,
            warning_count=warning_count,
            confidence=confidence
        )

    def _combine_text(
        self,
        vignette: str,
        correct_answer: str,
        explanation: Dict[str, Any]
    ) -> str:
        """Combine all question text for analysis"""
        parts = [vignette, correct_answer]

        if isinstance(explanation, dict):
            for key in ['principle', 'clinical_reasoning', 'correct_answer_explanation']:
                if key in explanation and explanation[key]:
                    parts.append(str(explanation[key]))
        elif isinstance(explanation, str):
            parts.append(explanation)

        return " ".join(parts)

    def _check_time_windows(self, text: str) -> List[FactCheckResult]:
        """Check time-sensitive intervention windows"""
        findings = []

        # Check tPA timing for stroke
        tpa_pattern = re.compile(
            r"(?:tPA|alteplase|tissue plasminogen).*?(\d+(?:\.\d+)?)\s*(hours?)",
            re.IGNORECASE
        )
        for match in tpa_pattern.finditer(text):
            hours = float(match.group(1))
            guideline = self.CLINICAL_THRESHOLDS["tpa_window_ischemic_stroke"]

            if hours > guideline["value"]:
                findings.append(FactCheckResult(
                    claim=f"tPA at {hours} hours",
                    is_valid=False,
                    severity=FactCheckSeverity.CRITICAL,
                    message=f"tPA window is {guideline['value']} hours, not {hours} hours",
                    guideline_source=guideline["source"],
                    suggested_correction=f"tPA within {guideline['value']} hours"
                ))
            elif hours == guideline["value"]:
                findings.append(FactCheckResult(
                    claim=f"tPA at {hours} hours",
                    is_valid=True,
                    severity=FactCheckSeverity.INFO,
                    message="Correct tPA window",
                    guideline_source=guideline["source"]
                ))

        # Check sepsis antibiotic timing
        sepsis_abx_pattern = re.compile(
            r"(?:sepsis|septic).*?antibiotic.*?(\d+)\s*(hours?|minutes?)",
            re.IGNORECASE
        )
        for match in sepsis_abx_pattern.finditer(text):
            value = float(match.group(1))
            unit = match.group(2).lower()
            hours = value if "hour" in unit else value / 60

            guideline = self.CLINICAL_THRESHOLDS["sepsis_antibiotic_window"]
            if hours > guideline["value"]:
                findings.append(FactCheckResult(
                    claim=f"Sepsis antibiotics within {value} {unit}",
                    is_valid=False,
                    severity=FactCheckSeverity.ERROR,
                    message=f"Sepsis antibiotics should be within {guideline['value']} hour",
                    guideline_source=guideline["source"],
                    suggested_correction=f"Antibiotics within 1 hour of recognition"
                ))

        return findings

    def _check_thresholds(self, text: str) -> List[FactCheckResult]:
        """Check clinical threshold values"""
        findings = []

        # Check diabetes thresholds
        hba1c_pattern = re.compile(r"HbA1c\s*[><=]\s*(\d+(?:\.\d+)?)\s*%?", re.IGNORECASE)
        for match in hba1c_pattern.finditer(text):
            value = float(match.group(1))
            guideline = self.CLINICAL_THRESHOLDS["hba1c_diabetes_diagnosis"]

            # If claiming diabetes diagnosis at wrong threshold
            if "diagnos" in text.lower() and abs(value - guideline["value"]) > 0.1:
                findings.append(FactCheckResult(
                    claim=f"HbA1c {value}% for diabetes diagnosis",
                    is_valid=False,
                    severity=FactCheckSeverity.WARNING,
                    message=f"Diabetes diagnosis threshold is HbA1c >= {guideline['value']}%",
                    guideline_source=guideline["source"],
                    suggested_correction=f"HbA1c >= {guideline['value']}%"
                ))

        # Check BP thresholds
        bp_pattern = re.compile(
            r"(?:BP|blood pressure)[:\s]*(\d+)/(\d+)",
            re.IGNORECASE
        )
        for match in bp_pattern.finditer(text):
            systolic = int(match.group(1))

            # Check for hypotension claims
            if "hypotens" in text.lower():
                guideline = self.CLINICAL_THRESHOLDS["hypotension_systolic"]
                if systolic >= guideline["value"]:
                    findings.append(FactCheckResult(
                        claim=f"BP {systolic} described as hypotensive",
                        is_valid=False,
                        severity=FactCheckSeverity.ERROR,
                        message=f"Hypotension is typically SBP < {guideline['value']} mmHg",
                        guideline_source=guideline["source"]
                    ))

        return findings

    def _check_drug_claims(self, text: str) -> List[FactCheckResult]:
        """Check drug-related claims for contraindications"""
        findings = []
        text_lower = text.lower()

        for drug, contraindications in self.DRUG_CONTRAINDICATIONS.items():
            if drug in text_lower:
                for ci in contraindications:
                    # Check if contraindication condition is mentioned in same context
                    condition = ci["condition"].lower()

                    # Simple keyword matching - could be enhanced with NLP
                    condition_keywords = condition.replace("<", "").replace(">", "").split()
                    if any(kw in text_lower for kw in condition_keywords if len(kw) > 3):
                        # Check if this is being used appropriately (not as contraindication)
                        if "contraindicated" not in text_lower and "avoid" not in text_lower:
                            findings.append(FactCheckResult(
                                claim=f"{drug.title()} with potential contraindication",
                                is_valid=False,
                                severity=FactCheckSeverity.WARNING,
                                message=f"{drug.title()} may be contraindicated with {ci['condition']}",
                                guideline_source=ci["source"],
                                suggested_correction=f"Verify {drug} is appropriate given {ci['condition']}"
                            ))

        return findings

    def _check_guideline_currency(self, text: str) -> List[FactCheckResult]:
        """Check for potentially outdated guideline references"""
        findings = []

        # Patterns suggesting outdated info
        outdated_patterns = [
            (r"JNC\s*7", "JNC 7 is outdated; current standard is ACC/AHA 2017"),
            (r"ATP\s*III", "ATP III is outdated; use 2018 ACC/AHA guidelines"),
            (r"(?:BP|blood pressure)\s*[>]\s*140/90.*?hypertension.*?stage\s*1",
             "Stage 1 HTN is now >= 130/80 per ACC/AHA 2017"),
        ]

        for pattern, message in outdated_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append(FactCheckResult(
                    claim="Potentially outdated guideline reference",
                    is_valid=False,
                    severity=FactCheckSeverity.WARNING,
                    message=message,
                    guideline_source="Current guidelines"
                ))

        return findings

    def validate_treatment(self, drug: str, indication: str, patient_context: str = "") -> FactCheckResult:
        """
        Validate a specific treatment against contraindications.

        Args:
            drug: Drug name
            indication: Why it's being given
            patient_context: Patient details that might affect appropriateness

        Returns:
            FactCheckResult
        """
        drug_lower = drug.lower()
        context_lower = patient_context.lower()

        if drug_lower in self.DRUG_CONTRAINDICATIONS:
            for ci in self.DRUG_CONTRAINDICATIONS[drug_lower]:
                # Check if contraindication present in patient context
                condition_keywords = ci["condition"].lower().split()
                if any(kw in context_lower for kw in condition_keywords if len(kw) > 3):
                    return FactCheckResult(
                        claim=f"{drug} for {indication}",
                        is_valid=False,
                        severity=FactCheckSeverity.ERROR,
                        message=f"{drug} contraindicated: {ci['condition']}",
                        guideline_source=ci["source"]
                    )

        return FactCheckResult(
            claim=f"{drug} for {indication}",
            is_valid=True,
            severity=FactCheckSeverity.INFO,
            message="No contraindications detected",
            guideline_source=None
        )

    def validate_threshold(
        self,
        parameter: str,
        value: float,
        claimed_interpretation: str
    ) -> FactCheckResult:
        """
        Validate a clinical threshold interpretation.

        Args:
            parameter: Clinical parameter (e.g., "HbA1c", "systolic_bp")
            value: Numeric value
            claimed_interpretation: What's being claimed (e.g., "diabetes diagnosis")

        Returns:
            FactCheckResult
        """
        # Map common parameters to guideline keys
        parameter_map = {
            "hba1c": "hba1c_diabetes_diagnosis",
            "fasting_glucose": "fasting_glucose_diabetes",
            "systolic_bp": "hypertension_stage1_systolic",
            "map": "map_target_sepsis",
            "gfr": "ckd_gfr_threshold",
        }

        param_key = parameter.lower().replace(" ", "_")
        guideline_key = parameter_map.get(param_key)

        if guideline_key and guideline_key in self.CLINICAL_THRESHOLDS:
            guideline = self.CLINICAL_THRESHOLDS[guideline_key]

            # Check if value matches expected threshold
            if abs(value - guideline["value"]) > 0.5:  # Allow small tolerance
                return FactCheckResult(
                    claim=f"{parameter} = {value} interpreted as {claimed_interpretation}",
                    is_valid=False,
                    severity=FactCheckSeverity.WARNING,
                    message=f"Standard threshold is {guideline['value']} {guideline['unit']}",
                    guideline_source=guideline["source"],
                    suggested_correction=f"Use threshold of {guideline['value']} {guideline['unit']}"
                )

        return FactCheckResult(
            claim=f"{parameter} = {value}",
            is_valid=True,
            severity=FactCheckSeverity.INFO,
            message="Value within expected range or not in guidelines database",
            guideline_source=None
        )


# Singleton instance for easy import
clinical_fact_checker = ClinicalFactChecker()


def validate_question_facts(
    vignette: str,
    correct_answer: str,
    explanation: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a question's clinical facts.

    Returns:
        Tuple of (passed, list of issue messages)
    """
    report = clinical_fact_checker.validate_question(vignette, correct_answer, explanation)

    issues = []
    for finding in report.findings:
        if not finding.is_valid:
            issues.append(f"[{finding.severity.value.upper()}] {finding.message}")
            if finding.suggested_correction:
                issues[-1] += f" (Suggestion: {finding.suggested_correction})"

    return report.passed, issues
