"""
Enhanced Explanation Schemas for ShelfSense

This module defines Pydantic models for structured medical explanations
following the 6-type framework (TYPE_A through TYPE_F).

Features:
- Type-safe explanation structures
- Validation for required fields
- Enhanced distractor explanations with misconceptions
- Adaptive depth levels for different learner stages
- Visual aid suggestions
- Effectiveness tracking fields
"""

from typing import Optional, List, Dict, Literal, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class ExplanationType(str, Enum):
    """
    The 6 clinical decision-making patterns for USMLE questions.
    Each type maps to specific clinical reasoning frameworks.
    """
    TYPE_A_STABILITY = "TYPE_A_STABILITY"      # Patient stability assessment
    TYPE_B_TIME_SENSITIVE = "TYPE_B_TIME_SENSITIVE"  # Time-critical decisions
    TYPE_C_DIAGNOSTIC = "TYPE_C_DIAGNOSTIC"    # Diagnostic sequence selection
    TYPE_D_RISK_STRATIFICATION = "TYPE_D_RISK_STRATIFICATION"  # Risk scoring
    TYPE_E_TREATMENT_HIERARCHY = "TYPE_E_TREATMENT_HIERARCHY"  # Treatment selection
    TYPE_F_DIFFERENTIAL = "TYPE_F_DIFFERENTIAL"  # Differential diagnosis


class DifficultyLevel(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ReasoningComplexity(str, Enum):
    SINGLE_STEP = "single_step"
    MULTI_STEP = "multi_step"
    INTEGRATION = "integration"


class LearnerStage(str, Enum):
    """User learning stage for adaptive explanation depth."""
    NOVICE = "novice"          # Show everything expanded
    INTERMEDIATE = "intermediate"  # Core + step-by-step
    ADVANCED = "advanced"      # Quick answer + traps only


# =============================================================================
# COMPONENT SCHEMAS
# =============================================================================

class DistractorExplanation(BaseModel):
    """
    Enhanced distractor explanation that addresses WHY students choose wrong answers.
    """
    choice_letter: Literal["A", "B", "C", "D", "E"]
    why_wrong: str = Field(
        ...,
        min_length=20,
        max_length=300,
        description="Why this answer is incorrect for THIS specific patient"
    )
    common_misconception: Optional[str] = Field(
        None,
        max_length=200,
        description="The cognitive error that leads students to choose this"
    )
    when_correct: Optional[str] = Field(
        None,
        max_length=200,
        description="Clinical scenario where this WOULD be the right answer"
    )
    teaching_point: Optional[str] = Field(
        None,
        max_length=150,
        description="Key takeaway to prevent this error in the future"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "choice_letter": "B",
                "why_wrong": "Metformin is contraindicated in this patient with eGFR of 25 mL/min due to risk of lactic acidosis",
                "common_misconception": "Students often default to metformin as first-line for T2DM without checking renal function",
                "when_correct": "Would be appropriate if eGFR >30 mL/min and no planned contrast studies",
                "teaching_point": "Always check eGFR before prescribing metformin; contraindicated if <30"
            }
        }


class StepByStep(BaseModel):
    """A single step in the clinical reasoning process."""
    step: int = Field(..., ge=1, le=10)
    action: str = Field(..., min_length=10, max_length=200, description="What to do")
    rationale: str = Field(..., min_length=10, max_length=300, description="Why this step")
    clinical_threshold: Optional[str] = Field(
        None,
        description="Specific numeric threshold if applicable (e.g., 'BP >180/120')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "step": 1,
                "action": "Assess hemodynamic stability using vital signs",
                "rationale": "Unstable patients require immediate intervention before diagnostic workup",
                "clinical_threshold": "SBP <90 or HR >120 indicates instability"
            }
        }


class DeepDive(BaseModel):
    """In-depth pathophysiology and clinical context."""
    pathophysiology: str = Field(
        ...,
        min_length=50,
        max_length=500,
        description="Mechanism of disease/treatment"
    )
    differential_comparison: Optional[str] = Field(
        None,
        max_length=400,
        description="How to distinguish from similar conditions"
    )
    clinical_pearls: List[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=5,
        description="2-3 high-yield facts"
    )
    guideline_reference: Optional[str] = Field(
        None,
        max_length=200,
        description="Relevant clinical guideline (e.g., 'AHA 2023 Heart Failure Guidelines')"
    )


