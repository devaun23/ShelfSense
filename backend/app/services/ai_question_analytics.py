"""
AI Question Analytics Service

Tracks performance of AI-generated questions vs NBME questions.
Handles:
1. Performance tracking (accuracy comparison)
2. Difficulty calibration based on actual user performance
3. Quality score calculation
4. Learning stage targeting

This is critical for ensuring AI questions are as effective as real NBME questions.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, Integer, Float, case
from app.models.models import (
    Question, QuestionAttempt, QuestionRating,
    ContentFreshnessScore, ScheduledReview
)


def get_ai_question_performance(db: Session) -> Dict:
    """
    Compare performance of AI-generated questions vs NBME questions.

    Returns accuracy, time spent, and rating comparisons.
    """
    # Get stats for AI-generated questions
    ai_stats = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct'),
        func.avg(QuestionAttempt.time_spent_seconds).label('avg_time')
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        Question.source.like('%AI%')
    ).first()

    # Get stats for NBME questions
    nbme_stats = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct'),
        func.avg(QuestionAttempt.time_spent_seconds).label('avg_time')
    ).join(
        Question, QuestionAttempt.question_id == Question.id
    ).filter(
        ~Question.source.like('%AI%')
    ).first()

    # Get rating stats
    ai_ratings = db.query(
        func.count(QuestionRating.id).label('total'),
        func.sum(func.cast(QuestionRating.rating, Integer)).label('approved')
    ).join(
        Question, QuestionRating.question_id == Question.id
    ).filter(
        Question.source.like('%AI%')
    ).first()

    nbme_ratings = db.query(
        func.count(QuestionRating.id).label('total'),
        func.sum(func.cast(QuestionRating.rating, Integer)).label('approved')
    ).join(
        Question, QuestionRating.question_id == Question.id
    ).filter(
        ~Question.source.like('%AI%')
    ).first()

    return {
        "ai_questions": {
            "total_attempts": ai_stats.total or 0,
            "correct": ai_stats.correct or 0,
            "accuracy": (ai_stats.correct or 0) / (ai_stats.total or 1),
            "avg_time_seconds": ai_stats.avg_time or 0,
            "total_ratings": ai_ratings.total or 0,
            "approval_rate": (ai_ratings.approved or 0) / (ai_ratings.total or 1) if ai_ratings.total else 0
        },
        "nbme_questions": {
            "total_attempts": nbme_stats.total or 0,
            "correct": nbme_stats.correct or 0,
            "accuracy": (nbme_stats.correct or 0) / (nbme_stats.total or 1),
            "avg_time_seconds": nbme_stats.avg_time or 0,
            "total_ratings": nbme_ratings.total or 0,
            "approval_rate": (nbme_ratings.approved or 0) / (nbme_ratings.total or 1) if nbme_ratings.total else 0
        },
        "comparison": {
            "accuracy_difference": ((ai_stats.correct or 0) / (ai_stats.total or 1)) - ((nbme_stats.correct or 0) / (nbme_stats.total or 1)),
            "time_difference": (ai_stats.avg_time or 0) - (nbme_stats.avg_time or 0),
            "ai_is_comparable": abs(((ai_stats.correct or 0) / (ai_stats.total or 1)) - ((nbme_stats.correct or 0) / (nbme_stats.total or 1))) < 0.1
        }
    }


def get_question_actual_difficulty(db: Session, question_id: str) -> Dict:
    """
    Calculate actual difficulty of a question based on user performance.

    Returns calibrated difficulty level and stats.
    """
    stats = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct'),
        func.avg(QuestionAttempt.time_spent_seconds).label('avg_time')
    ).filter(
        QuestionAttempt.question_id == question_id
    ).first()

    total = stats.total or 0
    correct = stats.correct or 0

    if total < 5:
        # Not enough data
        return {
            "question_id": question_id,
            "calibrated": False,
            "reason": "insufficient_data",
            "attempts": total
        }

    accuracy = correct / total

    # Calibrate difficulty based on actual performance
    if accuracy >= 0.85:
        difficulty = "easy"
        target_accuracy = 0.85
    elif accuracy >= 0.65:
        difficulty = "medium"
        target_accuracy = 0.65
    elif accuracy >= 0.45:
        difficulty = "hard"
        target_accuracy = 0.50
    else:
        difficulty = "very_hard"
        target_accuracy = 0.35

    return {
        "question_id": question_id,
        "calibrated": True,
        "actual_accuracy": accuracy,
        "calibrated_difficulty": difficulty,
        "target_accuracy": target_accuracy,
        "attempts": total,
        "avg_time_seconds": stats.avg_time or 0,
        "needs_adjustment": abs(accuracy - target_accuracy) > 0.15
    }


def calibrate_ai_questions(db: Session, min_attempts: int = 10) -> Dict:
    """
    Batch calibrate all AI questions with sufficient data.

    Updates difficulty_level based on actual performance.
    Returns summary of calibrations made.
    """
    # Get AI questions with enough attempts
    ai_questions = db.query(
        Question.id,
        func.count(QuestionAttempt.id).label('attempts'),
        func.avg(func.cast(QuestionAttempt.is_correct, Float)).label('accuracy')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        Question.source.like('%AI%')
    ).group_by(
        Question.id
    ).having(
        func.count(QuestionAttempt.id) >= min_attempts
    ).all()

    calibrations = {
        "total_calibrated": 0,
        "upgraded": [],  # Made easier
        "downgraded": [],  # Made harder
        "unchanged": [],
        "details": []
    }

    for q_id, attempts, accuracy in ai_questions:
        question = db.query(Question).filter(Question.id == q_id).first()
        if not question:
            continue

        old_difficulty = question.difficulty_level or "medium"

        # Determine new difficulty
        if accuracy >= 0.85:
            new_difficulty = "easy"
        elif accuracy >= 0.60:
            new_difficulty = "medium"
        else:
            new_difficulty = "hard"

        # Track change
        if old_difficulty != new_difficulty:
            question.difficulty_level = new_difficulty
            calibrations["total_calibrated"] += 1

            if (old_difficulty == "hard" and new_difficulty in ["medium", "easy"]) or \
               (old_difficulty == "medium" and new_difficulty == "easy"):
                calibrations["upgraded"].append(q_id)
            else:
                calibrations["downgraded"].append(q_id)

            calibrations["details"].append({
                "question_id": q_id,
                "old_difficulty": old_difficulty,
                "new_difficulty": new_difficulty,
                "actual_accuracy": accuracy,
                "attempts": attempts
            })
        else:
            calibrations["unchanged"].append(q_id)

    db.commit()

    return calibrations


def calculate_question_quality_score(db: Session, question_id: str) -> Dict:
    """
    Calculate comprehensive quality score for a question.

    Quality Score = (
        Medical Accuracy (40%) - based on user ratings
        + Discrimination Index (30%) - how well it differentiates skill levels
        + Completion Rate (15%) - % of users who complete vs skip
        + Time Efficiency (15%) - appropriate time spent
    )
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return {"error": "Question not found"}

    # Get attempt stats
    attempts = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct'),
        func.avg(QuestionAttempt.time_spent_seconds).label('avg_time'),
        func.count(case((QuestionAttempt.user_answer.isnot(None), 1))).label('completed')
    ).filter(
        QuestionAttempt.question_id == question_id
    ).first()

    # Get rating stats
    ratings = db.query(
        func.count(QuestionRating.id).label('total'),
        func.sum(func.cast(QuestionRating.rating, Integer)).label('approved')
    ).filter(
        QuestionRating.question_id == question_id
    ).first()

    # Calculate component scores

    # 1. Medical Accuracy Score (from ratings) - 40%
    if ratings.total and ratings.total > 0:
        accuracy_score = (ratings.approved or 0) / ratings.total * 100
    else:
        accuracy_score = 70  # Default for unrated

    # 2. Discrimination Index - 30%
    # Good questions should have ~60-70% correct rate
    if attempts.total and attempts.total >= 5:
        actual_accuracy = (attempts.correct or 0) / attempts.total
        # Optimal is 0.65, penalize for being too easy or too hard
        deviation = abs(actual_accuracy - 0.65)
        discrimination_score = max(0, 100 - (deviation * 200))
    else:
        discrimination_score = 50  # Not enough data

    # 3. Completion Rate - 15%
    if attempts.total and attempts.total > 0:
        completion_rate = (attempts.completed or 0) / attempts.total * 100
    else:
        completion_rate = 100

    # 4. Time Efficiency - 15%
    # Optimal time is 60-120 seconds
    avg_time = attempts.avg_time or 90
    if 60 <= avg_time <= 120:
        time_score = 100
    elif 30 <= avg_time <= 180:
        time_score = 75
    else:
        time_score = 50

    # Calculate weighted total
    quality_score = (
        accuracy_score * 0.40 +
        discrimination_score * 0.30 +
        completion_rate * 0.15 +
        time_score * 0.15
    )

    # Update question quality score
    question.quality_score = quality_score
    db.commit()

    return {
        "question_id": question_id,
        "quality_score": round(quality_score, 1),
        "components": {
            "medical_accuracy": round(accuracy_score, 1),
            "discrimination_index": round(discrimination_score, 1),
            "completion_rate": round(completion_rate, 1),
            "time_efficiency": round(time_score, 1)
        },
        "stats": {
            "total_attempts": attempts.total or 0,
            "approval_rate": (ratings.approved or 0) / (ratings.total or 1) if ratings.total else None,
            "actual_accuracy": (attempts.correct or 0) / (attempts.total or 1) if attempts.total else None,
            "avg_time_seconds": avg_time
        },
        "quality_level": "high" if quality_score >= 80 else "medium" if quality_score >= 60 else "low"
    }


