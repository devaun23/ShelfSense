"""
Study Modes Router for ShelfSense

Provides different study modes to simulate exam conditions and optimize learning:
1. Timed Mode - Simulates real exam with countdown timer
2. Tutor Mode - Immediate feedback after each question
3. Challenge Mode - Only hard questions (< 60% global accuracy)
4. Review Mode - Spaced repetition reviews
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func

from app.database import get_db
from app.models.models import Question, QuestionAttempt, ScheduledReview
from app.services.adaptive import select_next_question
from app.services.spaced_repetition import get_todays_reviews, get_questions_for_todays_reviews

router = APIRouter(prefix="/api/study-modes", tags=["study-modes"])


class StudyModeConfig(BaseModel):
    mode: str  # "timed", "tutor", "challenge", "review"
    question_count: Optional[int] = 10
    time_limit_minutes: Optional[int] = None  # For timed mode
    specialty: Optional[str] = None


class StudySessionResponse(BaseModel):
    session_id: str
    mode: str
    question_count: int
    time_limit_seconds: Optional[int]
    questions: List[str]  # Question IDs
    started_at: datetime


class QuestionResponse(BaseModel):
    id: str
    vignette: str
    choices: List[str]
    source: str
    # In tutor mode, return immediately after answer
    # In timed/challenge mode, withhold until session end


@router.post("/start-session", response_model=StudySessionResponse)
def start_study_session(
    config: StudyModeConfig,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Start a study session with specified mode

    Modes:
    - timed: Simulate real exam (default 60 mins for 10 questions)
    - tutor: Immediate feedback after each question
    - challenge: Only hard questions (global accuracy < 60%)
    - review: Today's spaced repetition reviews
    """
    import uuid

    session_id = str(uuid.uuid4())
    started_at = datetime.utcnow()

    # Get questions based on mode
    questions = []

    if config.mode == "review":
        # Get today's scheduled reviews
        review_questions = get_questions_for_todays_reviews(db, user_id)
        questions = review_questions[:config.question_count]

    elif config.mode == "challenge":
        # Get hard questions (global accuracy < 60%)
        # Calculate global accuracy for each question
        hard_questions = db.query(Question).join(
            QuestionAttempt, Question.id == QuestionAttempt.question_id
        ).group_by(Question.id).having(
            func.avg(func.cast(QuestionAttempt.is_correct, func.INTEGER())) < 0.6
        ).limit(config.question_count).all()

        questions = hard_questions

    else:
        # For timed and tutor modes, use adaptive algorithm
        for _ in range(config.question_count):
            question = select_next_question(db, user_id, use_ai=False)
            if question:
                questions.append(question)

    if not questions:
        raise HTTPException(status_code=404, detail="No questions available for this mode")

    # Calculate time limit for timed mode
    time_limit_seconds = None
    if config.mode == "timed":
        if config.time_limit_minutes:
            time_limit_seconds = config.time_limit_minutes * 60
        else:
            # Default: 6 minutes per question (real exam pace)
            time_limit_seconds = len(questions) * 6 * 60

    # Store session in cache/memory (for production, use Redis)
    # For now, we'll just return the session info
    # Client will track the session state

    return StudySessionResponse(
        session_id=session_id,
        mode=config.mode,
        question_count=len(questions),
        time_limit_seconds=time_limit_seconds,
        questions=[q.id for q in questions],
        started_at=started_at
    )


class ModeStatsResponse(BaseModel):
    mode: str
    sessions_completed: int
    total_questions_answered: int
    average_accuracy: float
    average_time_per_question: float
    best_streak: int


@router.get("/stats", response_model=List[ModeStatsResponse])
def get_study_mode_stats(user_id: str, db: Session = Depends(get_db)):
    """
    Get statistics for each study mode

    Returns performance metrics per mode
    """
    # For now, return basic stats
    # In production, track sessions in a StudySessions table
    return []


class ReviewScheduleResponse(BaseModel):
    date: str
    count: int
    questions: List[dict]


@router.get("/review-schedule", response_model=List[ReviewScheduleResponse])
def get_review_schedule(user_id: str, days: int = 7, db: Session = Depends(get_db)):
    """
    Get upcoming review schedule

    Args:
        user_id: User ID
        days: Number of days to look ahead (default 7)

    Returns:
        Schedule of reviews by date
    """
    from app.services.spaced_repetition import get_upcoming_reviews

    calendar = get_upcoming_reviews(db, user_id, days)

    results = []
    for date_str, reviews in sorted(calendar.items()):
        results.append(ReviewScheduleResponse(
            date=date_str,
            count=len(reviews),
            questions=[
                {
                    "question_id": r.question_id,
                    "interval": r.review_interval,
                    "stage": r.learning_stage,
                    "times_reviewed": r.times_reviewed
                }
                for r in reviews
            ]
        ))

    return results


class ChallengeQuestionStats(BaseModel):
    question_id: str
    global_accuracy: float
    attempts: int
    vignette_preview: str


@router.get("/challenge-questions", response_model=List[ChallengeQuestionStats])
def get_challenge_questions(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get hardest questions (lowest global accuracy)

    Args:
        limit: Number of questions to return (default 20)

    Returns:
        List of challenge questions with stats
    """
    # Calculate global accuracy for each question
    hard_questions = db.query(
        Question,
        func.avg(func.cast(QuestionAttempt.is_correct, func.INTEGER())).label('accuracy'),
        func.count(QuestionAttempt.id).label('attempts')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).group_by(Question.id).having(
        func.count(QuestionAttempt.id) >= 5  # At least 5 attempts for statistical significance
    ).order_by(
        func.avg(func.cast(QuestionAttempt.is_correct, func.INTEGER())).asc()
    ).limit(limit).all()

    results = []
    for question, accuracy, attempts in hard_questions:
        results.append(ChallengeQuestionStats(
            question_id=question.id,
            global_accuracy=round(accuracy * 100, 2) if accuracy else 0.0,
            attempts=attempts,
            vignette_preview=question.vignette[:100] + "..." if len(question.vignette) > 100 else question.vignette
        ))

    return results


@router.get("/review-stats")
def get_review_statistics(user_id: str, db: Session = Depends(get_db)):
    """
    Get spaced repetition review statistics

    Returns:
        - Total reviews
        - Due today
        - By learning stage (Learning, Review, Mastered)
        - By specialty/source
    """
    from app.services.spaced_repetition import get_review_stats

    return get_review_stats(db, user_id)
