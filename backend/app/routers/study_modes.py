"""
Study Modes API Router

Provides endpoints for different study experiences:
- Practice Mode: Free-form questions, immediate feedback
- Timed Mode: Exam simulation with time limit
- Tutor Mode: Detailed explanations after each question
- Challenge Mode: Hard questions only
- Review Mode: Spaced repetition questions
- Weak Focus Mode: Target weak areas
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.models import User, StudySession
from app.services.study_modes import (
    create_study_session,
    get_session,
    get_active_session,
    get_user_sessions,
    get_next_question,
    submit_answer,
    skip_question,
    pause_session,
    resume_session,
    end_session,
    get_session_summary,
    get_mode_statistics,
    VALID_MODES,
    MODE_DEFAULTS
)

router = APIRouter(prefix="/api/study-modes", tags=["study-modes"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StartSessionRequest(BaseModel):
    """Request to start a new study session."""
    mode: str = Field(..., description="Study mode: practice, timed, tutor, challenge, review, weak_focus")
    specialty: Optional[str] = Field(None, description="Focus on specific specialty")
    difficulty: Optional[str] = Field(None, description="Difficulty: easy, medium, hard, adaptive")
    target_count: Optional[int] = Field(None, ge=1, le=100, description="Number of questions")
    time_limit_minutes: Optional[int] = Field(None, ge=5, le=180, description="Time limit in minutes")
    name: Optional[str] = Field(None, description="Custom session name")


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer."""
    question_id: str
    answer: str = Field(..., pattern="^[A-E]$", description="Answer choice A-E")
    time_spent_seconds: int = Field(0, ge=0)
    confidence_level: Optional[int] = Field(None, ge=1, le=5)


class SessionResponse(BaseModel):
    """Response with session details."""
    id: str
    mode: str
    name: str
    status: str
    specialty: Optional[str]
    difficulty: Optional[str]
    target_count: Optional[int]
    time_limit_seconds: Optional[int]
    questions_answered: int
    questions_correct: int
    accuracy: Optional[float]
    time_remaining: Optional[int]
    started_at: str
    ended_at: Optional[str]


class QuestionResponse(BaseModel):
    """Response with question for studying."""
    question_id: str
    vignette: str
    choices: Dict[str, str]
    specialty: Optional[str]
    session_info: Dict[str, Any]
    hint_available: bool = False


class FeedbackResponse(BaseModel):
    """Response after submitting an answer."""
    is_correct: bool
    correct_answer: str
    explanation: Optional[Any] = None
    hint: Optional[str] = None
    detailed_explanation: Optional[Dict] = None
    session_progress: Dict[str, Any]


class SessionSummaryResponse(BaseModel):
    """Response with session summary."""
    session_id: str
    mode: str
    name: str
    status: str
    duration_minutes: float
    questions_answered: int
    questions_correct: int
    questions_skipped: int
    accuracy: Optional[float]
    score: Optional[int]
    avg_time_per_question: Optional[float]
    specialty_breakdown: Dict[str, Dict[str, Any]]
    started_at: Optional[str]
    ended_at: Optional[str]


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.get("/modes")
async def get_available_modes():
    """
    Get list of available study modes with their default configurations.
    """
    return {
        "modes": [
            {
                "id": mode,
                "name": mode.replace("_", " ").title(),
                "description": _get_mode_description(mode),
                "defaults": MODE_DEFAULTS.get(mode, {})
            }
            for mode in VALID_MODES
        ]
    }


@router.post("/sessions/start", response_model=SessionResponse)
async def start_study_session(
    request: StartSessionRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Start a new study session.

    Modes:
    - practice: Free-form, immediate feedback, unlimited time
    - timed: Exam simulation, feedback after completion
    - tutor: Detailed explanations and hints
    - challenge: Hard questions only, no hints
    - review: Spaced repetition questions due
    - weak_focus: Target your weak areas
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for existing active session
    active = get_active_session(db, user_id)
    if active:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Active session exists",
                "session_id": active.id,
                "message": "End or abandon your current session first"
            }
        )

    # Validate mode
    if request.mode not in VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {', '.join(VALID_MODES)}"
        )

    try:
        session = create_study_session(
            db=db,
            user_id=user_id,
            mode=request.mode,
            specialty=request.specialty,
            difficulty=request.difficulty,
            target_count=request.target_count,
            time_limit_seconds=request.time_limit_minutes * 60 if request.time_limit_minutes else None,
            name=request.name
        )

        return _session_to_response(session)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/active", response_model=Optional[SessionResponse])
