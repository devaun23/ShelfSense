from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db
from app.models.models import Question, QuestionAttempt, QuestionRating
from app.services.adaptive import select_next_question
from app.services.question_generator import generate_and_save_question
from app.services.question_cache import get_cache_stats, get_cached_or_generate_question
from app.middleware.rate_limiter import check_ai_generation_rate_limit, get_rate_limiter_stats

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
    explanation: Optional[Dict[str, Any]]  # Now returns structured explanation
    source: str


@router.get("/next", response_model=QuestionResponse)
def get_next_question(user_id: str, db: Session = Depends(get_db)):
    """
    Get next question for user using adaptive algorithm
    """
    question = select_next_question(db, user_id, use_ai=False)

    if not question:
        raise HTTPException(status_code=404, detail="No questions available")

    # Validate question has exactly 5 choices
    if not question.choices or len(question.choices) != 5:
        raise HTTPException(status_code=500, detail="Invalid question format")

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
    Returns immediate feedback and schedules spaced repetition
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

    # Schedule spaced repetition review
    from app.services.spaced_repetition import schedule_review
    schedule_review(
        db=db,
        user_id=request.user_id,
        question_id=request.question_id,
        is_correct=is_correct,
        source=question.source
    )

    # Parse explanation - handle both old string format and new JSON format
    parsed_explanation = None
    if question.explanation:
        if isinstance(question.explanation, dict):
            # Already a dictionary
            parsed_explanation = question.explanation
        elif isinstance(question.explanation, str):
            # Try to parse as JSON
            try:
                parsed_explanation = json.loads(question.explanation)
            except json.JSONDecodeError:
                # Old string format - wrap it
                parsed_explanation = {
                    "correct_answer_explanation": question.explanation,
                    "distractor_explanations": {}
                }

    return AnswerFeedback(
        is_correct=is_correct,
        correct_answer=question.answer_key,
        explanation=parsed_explanation,
        source=question.source or "Unknown"
    )


@router.get("/random", response_model=QuestionResponse)
def get_random_question(
    db: Session = Depends(get_db),
    specialty: Optional[str] = None,
    use_ai: bool = True,
    use_cache: bool = True,
    user_id: Optional[str] = "demo-user-1"
):
    """
    Generate a new AI question on-demand (default behavior)
    Pure AI generation - no NBME questions shown to user

    Args:
        specialty: Filter by specialty
        use_ai: Whether to use AI generation (default True)
        use_cache: Whether to use cached questions (default True, reduces API costs)
        user_id: User ID for cache lookup (default demo-user-1)
    """
    # Always generate AI questions on-demand
    if use_ai:
        try:
            # Check rate limit for AI generation
            rate_limit_info = check_ai_generation_rate_limit(user_id)

            # Generate new question using AI (with optional caching)
            if use_cache:
                question = get_cached_or_generate_question(db, user_id, specialty=specialty)
            else:
                question = generate_and_save_question(db, specialty=specialty)

            # Validate AI-generated question
            if not question.choices or len(question.choices) != 5:
                raise ValueError("AI generated invalid question format")

            return QuestionResponse(
                id=question.id,
                vignette=question.vignette,
                choices=question.choices,
                source=question.source or "AI Generated",
                recency_weight=question.recency_weight or 1.0
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"AI generation failed: {str(e)}")
            print(f"Full traceback: {error_details}")
            raise HTTPException(status_code=500, detail=f"Failed to generate question: {str(e)}")

    # Fallback: Get a random non-rejected question from database (for testing only)
    question = db.query(Question).filter(Question.rejected == False).order_by(Question.recency_weight.desc()).first()

    if not question:
        raise HTTPException(status_code=404, detail="No questions available")

    # Validate question has exactly 5 choices
    if not question.choices or len(question.choices) != 5:
        raise HTTPException(status_code=500, detail="Invalid question format")

    return QuestionResponse(
        id=question.id,
        vignette=question.vignette,
        choices=question.choices,
        source=question.source or "Database",
        recency_weight=question.recency_weight or 0.5
    )


class RateQuestionRequest(BaseModel):
    question_id: str
    user_id: str
    rating: bool  # TRUE = approved (✓), FALSE = rejected (✗)
    feedback_text: Optional[str] = None


class RateQuestionResponse(BaseModel):
    success: bool
    message: str


@router.post("/rate", response_model=RateQuestionResponse)
def rate_question(request: RateQuestionRequest, db: Session = Depends(get_db)):
    """
    Rate a question (approve ✓ or reject ✗) with optional feedback
    Rejected questions are marked and won't be shown again
    """
    # Get the question
    question = db.query(Question).filter(Question.id == request.question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Create rating record
    rating = QuestionRating(
        question_id=request.question_id,
        user_id=request.user_id,
        rating=request.rating,
        feedback_text=request.feedback_text,
        created_at=datetime.utcnow()
    )

    db.add(rating)

    # If rejected, mark the question
    if not request.rating:
        question.rejected = True

    db.commit()

    return RateQuestionResponse(
        success=True,
        message="Rating saved successfully"
    )


@router.get("/count")
def get_question_count(db: Session = Depends(get_db)):
    """
    Get total number of questions in the database
    """
    total = db.query(Question).count()
    return {"total": total}


@router.get("/cache-stats")
def get_cache_statistics(db: Session = Depends(get_db)):
    """
    Get caching statistics to monitor API cost savings

    Returns:
        - total_ai_questions_generated: Total AI questions created
        - ai_questions_used: Questions that have been answered
        - ai_questions_unused: Questions available for reuse (cache hits)
        - reuse_percentage: How often questions are reused (cost savings)
        - estimated_api_calls_saved: Approximate API calls saved by caching
    """
    return get_cache_stats(db)


@router.get("/rate-limit-stats")
def get_rate_limit_statistics():
    """
    Get rate limiter statistics

    Returns:
        - total_users_tracked: Number of users being tracked
        - total_active_requests: Current active requests in memory
        - rate_limits: Configuration for each rate limit type
    """
    return get_rate_limiter_stats()
