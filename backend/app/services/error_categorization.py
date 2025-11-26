"""
Error Categorization Service

Analyzes incorrect question attempts and categorizes the type of error
to provide targeted learning interventions.

Based on medical education research on diagnostic reasoning errors.
"""

from typing import Dict, Optional, List
from openai import OpenAI
import os
import json

# Error taxonomy based on medical education research
ERROR_TYPES = {
    "knowledge_gap": {
        "name": "Knowledge Gap",
        "description": "Missing key medical knowledge or facts",
        "icon": "📚",
        "color": "blue"
    },
    "premature_closure": {
        "name": "Premature Closure",
        "description": "Stopped at first diagnosis without considering alternatives",
        "icon": "🚪",
        "color": "yellow"
    },
    "misread_stem": {
        "name": "Misread Clinical Vignette",
        "description": "Missed or misinterpreted key clinical details",
        "icon": "👁️",
        "color": "orange"
    },
    "faulty_reasoning": {
        "name": "Faulty Clinical Reasoning",
        "description": "Logical error in diagnostic approach or treatment selection",
        "icon": "🧠",
        "color": "purple"
    },
    "test_taking_error": {
        "name": "Test-Taking Error",
        "description": "Second-guessed yourself or eliminated correct answer",
        "icon": "✏️",
        "color": "red"
    },
    "time_pressure": {
        "name": "Time Pressure",
        "description": "Rushed through question without full analysis",
        "icon": "⏱️",
        "color": "gray"
    }
}


def categorize_error(
    question_text: str,
    correct_answer: str,
    user_answer: str,
    choices: List[str],
    time_spent: Optional[int] = None,
    user_history: Optional[Dict] = None
) -> Dict:
    """
    Analyze an incorrect answer and categorize the error type.

    Args:
        question_text: The full clinical vignette
        correct_answer: The correct answer choice
        user_answer: The user's selected answer
        choices: All answer choices
        time_spent: Time in seconds spent on question
        user_history: Optional dict with user's past performance patterns

    Returns:
        Dict with error_type, explanation, reasoning_coach_prompt
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Build the analysis prompt
    prompt = f"""You are a medical education expert analyzing why a student got a Step 2 CK question wrong.

QUESTION VIGNETTE:
{question_text}

ANSWER CHOICES:
{chr(10).join([f'{chr(65+i)}. {choice}' for i, choice in enumerate(choices)])}

CORRECT ANSWER: {correct_answer}
STUDENT'S ANSWER: {user_answer}
TIME SPENT: {time_spent if time_spent else 'Unknown'} seconds

Analyze this error and categorize it into ONE of these types:

1. **knowledge_gap**: Student lacks key medical knowledge/facts needed to answer correctly
2. **premature_closure**: Student stopped at first diagnosis without considering full differential
3. **misread_stem**: Student missed or misinterpreted critical clinical details in the vignette
4. **faulty_reasoning**: Student had knowledge but applied faulty clinical reasoning logic
5. **test_taking_error**: Student second-guessed themselves or used poor test strategy
6. **time_pressure**: Student rushed (if time < 60 seconds) and made careless error

Provide your analysis in JSON format:
{{
    "error_type": "one of the 6 types above",
    "confidence": 0.0-1.0,
    "explanation": "2-3 sentences explaining WHY this error occurred and what the student was thinking",
    "missed_detail": "The specific fact, symptom, or reasoning step the student missed",
    "correct_reasoning": "1-2 sentences showing the correct clinical reasoning pathway",
    "coaching_question": "A Socratic question to guide the student toward correct reasoning (e.g., 'What made you choose X over Y?' or 'What symptom pattern suggests Z diagnosis?')"
}}

Be specific and educational. Your explanation should help the student understand their thinking pattern."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a medical education expert who analyzes student errors to provide targeted learning interventions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Add metadata from our taxonomy
        error_type = result.get("error_type", "knowledge_gap")
        result["error_metadata"] = ERROR_TYPES.get(error_type, ERROR_TYPES["knowledge_gap"])

        return result

    except Exception as e:
        print(f"Error in error categorization: {str(e)}")
        # Fallback to knowledge gap if API fails
        return {
            "error_type": "knowledge_gap",
            "confidence": 0.5,
            "explanation": "Unable to categorize error automatically. Review the explanation to understand the correct answer.",
            "missed_detail": "Review the question and explanation carefully.",
            "correct_reasoning": "See the full explanation below.",
            "coaching_question": "What key clinical features distinguish the correct answer from your choice?",
            "error_metadata": ERROR_TYPES["knowledge_gap"]
        }


