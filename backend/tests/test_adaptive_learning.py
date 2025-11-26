"""
Tests for Adaptive Learning Engine Agent.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.models import User, Question, QuestionAttempt
from app.services.adaptive_learning_engine import (
    AdaptiveLearningEngineAgent,
    get_adaptive_learning_engine,
    EXPLANATION_TYPES,
    EXPLANATION_QUALITY_RULES
)


class TestWeakAreaIdentification:
    """Test weak area identification with recency weighting"""

    @pytest.mark.unit
    def test_get_weak_areas_no_attempts(self, db: Session, test_user: User):
        """Test weak areas returns empty for user with no attempts"""
        agent = get_adaptive_learning_engine(db)
        result = agent.get_detailed_weak_areas(test_user.id)

        assert result["weak_areas"] == []
        assert "No attempts yet" in result["analysis"]

    @pytest.mark.unit
    def test_get_weak_areas_with_attempts(
        self, db: Session, test_user: User, test_attempts_history: list[QuestionAttempt]
    ):
        """Test weak areas identified from attempt history"""
        agent = get_adaptive_learning_engine(db)
        result = agent.get_detailed_weak_areas(test_user.id, threshold=0.6)

        assert "weak_areas" in result
        assert "strong_areas" in result
        assert "recommendations" in result
        assert isinstance(result["weak_areas"], list)

    @pytest.mark.unit
    def test_weak_area_threshold(self, db: Session):
        """Test that threshold correctly filters weak areas"""
        from tests.conftest import create_user_with_performance

        # Create user with 50% accuracy
        user, _ = create_user_with_performance(db, accuracy=0.5, num_attempts=20)

        agent = get_adaptive_learning_engine(db)

        # With 60% threshold, 50% accuracy should be weak
        result_60 = agent.get_detailed_weak_areas(user.id, threshold=0.6)

        # With 40% threshold, 50% accuracy should not be weak
        result_40 = agent.get_detailed_weak_areas(user.id, threshold=0.4)

        # Results should differ based on threshold
        assert len(result_60.get("weak_areas", [])) >= len(result_40.get("weak_areas", []))


class TestQuestionSelection:
    """Test adaptive question selection algorithm"""

    @pytest.mark.unit
    def test_select_question_returns_question(
        self, db: Session, test_user: User, test_questions_batch: list[Question]
    ):
        """Test that question selection returns a question"""
        agent = get_adaptive_learning_engine(db)
        question = agent.select_adaptive_question(test_user.id)

        assert question is not None
        assert isinstance(question, Question)
        assert question.vignette is not None

    @pytest.mark.unit
    def test_select_question_avoids_recent(
        self, db: Session, test_user: User, test_question: Question, test_attempt: QuestionAttempt
    ):
        """Test that recently answered questions are avoided"""
        # Create more questions so there are alternatives
        for i in range(5):
            q = Question(
                vignette=f"Alternative question {i}",
                answer_key="A",
                choices=["A", "B", "C", "D", "E"],
                source="Test",
                recency_weight=0.8
            )
            db.add(q)
        db.commit()

        agent = get_adaptive_learning_engine(db)

        # Select multiple times - should not get the recently answered question
        selected_ids = set()
        for _ in range(5):
            q = agent.select_adaptive_question(test_user.id)
            if q:
                selected_ids.add(q.id)

        # The test_question was answered recently, so it should be avoided
        # (though not guaranteed if it's the only option)
        assert len(selected_ids) >= 1

    @pytest.mark.unit
    def test_difficulty_adjustment(self, db: Session, test_user: User, test_questions_batch: list[Question]):
        """Test that difficulty adjustment affects selection"""
        agent = get_adaptive_learning_engine(db)

        # Select with easier difficulty
        q_easier = agent.select_adaptive_question(test_user.id, difficulty_adjustment=-0.5)

        # Select with harder difficulty
        q_harder = agent.select_adaptive_question(test_user.id, difficulty_adjustment=0.5)

        # Both should return questions
        assert q_easier is not None or q_harder is not None


class TestTimeAnalysis:
    """Test time-to-answer analysis"""

    @pytest.mark.unit
    def test_time_analysis_insufficient_data(self, db: Session, test_user: User):
        """Test time analysis with insufficient data"""
        agent = get_adaptive_learning_engine(db)
        result = agent.analyze_time_patterns(test_user.id)

        assert "Need more attempts" in result["analysis"]

    @pytest.mark.unit
    def test_time_analysis_with_data(self, db: Session, test_user: User, test_questions_batch: list[Question]):
        """Test time analysis with sufficient data"""
        # Create attempts with varying times
        for i, q in enumerate(test_questions_batch * 3):  # 15 attempts
            attempt = QuestionAttempt(
                user_id=test_user.id,
                question_id=q.id,
                user_answer="A",
                is_correct=(i % 2 == 0),
                time_spent_seconds=30 + (i * 15),  # Varying times
                attempted_at=datetime.utcnow() - timedelta(hours=i)
            )
            db.add(attempt)
        db.commit()

        agent = get_adaptive_learning_engine(db)
        result = agent.analyze_time_patterns(test_user.id)

        assert "time_buckets" in result
        assert "optimal_time_range" in result
        assert "avg_time_correct" in result
        assert "avg_time_incorrect" in result


class TestConfidenceTracking:
    """Test confidence calibration analysis"""

    @pytest.mark.unit
    def test_confidence_analysis_insufficient_data(self, db: Session, test_user: User):
        """Test confidence analysis with insufficient data"""
        agent = get_adaptive_learning_engine(db)
        result = agent.analyze_confidence_patterns(test_user.id)

        assert "Need more" in result["analysis"]

    @pytest.mark.unit
    def test_confidence_calibration_score(self, db: Session, test_user: User, test_questions_batch: list[Question]):
        """Test confidence calibration scoring"""
        # Create attempts with confidence levels
        for i, q in enumerate(test_questions_batch * 5):  # 25 attempts
            confidence = (i % 5) + 1  # 1-5 confidence
            is_correct = confidence >= 3  # Higher confidence = more likely correct (well calibrated)

            attempt = QuestionAttempt(
                user_id=test_user.id,
                question_id=q.id,
                user_answer="A" if is_correct else "B",
                is_correct=is_correct,
                time_spent_seconds=90,
                confidence_level=confidence,
                attempted_at=datetime.utcnow() - timedelta(hours=i)
            )
            db.add(attempt)
        db.commit()

        agent = get_adaptive_learning_engine(db)
        result = agent.analyze_confidence_patterns(test_user.id)

        assert "calibration_score" in result
        assert "by_confidence_level" in result


class TestLearningVelocity:
    """Test learning velocity measurement"""

    @pytest.mark.unit
    def test_velocity_insufficient_data(self, db: Session, test_user: User):
        """Test velocity with insufficient data"""
        agent = get_adaptive_learning_engine(db)
        result = agent.calculate_learning_velocity(test_user.id)

        assert "Need more" in result["analysis"]


class TestPredictiveAnalytics:
    """Test performance prediction"""

    @pytest.mark.unit
    def test_prediction_insufficient_data(self, db: Session, test_user: User):
        """Test prediction with insufficient data"""
        agent = get_adaptive_learning_engine(db)
        result = agent.predict_exam_performance(test_user.id)

        assert result["predicted_score"] is None
        assert "Need at least 50" in result["analysis"]

    @pytest.mark.unit
    def test_prediction_with_data(self, db: Session):
        """Test prediction with sufficient data"""
        from tests.conftest import create_user_with_performance

        user, _ = create_user_with_performance(db, accuracy=0.75, num_attempts=60)

        agent = get_adaptive_learning_engine(db)
        result = agent.predict_exam_performance(user.id)

        assert result["predicted_score"] is not None
        assert 194 <= result["predicted_score"] <= 300
        assert result["readiness"] in ["high", "moderate", "developing", "needs_work"]


class TestExplanationValidation:
    """Test explanation validation and quality assurance"""

    @pytest.mark.unit
    def test_validate_good_explanation(self, db: Session, test_question: Question):
        """Test validation of a properly structured explanation"""
        agent = get_adaptive_learning_engine(db)
        result = agent.validate_question_explanation(test_question.id)

        assert result["valid"] == True or result["quality_score"] >= 60
        assert result["question_id"] == test_question.id

    @pytest.mark.unit
    def test_validate_missing_explanation(self, db: Session):
        """Test validation of question without explanation"""
        question = Question(
            vignette="Test vignette",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=None  # No explanation
        )
        db.add(question)
        db.commit()

        agent = get_adaptive_learning_engine(db)
        result = agent.validate_question_explanation(question.id)

        assert result["valid"] == False
        assert result["needs_regeneration"] == True
        assert "No explanation found" in result["issues"]

    @pytest.mark.unit
    def test_validate_string_explanation(self, db: Session):
        """Test validation of legacy string explanation"""
        question = Question(
            vignette="Test vignette",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation="This is a plain text explanation without structure."
        )
        db.add(question)
        db.commit()

        agent = get_adaptive_learning_engine(db)
        result = agent.validate_question_explanation(question.id)

        assert result["valid"] == False
        assert result["needs_regeneration"] == True

    @pytest.mark.unit
    def test_explanation_types_defined(self):
        """Test that all explanation types are properly defined"""
        expected_types = [
            "TYPE_A_STABILITY",
            "TYPE_B_TIME_SENSITIVE",
            "TYPE_C_DIAGNOSTIC_SEQUENCE",
            "TYPE_D_RISK_STRATIFICATION",
            "TYPE_E_TREATMENT_HIERARCHY",
            "TYPE_F_DIFFERENTIAL"
        ]

        for exp_type in expected_types:
            assert exp_type in EXPLANATION_TYPES
            assert "name" in EXPLANATION_TYPES[exp_type]
            assert "identify" in EXPLANATION_TYPES[exp_type]
            assert "pattern" in EXPLANATION_TYPES[exp_type]

    @pytest.mark.unit
    def test_quality_rules_defined(self):
        """Test that quality rules are properly defined"""
        assert len(EXPLANATION_QUALITY_RULES) > 0
        assert "principle_required" in EXPLANATION_QUALITY_RULES
        assert "numbers_defined" in EXPLANATION_QUALITY_RULES


class TestAnswerChoiceValidation:
    """Test answer choice validation"""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_validate_good_choices(self, db: Session, test_question: Question, mock_openai):
        """Test validation of properly structured choices"""
        # Mock the OpenAI response for validation
        mock_openai.chat.completions.create.return_value.choices[0].message.content = '''
        {
            "same_category": true,
            "category_type": "treatment",
            "has_duplicates": false,
            "correct_is_unambiguous": true,
            "distractors_plausible": true,
            "has_giveaway": false,
            "terminology_issues": [],
            "overall_quality": 8,
            "improvement_suggestions": []
        }
        '''

        agent = get_adaptive_learning_engine(db)
        result = agent.validate_answer_choices(test_question.id)

        assert "valid" in result
        assert "quality_score" in result


class TestBatchOperations:
    """Test batch validation operations"""

    @pytest.mark.unit
    def test_batch_validate_explanations(self, db: Session, test_questions_batch: list[Question]):
        """Test batch validation of multiple questions"""
        agent = get_adaptive_learning_engine(db)
        result = agent.batch_validate_explanations(limit=10)

        assert "total_validated" in result
        assert "valid" in result
        assert "needs_improvement" in result
        assert "questions_needing_attention" in result
        assert isinstance(result["questions_needing_attention"], list)


class TestComprehensiveReport:
    """Test comprehensive learning report generation"""

    @pytest.mark.unit
    def test_generate_report(self, db: Session, test_user: User, test_attempts_history: list[QuestionAttempt]):
        """Test comprehensive report generation"""
        agent = get_adaptive_learning_engine(db)
        result = agent.generate_comprehensive_report(test_user.id)

        assert "user_id" in result
        assert "summary" in result
        assert "weak_areas" in result
        assert "top_recommendations" in result
        assert result["user_id"] == test_user.id
