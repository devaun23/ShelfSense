"""
Item Response Theory (IRT) Based Difficulty Calibration

Implements psychometric calibration to replace LLM-predicted difficulty
with empirically-measured difficulty from actual user responses.

Issue: #9
"""

import math
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    """Empirically calibrated difficulty levels"""
    VERY_EASY = "very_easy"   # p-value > 0.85
    EASY = "easy"             # p-value 0.70-0.85
    MEDIUM = "medium"         # p-value 0.55-0.70
    HARD = "hard"             # p-value 0.40-0.55
    VERY_HARD = "very_hard"   # p-value < 0.40


@dataclass
class IRTParameters:
    """Item Response Theory parameters for a question"""
    question_id: str
    p_value: float                    # Proportion correct (difficulty)
    discrimination_index: float       # Point-biserial correlation
    response_count: int               # Number of responses used
    difficulty_level: DifficultyLevel # Categorical difficulty
    confidence_interval: Tuple[float, float]  # 95% CI for p-value
    last_calibrated: datetime
    is_calibrated: bool               # True if min responses met


@dataclass
class DistractorMetrics:
    """Metrics for individual answer choices"""
    choice: str                       # A, B, C, D, or E
    selection_rate: float             # Proportion who selected this
    strong_student_rate: float        # Rate among top 27%
    weak_student_rate: float          # Rate among bottom 27%
    discrimination: float             # Difference in rates


@dataclass
class QuestionPsychometrics:
    """Complete psychometric profile for a question"""
    irt_params: IRTParameters
    distractor_metrics: List[DistractorMetrics]
    correct_choice: str
    quality_flags: List[str]          # Issues detected
    recommendations: List[str]        # Suggested improvements