class MemoryHooks(BaseModel):
    """Memory aids to help retention."""
    analogy: Optional[str] = Field(
        None,
        max_length=200,
        description="Relatable comparison to everyday concept"
    )
    mnemonic: Optional[str] = Field(
        None,
        max_length=100,
        description="Memory device if applicable"
    )
    clinical_story: Optional[str] = Field(
        None,
        max_length=300,
        description="Brief memorable clinical scenario"
    )
    visual_cue: Optional[str] = Field(
        None,
        max_length=150,
        description="Mental image to remember the concept"
    )


class CommonTrap(BaseModel):
    """Common mistakes students make."""
    trap: str = Field(..., max_length=150, description="The common mistake")
    why_wrong: str = Field(..., max_length=200, description="Why this thinking fails")
    correct_thinking: str = Field(..., max_length=200, description="The right approach")
    frequency: Optional[Literal["very_common", "common", "occasional"]] = Field(
        None,
        description="How often students fall into this trap"
    )


class VisualAid(BaseModel):
    """Suggested visual representations for complex concepts."""
    type: Literal["flowchart", "comparison_table", "decision_tree", "diagram", "timeline"]
    title: str = Field(..., max_length=100)
    description: str = Field(..., max_length=300)
    elements: Optional[List[str]] = Field(
        None,
        description="Key elements to include in the visual"
    )


class DifficultyFactors(BaseModel):
    """Factors contributing to question difficulty."""
    content_difficulty: DifficultyLevel
    reasoning_complexity: ReasoningComplexity
    common_error_rate: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Estimated proportion of students who get this wrong"
    )
    requires_integration: bool = Field(
        False,
        description="Whether answer requires integrating multiple concepts"
    )
    time_pressure_factor: Optional[Literal["low", "medium", "high"]] = Field(
        None,
        description="How much time pressure affects performance"
    )


# =============================================================================
# MAIN EXPLANATION SCHEMA
# =============================================================================

