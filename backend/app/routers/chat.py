"""
AI Chat Router

Provides endpoints for chatting with AI about specific questions.
Includes streaming support for real-time responses.
"""

import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from openai import OpenAI

from app.database import get_db
from app.models.models import Question, ChatMessage, QuestionAttempt

logger = logging.getLogger(__name__)

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


def build_chat_context(question, user_answer: str, is_correct: bool):
    """Build the system prompt with full question context."""
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

    return f"""You are a concise USMLE Step 2 CK tutor helping a student understand this question.

Question: {question.vignette}

Answer Choices:
{chr(10).join([f"{chr(65+i)}. {choice}" for i, choice in enumerate(question.choices)])}

Correct Answer: {question.answer_key}
Student's Answer: {user_answer} ({'correct' if is_correct else 'incorrect'})

Explanation:
{explanation_text}

CRITICAL INSTRUCTIONS:
- Be EXTREMELY concise - max 2-3 sentences per answer
- Use bullet points for lists
- Get straight to the point - no fluff
- Use medical shorthand when appropriate (e.g., "pt" for patient, "dx" for diagnosis)
- If they ask a simple question, give a simple answer (1 sentence is often enough)
- Only elaborate if they explicitly ask for more detail
- Use arrows (→) to show clinical reasoning flow
- Examples:
  * "Why not C?" → "C treats X, but pt has Y → needs Z instead"
  * "What's the mechanism?" → "Drug blocks receptor → decreases BP → improves outcome"
"""


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

    # Get user's most recent answer if available
    last_attempt = db.query(QuestionAttempt).filter_by(
        user_id=request.user_id,
        question_id=request.question_id
    ).order_by(QuestionAttempt.attempted_at.desc()).first()

    user_answer = last_attempt.user_answer if last_attempt else "Not yet answered"
    is_correct = last_attempt.is_correct if last_attempt else False

    # Build system prompt with full context
    system_prompt = build_chat_context(question, user_answer, is_correct)

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
        # Call OpenAI with increased token limit for fuller responses
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,  # Increased for fuller responses
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
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate response")


@router.post("/question/stream")
async def chat_about_question_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Stream chat response about a specific question using Server-Sent Events.

    Provides real-time streaming of AI responses for better UX.
    First token arrives in <500ms, full response streams progressively.
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

    # Build system prompt with full context
    system_prompt = build_chat_context(question, user_answer, is_correct)

    # Build messages array with history
    messages = [{"role": "system", "content": system_prompt}]

    for msg in history:
        messages.append({
            "role": msg.role,
            "content": msg.message
        })

    messages.append({
        "role": "user",
        "content": request.message
    })

    # Save user message immediately (optimistic)
    user_msg = ChatMessage(
        user_id=request.user_id,
        question_id=request.question_id,
        message=request.message,
        role="user",
        created_at=datetime.utcnow()
    )
    db.add(user_msg)
    db.commit()

    async def generate_stream():
        """Generate SSE stream of AI response chunks."""
        full_response = []

        try:
            # Create streaming request
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                stream=True
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response.append(content)
                    # SSE format: data: {json}\n\n
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # Send done signal
            yield f"data: {json.dumps({'done': True})}\n\n"

            # Save complete AI response to database
            ai_message = "".join(full_response)
            ai_msg = ChatMessage(
                user_id=request.user_id,
                question_id=request.question_id,
                message=ai_message,
                role="assistant",
                created_at=datetime.utcnow()
            )
            db.add(ai_msg)
            db.commit()

        except Exception as e:
            logger.error("Streaming chat error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'error': 'AI service temporarily unavailable'})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


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
