"""
Integration Tests for Adaptive Learning Algorithm.

Tests the complete flow of the adaptive algorithm including:
- Weak area identification
- Question selection strategy
- Score prediction
- Performance tracking
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import User, Question, QuestionAttempt
from app.services.adaptive import (
    get_weak_areas,
    get_unanswered_questions,
    select_next_question,
    calculate_predicted_score,
    get_performance_by_source
)


class TestWeakAreaIdentification:
    """Integration tests for identifying user weak areas"""

    @pytest.mark.integration
    def test_identifies_weak_specialty(self, db: Session, test_user: User):
        """Test that weak areas are correctly identified by specialty"""
        # Create questions in two specialties
        specialties = ["Internal Medicine - Strong", "Surgery - Weak"]

        for specialty in specialties:
            for i in range(10):
                q = Question(
                    vignette=f"Question {i} for {specialty}",
                    answer_key="A",
                    choices=["A", "B", "C", "D", "E"],
                    source=specialty,
                    recency_weight=0.8
                )
                db.add(q)
                db.flush()

                # Internal Medicine: 80% correct, Surgery: 40% correct
                is_correct = (
                    (specialty == "Internal Medicine - Strong" and i < 8) or
                    (specialty == "Surgery - Weak" and i < 4)
                )

                attempt = QuestionAttempt(
                    user_id=test_user.id,
                    question_id=q.id,
                    user_answer="A" if is_correct else "B",
                    is_correct=is_correct,
                    time_spent_seconds=60
                )
                db.add(attempt)
        db.commit()

        weak_areas = get_weak_areas(db, test_user.id, threshold=0.6)

        # Surgery should be identified as weak area
        assert "Surgery - Weak" in weak_areas
        assert "Internal Medicine - Strong" not in weak_areas

    @pytest.mark.integration
    def test_no_weak_areas_for_strong_performance(self, db: Session, test_user: User):
        """Test that no weak areas returned when all performance is strong"""
        # Create questions with 80% accuracy across all areas
        for i in range(15):
            q = Question(
                vignette=f"Strong performance question {i}",
                answer_key="A",
                choices=["A", "B", "C", "D", "E"],
                source="General Medicine",
                recency_weight=0.8
            )
            db.add(q)
            db.flush()

            attempt = QuestionAttempt(
                user_id=test_user.id,
                question_id=q.id,
                user_answer="A" if i < 12 else "B",  # 80% correct
                is_correct=i < 12,
                time_spent_seconds=60
            )
            db.add(attempt)
        db.commit()

        weak_areas = get_weak_areas(db, test_user.id, threshold=0.6)

        assert len(weak_areas) == 0


class TestQuestionSelection:
    """Integration tests for adaptive question selection"""

    @pytest.mark.integration
    def test_select_unanswered_questions(self, db: Session, test_user: User):
        """Test that unanswered questions are prioritized"""
        # Create questions - some answered, some not
        answered_q = Question(
            vignette="Answered question",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            source="Test",
            recency_weight=0.8
        )
        unanswered_q = Question(
            vignette="Unanswered question",
            answer_key="B",
            choices=["A", "B", "C", "D", "E"],
            source="Test",
            recency_weight=0.9
        )
        db.add(answered_q)
        db.add(unanswered_q)
        db.flush()

        # Mark one as answered
        attempt = QuestionAttempt(
            user_id=test_user.id,
            question_id=answered_q.id,
            user_answer="A",
            is_correct=True,
            time_spent_seconds=60
        )
        db.add(attempt)
        db.commit()

        unanswered = get_unanswered_questions(db, test_user.id)

        # Should only return the unanswered question
        unanswered_ids = [q.id for q in unanswered]
        assert unanswered_q.id in unanswered_ids
        assert answered_q.id not in unanswered_ids

    @pytest.mark.integration
    def test_select_question_returns_question(self, db: Session, test_user: User, test_questions_batch: list[Question]):
        """Test that select_next_question returns a valid question"""
        selected = select_next_question(db, test_user.id, use_ai=False)

        assert selected is not None
        assert isinstance(selected, Question)
        assert selected.vignette is not None


class TestScorePrediction:
    """Integration tests for predicted score calculation"""

    @pytest.mark.integration
    def test_predict_score_no_attempts(self, db: Session, test_user: User):
        """Test prediction returns None for user with no attempts"""
        score = calculate_predicted_score(db, test_user.id)

        assert score is None

    @pytest.mark.integration
    def test_predict_score_high_performer(self, db: Session, test_user: User):
        """Test score prediction for high performer (should be high)"""
        # Create 30 attempts with 85% accuracy
        for i in range(30):
            q = Question(
                vignette=f"Prediction test {i}",
                answer_key="A",
                choices=["A", "B", "C", "D", "E"],
                source="Test",
                recency_weight=0.9
            )
            db.add(q)
            db.flush()

            attempt = QuestionAttempt(
                user_id=test_user.id,
                question_id=q.id,
                user_answer="A" if i < 26 else "B",  # ~85% accuracy
                is_correct=i < 26,
                time_spent_seconds=60
            )
            db.add(attempt)
        db.commit()

        score = calculate_predicted_score(db, test_user.id)

        assert score is not None
        assert 194 <= score <= 300
        assert score >= 240  # High performers should predict high

    @pytest.mark.integration
    def test_predict_score_low_performer(self, db: Session, test_user: User):
        """Test score prediction for struggling user (should be lower)"""
        # Create 30 attempts with 50% accuracy
        for i in range(30):
            q = Question(
                vignette=f"Low score test {i}",
                answer_key="A",
                choices=["A", "B", "C", "D", "E"],
                source="Test",
                recency_weight=0.9
            )
            db.add(q)
            db.flush()

            attempt = QuestionAttempt(
                user_id=test_user.id,
                question_id=q.id,
                user_answer="A" if i < 15 else "B",  # 50% accuracy
                is_correct=i < 15,
                time_spent_seconds=60
            )
            db.add(attempt)
        db.commit()

        score = calculate_predicted_score(db, test_user.id)

        assert score is not None
        assert 194 <= score <= 300
        assert score < 240  # Low performers should predict lower


class TestPerformanceBySource:
    """Integration tests for performance breakdown by source"""

    @pytest.mark.integration
    def test_performance_breakdown_by_specialty(self, db: Session, test_user: User):
        """Test performance is correctly broken down by source"""
        sources = {
            "Internal Medicine": (10, 8),  # 80% accuracy
            "Surgery": (10, 5),  # 50% accuracy
            "Pediatrics": (10, 9)  # 90% accuracy
        }

        for source, (total, correct) in sources.items():
            for i in range(total):
                q = Question(
                    vignette=f"{source} question {i}",
                    answer_key="A",
                    choices=["A", "B", "C", "D", "E"],
                    source=source,
                    recency_weight=0.8
                )
                db.add(q)
                db.flush()

                attempt = QuestionAttempt(
                    user_id=test_user.id,
                    question_id=q.id,
                    user_answer="A" if i < correct else "B",
                    is_correct=i < correct,
                    time_spent_seconds=60
                )
                db.add(attempt)
        db.commit()

        performance = get_performance_by_source(db, test_user.id)

        assert "Internal Medicine" in performance
        assert "Surgery" in performance
        assert "Pediatrics" in performance

        assert performance["Internal Medicine"]["accuracy"] == pytest.approx(0.8, rel=0.01)
        assert performance["Surgery"]["accuracy"] == pytest.approx(0.5, rel=0.01)
        assert performance["Pediatrics"]["accuracy"] == pytest.approx(0.9, rel=0.01)
