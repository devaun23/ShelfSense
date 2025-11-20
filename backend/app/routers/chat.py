"""
AI Chat Router

Provides endpoints for chatting with AI about specific questions.
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from openai import OpenAI

from app.database import get_db
from app.models.models import Question, ChatMessage

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


class ChatRequest(BaseModel):
    user_id: str
    question_id: str
    message: str


class ChatResponse(BaseModel):
    message: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: List[dict]


@router.post("/question", response_model=ChatResponse)
def chat_about_question(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with AI about a specific question.

    Context includes:
    - Question vignette
    - All answer choices
    - Correct answer
    - User's answer (if available)
    - Framework explanation
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

    # Build context for AI
    # Get user's most recent answer if available
    from app.models.models import QuestionAttempt
    last_attempt = db.query(QuestionAttempt).filter_by(
        user_id=request.user_id,
        question_id=request.question_id
    ).order_by(QuestionAttempt.attempted_at.desc()).first()

    user_answer = last_attempt.user_answer if last_attempt else "Not yet answered"
    is_correct = last_attempt.is_correct if last_attempt else False

    # Format explanation
    explanation_text = ""
    if isinstance(question.explanation, dict):
        # Framework-based explanation
        exp = question.explanation
        explanation_text = f"""
Principle: {exp.get('principle', 'N/A')}

Clinical Reasoning: {exp.get('clinical_reasoning', 'N/A')}

Correct Answer Explanation: {exp.get('correct_answer_explanation', 'N/A')}
"""
    elif isinstance(question.explanation, str):
        explanation_text = question.explanation

    # Build system prompt with full context
    system_prompt = f"""You are a USMLE Step 2 CK tutor helping a student understand this question.

Question: {question.vignette}

Answer Choices:
{chr(10).join([f"{chr(65+i)}. {choice}" for i, choice in enumerate(question.choices)])}

Correct Answer: {question.answer_key}
Student's Answer: {user_answer} ({'✓ Correct' if is_correct else '✗ Incorrect'})

Explanation:
{explanation_text}

Your role:
- Answer the student's follow-up questions clearly and concisely
- Help them understand the clinical reasoning
- Explain concepts they're struggling with
- Be encouraging but honest
- Keep responses focused and under 150 words unless they ask for more detail
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
        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
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
            message=ai_message,
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
