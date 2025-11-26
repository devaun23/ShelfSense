"""
AI Chat Router

Provides endpoints for chatting with AI about specific questions.
Uses clinical reasoning frameworks for Socratic-method tutoring.
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from openai import OpenAI

from app.database import get_db
from app.models.models import Question, ChatMessage, ErrorAnalysis, QuestionAttempt
from app.services.clinical_reasoning import (
    build_reasoning_coach_prompt,
    get_framework_for_error,
    generate_socratic_prompt,
    ReasoningFramework
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


class ChatRequest(BaseModel):
    user_id: str
    question_id: str
    message: str
    user_answer: str | None = None
    is_correct: bool | None = None


class ChatResponse(BaseModel):
    response: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: List[dict]


@router.post("/question", response_model=ChatResponse)
def chat_about_question(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with AI about a specific question.

    Uses clinical reasoning frameworks for Socratic-method tutoring when
    the student answered incorrectly and error analysis exists.

    Context includes:
    - Question vignette
    - All answer choices
    - Correct answer
    - User's answer (if available)
    - Framework explanation
    - Clinical reasoning framework (if error analysis exists)
    """
    # Get question
    question = db.query(Question).filter(Question.id == request.question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Get conversation history for this question
    history = db.query(ChatMessage).filter_by(
        user_id=request.user_id,
        question_id=request.question_id
    ).order_by(ChatMessage.created_at).all()

    # Get user's most recent answer if available
    last_attempt = db.query(QuestionAttempt).filter_by(
        user_id=request.user_id,
        question_id=request.question_id
    ).order_by(QuestionAttempt.attempted_at.desc()).first()

    user_answer = last_attempt.user_answer if last_attempt else "Not yet answered"
    is_correct = last_attempt.is_correct if last_attempt else False

    # Check for error analysis (only exists for incorrect answers)
    error_analysis = None
    error_type = None
    if last_attempt and not is_correct:
        error_analysis = db.query(ErrorAnalysis).filter_by(
            attempt_id=last_attempt.id
        ).first()
        if error_analysis:
            error_type = error_analysis.error_type

    # Count conversation exchanges for progressive coaching
    conversation_depth = len([m for m in history if m.role == "user"])

    # Format explanation
    explanation_text = ""
    if isinstance(question.explanation, dict):
        exp = question.explanation
        explanation_text = f"""
Principle: {exp.get('principle', 'N/A')}

Clinical Reasoning: {exp.get('clinical_reasoning', 'N/A')}

Correct Answer Explanation: {exp.get('correct_answer_explanation', 'N/A')}
"""
    elif isinstance(question.explanation, str):
        explanation_text = question.explanation

    # Build system prompt - use clinical reasoning framework if error exists
    if error_type and not is_correct:
        # Use framework-enhanced Socratic coaching for incorrect answers
        system_prompt = build_reasoning_coach_prompt(
            error_type=error_type,
            question_text=question.vignette,
            user_answer=user_answer,
            correct_answer=question.answer_key,
            explanation=question.explanation if isinstance(question.explanation, dict) else None
        )

        # Add conversation depth guidance
        if conversation_depth >= 3:
            system_prompt += "\n\nNOTE: This is exchange #{} - the student may be stuck. Provide more direct guidance while still encouraging active thinking.".format(conversation_depth + 1)
    else:
        # Standard tutoring prompt for correct answers or no error analysis
        system_prompt = f"""You are a USMLE Step 2 CK tutor. Be EXTREMELY CONCISE.

Question: {question.vignette}

Choices: {', '.join([f"{chr(65+i)}. {choice}" for i, choice in enumerate(question.choices)])}

Correct: {question.answer_key}
Student chose: {user_answer} ({'✓' if is_correct else '✗'})

{explanation_text}

RULES:
- 50-80 words max, NEVER exceed 100 words
- ONE key point per response
- End with ONE Socratic question
- No fluff, no praise, just clarity
"""

    # Build messages array with history
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    for msg in history:
        messages.append({
            "role": msg.role,
            "content": msg.message
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": request.message
    })

    try:
        # Call OpenAI - limit tokens for concise responses
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=150,  # Enforces brevity (~100 words max)
            temperature=0.7
        )

        ai_message = response.choices[0].message.content

        # Save user message
        user_msg = ChatMessage(
            user_id=request.user_id,
            question_id=request.question_id,
            message=request.message,
            role="user",
            created_at=datetime.utcnow()
        )
        db.add(user_msg)

        # Save AI response
        ai_msg = ChatMessage(
            user_id=request.user_id,
            question_id=request.question_id,
            message=ai_message,
            role="assistant",
            created_at=datetime.utcnow()
        )
        db.add(ai_msg)

        db.commit()

        return ChatResponse(
            response=ai_message,
            created_at=ai_msg.created_at
        )

    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")


@router.get("/history/{question_id}", response_model=ChatHistoryResponse)
def get_chat_history(
    question_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get chat history for a specific question.
    """
    messages = db.query(ChatMessage).filter_by(
        user_id=user_id,
        question_id=question_id
    ).order_by(ChatMessage.created_at).all()

    return ChatHistoryResponse(
        messages=[
            {
                "role": msg.role,
                "message": msg.message,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    )


@router.delete("/history/{question_id}")
def clear_chat_history(
    question_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Clear chat history for a specific question.
    """
    db.query(ChatMessage).filter_by(
        user_id=user_id,
        question_id=question_id
    ).delete()

    db.commit()

    return {"message": "Chat history cleared"}
