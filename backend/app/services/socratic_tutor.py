"""
Enhanced Socratic AI Tutor Service

Provides guided discovery learning using the Socratic method.
Never gives direct answers first; instead asks guiding questions
that lead students to discover the answer themselves.

Key Features:
- Clinical reasoning frameworks (Chief Complaint → DDx → Workup → Diagnosis → Management)
- Breadcrumb hints that progressively reveal information
- Reasoning gap identification and tracking
- "Teach Me" mode for concept explanations
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Question, QuestionAttempt, ErrorAnalysis, ChatMessage, generate_uuid
)


# Clinical reasoning stages in order
CLINICAL_REASONING_STAGES = [
    ("chief_complaint", "Identify the Chief Complaint", "What is the patient's main problem?"),
    ("history", "Gather History", "What key historical details are relevant?"),
    ("physical_exam", "Physical Examination", "What examination findings are significant?"),
    ("differential", "Generate Differential", "What diagnoses could explain this presentation?"),
    ("workup", "Plan Workup", "What tests would help narrow the differential?"),
    ("diagnosis", "Make Diagnosis", "What is the most likely diagnosis?"),
    ("management", "Plan Management", "What is the appropriate treatment?"),
]


# Breadcrumb hint templates by error type
BREADCRUMB_HINTS = {
    "knowledge_gap": [
        "Let's start with what you do know about this presentation...",
        "In this demographic, what conditions commonly present this way?",
        "The key finding here is {key_finding}. What does that tell you?",
        "Think about the pathophysiology: {mechanism_hint}",
        "The answer involves {partial_answer}. Can you connect the dots?"
    ],
    "premature_closure": [
        "Good thought, but let's make sure we're not missing anything...",
        "What other diagnoses could present similarly?",
        "Notice {contradicting_finding}. Does that fit your diagnosis?",
        "What would you expect to see if your diagnosis was correct?",
        "Consider: {correct_diagnosis} would also explain these findings."
    ],
    "misread_stem": [
        "Let's reread the stem carefully. What stands out?",
        "Did you notice the {missed_detail}?",
        "The timing is important here: {temporal_detail}",
        "This finding is crucial: {critical_finding}",
        "With {key_finding}, what diagnosis fits best?"
    ],
    "faulty_reasoning": [
        "Walk me through your reasoning step by step...",
        "If {mechanism} causes {symptom}, what else would you expect?",
        "The pathophysiology here is: {pathway}",
        "Your reasoning breaks at: {error_point}",
        "The connection is: {correct_reasoning}"
    ],
    "test_taking_error": [
        "What was your initial instinct?",
        "Why did you change your answer?",
        "Trust your systematic approach over gut feelings...",
        "First instinct was {first_choice}. Why did you switch?",
        "The question is asking about {actual_question}"
    ],
    "time_pressure": [
        "Let's slow down and focus on the key finding...",
        "What's the one detail that matters most here?",
        "Classic presentation for {condition}: {classic_features}",
        "The buzzword here is {buzzword}",
        "Pattern: {pattern} → {answer}"
    ]
}


# Teach Me templates for different concepts
TEACH_ME_TEMPLATES = {
    "pathophysiology": """
Explain the pathophysiology of {topic} in a clear, stepwise manner:

1. Normal physiology: {normal_function}
2. What goes wrong: {dysfunction}
3. Resulting symptoms: {symptoms}
4. Key diagnostic findings: {findings}
5. Treatment approach: {treatment}

Keep it concise and clinically relevant. No more than 150 words.
""",
    "differential": """
For a patient presenting with {presentation}, create a differential diagnosis:

Most likely:
1. {diagnosis_1} - because {reason_1}
2. {diagnosis_2} - because {reason_2}
3. {diagnosis_3} - because {reason_3}

Must-not-miss:
- {dangerous_1}
- {dangerous_2}

Key discriminating features to look for: {discriminators}
""",
    "management": """
Step-by-step management of {condition}:

Immediate (within minutes):
- {immediate_steps}

Short-term (within hours):
- {short_term}

Long-term:
- {long_term}

