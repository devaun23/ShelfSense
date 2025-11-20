from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.models import Question, QuestionAttempt
from app.services.adaptive import select_next_question

router = APIRouter(prefix="/api/questions", tags=["questions"])


class QuestionResponse(BaseModel):
    id: str
    vignette: str
    choices: List[str]
    source: str
    recency_weight: float

    class Config:
        from_attributes = True


class SubmitAnswerRequest(BaseModel):
    question_id: str
    user_id: str
    user_answer: str
    time_spent_seconds: int
    hover_events: Optional[dict] = None
    scroll_events: Optional[dict] = None


class AnswerFeedback(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: Optional[str]
    source: str


@router.get("/next", response_model=QuestionResponse)
def get_next_question(user_id: str, db: Session = Depends(get_db)):
    """
    Get next question for user using adaptive algorithm
    """
    question = select_next_question(db, user_id)

    if not question:
        raise HTTPException(status_code=404, detail="No questions available")

    return QuestionResponse(
        id=question.id,
        vignette=question.vignette,
        choices=question.choices,
        source=question.source or "Unknown",
        recency_weight=question.recency_weight or 0.5
    )


@router.post("/submit", response_model=AnswerFeedback)
def submit_answer(request: SubmitAnswerRequest, db: Session = Depends(get_db)):
    """
    Submit answer and record attempt
    Returns immediate feedback
    """
    # Get question
    question = db.query(Question).filter(Question.id == request.question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if answer is correct
    is_correct = request.user_answer.strip() == question.answer_key.strip()

    # Record attempt
    attempt = QuestionAttempt(
        user_id=request.user_id,
        question_id=request.question_id,
        user_answer=request.user_answer,
        is_correct=is_correct,
        time_spent_seconds=request.time_spent_seconds,
        hover_events=request.hover_events,
        scroll_events=request.scroll_events,
        attempted_at=datetime.utcnow()
    )

    db.add(attempt)
    db.commit()

    return AnswerFeedback(
        is_correct=is_correct,
        correct_answer=question.answer_key,
        explanation=question.explanation,
        source=question.source or "Unknown"
    )


@router.get("/random", response_model=QuestionResponse)
def get_random_question(db: Session = Depends(get_db)):
    """
    Get random question (for testing/demo)
    """
    import random as rand

    questions = db.query(Question).limit(100).all()

    if not questions:
        raise HTTPException(status_code=404, detail="No questions in database")

    question = rand.choice(questions)

    return QuestionResponse(
        id=question.id,
        vignette=question.vignette,
        choices=question.choices,
        source=question.source or "Unknown",
        recency_weight=question.recency_weight or 0.5
    )