def get_user_learning_stage(db: Session, user_id: str, topic: str = None) -> Dict:
    """
    Determine user's learning stage for targeted question generation.

    Learning Stages:
    - New: < 10 questions in topic, < 50% accuracy
    - Learning: 10-30 questions, 50-70% accuracy
    - Review: 30-100 questions, 70-85% accuracy
    - Mastered: 100+ questions, > 85% accuracy

    Returns appropriate question generation parameters for the stage.
    """
    # Build query for topic or overall
    query = db.query(
        func.count(QuestionAttempt.id).label('total'),
        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
    ).filter(
        QuestionAttempt.user_id == user_id
    )

    if topic:
        query = query.join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            Question.source.like(f'%{topic}%')
        )

    stats = query.first()
    total = stats.total or 0
    correct = stats.correct or 0
    accuracy = correct / total if total > 0 else 0

    # Determine learning stage
    if total < 10 or accuracy < 0.50:
        stage = "New"
        generation_params = {
            "difficulty": "easy",
            "focus": "foundational_concepts",
            "distractor_style": "obvious",
            "explanation_depth": "detailed",
            "target_accuracy": 0.75
        }
    elif total < 30 or accuracy < 0.70:
        stage = "Learning"
        generation_params = {
            "difficulty": "medium",
            "focus": "clinical_application",
            "distractor_style": "moderate",
            "explanation_depth": "standard",
            "target_accuracy": 0.65
        }
    elif total < 100 or accuracy < 0.85:
        stage = "Review"
        generation_params = {
            "difficulty": "medium",
            "focus": "integration",
            "distractor_style": "subtle",
            "explanation_depth": "concise",
            "target_accuracy": 0.70
        }
    else:
        stage = "Mastered"
        generation_params = {
            "difficulty": "hard",
            "focus": "edge_cases",
            "distractor_style": "subtle",
            "explanation_depth": "brief",
            "target_accuracy": 0.60
        }

    return {
        "user_id": user_id,
        "topic": topic or "overall",
        "learning_stage": stage,
        "questions_answered": total,
        "accuracy": accuracy,
        "generation_params": generation_params,
        "next_milestone": {
            "New": {"questions": 10, "accuracy": 0.50},
            "Learning": {"questions": 30, "accuracy": 0.70},
            "Review": {"questions": 100, "accuracy": 0.85},
            "Mastered": {"questions": None, "accuracy": None}
        }.get(stage)
    }