Key medications and dosing: {medications}
Monitoring parameters: {monitoring}
"""
}


def get_reasoning_stage(conversation_history: List[Dict]) -> Tuple[str, int]:
    """
    Determine which clinical reasoning stage the student is at based on conversation.

    Returns:
        Tuple of (current_stage_id, stage_index)
    """
    # Analyze conversation for stage indicators
    if not conversation_history:
        return ("chief_complaint", 0)

    # Simple heuristic based on turn count and content
    turn_count = len([m for m in conversation_history if m.get("role") == "user"])

    # Progress through stages based on conversation depth
    stage_index = min(turn_count, len(CLINICAL_REASONING_STAGES) - 1)
    return (CLINICAL_REASONING_STAGES[stage_index][0], stage_index)


def generate_socratic_question(
    question: Question,
    error_type: Optional[str],
    conversation_history: List[Dict],
    user_message: str
) -> str:
    """
    Generate a Socratic question that guides the student without giving the answer.
    """
    stage_id, stage_index = get_reasoning_stage(conversation_history)
    stage_name = CLINICAL_REASONING_STAGES[stage_index][1]
    stage_question = CLINICAL_REASONING_STAGES[stage_index][2]

    # Base Socratic prompt
    prompt = f"""You are a medical educator using the Socratic method.

CURRENT STAGE: {stage_name}
GUIDING QUESTION: {stage_question}

CLINICAL VIGNETTE:
{question.vignette}

ANSWER CHOICES:
{chr(10).join([f"{chr(65+i)}. {c}" for i, c in enumerate(question.choices)])}

CORRECT ANSWER: {question.answer_key} (DO NOT REVEAL THIS)

STUDENT'S MESSAGE: {user_message}

SOCRATIC METHOD RULES:
1. NEVER reveal the correct answer directly
2. Ask ONE guiding question that leads them toward discovery
3. Reference specific clinical details from the vignette
4. If they're stuck, provide ONE breadcrumb hint
5. Guide them through clinical reasoning stages:
   Chief Complaint → History → Physical → Differential → Workup → Diagnosis → Management

RESPONSE FORMAT:
- Maximum 80 words
- End with exactly ONE question
- Be encouraging but not patronizing
- Focus on clinical reasoning, not memorization

Generate a Socratic response:"""

    return prompt


def generate_breadcrumb_hint(
    error_type: str,
    hint_level: int,
    question: Question,
    explanation: Optional[Dict] = None
) -> str:
    """
    Generate a progressive hint based on error type and how many hints given.
    """
    hints = BREADCRUMB_HINTS.get(error_type, BREADCRUMB_HINTS["knowledge_gap"])
    hint_index = min(hint_level, len(hints) - 1)
    hint_template = hints[hint_index]

    # Fill in template variables based on question/explanation
    key_finding = ""
    if explanation:
        principle = explanation.get("principle", "")
        if principle:
            # Extract key finding from principle
            key_finding = principle.split("→")[0].strip() if "→" in principle else principle[:50]

    return hint_template.format(
        key_finding=key_finding or "the key clinical finding",
        mechanism_hint="the underlying mechanism",
        partial_answer="the correct approach",
        contradicting_finding="an important finding",
        correct_diagnosis="an alternative diagnosis",
        missed_detail="a crucial detail",
        temporal_detail="the timing of symptoms",
        critical_finding="this finding",
        pathway="the disease pathway",
        error_point="a logical step",
        correct_reasoning="the correct connection",
        first_choice="your first choice",
        actual_question="the question's focus",
        condition="this condition",
        classic_features="classic features",
        buzzword="a key term",
        pattern="this pattern"
    )


def build_teach_me_prompt(
    topic: str,
    question: Question,
    explanation: Optional[Dict] = None
) -> str:
    """
    Build a prompt for "Teach Me" mode - explaining concepts without giving answers.
    """
    # Extract relevant info from explanation
    principle = ""
    clinical_reasoning = ""
    if explanation:
        principle = explanation.get("principle", "")
        clinical_reasoning = explanation.get("clinical_reasoning", "")

    return f"""You are a medical educator explaining a concept to a student.

TOPIC TO EXPLAIN: {topic}

