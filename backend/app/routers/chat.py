"""
AI Chat Router

Provides endpoints for chatting with AI about specific questions.
Uses clinical reasoning frameworks for Socratic-method tutoring.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.models import Question, ChatMessage, ErrorAnalysis, QuestionAttempt
from app.services.clinical_reasoning import (
    build_reasoning_coach_prompt,
    get_framework_for_error,
    generate_socratic_prompt,
    ReasoningFramework
)
from app.services.multi_turn_reasoning import (
    build_multi_turn_prompt,
    get_reasoning_state_summary,
    detect_reasoning_stage,
    assess_progress
)
from app.services.openai_service import openai_service, CircuitBreakerOpenError

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: str
    question_id: str
    message: str
    user_answer: str | None = None
    is_correct: bool | None = None


class ReasoningState(BaseModel):
    stage: str
    progress: str
    turn: int
    stages_completed: int
    total_stages: int


class ChatResponse(BaseModel):
    response: str
    created_at: datetime
    reasoning_state: Optional[ReasoningState] = None


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

    # Build conversation history for multi-turn reasoning
    history_dicts = [
        {"role": msg.role, "message": msg.message}
        for msg in history
    ]

    # Build system prompt - use multi-turn reasoning for deeper conversations
    if error_type and not is_correct and conversation_depth >= 1:
        # Use multi-turn reasoning for ongoing conversations
        system_prompt = build_multi_turn_prompt(
            question_text=question.vignette,
            user_answer=user_answer,
            correct_answer=question.answer_key,
            error_type=error_type,
            history=history_dicts,
            current_message=request.message
        )
    elif error_type and not is_correct:
        # Use framework-enhanced Socratic coaching for first incorrect answer
        system_prompt = build_reasoning_coach_prompt(
            error_type=error_type,
            question_text=question.vignette,
            user_answer=user_answer,
            correct_answer=question.answer_key,
            explanation=question.explanation if isinstance(question.explanation, dict) else None
        )
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
        # Call OpenAI with circuit breaker protection
        response = openai_service.chat_completion(
            messages=messages,
            model="gpt-4o-mini",
            max_tokens=500,  # Allows fuller responses (~350 words max)
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

        # Get reasoning state if in multi-turn mode
        reasoning_state = None
        if error_type and not is_correct:
            state_summary = get_reasoning_state_summary(
                history=history_dicts,
                current_message=request.message,
                error_type=error_type
            )
            reasoning_state = ReasoningState(**state_summary)

        return ChatResponse(
            response=ai_message,
            created_at=ai_msg.created_at,
            reasoning_state=reasoning_state
        )

    except CircuitBreakerOpenError:
        # Circuit breaker is open - return a helpful fallback message
        ai_message = "I'm temporarily unable to respond due to high demand. Please try again in a moment, or review the explanation above."

        # Still save the conversation
        user_msg = ChatMessage(
            user_id=request.user_id,
            question_id=request.question_id,
            message=request.message,
            role="user",
            created_at=datetime.utcnow()
        )
        db.add(user_msg)

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
            created_at=ai_msg.created_at,
            reasoning_state=None
        )

    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")


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

    # Build conversation history for multi-turn reasoning
    history_dicts = [
        {"role": msg.role, "message": msg.message}
        for msg in history
    ]

    # Build system prompt - use multi-turn reasoning for deeper conversations
    if error_type and not is_correct and conversation_depth >= 1:
        system_prompt = build_multi_turn_prompt(
            question_text=question.vignette,
            user_answer=user_answer,
            correct_answer=question.answer_key,
            error_type=error_type,
            history=history_dicts,
            current_message=request.message
        )
    elif error_type and not is_correct:
        system_prompt = build_reasoning_coach_prompt(
            error_type=error_type,
            question_text=question.vignette,
            user_answer=user_answer,
            correct_answer=question.answer_key,
            explanation=question.explanation if isinstance(question.explanation, dict) else None
        )
    else:
        system_prompt = f"""You are a USMLE Step 2 CK tutor. Be EXTREMELY CONCISE.

Question: {question.vignette}

Choices: {', '.join([f"{chr(65+i)}. {choice}" for i, choice in enumerate(question.choices)])}

Correct: {question.answer_key}
Student chose: {user_answer} ({'correct' if is_correct else 'incorrect'})

{explanation_text}

RULES:
- 50-80 words max, NEVER exceed 100 words
- ONE key point per response
- End with ONE Socratic question
- No fluff, no praise, just clarity
"""

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
            async for chunk in openai_service.chat_completion_stream(
                messages=messages,
                model="gpt-4o-mini",
                max_tokens=500,
                temperature=0.7
            ):
                full_response.append(chunk)
                # SSE format: data: {json}\n\n
                yield f"data: {json.dumps({'content': chunk})}\n\n"

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

        except CircuitBreakerOpenError:
            # Send error in SSE format
            error_msg = "I'm temporarily unable to respond due to high demand. Please try again in a moment."
            yield f"data: {json.dumps({'error': error_msg})}\n\n"

            # Save fallback message
            ai_msg = ChatMessage(
                user_id=request.user_id,
                question_id=request.question_id,
                message=error_msg,
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