class EnhancedExplanation(BaseModel):
    """
    Complete explanation structure for a ShelfSense question.

    This schema ensures all explanations follow a consistent, pedagogically
    sound structure that supports different learner stages and enables
    effectiveness tracking.
    """

    # === Classification ===
    type: ExplanationType = Field(
        ...,
        description="Clinical decision-making pattern (TYPE_A through TYPE_F)"
    )

    # === Quick Access (always visible) ===
    quick_answer: str = Field(
        ...,
        min_length=10,
        max_length=150,
        description="1-2 sentence direct answer (first thing students see)"
    )

    principle: str = Field(
        ...,
        min_length=20,
        max_length=200,
        description="Core decision rule using → notation"
    )

    # === Core Explanation ===
    clinical_reasoning: str = Field(
        ...,
        min_length=50,
        max_length=500,
        description="2-5 sentences with explicit thresholds, using → notation"
    )

    correct_answer_explanation: str = Field(
        ...,
        min_length=50,
        max_length=600,
        description="Why the correct answer is right, with pathophysiology"
    )

    # === Distractor Analysis ===
    distractor_explanations: Dict[Literal["A", "B", "C", "D", "E"], Union[str, DistractorExplanation]] = Field(
        ...,
        description="Explanation for each answer choice (all 5 required)"
    )

    # === Deep Learning (expandable) ===
    deep_dive: Optional[DeepDive] = None

    step_by_step: List[StepByStep] = Field(
        default_factory=list,
        max_length=8,
        description="Numbered reasoning steps"
    )

    memory_hooks: Optional[MemoryHooks] = None

    common_traps: List[CommonTrap] = Field(
        default_factory=list,
        max_length=4,
        description="Common mistakes to avoid"
    )

    # === Visual Aids ===
    visual_aids: List[VisualAid] = Field(
        default_factory=list,
        max_length=3,
        description="Suggested visual representations"
    )

    # === Metadata ===
    educational_objective: str = Field(
        ...,
        max_length=200,
        description="What the student should learn from this question"
    )

    concept: Optional[str] = Field(
        None,
        max_length=100,
        description="Main concept being tested"
    )

    related_topics: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Related concepts for further study"
    )

    difficulty_factors: Optional[DifficultyFactors] = None

    # === Effectiveness Tracking ===
    version: int = Field(default=1, description="Explanation version for A/B testing")

    @field_validator('distractor_explanations')
    @classmethod
    def validate_all_choices_present(cls, v):
        """Ensure all 5 answer choices have explanations."""
        required_choices = {"A", "B", "C", "D", "E"}
        if set(v.keys()) != required_choices:
            missing = required_choices - set(v.keys())
            raise ValueError(f"Missing distractor explanations for: {missing}")
        return v

    @field_validator('clinical_reasoning')
    @classmethod
    def validate_arrow_notation(cls, v):
        """Ensure clinical reasoning uses arrow notation for flow."""
        if "→" not in v and "->" not in v:
            # Soft warning - don't fail validation
            pass
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "type": "TYPE_A_STABILITY",
                "quick_answer": "This patient with septic shock requires immediate IV fluid resuscitation and vasopressors, not oral antibiotics.",
                "principle": "Hemodynamic instability (SBP <90, MAP <65) → IV access + fluids + vasopressors before any other intervention",
                "clinical_reasoning": "Patient presents with fever, tachycardia (HR 118), hypotension (BP 82/54), and altered mental status → septic shock. Initial management: IV crystalloid 30 mL/kg within first 3 hours → if MAP remains <65, start norepinephrine → blood cultures before antibiotics but don't delay antibiotics >1 hour.",
                "correct_answer_explanation": "IV fluid resuscitation with crystalloids is the first-line treatment for septic shock. The Surviving Sepsis Campaign guidelines recommend 30 mL/kg within the first 3 hours. This patient's hypotension (MAP ~63) and signs of tissue hypoperfusion require immediate volume expansion.",
                "distractor_explanations": {
                    "A": {
                        "choice_letter": "A",
                        "why_wrong": "Oral antibiotics are inappropriate for septic shock due to unreliable absorption in hypoperfused gut",
                        "common_misconception": "Students may focus on infection treatment without recognizing shock state",
                        "when_correct": "Appropriate for stable patients with uncomplicated infections (e.g., outpatient UTI)",
                        "teaching_point": "Shock = IV access mandatory; oral medications unreliable"
                    },
                    "B": "This is the correct answer",
                    "C": {
                        "choice_letter": "C",
                        "why_wrong": "CT imaging delays resuscitation and is not indicated for septic shock management",
                        "common_misconception": "Desire to find source should not delay resuscitation",
                        "when_correct": "After initial stabilization if source unclear",
                        "teaching_point": "Stabilize first, then diagnose source"
                    },
                    "D": {
                        "choice_letter": "D",
                        "why_wrong": "Observation alone will lead to cardiovascular collapse in septic shock",
                        "common_misconception": "Underestimating severity of hypotension",
                        "when_correct": "Never appropriate in shock states",
                        "teaching_point": "MAP <65 requires immediate intervention"
                    },
                    "E": {
                        "choice_letter": "E",
                        "why_wrong": "Steroids are not first-line and only indicated if shock refractory to fluids and vasopressors",
                        "common_misconception": "Steroids are adjunctive, not primary resuscitation",
                        "when_correct": "Consider if patient remains hypotensive despite adequate fluids and vasopressors",
                        "teaching_point": "Steroids = refractory shock only"
                    }
                },
                "deep_dive": {
                    "pathophysiology": "Septic shock results from dysregulated host response to infection causing vasodilation, capillary leak, and myocardial depression. Hypoperfusion leads to lactate accumulation and multi-organ dysfunction.",
                    "differential_comparison": "Distinguish from cardiogenic shock (elevated JVP, pulmonary edema) and hypovolemic shock (clear fluid loss history).",
                    "clinical_pearls": [
                        "MAP <65 defines shock regardless of SBP",
                        "Lactate >2 indicates tissue hypoperfusion",
                        "Hour-1 bundle: cultures, antibiotics, fluids, vasopressors if needed"
                    ]
                },
                "step_by_step": [
                    {"step": 1, "action": "Recognize shock state", "rationale": "BP 82/54 with altered mental status = inadequate tissue perfusion", "clinical_threshold": "MAP <65 or SBP <90"},
                    {"step": 2, "action": "Establish IV access", "rationale": "Required for fluid and medication delivery"},
                    {"step": 3, "action": "Administer 30 mL/kg crystalloid", "rationale": "Guideline-recommended initial resuscitation volume", "clinical_threshold": "Within 3 hours of presentation"},
                    {"step": 4, "action": "Start vasopressors if hypotension persists", "rationale": "Norepinephrine first-line if MAP <65 despite fluids"}
                ],
                "memory_hooks": {
                    "analogy": "Septic shock is like a leaky garden hose - you need to both fill the tank (fluids) and squeeze the hose (vasopressors) to maintain pressure",
                    "mnemonic": "SEPSIS-6: Blood cultures, Lactate, Oxygen, Fluids, Antibiotics, Urine output",
                    "clinical_story": "Think of the ER patient who 'just has a UTI' but has HR 120 and BP 85/50 - this is septic shock until proven otherwise"
                },
                "common_traps": [
                    {
                        "trap": "Waiting for culture results before starting antibiotics",
                        "why_wrong": "Mortality increases 7.6% per hour of delayed antibiotics",
                        "correct_thinking": "Draw cultures, then immediately give broad-spectrum antibiotics",
                        "frequency": "very_common"
                    }
                ],
                "visual_aids": [
                    {
                        "type": "flowchart",
                        "title": "Septic Shock Management Algorithm",
                        "description": "Decision flow from recognition through resuscitation",
                        "elements": ["Recognize shock", "IV access", "30mL/kg fluids", "Reassess MAP", "Vasopressors if needed"]
                    }
                ],
                "educational_objective": "Recognize septic shock and initiate appropriate resuscitation with IV fluids before other interventions",
                "concept": "Septic shock management",
                "related_topics": ["SIRS criteria", "Surviving Sepsis Campaign", "Vasopressor selection", "Lactate clearance"],
                "difficulty_factors": {
                    "content_difficulty": "intermediate",
                    "reasoning_complexity": "multi_step",
                    "common_error_rate": 0.25,
                    "requires_integration": True,
                    "time_pressure_factor": "high"
                }
            }
        }