class IRTCalibrator:
    """
    Calibrate question difficulty using Item Response Theory.

    After sufficient responses (default 50), calculates:
    - Difficulty (p-value): What proportion answer correctly?
    - Discrimination (point-biserial): How well does it separate strong/weak students?
    - Guessing parameter: Estimated chance of guessing (typically 0.2 for 5-choice)
    """

    MIN_RESPONSES_FOR_CALIBRATION = 50
    MIN_RESPONSES_FOR_DISTRACTOR_ANALYSIS = 100

    # P-value thresholds for difficulty classification
    DIFFICULTY_THRESHOLDS = {
        DifficultyLevel.VERY_EASY: 0.85,
        DifficultyLevel.EASY: 0.70,
        DifficultyLevel.MEDIUM: 0.55,
        DifficultyLevel.HARD: 0.40,
        # Below 0.40 = VERY_HARD
    }

    def __init__(self, db: Session):
        """Initialize calibrator with database session"""
        self.db = db

    def get_question_responses(
        self,
        question_id: str,
        min_count: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all responses for a question.

        Returns list of dicts with:
        - user_id
        - is_correct
        - user_answer
        - user_total_score (for discrimination calculation)
        """
        from app.models.models import QuestionAttempt
        from sqlalchemy import case

        min_count = min_count or self.MIN_RESPONSES_FOR_CALIBRATION

        # Get responses for this question
        responses = self.db.query(QuestionAttempt).filter(
            QuestionAttempt.question_id == question_id
        ).all()

        if len(responses) < min_count:
            return []

        # Get unique user IDs from responses
        user_ids = list(set(r.user_id for r in responses))

        # BATCH QUERY: Get all user scores in ONE query instead of N queries
        # This fixes the N+1 query problem identified in code review
        user_score_query = self.db.query(
            QuestionAttempt.user_id,
            (func.sum(case((QuestionAttempt.is_correct.is_(True), 1), else_=0)) /
             func.count(QuestionAttempt.id)).label('accuracy')
        ).filter(
            QuestionAttempt.user_id.in_(user_ids)
        ).group_by(
            QuestionAttempt.user_id
        ).all()

        # Convert to dictionary for O(1) lookup
        user_scores = {user_id: float(accuracy) for user_id, accuracy in user_score_query}

        return [{
            "user_id": r.user_id,
            "is_correct": r.is_correct,
            "user_answer": r.user_answer,
            "user_total_score": user_scores.get(r.user_id, 0.5)
        } for r in responses]

    def calculate_p_value(self, responses: List[Dict]) -> float:
        """
        Calculate proportion correct (p-value).

        This is the classical test theory difficulty metric.
        Higher p-value = easier question.
        """
        if not responses:
            return 0.5  # Default to medium if no data

        correct_count = sum(1 for r in responses if r["is_correct"])
        return correct_count / len(responses)

    def calculate_discrimination_index(self, responses: List[Dict]) -> float:
        """
        Calculate point-biserial correlation (discrimination index).

        Measures how well the item distinguishes between high and low performers.
        - Good items: 0.30-0.70
        - Excellent items: > 0.70
        - Poor items: < 0.20 (consider revising)
        - Negative: Item is flawed (high performers doing worse)
        """
        if len(responses) < 20:
            return 0.0  # Not enough data

        # Sort by total score
        sorted_responses = sorted(responses, key=lambda x: x["user_total_score"])

        # Take top and bottom 27% (standard psychometric practice)
        n = len(sorted_responses)
        group_size = max(1, int(n * 0.27))

        bottom_group = sorted_responses[:group_size]
        top_group = sorted_responses[-group_size:]

        # Calculate proportion correct in each group
        bottom_correct = sum(1 for r in bottom_group if r["is_correct"]) / len(bottom_group)
        top_correct = sum(1 for r in top_group if r["is_correct"]) / len(top_group)

        # Discrimination = difference in proportions
        discrimination = top_correct - bottom_correct

        return discrimination

    def calculate_confidence_interval(
        self,
        p_value: float,
        n: int,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for p-value using Wilson score interval.

        This is more accurate than normal approximation for proportions,
        especially near 0 or 1.
        """
        if n == 0:
            return (0.0, 1.0)

        z = 1.96 if confidence == 0.95 else 2.576  # z-score for 95% or 99% CI

        denominator = 1 + z**2 / n
        center = (p_value + z**2 / (2*n)) / denominator
        spread = z * math.sqrt((p_value * (1 - p_value) + z**2 / (4*n)) / n) / denominator

        lower = max(0.0, center - spread)
        upper = min(1.0, center + spread)

        return (lower, upper)

    def classify_difficulty(self, p_value: float) -> DifficultyLevel:
        """Convert p-value to categorical difficulty level"""
        for level, threshold in self.DIFFICULTY_THRESHOLDS.items():
            if p_value >= threshold:
                return level
        return DifficultyLevel.VERY_HARD

    def calibrate_question(self, question_id: str) -> Optional[IRTParameters]:
        """
        Perform full IRT calibration for a question.

        Returns None if insufficient responses.
        """
        responses = self.get_question_responses(question_id)

        if len(responses) < self.MIN_RESPONSES_FOR_CALIBRATION:
            logger.debug(
                "Question %s has %d responses, need %d for calibration",
                question_id, len(responses), self.MIN_RESPONSES_FOR_CALIBRATION
            )
            return None

        p_value = self.calculate_p_value(responses)
        discrimination = self.calculate_discrimination_index(responses)
        ci = self.calculate_confidence_interval(p_value, len(responses))
        difficulty = self.classify_difficulty(p_value)

        return IRTParameters(
            question_id=question_id,
            p_value=p_value,
            discrimination_index=discrimination,
            response_count=len(responses),
            difficulty_level=difficulty,
            confidence_interval=ci,
            last_calibrated=datetime.utcnow(),
            is_calibrated=True
        )

    def analyze_distractors(self, question_id: str) -> List[DistractorMetrics]:
        """
        Analyze distractor effectiveness.

        Good distractors:
        - Selected by 15-25% of students
        - Selected more by weak students than strong students
        - Not selected by >30% (too attractive) or <5% (obviously wrong)
        """
        from app.models.models import QuestionAttempt, Question

        responses = self.get_question_responses(
            question_id,
            min_count=self.MIN_RESPONSES_FOR_DISTRACTOR_ANALYSIS
        )

        if len(responses) < self.MIN_RESPONSES_FOR_DISTRACTOR_ANALYSIS:
            return []

        # Get the correct answer
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return []

        correct_answer = question.answer_key

        # Sort by total score for group analysis
        sorted_responses = sorted(responses, key=lambda x: x["user_total_score"])
        n = len(sorted_responses)
        group_size = max(1, int(n * 0.27))

        weak_group = sorted_responses[:group_size]
        strong_group = sorted_responses[-group_size:]

        metrics = []
        for choice in ["A", "B", "C", "D", "E"]:
            # Overall selection rate
            choice_count = sum(1 for r in responses if r["user_answer"] == choice)
            selection_rate = choice_count / len(responses) if responses else 0

            # Strong student rate
            strong_count = sum(1 for r in strong_group if r["user_answer"] == choice)
            strong_rate = strong_count / len(strong_group) if strong_group else 0

            # Weak student rate
            weak_count = sum(1 for r in weak_group if r["user_answer"] == choice)
            weak_rate = weak_count / len(weak_group) if weak_group else 0

            # Discrimination for this choice
            # For correct answer: strong should select more (positive)
            # For distractors: weak should select more (negative is good)
            discrimination = strong_rate - weak_rate

            metrics.append(DistractorMetrics(
                choice=choice,
                selection_rate=selection_rate,
                strong_student_rate=strong_rate,
                weak_student_rate=weak_rate,
                discrimination=discrimination
            ))

        return metrics

    def get_full_psychometrics(self, question_id: str) -> Optional[QuestionPsychometrics]:
        """
        Get complete psychometric profile for a question.

        Includes IRT parameters, distractor analysis, and quality flags.
        """
        from app.models.models import Question

        irt_params = self.calibrate_question(question_id)
        if not irt_params:
            return None

        distractor_metrics = self.analyze_distractors(question_id)

        question = self.db.query(Question).filter(Question.id == question_id).first()
        correct_choice = question.answer_key if question else "?"

        # Generate quality flags and recommendations
        flags = []
        recommendations = []

        # Check difficulty
        if irt_params.p_value > 0.90:
            flags.append("TOO_EASY")
            recommendations.append("Question may be too easy; consider increasing difficulty")
        elif irt_params.p_value < 0.30:
            flags.append("TOO_HARD")
            recommendations.append("Question may be too hard; review for clarity or content issues")

        # Check discrimination
        if irt_params.discrimination_index < 0.20:
            flags.append("LOW_DISCRIMINATION")
            recommendations.append("Item does not discriminate well between strong and weak students")
        elif irt_params.discrimination_index < 0:
            flags.append("NEGATIVE_DISCRIMINATION")
            recommendations.append("CRITICAL: Strong students perform worse than weak students - review for errors")

        # Check distractors
        for dm in distractor_metrics:
            if dm.choice != correct_choice:
                if dm.selection_rate < 0.05:
                    flags.append(f"DISTRACTOR_{dm.choice}_TOO_OBVIOUS")
                    recommendations.append(f"Choice {dm.choice} selected by <5% - too obviously wrong")
                elif dm.selection_rate > 0.30:
                    flags.append(f"DISTRACTOR_{dm.choice}_TOO_ATTRACTIVE")
                    recommendations.append(f"Choice {dm.choice} selected by >30% - may be correct or ambiguous")

                # Positive discrimination for distractor is bad
                if dm.discrimination > 0.1:
                    flags.append(f"DISTRACTOR_{dm.choice}_ATTRACTS_STRONG")
                    recommendations.append(f"Choice {dm.choice} attracts strong students - review for accuracy")

        return QuestionPsychometrics(
            irt_params=irt_params,
            distractor_metrics=distractor_metrics,
            correct_choice=correct_choice,
            quality_flags=flags,
            recommendations=recommendations
        )

    def recalibrate_difficulty(self, question_id: str) -> Optional[str]:
        """
        Recalibrate and update question difficulty based on actual performance.

        Returns the new difficulty level string, or None if cannot calibrate.
        """
        from app.models.models import Question

        irt_params = self.calibrate_question(question_id)
        if not irt_params:
            return None

        # Map IRT difficulty to stored difficulty levels
        difficulty_map = {
            DifficultyLevel.VERY_EASY: "easy",
            DifficultyLevel.EASY: "easy",
            DifficultyLevel.MEDIUM: "medium",
            DifficultyLevel.HARD: "hard",
            DifficultyLevel.VERY_HARD: "hard",
        }

        new_difficulty = difficulty_map[irt_params.difficulty_level]

        # Update the question
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if question:
            old_difficulty = question.difficulty_level
            question.difficulty_level = new_difficulty

            # Store IRT data in extra_data
            # Create new dict to ensure SQLAlchemy detects the mutation
            existing_data = question.extra_data or {}
            question.extra_data = {
                **existing_data,
                "irt_calibration": {
                    "p_value": irt_params.p_value,
                    "discrimination": irt_params.discrimination_index,
                    "response_count": irt_params.response_count,
                    "confidence_interval": list(irt_params.confidence_interval),
                    "calibrated_at": irt_params.last_calibrated.isoformat(),
                    "previous_difficulty": old_difficulty
                }
            }

            # Safe commit with rollback on failure
            try:
                self.db.commit()
                logger.info(
                    "Recalibrated question %s: %s -> %s (p=%.2f, d=%.2f, n=%d)",
                    question_id, old_difficulty, new_difficulty,
                    irt_params.p_value, irt_params.discrimination_index,
                    irt_params.response_count
                )
            except Exception as e:
                self.db.rollback()
                logger.error("Failed to commit recalibration for %s: %s", question_id, e)
                return None

        return new_difficulty

    def get_calibration_candidates(self, limit: int = 100) -> List[str]:
        """
        Get questions that need calibration.

        Prioritizes:
        1. Questions with enough responses but never calibrated
        2. Questions not calibrated in >30 days
        3. Questions with significant response count increase since last calibration
        """
        from app.models.models import Question, QuestionAttempt

        # Get questions with enough responses
        response_counts = self.db.query(
            QuestionAttempt.question_id,
            func.count(QuestionAttempt.id).label("count")
        ).group_by(
            QuestionAttempt.question_id
        ).having(
            func.count(QuestionAttempt.id) >= self.MIN_RESPONSES_FOR_CALIBRATION
        ).subquery()

        # Get questions that need calibration
        candidates = self.db.query(Question.id).join(
            response_counts,
            Question.id == response_counts.c.question_id
        ).filter(
            # Either never calibrated or calibrated >30 days ago
            (Question.extra_data.is_(None)) |
            (~Question.extra_data.has_key("irt_calibration"))
        ).limit(limit).all()

        return [c[0] for c in candidates]

    def batch_calibrate(self, question_ids: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Calibrate multiple questions.

        If question_ids is None, auto-selects candidates.

        Returns dict of question_id -> new difficulty level
        """
        if question_ids is None:
            question_ids = self.get_calibration_candidates()

        results = {}
        for qid in question_ids:
            try:
                new_difficulty = self.recalibrate_difficulty(qid)
                if new_difficulty:
                    results[qid] = new_difficulty
            except Exception as e:
                logger.warning("Failed to calibrate question %s: %s", qid, e)

        logger.info("Batch calibration complete: %d questions calibrated", len(results))
        return results


def get_empirical_difficulty(db: Session, question_id: str) -> Optional[float]:
    """
    Convenience function to get empirical difficulty (p-value) for a question.

    Returns None if insufficient data.
    """
    calibrator = IRTCalibrator(db)
    params = calibrator.calibrate_question(question_id)
    return params.p_value if params else None


def should_use_empirical_difficulty(db: Session, question_id: str) -> bool:
    """
    Check if we have enough data to use empirical difficulty instead of LLM-predicted.
    """
    from app.models.models import QuestionAttempt

    count = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.question_id == question_id
    ).scalar() or 0

    return count >= IRTCalibrator.MIN_RESPONSES_FOR_CALIBRATION
