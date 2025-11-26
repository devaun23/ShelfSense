from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db
from app.models.models import Question, QuestionAttempt, QuestionRating, ErrorAnalysis, generate_uuid
from app.services.adaptive import select_next_question
from app.services.question_generator import generate_and_save_question, save_generated_question
from app.services.question_agent import generate_question_with_agent
from app.services.question_pool import get_instant_question, get_pool_stats, warm_pool_async
from app.services.adaptive import get_user_difficulty_target
from app.services.error_categorization import categorize_error
import threading

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


class ErrorAnalysisResponse(BaseModel):
    error_type: str
    error_name: str
    error_icon: str
    error_color: str
    confidence: float
    explanation: str
    missed_detail: str
    correct_reasoning: str
    coaching_question: str
    user_acknowledged: bool

    class Config:
        from_attributes = True


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
    db.refresh(attempt)  # Get the attempt ID

    # Schedule spaced repetition review
    from app.services.spaced_repetition import schedule_review
    schedule_review(
        db=db,
        user_id=request.user_id,
        question_id=request.question_id,
        is_correct=is_correct,
        source=question.source
    )

    # Trigger error analysis asynchronously if incorrect
    if not is_correct:
        def analyze_error_async():
            """Background task to analyze error without blocking response"""
            from app.database import SessionLocal
            db_async = SessionLocal()
            try:
                error_analysis = categorize_error(
                    question_text=question.vignette,
                    correct_answer=question.answer_key,
                    user_answer=request.user_answer,
                    choices=question.choices,
                    time_spent=request.time_spent_seconds
                )

                # Save to database
                error_record = ErrorAnalysis(
                    attempt_id=attempt.id,
                    user_id=request.user_id,
                    question_id=request.question_id,
                    error_type=error_analysis.get("error_type", "knowledge_gap"),
                    confidence=error_analysis.get("confidence", 0.5),
                    explanation=error_analysis.get("explanation", ""),
                    missed_detail=error_analysis.get("missed_detail", ""),
                    correct_reasoning=error_analysis.get("correct_reasoning", ""),
                    coaching_question=error_analysis.get("coaching_question", "")
                )

                db_async.add(error_record)
                db_async.commit()
                print(f"✅ Error analysis complete for attempt {attempt.id}: {error_analysis.get('error_type')}")

            except Exception as e:
                print(f"❌ Error in background error analysis: {str(e)}")
                db_async.rollback()
            finally:
                db_async.close()

        # Launch in background thread
        thread = threading.Thread(target=analyze_error_async)
        thread.daemon = True
        thread.start()

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
    user_id: Optional[str] = None,
    use_ai: bool = True,
    instant: bool = True
):
    """
    Get an AI-generated question - INSTANT from pre-generated pool.

    Args:
        specialty: Optional specialty filter (Medicine, Surgery, etc.)
        user_id: Optional user ID to exclude already-answered questions
        use_ai: If True, use AI generation (default)
        instant: If True, serve from pre-generated pool (default, <100ms)
                 If False, generate on-demand (slower, 10-30s)

    Returns:
        QuestionResponse with vignette, choices, and metadata
    """
    if use_ai:
        try:
            if instant:
                # INSTANT: Get from pre-generated pool (<100ms)
                print(f"[API] Getting instant question for {specialty or 'any specialty'}...")
                question = get_instant_question(db, specialty=specialty, user_id=user_id)

                if not question:
                    # Pool empty - fall back to on-demand generation
                    print(f"[API] Pool empty, generating on-demand...")
                    question_data = generate_question_with_agent(db, specialty=specialty)
                    question = save_generated_question(db, question_data)
            else:
                # ON-DEMAND: Generate fresh question (10-30s)
                print(f"[API] Generating on-demand for {specialty or 'random specialty'}...")
                question_data = generate_question_with_agent(db, specialty=specialty)
                question = save_generated_question(db, question_data)

            # Validate AI-generated question
            if not question or not question.choices or len(question.choices) != 5:
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


@router.get("/pool/stats")
def get_question_pool_stats(db: Session = Depends(get_db)):
    """
    Get statistics about the pre-generated question pool.

    Returns count of available questions per specialty.
    """
    stats = get_pool_stats(db)
    return {
        "pool_stats": stats,
        "status": "healthy" if stats.get("total", 0) >= 20 else "low"
    }


@router.post("/pool/warm")
def warm_question_pool(
    target_per_specialty: int = 20,
    background_tasks: BackgroundTasks = None
):
    """
    Warm up the question pool with pre-generated questions.

    This runs in background and returns immediately.
    Use /pool/stats to monitor progress.

    Args:
        target_per_specialty: Number of questions per specialty to generate (default: 20)
    """
    warm_pool_async(target_per_specialty)
    return {
        "status": "warming",
        "message": f"Pool warming started with target {target_per_specialty} per specialty",
        "check_progress": "/api/questions/pool/stats"
    }


@router.get("/difficulty/{user_id}")
def get_difficulty_target(user_id: str, db: Session = Depends(get_db)):
    """
    Get the recommended difficulty level for a user based on their overall performance.

    Returns difficulty level, target accuracy, and complexity settings.
    This determines what difficulty of questions will be generated for them.
    """
    difficulty_info = get_user_difficulty_target(db, user_id)
    return {
        "user_id": user_id,
        "difficulty": difficulty_info,
        "recommendation": f"Generate {difficulty_info['difficulty_level']} questions targeting {difficulty_info['target_correct_rate']:.0%} correct rate"
    }


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


@router.get("/error-analysis/{question_id}", response_model=Optional[ErrorAnalysisResponse])
def get_error_analysis(question_id: str, user_id: str, db: Session = Depends(get_db)):
    """
    Get error analysis for the most recent incorrect attempt of this question by this user
    """
    from app.services.error_categorization import ERROR_TYPES

    # Find the most recent error analysis for this question + user
    error_analysis = db.query(ErrorAnalysis).filter(
        ErrorAnalysis.question_id == question_id,
        ErrorAnalysis.user_id == user_id
    ).order_by(
        ErrorAnalysis.created_at.desc()
    ).first()

    if not error_analysis:
        return None

    # Get metadata from taxonomy
    error_metadata = ERROR_TYPES.get(error_analysis.error_type, {})

    return ErrorAnalysisResponse(
        error_type=error_analysis.error_type,
        error_name=error_metadata.get("name", "Unknown Error"),
        error_icon=error_metadata.get("icon", "�"),
        error_color=error_metadata.get("color", "gray"),
        confidence=error_analysis.confidence or 0.5,
        explanation=error_analysis.explanation or "",
        missed_detail=error_analysis.missed_detail or "",
        correct_reasoning=error_analysis.correct_reasoning or "",
        coaching_question=error_analysis.coaching_question or "",
        user_acknowledged=error_analysis.user_acknowledged or False
    )


@router.post("/acknowledge-error/{question_id}")
def acknowledge_error(question_id: str, user_id: str, db: Session = Depends(get_db)):
    """
    Mark error analysis as acknowledged by user
    """
    error_analysis = db.query(ErrorAnalysis).filter(
        ErrorAnalysis.question_id == question_id,
        ErrorAnalysis.user_id == user_id
    ).order_by(
        ErrorAnalysis.created_at.desc()
    ).first()

    if error_analysis:
        error_analysis.user_acknowledged = True
        db.commit()
        return {"success": True}

    return {"success": False, "message": "Error analysis not found"}