CONTEXT (from the question):
{question.vignette[:500]}

RELEVANT PRINCIPLE: {principle}
CLINICAL REASONING: {clinical_reasoning}

TEACHING RULES:
1. Explain the concept clearly and concisely
2. Use clinical examples where relevant
3. Do NOT reveal the answer to the specific question
4. Focus on understanding, not memorization
5. Include key pathophysiology when relevant
6. Maximum 150 words

Explain this concept:"""


def identify_reasoning_gap(
    user_message: str,
    correct_answer: str,
    explanation: Optional[Dict] = None
) -> Optional[str]:
    """
    Identify what reasoning gap the student might have based on their response.
    """
    user_lower = user_message.lower()

    # Check for common reasoning gaps
    if any(word in user_lower for word in ["don't know", "not sure", "confused", "help"]):
        return "knowledge_gap"

    if any(word in user_lower for word in ["thought it was", "initially", "changed"]):
        return "test_taking_error"

    if any(word in user_lower for word in ["why not", "isn't it", "could it be"]):
        return "premature_closure"

    if any(word in user_lower for word in ["but what about", "how does", "mechanism"]):
        return "faulty_reasoning"

    return None


def track_reasoning_progress(
    db: Session,
    user_id: str,
    question_id: str,
    conversation_history: List[Dict],
    current_stage: str
) -> Dict:
    """
    Track student's progress through clinical reasoning stages.
    Returns progress metrics and recommendations.
    """
    stages_completed = []
    current_index = 0

    for i, (stage_id, _, _) in enumerate(CLINICAL_REASONING_STAGES):
        if stage_id == current_stage:
            current_index = i
            break
        stages_completed.append(stage_id)

    total_stages = len(CLINICAL_REASONING_STAGES)
    progress_percent = (current_index / total_stages) * 100

    return {
        "current_stage": current_stage,
        "stage_index": current_index,
        "stages_completed": len(stages_completed),
        "total_stages": total_stages,
        "progress_percent": round(progress_percent, 1),
        "next_stage": CLINICAL_REASONING_STAGES[min(current_index + 1, total_stages - 1)][0],
        "stages": [
            {
                "id": stage[0],
                "name": stage[1],
                "question": stage[2],
                "completed": stage[0] in stages_completed,
                "current": stage[0] == current_stage
            }
            for stage in CLINICAL_REASONING_STAGES
        ]
    }


def build_enhanced_socratic_prompt(
    question: Question,
    user_answer: str,
    correct_answer: str,
    error_type: Optional[str],
    conversation_history: List[Dict],
    user_message: str,
    hint_level: int = 0
) -> str:
    """
    Build the complete system prompt for enhanced Socratic tutoring.
    """
    stage_id, stage_index = get_reasoning_stage(conversation_history)
    stage_info = CLINICAL_REASONING_STAGES[stage_index]

    # Get breadcrumb hint if needed
    breadcrumb = ""
    if hint_level > 0 and error_type:
        breadcrumb = generate_breadcrumb_hint(
            error_type, hint_level, question,
            question.explanation if isinstance(question.explanation, dict) else None
        )

    # Format explanation if available
    explanation_context = ""
    if isinstance(question.explanation, dict):
        exp = question.explanation
        explanation_context = f"""
KEY PRINCIPLE: {exp.get('principle', 'N/A')}
CLINICAL REASONING: {exp.get('clinical_reasoning', 'N/A')}
"""

    prompt = f"""You are an expert medical educator using the Socratic method to guide clinical reasoning.

CLINICAL REASONING FRAMEWORK:
You will guide the student through these stages:
1. Chief Complaint → 2. History → 3. Physical → 4. Differential → 5. Workup → 6. Diagnosis → 7. Management

CURRENT STAGE: {stage_info[1]} ({stage_index + 1}/{len(CLINICAL_REASONING_STAGES)})
GUIDING QUESTION FOR THIS STAGE: {stage_info[2]}

---

CLINICAL VIGNETTE:
{question.vignette}

ANSWER CHOICES:
{chr(10).join([f"{chr(65+i)}. {c}" for i, c in enumerate(question.choices)])}