def get_generation_recommendations(db: Session, user_id: str) -> Dict:
    """
    Get comprehensive recommendations for AI question generation.

    Combines:
    - Weakness profile
    - Learning stage
    - Recent performance trends
    - Error patterns

    Returns specific generation parameters for optimal learning.
    """
    from app.services.adaptive import get_user_weakness_profile, get_user_difficulty_target

    # Get weakness profile
    weakness_profile = get_user_weakness_profile(db, user_id)

    # Get learning stage
    learning_stage = get_user_learning_stage(db, user_id)

    # Get difficulty target
    difficulty_target = get_user_difficulty_target(db, user_id)

    # Determine recommended specialty
    if weakness_profile.get("weak_specialties"):
        recommended_specialty = weakness_profile["weak_specialties"][0]["specialty"]
    else:
        recommended_specialty = None

    # Determine recommended topic
    if weakness_profile.get("recent_wrong_topics"):
        recommended_topic = weakness_profile["recent_wrong_topics"][0]
    elif weakness_profile.get("missed_concepts"):
        recommended_topic = weakness_profile["missed_concepts"][0]
    else:
        recommended_topic = None

    # Build generation recommendation
    return {
        "user_id": user_id,
        "recommendation": {
            "specialty": recommended_specialty,
            "topic": recommended_topic,
            "difficulty": difficulty_target["difficulty_level"],
            "learning_stage": learning_stage["learning_stage"],
            "error_pattern_to_target": weakness_profile.get("most_common_error"),
            "generation_params": learning_stage["generation_params"]
        },
        "context": {
            "weakness_profile": weakness_profile,
            "learning_stage": learning_stage,
            "difficulty_target": difficulty_target
        },
        "priority": "weakness_targeted" if weakness_profile.get("weak_specialties") else "learning_stage_appropriate"
    }


