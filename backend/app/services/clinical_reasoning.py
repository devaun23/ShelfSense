"""
Clinical Reasoning Frameworks Service

Provides structured clinical reasoning frameworks for the AI Chat Tutor.
Based on medical education research and NBME question patterns.

Frameworks:
1. Illness Scripts - Pattern recognition for diagnoses
2. Problem Representation - Summarizing clinical data
3. Schema-Based Reasoning - Mental models for pathophysiology
4. Analytical Reasoning - Systematic differential diagnosis
5. Dual Process Theory - Type 1 (intuitive) vs Type 2 (analytical)
"""

from typing import Dict, List, Optional
from enum import Enum


class ReasoningFramework(str, Enum):
    """Clinical reasoning frameworks aligned with medical education."""
    ILLNESS_SCRIPT = "illness_script"
    PROBLEM_REPRESENTATION = "problem_representation"
    SCHEMA_BASED = "schema_based"
    ANALYTICAL = "analytical"
    DUAL_PROCESS = "dual_process"


# Framework definitions with Socratic prompts
CLINICAL_REASONING_FRAMEWORKS = {
    ReasoningFramework.ILLNESS_SCRIPT: {
        "name": "Illness Script Framework",
        "description": "Pattern matching clinical presentations to disease prototypes",
        "components": [
            "Epidemiology (who gets this?)",
            "Pathophysiology (what's happening?)",
            "Time course (how does it evolve?)",
            "Clinical features (what do we see?)",
            "Enabling conditions (what predisposes?)"
        ],
        "socratic_prompts": [
            "What patient population typically presents this way?",
            "What's the underlying mechanism causing these symptoms?",
            "How would you expect this condition to progress untreated?",
            "What's the classic presentation you'd expect to see?",
            "What risk factors made this patient vulnerable?"
        ],
        "thinking_prompt": """Walk through the illness script:
1. WHO gets this? (age, gender, risk factors)
2. WHAT is happening physiologically?
3. WHEN/HOW does it typically present and progress?
4. WHAT are the cardinal features we'd expect?"""
    },

    ReasoningFramework.PROBLEM_REPRESENTATION: {
        "name": "Problem Representation",
        "description": "Distilling key clinical data into a one-sentence summary",
        "components": [
            "Patient demographics",
            "Key clinical features (2-3 max)",
            "Temporal pattern",
            "Syndrome identification"
        ],
        "socratic_prompts": [
            "Can you summarize this patient in one sentence?",
            "What are the 2-3 most important findings here?",
            "How would you describe the timeline of this illness?",
            "What syndrome does this pattern suggest?"
        ],
        "thinking_prompt": """Create a problem representation:
"This is a [age] [gender] with [key risk factors] presenting with [duration] of [cardinal symptoms] suggesting [syndrome/diagnosis]."

What details are essential? What can be omitted?"""
    },

    ReasoningFramework.SCHEMA_BASED: {
        "name": "Schema-Based Reasoning",
        "description": "Using pathophysiologic mental models to predict findings",
        "components": [
            "Underlying mechanism",
            "Expected manifestations",
            "Compensatory responses",
            "Complications pathway"
        ],
        "socratic_prompts": [
            "What's the pathophysiology that connects these findings?",
            "If this mechanism is correct, what else would you expect to find?",
            "How would the body try to compensate for this?",
            "What complications could develop from this process?"
        ],
        "thinking_prompt": """Apply schema-based reasoning:
1. What pathophysiologic process explains these findings?
2. Given this mechanism, what other findings would you predict?
3. What would you NOT expect to see if this is the diagnosis?
4. How does treatment interrupt this pathway?"""
    },

    ReasoningFramework.ANALYTICAL: {
        "name": "Analytical Reasoning",
        "description": "Systematic hypothesis testing with differential diagnosis",
        "components": [
            "Generate differential",
            "Prioritize by probability/severity",
            "Identify discriminating features",
            "Test and revise hypotheses"
        ],
        "socratic_prompts": [
            "What's on your differential for this presentation?",
            "Which diagnosis would be most dangerous to miss?",
            "What finding would make you favor one diagnosis over another?",
            "What test would best discriminate between your top two diagnoses?",
            "What finding argues against your leading diagnosis?"
        ],
        "thinking_prompt": """Work through the differential systematically:
1. List possible diagnoses (must-not-miss first)
2. What key features SUPPORT each diagnosis?
3. What features ARGUE AGAINST each diagnosis?
4. What single test would most change your thinking?"""
    },

    ReasoningFramework.DUAL_PROCESS: {
        "name": "Dual Process Theory",
        "description": "Balancing intuitive (Type 1) and analytical (Type 2) thinking",
        "components": [
            "Type 1: Pattern recognition, fast",
            "Type 2: Analytical, deliberate",
            "Metacognition: Knowing when to switch",
            "Cognitive forcing: Debiasing strategies"
        ],
        "socratic_prompts": [
            "What was your first instinct when you read this question?",
            "What made you change your mind (if you did)?",
            "Did you consider any alternatives before choosing?",
            "What would make you slow down and reconsider?"
        ],
        "thinking_prompt": """Check your reasoning process:
1. What did your gut tell you first? (Type 1)
2. Did you verify that instinct systematically? (Type 2)
3. What biases might be affecting your thinking?
4. What would an expert do differently here?"""
    }
}