async def get_active_study_session(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get user's currently active study session.
    """
    session = get_active_session(db, user_id)
    if not session:
        return None

    return _session_to_response(session)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_study_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific study session.
    """
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return _session_to_response(session)


@router.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_study_session_summary(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed summary of a study session.
    """
    summary = get_session_summary(db, session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")

    return summary


@router.get("/sessions/history/{user_id}")
async def get_session_history(
    user_id: str,
    mode: Optional[str] = Query(None, description="Filter by mode"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get user's study session history.
    """
    sessions = get_user_sessions(db, user_id, mode=mode, status=status, limit=limit)

    return {
        "sessions": [_session_to_response(s) for s in sessions],
        "total": len(sessions)
    }


# ============================================================================
# Question Flow Endpoints
# ============================================================================

@router.get("/sessions/{session_id}/next", response_model=Optional[QuestionResponse])
async def get_next_session_question(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the next question in the study session.

    Returns null if session is complete or time expired.
    """
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "active":
        return None

    question = get_next_question(db, session)
    if not question:
        return None

    return QuestionResponse(**question)


@router.post("/sessions/{session_id}/submit", response_model=FeedbackResponse)
async def submit_session_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db)
):
    """
    Submit an answer for the current question.

    Feedback varies by mode:
    - Practice/Tutor: Full explanation
    - Timed: Minimal (correct/incorrect only)
    - Challenge: Explanation but no hints
    """
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    result = submit_answer(
        db=db,
        session=session,
        question_id=request.question_id,
        answer=request.answer,
        time_spent_seconds=request.time_spent_seconds,
        confidence_level=request.confidence_level
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return FeedbackResponse(**result)


@router.post("/sessions/{session_id}/skip")
async def skip_session_question(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Skip the current question (for practice/tutor modes).
    """
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.mode == "timed":
        raise HTTPException(status_code=400, detail="Cannot skip questions in timed mode")

    success = skip_question(db, session)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot skip question")

    return {"message": "Question skipped", "skipped_count": session.questions_skipped}


# ============================================================================
# Session Control Endpoints
# ============================================================================

@router.post("/sessions/{session_id}/pause")
async def pause_study_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Pause an active study session.
    Time stops counting for timed sessions.
    """
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.mode == "timed":
        raise HTTPException(status_code=400, detail="Cannot pause timed mode")

    success = pause_session(db, session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause session")

    return {"message": "Session paused", "session_id": session_id}


@router.post("/sessions/{session_id}/resume")
async def resume_study_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Resume a paused study session.
    """
    success = resume_session(db, session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume session")

    return {"message": "Session resumed", "session_id": session_id}


@router.post("/sessions/{session_id}/end", response_model=SessionSummaryResponse)
async def end_study_session(
    session_id: str,
    abandon: bool = Query(False, description="Abandon session without saving results"),
    db: Session = Depends(get_db)
):
    """
    End a study session and get final results.
    """
    reason = "abandoned" if abandon else "completed"
    summary = end_session(db, session_id, reason=reason)

    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")

    return summary


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats/{user_id}")
async def get_user_mode_statistics(
    user_id: str,
    mode: Optional[str] = Query(None, description="Filter by specific mode"),
    db: Session = Depends(get_db)
):
    """
    Get statistics for user's study sessions.
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return get_mode_statistics(db, user_id, mode=mode)


@router.get("/leaderboard/{mode}")
async def get_mode_leaderboard(
    mode: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard for a specific study mode.
    Shows top performers based on accuracy and score.
    """
    if mode not in VALID_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")

    # Query top sessions for this mode
    sessions = db.query(StudySession).filter(
        StudySession.mode == mode,
        StudySession.status == "completed",
        StudySession.questions_answered >= 10  # Minimum questions for ranking
    ).order_by(
        StudySession.accuracy.desc(),
        StudySession.score.desc()
    ).limit(limit).all()

    leaderboard = []
    for i, session in enumerate(sessions):
        user = db.query(User).filter(User.id == session.user_id).first()
        leaderboard.append({
            "rank": i + 1,
            "user_name": user.first_name if user else "Anonymous",
            "accuracy": session.accuracy,
            "score": session.score,
            "questions": session.questions_answered,
            "date": session.ended_at.isoformat() if session.ended_at else None
        })

    return {
        "mode": mode,
        "leaderboard": leaderboard
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _session_to_response(session: StudySession) -> SessionResponse:
    """Convert StudySession to response format."""
    time_remaining = None
    if session.time_limit_seconds and session.status == "active":
        elapsed = (datetime.utcnow() - session.started_at).total_seconds()
        time_remaining = max(0, int(session.time_limit_seconds - elapsed))

    return SessionResponse(
        id=session.id,
        mode=session.mode,
        name=session.name or f"{session.mode.title()} Session",
        status=session.status,
        specialty=session.specialty,
        difficulty=session.difficulty,
        target_count=session.target_count,
        time_limit_seconds=session.time_limit_seconds,
        questions_answered=session.questions_answered or 0,
        questions_correct=session.questions_correct or 0,
        accuracy=session.accuracy,
        time_remaining=time_remaining,
        started_at=session.started_at.isoformat() if session.started_at else None,
        ended_at=session.ended_at.isoformat() if session.ended_at else None
    )


def _get_mode_description(mode: str) -> str:
    """Get description for a study mode."""
    descriptions = {
        "practice": "Free-form study with immediate feedback. No time limit, learn at your own pace.",
        "timed": "Simulate real exam conditions. 40 questions in 60 minutes, feedback after completion.",
        "tutor": "Detailed explanations and hints after each question. Best for learning new material.",
        "challenge": "Hard questions only, no hints. Test your knowledge under pressure.",
        "review": "Spaced repetition review of questions you've seen before. Optimize retention.",
        "weak_focus": "Target your weak areas. Focus on specialties where you need improvement."
    }
    return descriptions.get(mode, "")
