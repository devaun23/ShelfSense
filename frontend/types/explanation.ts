/**
 * Enhanced Explanation Types for ShelfSense
 *
 * TypeScript types matching the backend Pydantic schemas for
 * structured medical explanations following the 6-type framework.
 */

// =============================================================================
// ENUMS
// =============================================================================

/**
 * The 6 clinical decision-making patterns for USMLE questions.
 * Each type maps to specific clinical reasoning frameworks.
 */
export type ExplanationType =
  | "TYPE_A_STABILITY"        // Patient stability assessment
  | "TYPE_B_TIME_SENSITIVE"   // Time-critical decisions
  | "TYPE_C_DIAGNOSTIC"       // Diagnostic sequence selection
  | "TYPE_D_RISK_STRATIFICATION"  // Risk scoring
  | "TYPE_E_TREATMENT_HIERARCHY"  // Treatment selection
  | "TYPE_F_DIFFERENTIAL";    // Differential diagnosis

export type DifficultyLevel = "basic" | "intermediate" | "advanced";

export type ReasoningComplexity = "single_step" | "multi_step" | "integration";

export type LearnerStage = "novice" | "intermediate" | "advanced";

export type ChoiceLetter = "A" | "B" | "C" | "D" | "E";

export type TrapFrequency = "very_common" | "common" | "occasional";

export type VisualAidType = "flowchart" | "comparison_table" | "decision_tree" | "diagram" | "timeline";

export type TimePressureFactor = "low" | "medium" | "high";

// =============================================================================
// TYPE-SPECIFIC COLORS AND LABELS
// =============================================================================

export const EXPLANATION_TYPE_CONFIG: Record<ExplanationType, {
  label: string;
  shortLabel: string;
  color: string;
  bgColor: string;
  description: string;
}> = {
  TYPE_A_STABILITY: {
    label: "Patient Stability",
    shortLabel: "Stability",
    color: "text-red-700",
    bgColor: "bg-red-100",
    description: "Assess if patient is stable vs unstable"
  },
  TYPE_B_TIME_SENSITIVE: {
    label: "Time-Sensitive",
    shortLabel: "Time",
    color: "text-orange-700",
    bgColor: "bg-orange-100",
    description: "Time-critical treatment windows"
  },
  TYPE_C_DIAGNOSTIC: {
    label: "Diagnostic Sequence",
    shortLabel: "Diagnostic",
    color: "text-blue-700",
    bgColor: "bg-blue-100",
    description: "Order of diagnostic testing"
  },
  TYPE_D_RISK_STRATIFICATION: {
    label: "Risk Stratification",
    shortLabel: "Risk",
    color: "text-purple-700",
    bgColor: "bg-purple-100",
    description: "Risk scoring and stratification"
  },
  TYPE_E_TREATMENT_HIERARCHY: {
    label: "Treatment Selection",
    shortLabel: "Treatment",
    color: "text-green-700",
    bgColor: "bg-green-100",
    description: "First-line vs alternative treatments"
  },
  TYPE_F_DIFFERENTIAL: {
    label: "Differential Diagnosis",
    shortLabel: "DDx",
    color: "text-yellow-700",
    bgColor: "bg-yellow-100",
    description: "Narrowing the differential"
  }
};

// =============================================================================
// COMPONENT INTERFACES
// =============================================================================

/**
 * Enhanced distractor explanation that addresses WHY students choose wrong answers.
 */
export interface DistractorExplanation {
  choice_letter: ChoiceLetter;
  /** Why this answer is incorrect for THIS specific patient */
  why_wrong: string;
  /** The cognitive error that leads students to choose this */
  common_misconception?: string;
  /** Clinical scenario where this WOULD be the right answer */
  when_correct?: string;
  /** Key takeaway to prevent this error in the future */
  teaching_point?: string;
}

/**
 * A single step in the clinical reasoning process.
 */
export interface StepByStep {
  step: number;
  /** What to do */
  action: string;
  /** Why this step */
  rationale: string;
  /** Specific numeric threshold if applicable (e.g., 'BP >180/120') */
  clinical_threshold?: string;
}

/**
 * In-depth pathophysiology and clinical context.
 */
export interface DeepDive {
  /** Mechanism of disease/treatment */
  pathophysiology: string;
  /** How to distinguish from similar conditions */
  differential_comparison?: string;
  /** 2-3 high-yield facts */
  clinical_pearls: string[];
  /** Relevant clinical guideline (e.g., 'AHA 2023 Heart Failure Guidelines') */
  guideline_reference?: string;
}

/**
 * Memory aids to help retention.
 */
export interface MemoryHooks {
  /** Relatable comparison to everyday concept */
  analogy?: string;
  /** Memory device if applicable */
  mnemonic?: string;
  /** Brief memorable clinical scenario */
  clinical_story?: string;
  /** Mental image to remember the concept */
  visual_cue?: string;
}

/**
 * Common mistakes students make.
 */
export interface CommonTrap {
  /** The common mistake */
  trap: string;
  /** Why this thinking fails */
  why_wrong: string;
  /** The right approach */
  correct_thinking: string;
  /** How often students fall into this trap */
  frequency?: TrapFrequency;
}

/**
 * Suggested visual representations for complex concepts.
 */
export interface VisualAid {
  type: VisualAidType;
  title: string;
  description: string;
  /** Key elements to include in the visual */
  elements?: string[];
}

/**
 * Factors contributing to question difficulty.
 */