# Question type to framework mapping (from EXPLANATION_FRAMEWORK.md)
QUESTION_TYPE_FRAMEWORK_MAP = {
    "TYPE_A_STABILITY": [ReasoningFramework.ILLNESS_SCRIPT, ReasoningFramework.DUAL_PROCESS],
    "TYPE_B_TIME_SENSITIVE": [ReasoningFramework.SCHEMA_BASED, ReasoningFramework.ANALYTICAL],
    "TYPE_C_DIAGNOSTIC": [ReasoningFramework.ANALYTICAL, ReasoningFramework.PROBLEM_REPRESENTATION],
    "TYPE_D_RISK_STRATIFICATION": [ReasoningFramework.SCHEMA_BASED, ReasoningFramework.ANALYTICAL],
    "TYPE_E_TREATMENT_HIERARCHY": [ReasoningFramework.SCHEMA_BASED, ReasoningFramework.ILLNESS_SCRIPT],
    "TYPE_F_DIFFERENTIAL": [ReasoningFramework.ANALYTICAL, ReasoningFramework.PROBLEM_REPRESENTATION]
}


# Error type to framework mapping (from error_categorization.py)
ERROR_TYPE_FRAMEWORK_MAP = {
    "knowledge_gap": ReasoningFramework.ILLNESS_SCRIPT,
    "premature_closure": ReasoningFramework.ANALYTICAL,
    "misread_stem": ReasoningFramework.PROBLEM_REPRESENTATION,
    "faulty_reasoning": ReasoningFramework.SCHEMA_BASED,
    "test_taking_error": ReasoningFramework.DUAL_PROCESS,
    "time_pressure": ReasoningFramework.DUAL_PROCESS
}


def get_framework_for_error(error_type: str) -> Dict:
    """
    Get the most appropriate reasoning framework based on error type.

    Args:
        error_type: One of the 6 error types from error_categorization.py

    Returns:
        Dict containing framework details and Socratic prompts
    """
    framework_key = ERROR_TYPE_FRAMEWORK_MAP.get(error_type, ReasoningFramework.ANALYTICAL)
    return CLINICAL_REASONING_FRAMEWORKS[framework_key]


def get_framework_for_question_type(question_type: str) -> List[Dict]:
    """
    Get appropriate reasoning frameworks based on question type.

    Args:
        question_type: One of TYPE_A through TYPE_F

    Returns:
        List of framework dicts ordered by relevance
    """
    framework_keys = QUESTION_TYPE_FRAMEWORK_MAP.get(
        question_type,
        [ReasoningFramework.ANALYTICAL]
    )
    return [CLINICAL_REASONING_FRAMEWORKS[key] for key in framework_keys]


