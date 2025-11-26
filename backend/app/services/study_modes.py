"""
Study Modes Service

Provides different study experiences:
- Practice Mode: Free-form questions, immediate feedback
- Timed Mode: Exam simulation with time limit, feedback after completion
- Tutor Mode: Detailed explanations and hints after each question
- Challenge Mode: Hard questions only, no hints
- Review Mode: Spaced repetition questions due for review
- Weak Focus Mode: Targets user's weak areas
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.models.models import (
    StudySession, Question, QuestionAttempt, User,
    ScheduledReview, generate_uuid
)
from app.services.adaptive import select_next_question, get_weak_areas


# ============================================================================
# CONSTANTS
# ============================================================================

VALID_MODES = ["practice", "timed", "tutor", "challenge", "review", "weak_focus"]
VALID_DIFFICULTIES = ["easy", "medium", "hard", "adaptive"]

# Default configurations per mode
MODE_DEFAULTS = {
    "practice": {
        "target_count": None,  # Unlimited
        "time_limit_seconds": None,
        "show_feedback": True,
        "show_hints": True,
        "difficulty": "adaptive"
    },
    "timed": {
        "target_count": 40,  # Standard block
        "time_limit_seconds": 60 * 60,  # 60 minutes
        "show_feedback": False,  # After completion only
        "show_hints": False,
        "difficulty": "adaptive"
    },
    "tutor": {
        "target_count": 20,
        "time_limit_seconds": None,
        "show_feedback": True,
        "show_hints": True,
        "show_detailed_explanation": True,
        "difficulty": "adaptive"
    },
    "challenge": {
        "target_count": 20,
        "time_limit_seconds": None,
        "show_feedback": True,
        "show_hints": False,
        "difficulty": "hard"
    },
    "review": {
        "target_count": None,  # Based on due reviews
        "time_limit_seconds": None,
        "show_feedback": True,
        "show_hints": True,
        "difficulty": None  # Use original difficulty
    },
    "weak_focus": {
        "target_count": 30,
        "time_limit_seconds": None,
        "show_feedback": True,
        "show_hints": True,
        "difficulty": "adaptive"
    }
}


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def create_study_session(
    db: Session,
    user_id: str,
    mode: str,
    specialty: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_count: Optional[int] = None,
    time_limit_seconds: Optional[int] = None,
    name: Optional[str] = None
) -> StudySession:
    """
    Create a new study session with the specified mode and configuration.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode: {mode}. Must be one of {VALID_MODES}")

    if difficulty and difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"Invalid difficulty: {difficulty}")

    # Get mode defaults
    defaults = MODE_DEFAULTS.get(mode, {})

    # Create session with merged config
    session = StudySession(
        id=generate_uuid(),
        user_id=user_id,
        mode=mode,
        name=name or f"{mode.title()} Session",
        specialty=specialty,
        difficulty=difficulty or defaults.get("difficulty"),
        target_count=target_count or defaults.get("target_count"),
        time_limit_seconds=time_limit_seconds or defaults.get("time_limit_seconds"),
        status="active",
        started_at=datetime.utcnow()
    )

    # Pre-populate question pool for certain modes
    if mode == "timed" or mode == "challenge":
        pool = _build_question_pool(
            db, user_id, session.target_count or 40,
            specialty=specialty,
            difficulty=session.difficulty
        )
        session.question_pool = pool

    elif mode == "review":
        pool = _get_due_reviews(db, user_id, limit=50)
        session.question_pool = pool
        session.target_count = len(pool)

    elif mode == "weak_focus":
        pool = _build_weak_area_pool(db, user_id, session.target_count or 30)
        session.question_pool = pool

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def get_session(db: Session, session_id: str) -> Optional[StudySession]:
    """Get a study session by ID."""
    return db.query(StudySession).filter(StudySession.id == session_id).first()


def get_active_session(db: Session, user_id: str) -> Optional[StudySession]:
    """Get user's currently active session, if any."""
    return db.query(StudySession).filter(
        StudySession.user_id == user_id,
        StudySession.status == "active"
    ).first()