def generate_coaching_session(
    question_text: str,
    correct_answer: str,
    user_answer: str,
    error_analysis: Dict,
    student_response: Optional[str] = None
) -> str:
    """
    Generate an interactive coaching session based on the error type.

    This is used when student clicks "Help me understand" and starts
    a conversation with the AI reasoning coach.

    Args:
        question_text: The clinical vignette
        correct_answer: Correct answer
        user_answer: User's wrong answer
        error_analysis: Result from categorize_error()
        student_response: Optional response to coaching_question

    Returns:
        AI coach's response string
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    error_type = error_analysis.get("error_type", "knowledge_gap")
    coaching_question = error_analysis.get("coaching_question", "")

    # Build coaching prompt based on error type
    if error_type == "premature_closure":
        coaching_strategy = "Guide them through differential diagnosis. Ask them to list all possible diagnoses first, then systematically rule out each one."
    elif error_type == "misread_stem":
        coaching_strategy = "Point them to the specific clinical detail they missed. Have them re-read that part and explain its significance."
    elif error_type == "faulty_reasoning":
        coaching_strategy = "Walk through the clinical reasoning step-by-step. Ask them to explain each step of their thought process and identify where the logic broke down."
    elif error_type == "knowledge_gap":
        coaching_strategy = "Teach the missing concept clearly and concisely. Use analogies or mnemonics. Then show how it applies to this question."
    else:
        coaching_strategy = "Use Socratic questioning to guide them toward the correct reasoning without giving away the answer immediately."

    system_prompt = f"""You are a compassionate medical education tutor helping a student learn from their mistake.

ERROR TYPE: {error_analysis.get('error_metadata', {}).get('name', 'Unknown')}
COACHING STRATEGY: {coaching_strategy}

QUESTION: {question_text}
CORRECT: {correct_answer}
STUDENT CHOSE: {user_answer}

Your job is to:
1. Use Socratic questioning (don't just tell the answer)
2. Guide them toward discovering WHY their reasoning was incorrect
3. Be encouraging and specific
4. Keep responses concise (2-3 paragraphs max)
5. End with a question that deepens understanding

The student was asked: "{coaching_question}"
"""

    if student_response:
        system_prompt += f"\n\nTheir response: {student_response}\n\nContinue the coaching conversation."
    else:
        system_prompt += "\n\nThis is the opening message. Start by asking the coaching question to understand their thinking."

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Coach me through this question."}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error in coaching session: {str(e)}")
        return f"Let's think through this together. {coaching_question}"


def get_error_pattern_summary(user_id: str, db) -> Dict:
    """
    Analyze user's error patterns over time.

    Returns summary like:
    {
        "most_common_error": "premature_closure",
        "error_counts": {"knowledge_gap": 5, "premature_closure": 12, ...},
        "weak_topics": ["Cardiology", "Renal"],
        "recommendation": "You tend to stop at the first diagnosis..."
    }
    """
    from app.models.models import QuestionAttempt, ErrorAnalysis
    from sqlalchemy import func

    # Get error distribution
    error_counts = db.query(
        ErrorAnalysis.error_type,
        func.count(ErrorAnalysis.id).label('count')
    ).join(
        QuestionAttempt, ErrorAnalysis.attempt_id == QuestionAttempt.id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).group_by(
        ErrorAnalysis.error_type
    ).all()

    if not error_counts:
        return {
            "most_common_error": None,
            "error_counts": {},
            "recommendation": "Keep practicing! We'll analyze your error patterns as you answer more questions."
        }

    # Build summary
    error_dict = {error_type: count for error_type, count in error_counts}
    most_common = max(error_dict.items(), key=lambda x: x[1])[0]

    # Generate personalized recommendation
    recommendations = {
        "premature_closure": "You tend to stop at the first diagnosis that fits. Try creating a full differential diagnosis list before selecting your answer.",
        "knowledge_gap": "You're missing some foundational knowledge. Focus on reviewing high-yield topics and using spaced repetition for weak areas.",
        "misread_stem": "You're missing key clinical details. Try underlining critical information (age, gender, timeline, key symptoms) as you read.",
        "faulty_reasoning": "Your clinical reasoning needs strengthening. Practice thinking through: What's the pathophysiology? What confirms/rules out this diagnosis?",
        "test_taking_error": "You're second-guessing yourself. Trust your first instinct if you've reasoned through it carefully.",
        "time_pressure": "You're rushing. Aim for 60-90 seconds per question to fully analyze the vignette."
    }

    return {
        "most_common_error": most_common,
        "error_counts": error_dict,
        "error_metadata": ERROR_TYPES.get(most_common, {}),
        "recommendation": recommendations.get(most_common, "Keep practicing and learning from each mistake!")
    }
