"""
Multi-Turn Reasoning Help Service

Provides scaffolded reasoning support across multiple conversation turns.
Tracks student progress through clinical reasoning steps and adapts guidance.

Key Features:
- Conversation state tracking (where is student in reasoning chain?)
- Progressive scaffolding (more help if stuck, less if progressing)
- Metacognitive prompts (help students understand their thinking)
- Breakthrough detection (recognize when student "gets it")
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime

from app.services.clinical_reasoning import (
    ReasoningFramework,
    CLINICAL_REASONING_FRAMEWORKS,
    ERROR_TYPE_FRAMEWORK_MAP
)


class ReasoningStage(str, Enum):
    """Stages in the clinical reasoning process."""
    GATHERING = "gathering"          # Collecting relevant info
    SYNTHESIZING = "synthesizing"    # Making sense of data
    HYPOTHESIZING = "hypothesizing"  # Forming differentials
    TESTING = "testing"              # Checking hypotheses
    CONCLUDING = "concluding"        # Reaching answer
    REFLECTING = "reflecting"        # Metacognition


class ProgressState(str, Enum):
    """Student progress indicators."""
    STUCK = "stuck"                  # No progress after 2+ turns
    STRUGGLING = "struggling"        # Partial progress, needs help
    PROGRESSING = "progressing"      # Moving forward
    BREAKTHROUGH = "breakthrough"    # Key insight achieved
    MASTERED = "mastered"           # Ready to move on


# Stage-specific scaffolding prompts (50-80 words max)
STAGE_SCAFFOLDS = {
    ReasoningStage.GATHERING: {
        "prompt": "What key findings jump out from this vignette?",
        "hints": [
            "Start with demographics and chief complaint.",
            "Note vital signs and physical exam findings.",
            "What lab or imaging results are given?"
        ],
        "stuck_help": "Let's simplify: What brought this patient in today? Just one or two words."
    },
    ReasoningStage.SYNTHESIZING: {
        "prompt": "How do these findings connect?",
        "hints": [
            "What pattern do you see?",
            "Which findings are abnormal?",
            "What syndrome does this suggest?"
        ],
        "stuck_help": "Pick ONE abnormal finding. What conditions cause that?"
    },
    ReasoningStage.HYPOTHESIZING: {
        "prompt": "What's on your differential?",
        "hints": [
            "What's the most likely diagnosis?",
            "What's the must-not-miss diagnosis?",
            "What would you bet money on?"
        ],
        "stuck_help": "Name just ONE condition that fits. Any guess is a start."
    },
    ReasoningStage.TESTING: {
        "prompt": "What argues for or against your hypothesis?",
        "hints": [
            "Does every finding fit your diagnosis?",
            "What finding doesn't quite fit?",
            "What would rule this out?"
        ],
        "stuck_help": "Look at your top diagnosis. What's ONE finding that supports it?"
    },
    ReasoningStage.CONCLUDING: {
        "prompt": "What's your final answer and why?",
        "hints": [
            "Which answer best fits ALL the findings?",
            "Eliminate answers that don't fit.",
            "Trust your systematic reasoning."
        ],
        "stuck_help": "You've done the work. Based on what you found, which answer fits best?"
    },
    ReasoningStage.REFLECTING: {
        "prompt": "What did you learn from this question?",
        "hints": [
            "What was the key insight?",
            "How will you recognize this pattern next time?",
            "What tripped you up initially?"
        ],
        "stuck_help": "In one sentence, what's the take-home point?"
    }
}


# Keywords indicating student progress or struggle
BREAKTHROUGH_INDICATORS = [
    "oh!", "i see", "that makes sense", "so it's", "because",
    "the key is", "i understand", "got it", "right, so",
    "now i realize", "of course", "that's why"
]

STRUGGLE_INDICATORS = [
    "i don't know", "confused", "not sure", "help",
    "stuck", "lost", "no idea", "what do you mean",
    "can you explain", "i give up", "just tell me"
]


def detect_reasoning_stage(
    message: str,
    history: List[Dict],
    error_type: Optional[str] = None
) -> ReasoningStage:
    """
    Detect where student is in the reasoning process.

    Args:
        message: Current student message
        history: Previous conversation messages
        error_type: Type of error if known

    Returns:
        Current reasoning stage
    """
    message_lower = message.lower()
    history_text = " ".join([m.get("message", "") for m in history]).lower()
    total_turns = len([m for m in history if m.get("role") == "user"])

    # Check for reflection stage (end of conversation)
    if total_turns >= 4 and any(ind in message_lower for ind in BREAKTHROUGH_INDICATORS):
        return ReasoningStage.REFLECTING

    # Check for concluding stage
    concluding_keywords = ["so the answer", "i think it's", "my answer is", "i'll go with"]
    if any(kw in message_lower for kw in concluding_keywords):
        return ReasoningStage.CONCLUDING

    # Check for testing stage
    testing_keywords = ["but what about", "doesn't fit", "rules out", "supports", "against"]
    if any(kw in message_lower for kw in testing_keywords):
        return ReasoningStage.TESTING

    # Check for hypothesizing stage
    hypothesis_keywords = ["could be", "might be", "differential", "i think", "maybe"]
    if any(kw in message_lower for kw in hypothesis_keywords):
        return ReasoningStage.HYPOTHESIZING

    # Check for synthesizing stage
    synthesis_keywords = ["pattern", "suggests", "points to", "consistent with", "means"]
    if any(kw in message_lower for kw in synthesis_keywords):
        return ReasoningStage.SYNTHESIZING

    # Default to gathering for early conversation
    return ReasoningStage.GATHERING


def assess_progress(
    current_message: str,
    history: List[Dict],
    current_stage: ReasoningStage,
    previous_stage: Optional[ReasoningStage] = None
) -> ProgressState:
    """
    Assess student's progress in reasoning.

    Args:
        current_message: Student's current message
        history: Conversation history
        current_stage: Current reasoning stage
        previous_stage: Previous reasoning stage

    Returns:
        Progress state indicator
    """
    message_lower = current_message.lower()
    user_turns = len([m for m in history if m.get("role") == "user"])

    # Check for breakthrough
    if any(ind in message_lower for ind in BREAKTHROUGH_INDICATORS):
        return ProgressState.BREAKTHROUGH

    # Check for struggle
    if any(ind in message_lower for ind in STRUGGLE_INDICATORS):
        if user_turns >= 3:
            return ProgressState.STUCK
        return ProgressState.STRUGGLING

    # Check for stage advancement
    stage_order = list(ReasoningStage)
    if previous_stage:
        prev_idx = stage_order.index(previous_stage)
        curr_idx = stage_order.index(current_stage)
        if curr_idx > prev_idx:
            return ProgressState.PROGRESSING

    # Check for mastery at end
    if current_stage == ReasoningStage.REFLECTING:
        return ProgressState.MASTERED

    # Default based on turn count
    if user_turns >= 4 and current_stage == ReasoningStage.GATHERING:
        return ProgressState.STUCK

    return ProgressState.PROGRESSING


def get_scaffolding_response(
    stage: ReasoningStage,
    progress: ProgressState,
    error_type: Optional[str] = None,
    turn_count: int = 1
) -> Dict:
    """
    Get appropriate scaffolding based on stage and progress.

    Args:
        stage: Current reasoning stage
        progress: Current progress state
        error_type: Error type if known
        turn_count: Number of conversation turns

    Returns:
        Dict with scaffolding guidance
    """
    scaffold = STAGE_SCAFFOLDS[stage]

    # Determine hint level based on progress
    if progress == ProgressState.STUCK:
        return {
            "type": "direct_help",
            "prompt": scaffold["stuck_help"],
            "advance_stage": True,
            "metacognitive": "It's okay to struggle - that's learning. Let's try a simpler step."
        }

    elif progress == ProgressState.STRUGGLING:
        hint_idx = min(turn_count - 1, len(scaffold["hints"]) - 1)
        return {
            "type": "hint",
            "prompt": scaffold["hints"][hint_idx],
            "advance_stage": False,
            "metacognitive": None
        }

    elif progress == ProgressState.BREAKTHROUGH:
        # Acknowledge insight and advance
        next_stage = _get_next_stage(stage)
        next_scaffold = STAGE_SCAFFOLDS.get(next_stage, scaffold)
        return {
            "type": "advance",
            "prompt": next_scaffold["prompt"],
            "advance_stage": True,
            "metacognitive": "Good insight. Now let's build on that."
        }

    elif progress == ProgressState.MASTERED:
        return {
            "type": "conclude",
            "prompt": "You've worked through this well. What's your key takeaway?",
            "advance_stage": False,
            "metacognitive": "Solid reasoning process - remember this approach."
        }

    else:  # PROGRESSING
        return {
            "type": "guide",
            "prompt": scaffold["prompt"],
            "advance_stage": False,
            "metacognitive": None
        }


def _get_next_stage(current: ReasoningStage) -> ReasoningStage:
    """Get the next stage in reasoning sequence."""
    stage_order = [
        ReasoningStage.GATHERING,
        ReasoningStage.SYNTHESIZING,
        ReasoningStage.HYPOTHESIZING,
        ReasoningStage.TESTING,
        ReasoningStage.CONCLUDING,
        ReasoningStage.REFLECTING
    ]
    curr_idx = stage_order.index(current)
    next_idx = min(curr_idx + 1, len(stage_order) - 1)
    return stage_order[next_idx]


def build_multi_turn_prompt(
    question_text: str,
    user_answer: str,
    correct_answer: str,
    error_type: Optional[str],
    history: List[Dict],
    current_message: str
) -> str:
    """
    Build system prompt for multi-turn reasoning support.

    Args:
        question_text: The clinical vignette
        user_answer: Student's answer
        correct_answer: Correct answer
        error_type: Error type if available
        history: Conversation history
        current_message: Student's current message

    Returns:
        System prompt string
    """
    # Detect current state
    stage = detect_reasoning_stage(current_message, history, error_type)

    # Get previous stage if available
    prev_stage = None
    if history:
        prev_msg = next((m for m in reversed(history) if m.get("role") == "user"), None)
        if prev_msg:
            prev_stage = detect_reasoning_stage(prev_msg.get("message", ""), history[:-2], error_type)

    # Assess progress
    progress = assess_progress(current_message, history, stage, prev_stage)

    # Get scaffolding
    turn_count = len([m for m in history if m.get("role") == "user"]) + 1
    scaffold = get_scaffolding_response(stage, progress, error_type, turn_count)

    # Get framework if error type exists
    framework_guidance = ""
    if error_type:
        framework = CLINICAL_REASONING_FRAMEWORKS.get(
            ERROR_TYPE_FRAMEWORK_MAP.get(error_type, ReasoningFramework.ANALYTICAL)
        )
        framework_guidance = f"\nFRAMEWORK: {framework['name']} - {framework['description']}"

    prompt = f"""You are a clinical reasoning coach guiding a student through multi-turn problem-solving.

