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
from app.services.question_agent import (
    generate_question_with_agent,
    generate_learning_stage_question,
    generate_optimal_question
)
from app.services.question_pool import get_instant_question, get_pool_stats, warm_pool_async
from app.services.adaptive import get_user_difficulty_target, get_user_weakness_profile
from app.services.error_categorization import categorize_error
from app.services.weakness_teaching import get_weakness_intervention
from app.services.ai_question_analytics import (
    get_ai_question_performance,
    get_question_actual_difficulty,
    calibrate_ai_questions,
    calculate_question_quality_score,
    get_user_learning_stage,
    get_generation_recommendations,
    update_content_freshness
)
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


class WeaknessIntervention(BaseModel):
    triggered: bool
    priority: Optional[str] = None  # "high" | "moderate" | None
    message: Optional[str] = None
    pattern_count: Optional[int] = None


class AnswerFeedback(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: Optional[Dict[str, Any]]  # Now returns structured explanation
    source: str
    weakness_intervention: Optional[WeaknessIntervention] = None


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
    weakness_intervention = None
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

        # Check for weakness pattern match (uses existing error history)
        # This runs sync but is fast since it just queries existing data
        try:
            # Get user's most common error type from history
            from sqlalchemy import func
            most_common_error = db.query(
                ErrorAnalysis.error_type,
                func.count(ErrorAnalysis.id).label('count')
            ).filter(
                ErrorAnalysis.user_id == request.user_id
            ).group_by(
                ErrorAnalysis.error_type
            ).order_by(
                func.count(ErrorAnalysis.id).desc()
            ).first()

            if most_common_error and most_common_error.count >= 3:
                # User has a pattern - check if this question's source is weak
                intervention = get_weakness_intervention(
                    db=db,
                    user_id=request.user_id,
                    error_type=most_common_error.error_type,
                    source=question.source or "Unknown"
                )
                if intervention:
                    weakness_intervention = WeaknessIntervention(
                        triggered=intervention["triggered"],
                        priority=intervention["priority"],
                        message=intervention["message"],
                        pattern_count=intervention["pattern_count"]
                    )
        except Exception as e:
            print(f"⚠️ Weakness intervention check failed: {e}")

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
        source=question.source or "Unknown",
        weakness_intervention=weakness_intervention
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


@router.get("/weakness-profile/{user_id}")
def get_weakness_profile(user_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive weakness profile for a user.

    Returns weak specialties, error patterns, missed concepts, and recommended focus.
    This is used to generate targeted questions for adaptive learning.
    """
    profile = get_user_weakness_profile(db, user_id)
    return {
        "user_id": user_id,
        "profile": profile,
        "has_weaknesses": bool(profile.get("weak_specialties") or profile.get("most_common_error"))
    }


@router.get("/targeted/{user_id}", response_model=QuestionResponse)
def get_targeted_question(user_id: str, db: Session = Depends(get_db)):
    """
    Generate a question specifically targeting the user's weaknesses.

    This is the core adaptive learning endpoint - it generates questions
    designed to address the user's specific weak areas and error patterns.

    The question will:
    - Target the user's weakest specialty
    - Address their most common error pattern
    - Test concepts they've recently missed
    - Use appropriate difficulty level

    Falls back to standard generation if no weakness profile exists.
    """
    from app.services.question_agent import generate_weakness_targeted_question

    try:
        # Get weakness profile first to check if we have enough data
        profile = get_user_weakness_profile(db, user_id)

        has_data = (
            profile.get("weak_specialties") or
            profile.get("most_common_error") or
            profile.get("missed_concepts")
        )

        if has_data:
            # Generate targeted question
            print(f"[API] Generating targeted question for user {user_id}")
            print(f"[API] Targeting: {profile.get('recommended_focus')}")

            question_data = generate_weakness_targeted_question(db, user_id)
            question = save_generated_question(db, question_data)

            return QuestionResponse(
                id=question.id,
                vignette=question.vignette,
                choices=question.choices,
                source=question.source or "AI Targeted",
                recency_weight=question.recency_weight or 1.0
            )
        else:
            # Not enough data - use standard instant generation
            print(f"[API] No weakness data for user {user_id}, using standard generation")
            question = get_instant_question(db, user_id=user_id)

            if not question:
                raise HTTPException(status_code=404, detail="Could not generate question")

            return QuestionResponse(
                id=question.id,
                vignette=question.vignette,
                choices=question.choices,
                source=question.source or "AI Generated",
                recency_weight=question.recency_weight or 1.0
            )

    except Exception as e:
        import traceback
        print(f"[API] Targeted generation failed: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate targeted question: {str(e)}")


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


# =============================================================================
# AI Question Analytics Endpoints
# =============================================================================

@router.get("/analytics/performance")
def get_ai_performance(db: Session = Depends(get_db)):
    """
    Compare performance of AI-generated questions vs NBME questions.

    Returns:
    - Accuracy comparison
    - Time spent comparison
    - Approval rate comparison
    - Whether AI questions are comparable to NBME (within 10% accuracy)

    Use this to monitor AI question quality over time.
    """
    performance = get_ai_question_performance(db)
    return {
        "performance": performance,
        "summary": {
            "ai_accuracy": f"{performance['ai_questions']['accuracy']:.1%}",
            "nbme_accuracy": f"{performance['nbme_questions']['accuracy']:.1%}",
            "comparable": performance['comparison']['ai_is_comparable']
        }
    }


@router.get("/analytics/difficulty/{question_id}")
def get_actual_difficulty(question_id: str, db: Session = Depends(get_db)):
    """
    Get the calibrated difficulty of a specific question based on actual user performance.

    Returns:
    - calibrated: Whether enough data exists
    - actual_accuracy: Real accuracy across all attempts
    - calibrated_difficulty: easy/medium/hard/very_hard
    - needs_adjustment: Whether the question difficulty needs updating
    """
    difficulty = get_question_actual_difficulty(db, question_id)
    return difficulty


@router.post("/analytics/calibrate")
def calibrate_questions(min_attempts: int = 10, db: Session = Depends(get_db)):
    """
    Batch calibrate all AI questions based on actual user performance.

    This updates difficulty_level for all AI questions with at least `min_attempts` attempts.

    Args:
        min_attempts: Minimum number of attempts required for calibration (default: 10)

    Returns:
    - total_calibrated: Number of questions with changed difficulty
    - upgraded: Questions made easier
    - downgraded: Questions made harder
    - details: Full calibration details
    """
    results = calibrate_ai_questions(db, min_attempts)
    return {
        "calibration_results": results,
        "summary": {
            "total_calibrated": results["total_calibrated"],
            "upgraded_count": len(results["upgraded"]),
            "downgraded_count": len(results["downgraded"]),
            "unchanged_count": len(results["unchanged"])
        }
    }


@router.get("/analytics/quality/{question_id}")
def get_quality_score(question_id: str, db: Session = Depends(get_db)):
    """
    Calculate comprehensive quality score for a question.

    Quality Score = (
        Medical Accuracy (40%) - based on user ratings
        + Discrimination Index (30%) - how well it differentiates skill levels
        + Completion Rate (15%) - % of users who complete vs skip
        + Time Efficiency (15%) - appropriate time spent
    )

    Returns:
    - quality_score: Overall score (0-100)
    - components: Individual scores for each component
    - quality_level: "high" (80+), "medium" (60-80), "low" (<60)
    """
    quality = calculate_question_quality_score(db, question_id)
    return quality


@router.get("/analytics/learning-stage/{user_id}")
def get_learning_stage(user_id: str, topic: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Determine user's learning stage for targeted question generation.

    Learning Stages:
    - New: < 10 questions, < 50% accuracy
    - Learning: 10-30 questions, 50-70% accuracy
    - Review: 30-100 questions, 70-85% accuracy
    - Mastered: 100+ questions, > 85% accuracy

    Args:
        user_id: User ID
        topic: Optional topic/specialty filter

    Returns:
    - learning_stage: Current stage
    - generation_params: Recommended question generation parameters
    - next_milestone: What's needed to advance to next stage
    """
    stage = get_user_learning_stage(db, user_id, topic)
    return stage


@router.get("/analytics/recommendations/{user_id}")
def get_recommendations(user_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive recommendations for AI question generation.

    Combines:
    - Weakness profile (weak specialties, error patterns)
    - Learning stage (New/Learning/Review/Mastered)
    - Difficulty target (easy/medium/hard)

    Returns specific parameters to use when generating the next question.
    """
    recommendations = get_generation_recommendations(db, user_id)
    return recommendations


class DetailedFeedbackRequest(BaseModel):
    question_id: str
    user_id: str
    rating: int  # 1-5 star rating
    feedback_type: str  # "content", "difficulty", "relevance", "clarity"
    feedback_text: Optional[str] = None
    suggested_improvement: Optional[str] = None


@router.post("/feedback")
def submit_detailed_feedback(request: DetailedFeedbackRequest, db: Session = Depends(get_db)):
    """
    Submit detailed feedback on an AI-generated question.

    This is different from the simple approve/reject rating - it collects
    structured feedback for improving question quality.

    Args:
        question_id: Question being rated
        user_id: User providing feedback
        rating: 1-5 star rating
        feedback_type: What aspect being rated (content/difficulty/relevance/clarity)
        feedback_text: Optional detailed feedback
        suggested_improvement: Optional suggestion for improvement

    The feedback is used to:
    - Update question quality scores
    - Flag questions for review
    - Improve future AI generation
    """
    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Create feedback record with detailed info
    feedback = QuestionRating(
        question_id=request.question_id,
        user_id=request.user_id,
        rating=request.rating >= 3,  # Convert 1-5 to boolean for compatibility
        feedback_text=json.dumps({
            "star_rating": request.rating,
            "feedback_type": request.feedback_type,
            "text": request.feedback_text,
            "suggested_improvement": request.suggested_improvement
        }),
        created_at=datetime.utcnow()
    )
    db.add(feedback)

    # Update content freshness scores
    update_content_freshness(db, request.question_id)

    # Recalculate quality score
    quality = calculate_question_quality_score(db, request.question_id)

    # Flag for review if quality drops below threshold
    if quality.get("quality_score", 100) < 60:
        question.rejected = True
        db.commit()
        return {
            "success": True,
            "message": "Feedback saved. Question flagged for review due to low quality score.",
            "quality_score": quality.get("quality_score")
        }

    db.commit()
    return {
        "success": True,
        "message": "Feedback saved successfully",
        "quality_score": quality.get("quality_score")
    }


@router.get("/optimal/{user_id}", response_model=QuestionResponse)
def get_optimal_question(user_id: str, topic: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Generate the most optimal question for a user based on their learning stage and weaknesses.

    This is the recommended endpoint for personalized question generation.
    It automatically:
    - Determines the user's learning stage (New/Learning/Review/Mastered)
    - Identifies their weak specialties and error patterns
    - Generates a question optimized for their current learning needs

    Args:
        user_id: User ID for personalization
        topic: Optional topic filter

    Returns:
        QuestionResponse with personalized question
    """
    try:
        print(f"[API] Generating optimal question for user {user_id}")

        # Generate learning-stage-aware question
        question_data = generate_learning_stage_question(db, user_id, topic)
        question = save_generated_question(db, question_data)

        return QuestionResponse(
            id=question.id,
            vignette=question.vignette,
            choices=question.choices,
            source=question.source or "AI Optimal",
            recency_weight=question.recency_weight or 1.0
        )
    except Exception as e:
        import traceback
        print(f"[API] Optimal generation failed: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate optimal question: {str(e)}")


@router.get("/analytics/batch-quality")
def batch_calculate_quality(limit: int = 100, db: Session = Depends(get_db)):
    """
    Calculate quality scores for all AI questions with sufficient data.

    Args:
        limit: Maximum number of questions to process (default: 100)

    Returns:
    - Summary of quality distribution
    - List of questions needing review
    """
    # Get AI questions with attempts
    from sqlalchemy import func

    ai_questions = db.query(
        Question.id
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        Question.source.like('%AI%')
    ).group_by(
        Question.id
    ).having(
        func.count(QuestionAttempt.id) >= 5
    ).limit(limit).all()

    results = {
        "total_processed": 0,
        "high_quality": [],
        "medium_quality": [],
        "low_quality": [],
        "needs_review": []
    }

    for (q_id,) in ai_questions:
        quality = calculate_question_quality_score(db, q_id)
        results["total_processed"] += 1

        score = quality.get("quality_score", 0)
        if score >= 80:
            results["high_quality"].append(q_id)
        elif score >= 60:
            results["medium_quality"].append(q_id)
        else:
            results["low_quality"].append(q_id)
            results["needs_review"].append({
                "question_id": q_id,
                "quality_score": score,
                "components": quality.get("components")
            })

    return {
        "results": results,
        "summary": {
            "high_quality_count": len(results["high_quality"]),
            "medium_quality_count": len(results["medium_quality"]),
            "low_quality_count": len(results["low_quality"]),
            "avg_quality": "N/A" if not ai_questions else f"{(len(results['high_quality'])*90 + len(results['medium_quality'])*70 + len(results['low_quality'])*50) / len(ai_questions):.1f}"
        }
    }