def get_user_sessions(
    db: Session,
    user_id: str,
    mode: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20
) -> List[StudySession]:
    """Get user's study sessions with optional filters."""
    query = db.query(StudySession).filter(StudySession.user_id == user_id)

    if mode:
        query = query.filter(StudySession.mode == mode)
    if status:
        query = query.filter(StudySession.status == status)

    return query.order_by(desc(StudySession.created_at)).limit(limit).all()


# ============================================================================
# SESSION ACTIONS
# ============================================================================

def get_next_question(
    db: Session,
    session: StudySession
) -> Optional[Dict[str, Any]]:
    """
    Get the next question for a study session based on mode logic.
    """
    if session.status != "active":
        return None

    # Check if timed session has expired
    if session.time_limit_seconds:
        elapsed = (datetime.utcnow() - session.started_at).total_seconds()
        if elapsed >= session.time_limit_seconds:
            end_session(db, session.id, reason="time_expired")
            return None

    # Check if target count reached
    if session.target_count and session.questions_answered >= session.target_count:
        end_session(db, session.id, reason="target_reached")
        return None

    # Get question based on mode
    question = None

    if session.question_pool:
        # Use pre-built pool
        if session.current_index < len(session.question_pool):
            question_id = session.question_pool[session.current_index]
            question = db.query(Question).filter(Question.id == question_id).first()
    else:
        # Dynamic selection for practice/tutor modes
        question = _select_question_for_mode(db, session)

    if not question:
        return None

    # Build response based on mode
    response = _format_question_for_mode(question, session)

    return response


def submit_answer(
    db: Session,
    session: StudySession,
    question_id: str,
    answer: str,
    time_spent_seconds: int = 0,
    confidence_level: Optional[int] = None
) -> Dict[str, Any]:
    """
    Submit an answer for a study session question.
    Returns feedback based on mode settings.
    """
    if session.status != "active":
        return {"error": "Session is not active"}

    # Get the question
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return {"error": "Question not found"}

    # Check answer
    is_correct = answer == question.correct_answer

    # Record attempt
    attempt = QuestionAttempt(
        id=generate_uuid(),
        user_id=session.user_id,
        question_id=question_id,
        user_answer=answer,
        is_correct=is_correct,
        time_spent_seconds=time_spent_seconds,
        confidence_level=confidence_level,
        attempted_at=datetime.utcnow()
    )
    db.add(attempt)

    # Update session progress
    session.questions_answered += 1
    if is_correct:
        session.questions_correct += 1
    session.time_spent_seconds += time_spent_seconds
    session.current_index += 1
    session.updated_at = datetime.utcnow()

    db.commit()

    # Build feedback based on mode
    mode_config = MODE_DEFAULTS.get(session.mode, {})
    feedback = {
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "session_progress": {
            "answered": session.questions_answered,
            "correct": session.questions_correct,
            "target": session.target_count,
            "accuracy": (session.questions_correct / session.questions_answered * 100)
                        if session.questions_answered > 0 else 0
        }
    }

    # Add feedback based on mode settings
    if mode_config.get("show_feedback", True):
        feedback["explanation"] = question.explanation

        if mode_config.get("show_hints", True) and not is_correct:
            feedback["hint"] = _get_hint_for_question(question, answer)

        if mode_config.get("show_detailed_explanation", False):
            feedback["detailed_explanation"] = _get_detailed_explanation(question)

    # For timed mode, minimal feedback
    if session.mode == "timed":
        feedback = {
            "is_correct": is_correct,
            "session_progress": feedback["session_progress"]
        }

    return feedback


def skip_question(db: Session, session: StudySession) -> bool:
    """Skip the current question in a session."""
    if session.status != "active":
        return False

    session.questions_skipped += 1
    session.current_index += 1
    session.updated_at = datetime.utcnow()
    db.commit()

    return True


def pause_session(db: Session, session_id: str) -> bool:
    """Pause an active session."""
    session = get_session(db, session_id)
    if not session or session.status != "active":
        return False

    session.status = "paused"
    session.paused_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()
    db.commit()

    return True


def resume_session(db: Session, session_id: str) -> bool:
    """Resume a paused session."""
    session = get_session(db, session_id)
    if not session or session.status != "paused":
        return False

    # Add paused duration to started_at to preserve time limit
    if session.paused_at and session.time_limit_seconds:
        pause_duration = datetime.utcnow() - session.paused_at
        session.started_at = session.started_at + pause_duration

    session.status = "active"
    session.paused_at = None
    session.updated_at = datetime.utcnow()
    db.commit()

    return True