export interface DifficultyFactors {
  content_difficulty: DifficultyLevel;
  reasoning_complexity: ReasoningComplexity;
  /** Estimated proportion of students who get this wrong (0-1) */
  common_error_rate?: number;
  /** Whether answer requires integrating multiple concepts */
  requires_integration: boolean;
  /** How much time pressure affects performance */
  time_pressure_factor?: TimePressureFactor;
}

// =============================================================================
// MAIN EXPLANATION INTERFACE
// =============================================================================

/**
 * Complete explanation structure for a ShelfSense question.
 *
 * This interface ensures all explanations follow a consistent, pedagogically
 * sound structure that supports different learner stages.
 */
export interface EnhancedExplanation {
  // === Classification ===
  /** Clinical decision-making pattern (TYPE_A through TYPE_F) */
  type: ExplanationType;

  // === Quick Access (always visible) ===
  /** 1-2 sentence direct answer (first thing students see) */
  quick_answer: string;
  /** Core decision rule using → notation */
  principle: string;

  // === Core Explanation ===
  /** 2-5 sentences with explicit thresholds, using → notation */
  clinical_reasoning: string;
  /** Why the correct answer is right, with pathophysiology */
  correct_answer_explanation: string;

  // === Distractor Analysis ===
  /** Explanation for each answer choice (all 5 required) */
  distractor_explanations: Record<ChoiceLetter, string | DistractorExplanation>;

  // === Deep Learning (expandable) ===
  deep_dive?: DeepDive;
  /** Numbered reasoning steps */
  step_by_step?: StepByStep[];
  memory_hooks?: MemoryHooks;
  /** Common mistakes to avoid */
  common_traps?: CommonTrap[];

  // === Visual Aids ===
  /** Suggested visual representations */
  visual_aids?: VisualAid[];

  // === Metadata ===
  /** What the student should learn from this question */
  educational_objective: string;
  /** Main concept being tested */
  concept?: string;
  /** Related concepts for further study */
  related_topics?: string[];
  difficulty_factors?: DifficultyFactors;

  // === Effectiveness Tracking ===
  /** Explanation version for A/B testing */
  version?: number;
}

// =============================================================================
// ADAPTIVE EXPLANATION VIEWS
// =============================================================================

/** Minimal explanation for advanced learners or quick review */
export interface QuickExplanation {
  type: ExplanationType;
  quick_answer: string;
  principle: string;
  common_traps?: CommonTrap[];
}

/** Standard explanation for intermediate learners */
export interface StandardExplanation {
  type: ExplanationType;
  quick_answer: string;
  principle: string;
  clinical_reasoning: string;
  correct_answer_explanation: string;
  distractor_explanations: Record<ChoiceLetter, string>;
  step_by_step?: StepByStep[];
  educational_objective: string;
}

/** Complete explanation with all fields */
export type FullExplanation = EnhancedExplanation;

// =============================================================================
// EFFECTIVENESS TRACKING
// =============================================================================

/** Track how effective an explanation is for learning */
export interface ExplanationEffectiveness {
  explanation_id: string;
  question_id: string;

  // Engagement metrics
  time_spent_seconds?: number;
  sections_expanded?: string[];
  scroll_depth_percent?: number;

  // Learning outcomes
  subsequent_similar_correct?: boolean;
  retention_test_correct?: boolean;

  // User feedback
  user_rating?: 1 | 2 | 3 | 4 | 5;
  user_feedback_text?: string;
  marked_helpful?: boolean;

  // A/B testing
  explanation_version?: number;
  variant?: string;
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Check if an explanation is in the legacy format and needs migration.
 */
export function isLegacyExplanation(explanation: unknown): boolean {
  if (typeof explanation === "string") return true;
  if (typeof explanation !== "object" || explanation === null) return true;

  const exp = explanation as Record<string, unknown>;
  return !("type" in exp) || !("quick_answer" in exp);
}

/**
 * Get the display configuration for an explanation type.
 */
export function getTypeConfig(type: ExplanationType) {
  return EXPLANATION_TYPE_CONFIG[type];
}

/**
 * Check if a distractor explanation is enhanced or simple string.
 */
export function isEnhancedDistractor(
  distractor: string | DistractorExplanation
): distractor is DistractorExplanation {
  return typeof distractor === "object" && "why_wrong" in distractor;
}

/**
 * Get explanation view based on learner stage.
 */
export function getExplanationView(
  explanation: EnhancedExplanation,
  stage: LearnerStage
): QuickExplanation | StandardExplanation | FullExplanation {
  switch (stage) {
    case "advanced":
      return {
        type: explanation.type,
        quick_answer: explanation.quick_answer,
        principle: explanation.principle,
        common_traps: explanation.common_traps?.slice(0, 2)
      };

    case "intermediate":
      return {
        type: explanation.type,
        quick_answer: explanation.quick_answer,
        principle: explanation.principle,
        clinical_reasoning: explanation.clinical_reasoning,
        correct_answer_explanation: explanation.correct_answer_explanation,
        distractor_explanations: Object.fromEntries(
          Object.entries(explanation.distractor_explanations).map(([k, v]) => [
            k,
            typeof v === "string" ? v : v.why_wrong
          ])
        ) as Record<ChoiceLetter, string>,
        step_by_step: explanation.step_by_step,
        educational_objective: explanation.educational_objective
      };

    case "novice":
    default:
      return explanation;
  }
}