STUDENT'S ANSWER: {user_answer}
CORRECT ANSWER: {correct_answer} (NEVER REVEAL DIRECTLY)
{"ERROR TYPE: " + error_type if error_type else ""}

{explanation_context}

---

CONVERSATION CONTEXT:
Turn {len([m for m in conversation_history if m.get('role') == 'user']) + 1}
{f"HINT TO INCORPORATE: {breadcrumb}" if breadcrumb else ""}

STUDENT'S CURRENT MESSAGE: {user_message}

---

SOCRATIC METHOD RULES:

1. NEVER reveal the correct answer directly
2. Ask exactly ONE guiding question per response
3. Reference SPECIFIC clinical details from the vignette
4. If stuck after 3+ turns, provide ONE breadcrumb hint
5. Guide through clinical reasoning stages progressively
6. Identify and address the specific reasoning gap

RESPONSE REQUIREMENTS:
- Maximum 80 words (strict limit)
- End with exactly ONE Socratic question
- Be warm but professional
- Focus on clinical reasoning process
- No generic praise or filler

Generate your Socratic response:"""

    return prompt


def generate_teach_me_response(
    db: Session,
    user_id: str,
    question_id: str,
    topic: str
) -> str:
    """
    Generate a "Teach Me" response that explains a concept without revealing answers.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return "I couldn't find that question. Please try again."

    prompt = build_teach_me_prompt(
        topic=topic,
        question=question,
        explanation=question.explanation if isinstance(question.explanation, dict) else None
    )

    return prompt


# Response generation helper for the router
def get_socratic_response_prompt(
    db: Session,
    user_id: str,
    question_id: str,
    user_message: str,
    mode: str = "standard"  # standard, teach_me, hint
) -> Tuple[str, Dict]:
    """
    Get the appropriate prompt and metadata for a Socratic response.

    Args:
        db: Database session
        user_id: User ID
        question_id: Question ID
        user_message: User's current message
        mode: Response mode (standard, teach_me, hint)

    Returns:
        Tuple of (system_prompt, metadata_dict)
    """
    # Get question
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return ("Question not found", {"error": True})

    # Get conversation history
    history = db.query(ChatMessage).filter_by(
        user_id=user_id,
        question_id=question_id
    ).order_by(ChatMessage.created_at).all()

    history_dicts = [
        {"role": msg.role, "message": msg.message}
        for msg in history
    ]

    # Get user's most recent attempt
    last_attempt = db.query(QuestionAttempt).filter_by(
        user_id=user_id,
        question_id=question_id
    ).order_by(QuestionAttempt.attempted_at.desc()).first()

    user_answer = last_attempt.user_answer if last_attempt else "Not answered"
    is_correct = last_attempt.is_correct if last_attempt else False

    # Get error type if incorrect
    error_type = None
    if last_attempt and not is_correct:
        error_analysis = db.query(ErrorAnalysis).filter_by(
            attempt_id=last_attempt.id
        ).first()
        if error_analysis:
            error_type = error_analysis.error_type

    # Calculate hint level based on conversation depth
    hint_level = len([m for m in history_dicts if m.get("role") == "user"]) // 2

    # Get reasoning progress
    stage_id, stage_index = get_reasoning_stage(history_dicts)
    progress = track_reasoning_progress(db, user_id, question_id, history_dicts, stage_id)

    # Build appropriate prompt based on mode
    if mode == "teach_me":
        prompt = build_teach_me_prompt(
            topic=user_message,
            question=question,
            explanation=question.explanation if isinstance(question.explanation, dict) else None
        )
    else:
        prompt = build_enhanced_socratic_prompt(
            question=question,
            user_answer=user_answer,
            correct_answer=question.answer_key,
            error_type=error_type,
            conversation_history=history_dicts,
            user_message=user_message,
            hint_level=hint_level if mode == "hint" else 0
        )

    metadata = {
        "error_type": error_type,
        "is_correct": is_correct,
        "reasoning_progress": progress,
        "hint_level": hint_level,
        "turn_count": len([m for m in history_dicts if m.get("role") == "user"]) + 1
    }

    return (prompt, metadata)