def generate_socratic_prompt(
    framework: ReasoningFramework,
    context: Optional[str] = None,
    attempt_number: int = 1
) -> str:
    """
    Generate a Socratic question based on framework and conversation depth.

    Args:
        framework: Which reasoning framework to use
        context: Optional context about what student is struggling with
        attempt_number: How many exchanges in this coaching session

    Returns:
        A Socratic question string
    """
    framework_data = CLINICAL_REASONING_FRAMEWORKS[framework]
    prompts = framework_data["socratic_prompts"]

    # Progress through prompts as conversation deepens
    prompt_index = min(attempt_number - 1, len(prompts) - 1)
    return prompts[prompt_index]


def build_reasoning_coach_prompt(
    error_type: str,
    question_text: str,
    user_answer: str,
    correct_answer: str,
    explanation: Optional[Dict] = None
) -> str:
    """
    Build a comprehensive coaching prompt using clinical reasoning frameworks.

    This creates the system prompt for AI tutoring that guides students
    through structured clinical reasoning rather than just giving answers.

    Args:
        error_type: The categorized error type
        question_text: The clinical vignette
        user_answer: What the student chose
        correct_answer: The correct answer
        explanation: Optional structured explanation dict

    Returns:
        System prompt string for the AI tutor
    """
    framework = get_framework_for_error(error_type)

    prompt = f"""You are a clinical reasoning coach using the {framework['name']} approach.

FRAMEWORK: {framework['description']}

KEY COMPONENTS TO EXPLORE:
{chr(10).join(f'- {c}' for c in framework['components'])}

GUIDING QUESTIONS (use progressively):
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(framework['socratic_prompts']))}

THINKING FRAMEWORK TO GUIDE STUDENT:
{framework['thinking_prompt']}

---

CLINICAL VIGNETTE:
{question_text}

STUDENT'S ANSWER: {user_answer}
CORRECT ANSWER: {correct_answer}
ERROR TYPE: {error_type}

---

COACHING RULES:
1. BE EXTREMELY CONCISE - aim for 50-80 words, NEVER exceed 100 words
2. DO NOT reveal the correct answer directly
3. Use ONE Socratic question to guide discovery
4. Reference ONE specific clinical detail from the vignette
5. If they seem stuck after 2-3 exchanges, provide a brief hint

COACHING STRATEGY FOR {error_type.upper().replace('_', ' ')}:
"""

    # Add error-specific coaching guidance (concise)
    coaching_strategies = {
        "knowledge_gap": "Ask what they DO know, then build from there with one key fact.",
        "premature_closure": "Ask what OTHER diagnoses they considered. Point to one finding that doesn't fit.",
        "misread_stem": "Point them to ONE specific finding they may have missed. Ask what it suggests.",
        "faulty_reasoning": "Ask them to trace the mechanism. Where does the logic break?",
        "test_taking_error": "Ask what made them change their answer. Trust systematic reasoning.",
        "time_pressure": "Focus on pattern recognition. What's the key finding here?"
    }

    prompt += coaching_strategies.get(error_type, "Use Socratic questioning to guide discovery.")

    return prompt