VIGNETTE: {question_text}

STUDENT ANSWERED: {user_answer}
CORRECT ANSWER: {correct_answer}
{framework_guidance}

CURRENT STATE:
- Reasoning stage: {stage.value}
- Progress: {progress.value}
- Conversation turn: {turn_count}

SCAFFOLDING GUIDANCE:
- Type: {scaffold['type']}
- Suggested prompt: "{scaffold['prompt']}"
{"- Metacognitive note: " + scaffold['metacognitive'] if scaffold.get('metacognitive') else ""}

COACHING RULES:
1. 50-80 words MAX, never exceed 100
2. DO NOT reveal correct answer directly
3. Use the scaffolding prompt or adapt it naturally
4. ONE focused question or observation per response
5. Match guidance to their progress level
6. {"Advance them to next stage" if scaffold.get('advance_stage') else "Keep working at current stage"}

{"STUCK PROTOCOL: They've struggled. Give more direct help while keeping them engaged." if progress == ProgressState.STUCK else ""}
{"BREAKTHROUGH: Acknowledge their insight briefly, then build on it." if progress == ProgressState.BREAKTHROUGH else ""}
"""

    return prompt


def get_reasoning_state_summary(
    history: List[Dict],
    current_message: str,
    error_type: Optional[str] = None
) -> Dict:
    """
    Get a summary of the current reasoning state for API response.

    Args:
        history: Conversation history
        current_message: Current student message
        error_type: Error type if known

    Returns:
        Dict with reasoning state info
    """
    stage = detect_reasoning_stage(current_message, history, error_type)

    prev_stage = None
    if history:
        prev_msg = next((m for m in reversed(history) if m.get("role") == "user"), None)
        if prev_msg:
            prev_stage = detect_reasoning_stage(prev_msg.get("message", ""), history[:-2], error_type)

    progress = assess_progress(current_message, history, stage, prev_stage)
    turn_count = len([m for m in history if m.get("role") == "user"]) + 1

    return {
        "stage": stage.value,
        "progress": progress.value,
        "turn": turn_count,
        "stages_completed": _count_stages_completed(stage),
        "total_stages": 6
    }


def _count_stages_completed(current_stage: ReasoningStage) -> int:
    """Count how many stages have been completed."""
    stage_order = list(ReasoningStage)
    return stage_order.index(current_stage)