def end_session(
    db: Session,
    session_id: str,
    reason: str = "completed"
) -> Optional[Dict[str, Any]]:
    """
    End a study session and calculate final results.
    """
    session = get_session(db, session_id)
    if not session:
        return None

    session.status = "completed" if reason != "abandoned" else "abandoned"
    session.ended_at = datetime.utcnow()

    # Calculate final stats
    if session.questions_answered > 0:
        session.accuracy = session.questions_correct / session.questions_answered * 100
        session.avg_time_per_question = session.time_spent_seconds / session.questions_answered

        # Calculate score (simple percentage * 260 scaling for USMLE-like score)
        session.score = int(session.accuracy * 2.6)

    session.updated_at = datetime.utcnow()
    db.commit()

    # Build session summary
    return get_session_summary(db, session_id)


def get_session_summary(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed summary of a completed session."""
    session = get_session(db, session_id)
    if not session:
        return None

    # Get attempts for this session (by user and time range)
    attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == session.user_id,
        QuestionAttempt.attempted_at >= session.started_at,
        QuestionAttempt.attempted_at <= (session.ended_at or datetime.utcnow())
    ).all()

    # Calculate specialty breakdown
    specialty_stats = {}
    for attempt in attempts:
        question = db.query(Question).filter(Question.id == attempt.question_id).first()
        if question:
            spec = question.source or "Unknown"
            if spec not in specialty_stats:
                specialty_stats[spec] = {"correct": 0, "total": 0}
            specialty_stats[spec]["total"] += 1
            if attempt.is_correct:
                specialty_stats[spec]["correct"] += 1

    return {
        "session_id": session.id,
        "mode": session.mode,
        "name": session.name,
        "status": session.status,
        "duration_minutes": session.time_spent_seconds / 60 if session.time_spent_seconds else 0,
        "questions_answered": session.questions_answered,
        "questions_correct": session.questions_correct,
        "questions_skipped": session.questions_skipped,
        "accuracy": session.accuracy,
        "score": session.score,
        "avg_time_per_question": session.avg_time_per_question,
        "specialty_breakdown": {
            spec: {
                "correct": stats["correct"],
                "total": stats["total"],
                "accuracy": stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
            }
            for spec, stats in specialty_stats.items()
        },
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_question_pool(
    db: Session,
    user_id: str,
    count: int,
    specialty: Optional[str] = None,
    difficulty: Optional[str] = None
) -> List[str]:
    """Build a pool of question IDs for a session."""
    query = db.query(Question.id)

    if specialty:
        query = query.filter(Question.source.ilike(f"%{specialty}%"))

    if difficulty == "hard":
        # Use questions with lower user accuracy or higher difficulty
        query = query.filter(Question.difficulty_level.in_(["hard", "medium"]))
    elif difficulty == "easy":
        query = query.filter(Question.difficulty_level == "easy")

    # Exclude recently answered questions
    recent_attempts = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= datetime.utcnow() - timedelta(days=7)
    ).subquery()

    query = query.filter(~Question.id.in_(recent_attempts))

    # Randomize and limit
    questions = query.order_by(func.random()).limit(count).all()

    return [q.id for q in questions]


def _build_weak_area_pool(
    db: Session,
    user_id: str,
    count: int
) -> List[str]:
    """Build a pool targeting user's weak areas."""
    # Get weak areas
    weak_areas = get_weak_areas(db, user_id)

    if not weak_areas:
        # Fall back to random questions
        return _build_question_pool(db, user_id, count)

    # Get questions from weak areas
    weak_specs = [area["specialty"] for area in weak_areas[:3]]

    query = db.query(Question.id).filter(
        Question.source.in_(weak_specs)
    )

    # Exclude recently answered
    recent_attempts = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= datetime.utcnow() - timedelta(days=3)
    ).subquery()

    query = query.filter(~Question.id.in_(recent_attempts))

    questions = query.order_by(func.random()).limit(count).all()

    return [q.id for q in questions]


def _get_due_reviews(db: Session, user_id: str, limit: int = 50) -> List[str]:
    """Get questions due for spaced repetition review."""
    reviews = db.query(ScheduledReview.question_id).filter(
        ScheduledReview.user_id == user_id,
        ScheduledReview.scheduled_for <= datetime.utcnow()
    ).limit(limit).all()

    return [r.question_id for r in reviews]