def get_step_by_step_reasoning_template(question_type: str) -> str:
    """
    Get a step-by-step reasoning template for the given question type.

    This provides structured guidance for working through different
    types of NBME questions systematically.

    Args:
        question_type: One of TYPE_A through TYPE_F

    Returns:
        Formatted reasoning template string
    """
    templates = {
        "TYPE_A_STABILITY": """
STEP-BY-STEP: STABLE VS UNSTABLE PATIENT

Step 1: Check vital signs for instability markers
- BP < 90 systolic?
- HR > 120?
- O2 sat < 92%?
- Altered mental status?

Step 2: If UNSTABLE → What immediate intervention?
- Airway? Breathing? Circulation?
- Source control?
- Resuscitation?

Step 3: If STABLE → What's the appropriate workup/management?
- Can we do more testing?
- Medical management first?
- Scheduled intervention?
""",
        "TYPE_B_TIME_SENSITIVE": """
STEP-BY-STEP: TIME-SENSITIVE DECISIONS

Step 1: Identify the time-sensitive condition
- Stroke (tPA window: 4.5 hrs)
- MI (door-to-balloon: 90 min)
- Sepsis (antibiotics: 1 hr)

Step 2: Calculate time since onset
- When did symptoms start?
- Are we within the window?

Step 3: Match intervention to time window
- Within window → specific intervention
- Outside window → alternative approach
""",
        "TYPE_C_DIAGNOSTIC": """
STEP-BY-STEP: DIAGNOSTIC SEQUENCE

Step 1: What's the clinical suspicion?
- Pre-test probability

Step 2: What's the FIRST test?
- Usually: screening test (sensitive)
- Non-invasive before invasive
- Cheap before expensive

Step 3: What CONFIRMS the diagnosis?
- Confirmatory test (specific)
- Gold standard if needed

Step 4: Can you skip steps?
- Only if high pre-test probability
- Only if test is both sensitive AND specific
""",
        "TYPE_D_RISK_STRATIFICATION": """
STEP-BY-STEP: RISK STRATIFICATION

Step 1: Identify the scoring system
- Wells (PE/DVT)
- CURB-65 (pneumonia)
- CHADS-VASc (afib)
- HEART score (ACS)

Step 2: Calculate the score
- List each criterion
- Add up points

Step 3: Apply the threshold
- Low risk → what management?
- High risk → what management?
- Borderline → additional testing?
""",
        "TYPE_E_TREATMENT_HIERARCHY": """
STEP-BY-STEP: TREATMENT SELECTION

Step 1: What's first-line for this condition?
- Guidelines recommend...
- In absence of contraindications...

Step 2: Any contraindications present?
- Allergies?
- Organ dysfunction?
- Drug interactions?
- Pregnancy?

Step 3: If contraindicated, what's second-line?
- Alternative with same efficacy?
- Alternative mechanism?
""",
        "TYPE_F_DIFFERENTIAL": """
STEP-BY-STEP: DIFFERENTIAL NARROWING

Step 1: List the differential
- What could cause this presentation?
- Don't forget must-not-miss diagnoses

Step 2: Find the discriminating feature
- What finding is SPECIFIC to one diagnosis?
- What would rule OUT your top diagnosis?

Step 3: Match finding to diagnosis
- Only diagnosis X causes finding Y
- Finding Y eliminates diagnosis Z
"""
    }

    return templates.get(question_type, templates["TYPE_F_DIFFERENTIAL"])


def detect_question_type(vignette: str, choices: List[str]) -> str:
    """
    Attempt to classify question type based on content analysis.

    This is a heuristic approach - the AI can refine this classification
    during the tutoring session.

    Args:
        vignette: The clinical scenario text
        choices: The answer choices

    Returns:
        Predicted question type string
    """
    vignette_lower = vignette.lower()

    # Stability indicators
    stability_keywords = ["hypotensive", "tachycardic", "unstable", "shock",
                         "bp 80", "bp 70", "bp 60", "altered mental", "unresponsive"]
    if any(kw in vignette_lower for kw in stability_keywords):
        return "TYPE_A_STABILITY"

    # Time-sensitive indicators
    time_keywords = ["hours ago", "minutes ago", "within", "window", "onset",
                    "sudden", "acute", "thunderclap", "woke up with"]
    if any(kw in vignette_lower for kw in time_keywords):
        return "TYPE_B_TIME_SENSITIVE"

    # Diagnostic sequence indicators
    diagnostic_keywords = ["next step", "next best", "initial test", "first test",
                          "confirm", "diagnose", "workup"]
    choices_text = " ".join(choices).lower()
    if any(kw in vignette_lower or kw in choices_text for kw in diagnostic_keywords):
        return "TYPE_C_DIAGNOSTIC"

    # Risk stratification indicators
    risk_keywords = ["score", "risk", "probability", "likelihood", "stratif",
                    "wells", "curb", "chads", "heart score"]
    if any(kw in vignette_lower for kw in risk_keywords):
        return "TYPE_D_RISK_STRATIFICATION"

    # Treatment hierarchy indicators
    treatment_keywords = ["treatment", "medication", "drug of choice", "first-line",
                         "management", "therapy", "prescribe"]
    if any(kw in vignette_lower or kw in choices_text for kw in treatment_keywords):
        return "TYPE_E_TREATMENT_HIERARCHY"

    # Default to differential narrowing
    return "TYPE_F_DIFFERENTIAL"