# =============================================================================
# ADAPTIVE EXPLANATION VIEWS
# =============================================================================

class QuickExplanation(BaseModel):
    """Minimal explanation for advanced learners or quick review."""
    type: ExplanationType
    quick_answer: str
    principle: str
    common_traps: List[CommonTrap] = Field(default_factory=list, max_length=2)


class StandardExplanation(BaseModel):
    """Standard explanation for intermediate learners."""
    type: ExplanationType
    quick_answer: str
    principle: str
    clinical_reasoning: str
    correct_answer_explanation: str
    distractor_explanations: Dict[str, str]
    step_by_step: List[StepByStep]
    educational_objective: str


class FullExplanation(EnhancedExplanation):
    """Complete explanation with all fields - alias for EnhancedExplanation."""
    pass


# =============================================================================
# EFFECTIVENESS TRACKING
# =============================================================================

class ExplanationEffectiveness(BaseModel):
    """Track how effective an explanation is for learning."""
    explanation_id: str
    question_id: str

    # Engagement metrics
    time_spent_seconds: Optional[int] = None
    sections_expanded: List[str] = Field(default_factory=list)
    scroll_depth_percent: Optional[float] = Field(None, ge=0, le=100)

    # Learning outcomes
    subsequent_similar_correct: Optional[bool] = None
    retention_test_correct: Optional[bool] = None

    # User feedback
    user_rating: Optional[Literal[1, 2, 3, 4, 5]] = None
    user_feedback_text: Optional[str] = None
    marked_helpful: Optional[bool] = None

    # A/B testing
    explanation_version: int = 1
    variant: Optional[str] = None


# =============================================================================
# MIGRATION HELPERS
# =============================================================================

class LegacyExplanation(BaseModel):
    """Schema for legacy text-only explanations before migration."""
    text: str
    needs_migration: bool = True


def is_legacy_explanation(explanation: Union[str, dict]) -> bool:
    """Check if an explanation needs migration to new format."""
    if isinstance(explanation, str):
        return True
    if isinstance(explanation, dict):
        return "type" not in explanation or "quick_answer" not in explanation
    return True