def _select_question_for_mode(
    db: Session,
    session: StudySession
) -> Optional[Question]:
    """Dynamically select a question based on session mode."""
    if session.mode == "practice" or session.mode == "tutor":
        # Use adaptive selection
        return select_next_question(
            db,
            session.user_id,
            specialty=session.specialty
        )
    return None


def _format_question_for_mode(
    question: Question,
    session: StudySession
) -> Dict[str, Any]:
    """Format question response based on mode settings."""
    mode_config = MODE_DEFAULTS.get(session.mode, {})

    response = {
        "question_id": question.id,
        "vignette": question.vignette,
        "choices": {
            "A": question.choice_a,
            "B": question.choice_b,
            "C": question.choice_c,
            "D": question.choice_d,
            "E": question.choice_e
        },
        "specialty": question.source,
        "session_info": {
            "mode": session.mode,
            "progress": f"{session.questions_answered + 1}/{session.target_count}" if session.target_count else f"{session.questions_answered + 1}",
            "time_remaining": _get_time_remaining(session)
        }
    }

    # Add hints for tutor mode
    if mode_config.get("show_hints", False) and session.mode == "tutor":
        response["hint_available"] = True

    return response


def _get_time_remaining(session: StudySession) -> Optional[int]:
    """Get remaining time in seconds for timed sessions."""
    if not session.time_limit_seconds:
        return None

    elapsed = (datetime.utcnow() - session.started_at).total_seconds()
    remaining = session.time_limit_seconds - elapsed

    return max(0, int(remaining))


def _get_hint_for_question(question: Question, wrong_answer: str) -> Optional[str]:
    """Generate a hint based on the wrong answer selected."""
    # Simple hint generation - could be enhanced with AI
    hints = {
        "A": "Consider why this option might be a distractor.",
        "B": "Think about the key clinical features mentioned.",
        "C": "Review the timing and presentation of symptoms.",
        "D": "Consider the patient's risk factors.",
        "E": "Think about what makes this diagnosis most likely."
    }
    return hints.get(wrong_answer, "Review the clinical scenario carefully.")


def _get_detailed_explanation(question: Question) -> Dict[str, Any]:
    """Get detailed explanation for tutor mode."""
    explanation = question.explanation
    if isinstance(explanation, dict):
        return explanation
    return {"text": explanation}


# ============================================================================
# STATISTICS
# ============================================================================

def get_mode_statistics(
    db: Session,
    user_id: str,
    mode: Optional[str] = None
) -> Dict[str, Any]:
    """Get statistics for user's study sessions by mode."""
    query = db.query(StudySession).filter(
        StudySession.user_id == user_id,
        StudySession.status == "completed"
    )

    if mode:
        query = query.filter(StudySession.mode == mode)

    sessions = query.all()

    if not sessions:
        return {
            "total_sessions": 0,
            "total_questions": 0,
            "overall_accuracy": 0,
            "by_mode": {}
        }

    total_questions = sum(s.questions_answered or 0 for s in sessions)
    total_correct = sum(s.questions_correct or 0 for s in sessions)

    # Group by mode
    by_mode = {}
    for session in sessions:
        if session.mode not in by_mode:
            by_mode[session.mode] = {
                "sessions": 0,
                "questions": 0,
                "correct": 0,
                "total_time": 0
            }
        by_mode[session.mode]["sessions"] += 1
        by_mode[session.mode]["questions"] += session.questions_answered or 0
        by_mode[session.mode]["correct"] += session.questions_correct or 0
        by_mode[session.mode]["total_time"] += session.time_spent_seconds or 0

    # Calculate accuracies
    for mode_name, stats in by_mode.items():
        stats["accuracy"] = (stats["correct"] / stats["questions"] * 100) if stats["questions"] > 0 else 0
        stats["avg_time_per_question"] = (stats["total_time"] / stats["questions"]) if stats["questions"] > 0 else 0

    return {
        "total_sessions": len(sessions),
        "total_questions": total_questions,
        "overall_accuracy": (total_correct / total_questions * 100) if total_questions > 0 else 0,
        "by_mode": by_mode
    }