def update_content_freshness(db: Session, question_id: str) -> None:
    """
    Update freshness score after a question is attempted or rated.
    """
    # Get or create freshness record
    freshness = db.query(ContentFreshnessScore).filter(
        ContentFreshnessScore.question_id == question_id
    ).first()

    if not freshness:
        freshness = ContentFreshnessScore(question_id=question_id)
        db.add(freshness)

    # Get latest stats
    stats = db.query(
        func.count(QuestionAttempt.id).label('attempts'),
        func.avg(func.cast(QuestionAttempt.is_correct, Float)).label('accuracy')
    ).filter(
        QuestionAttempt.question_id == question_id
    ).first()

    ratings = db.query(
        func.count(QuestionRating.id).label('total'),
        func.avg(func.cast(QuestionRating.rating, Float)).label('approval')
    ).filter(
        QuestionRating.question_id == question_id
    ).first()

    # Update metrics
    freshness.times_attempted = stats.attempts or 0
    freshness.difficulty_index = stats.accuracy if stats.accuracy else None
    freshness.rating_count = ratings.total or 0
    freshness.average_rating = ratings.approval if ratings.approval else None
    freshness.last_updated = datetime.utcnow()

    # Calculate discrimination index (simplified)
    if stats.accuracy and 0.4 <= stats.accuracy <= 0.8:
        freshness.discrimination_index = 1.0 - abs(stats.accuracy - 0.65) * 2
    else:
        freshness.discrimination_index = 0.5

    # Flag for review if issues detected
    if ratings.total and ratings.total >= 5:
        if (ratings.approval or 0) < 0.6:
            freshness.needs_review = True
            freshness.review_reason = "low_rating"
        elif freshness.times_reported > 3:
            freshness.needs_review = True
            freshness.review_reason = "high_report"

    db.commit()
