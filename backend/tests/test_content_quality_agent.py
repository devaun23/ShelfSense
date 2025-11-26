"""
Tests for ContentQualityAgent service.

Tests cover:
- Quality overview generation
- Question identification for attention
- Batch validation
- Quality score calculation
- Explanation validation
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.services.content_quality_agent import ContentQualityAgent
from app.models.models import Question, ExplanationQualityLog
from tests.mocks.openai_mocks import (
    MockOpenAIClient,
    MOCK_EXPLANATION,
    MOCK_QUALITY_SCORES,
    mock_openai_completion
)


class TestContentQualityAgentInit:
    """Tests for agent initialization"""

    def test_init_with_defaults(self, db):
        """Test agent initializes with default values"""
        agent = ContentQualityAgent(db)

        assert agent.db == db
        assert agent.model == "gpt-4o"
        assert agent.batch_size == 10

    def test_init_with_custom_model(self, db):
        """Test agent initializes with custom model"""
        agent = ContentQualityAgent(db, model="gpt-4o-mini")

        assert agent.model == "gpt-4o-mini"


class TestQualityOverview:
    """Tests for get_quality_overview method"""

    def test_empty_database_returns_zeros(self, db):
        """Test quality overview with no questions"""
        agent = ContentQualityAgent(db)
        overview = agent.get_quality_overview()

        assert overview["total_questions"] == 0
        assert overview["with_explanation"] == 0
        assert overview["without_explanation"] == 0
        assert overview["quality_score"] == 0

    def test_overview_with_questions(self, db, test_questions_batch):
        """Test quality overview with existing questions"""
        agent = ContentQualityAgent(db)
        overview = agent.get_quality_overview()

        assert overview["total_questions"] == len(test_questions_batch)
        assert "coverage_metrics" in overview
        assert "by_explanation_type" in overview
        assert "recent_validation" in overview

    def test_overview_counts_structured_explanations(self, db, sample_explanation):
        """Test that structured explanations are counted correctly"""
        # Create questions with different explanation types
        q1 = Question(
            id="quality-test-1",
            vignette="Test vignette 1",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=sample_explanation,  # Structured
            source="Test"
        )
        q2 = Question(
            id="quality-test-2",
            vignette="Test vignette 2",
            answer_key="B",
            choices=["A", "B", "C", "D", "E"],
            explanation="Plain text explanation",  # Not structured
            source="Test"
        )
        q3 = Question(
            id="quality-test-3",
            vignette="Test vignette 3",
            answer_key="C",
            choices=["A", "B", "C", "D", "E"],
            explanation=None,  # Missing
            source="Test"
        )
        db.add_all([q1, q2, q3])
        db.commit()

        agent = ContentQualityAgent(db)
        overview = agent.get_quality_overview()

        assert overview["total_questions"] == 3
        assert overview["structured_explanations"] == 1  # Only q1
        assert overview["without_explanation"] == 1  # Only q3

    def test_overview_counts_distractor_explanations(self, db, sample_explanation):
        """Test that distractor explanations are counted"""
        q_with_distractors = Question(
            id="distractor-test-1",
            vignette="Test",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=sample_explanation,  # Has distractors
            source="Test"
        )
        explanation_no_distractors = {
            "type": "TYPE_A_STABILITY",
            "principle": "Test principle",
            "clinical_reasoning": "Test reasoning",
            "correct_answer_explanation": "Test"
            # No distractor_explanations
        }
        q_without_distractors = Question(
            id="distractor-test-2",
            vignette="Test",
            answer_key="B",
            choices=["A", "B", "C", "D", "E"],
            explanation=explanation_no_distractors,
            source="Test"
        )
        db.add_all([q_with_distractors, q_without_distractors])
        db.commit()

        agent = ContentQualityAgent(db)
        overview = agent.get_quality_overview()

        assert overview["with_distractor_explanations"] == 1

    def test_overview_by_explanation_type(self, db, sample_explanation):
        """Test breakdown by explanation type"""
        type_a = sample_explanation.copy()
        type_a["type"] = "TYPE_A_STABILITY"

        type_b = sample_explanation.copy()
        type_b["type"] = "TYPE_B_PATHOPHYSIOLOGY"

        q1 = Question(
            id="type-test-1",
            vignette="Test",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=type_a,
            source="Test"
        )
        q2 = Question(
            id="type-test-2",
            vignette="Test",
            answer_key="B",
            choices=["A", "B", "C", "D", "E"],
            explanation=type_b,
            source="Test"
        )
        db.add_all([q1, q2])
        db.commit()

        agent = ContentQualityAgent(db)
        overview = agent.get_quality_overview()

        assert "TYPE_A_STABILITY" in overview["by_explanation_type"]
        assert "TYPE_B_PATHOPHYSIOLOGY" in overview["by_explanation_type"]


class TestQualityScoreCalculation:
    """Tests for _calculate_overall_quality_score method"""

    def test_zero_total_returns_zero(self, db):
        """Test that zero total questions returns zero score"""
        agent = ContentQualityAgent(db)
        score = agent._calculate_overall_quality_score(0, 0, 0)
        assert score == 0

    def test_perfect_score(self, db):
        """Test perfect score calculation"""
        agent = ContentQualityAgent(db)
        # All questions have structured + distractors
        score = agent._calculate_overall_quality_score(100, 100, 100)
        assert score == 100.0

    def test_partial_score(self, db):
        """Test partial score calculation"""
        agent = ContentQualityAgent(db)
        # 50% structured, 50% distractors
        score = agent._calculate_overall_quality_score(100, 50, 50)
        # (50/100)*40 + (50/100)*40 + (50/100)*20 = 20 + 20 + 10 = 50
        assert score == 50.0

    def test_score_weights_correctly(self, db):
        """Test that weights are applied correctly"""
        agent = ContentQualityAgent(db)
        # Only structured, no distractors
        score = agent._calculate_overall_quality_score(100, 100, 0)
        # 40 + 0 + 20 = 60
        assert score == 60.0


class TestIdentifyQuestionsNeedingAttention:
    """Tests for identify_questions_needing_attention method"""

    def test_empty_database(self, db):
        """Test with no questions"""
        agent = ContentQualityAgent(db)
        results = agent.identify_questions_needing_attention()

        assert results["summary"]["total_needing_attention"] == 0

    def test_identifies_missing_explanations(self, db):
        """Test identification of questions without explanations"""
        q = Question(
            id="missing-exp-1",
            vignette="Test vignette",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=None,
            source="Test"
        )
        db.add(q)
        db.commit()

        agent = ContentQualityAgent(db)
        results = agent.identify_questions_needing_attention()

        assert len(results["missing_explanation"]) == 1
        assert results["missing_explanation"][0]["id"] == "missing-exp-1"

    def test_identifies_text_only_explanations(self, db):
        """Test identification of text-only explanations"""
        q = Question(
            id="text-exp-1",
            vignette="Test vignette",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation="Plain text explanation without structure",
            source="Test"
        )
        db.add(q)
        db.commit()

        agent = ContentQualityAgent(db)
        results = agent.identify_questions_needing_attention()

        assert len(results["text_only_explanation"]) == 1

    def test_identifies_missing_distractors(self, db):
        """Test identification of questions without distractor explanations"""
        exp_no_distractors = {
            "type": "TYPE_A_STABILITY",
            "principle": "Test",
            "clinical_reasoning": "Test",
            "correct_answer_explanation": "Test"
        }
        q = Question(
            id="no-distractor-1",
            vignette="Test vignette",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=exp_no_distractors,
            source="Test"
        )
        db.add(q)
        db.commit()

        agent = ContentQualityAgent(db)
        results = agent.identify_questions_needing_attention()

        assert len(results["missing_distractors"]) == 1

    def test_respects_limit(self, db):
        """Test that limit parameter is respected"""
        # Create 10 questions without explanations
        for i in range(10):
            q = Question(
                id=f"limit-test-{i}",
                vignette=f"Test vignette {i}",
                answer_key="A",
                choices=["A", "B", "C", "D", "E"],
                explanation=None,
                source="Test"
            )
            db.add(q)
        db.commit()

        agent = ContentQualityAgent(db)
        results = agent.identify_questions_needing_attention(limit=5)

        assert len(results["missing_explanation"]) == 5

    def test_excludes_rejected_questions(self, db):
        """Test that rejected questions are excluded"""
        q_active = Question(
            id="active-q",
            vignette="Test",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=None,
            source="Test",
            rejected=False
        )
        q_rejected = Question(
            id="rejected-q",
            vignette="Test",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=None,
            source="Test",
            rejected=True
        )
        db.add_all([q_active, q_rejected])
        db.commit()

        agent = ContentQualityAgent(db)
        results = agent.identify_questions_needing_attention()

        # Only active question should be found
        assert len(results["missing_explanation"]) == 1
        assert results["missing_explanation"][0]["id"] == "active-q"


class TestBatchValidation:
    """Tests for batch_validate_questions method"""

    def test_validate_specific_questions(self, db, test_question):
        """Test validation of specific question IDs"""
        agent = ContentQualityAgent(db)
        results = agent.batch_validate_questions(
            question_ids=[test_question.id],
            log_results=False
        )

        assert results["validated"] == 1
        assert "details" in results

    def test_validate_auto_select(self, db, test_questions_batch):
        """Test automatic question selection for validation"""
        agent = ContentQualityAgent(db)
        results = agent.batch_validate_questions(limit=3, log_results=False)

        assert results["validated"] <= 3

    def test_validation_categorizes_results(self, db, sample_explanation):
        """Test that validation results are properly categorized"""
        # Create questions with different quality levels
        good_q = Question(
            id="good-q",
            vignette="A detailed vignette with proper clinical content",
            answer_key="A",
            choices=["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4", "E. Option 5"],
            explanation=sample_explanation,
            source="Test"
        )
        bad_q = Question(
            id="bad-q",
            vignette="Short",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation=None,
            source="Test"
        )
        db.add_all([good_q, bad_q])
        db.commit()

        agent = ContentQualityAgent(db)
        results = agent.batch_validate_questions(
            question_ids=["good-q", "bad-q"],
            log_results=False
        )

        assert results["validated"] == 2
        # At least one should need improvement (bad_q)
        assert results["needs_improvement"] + results["needs_regeneration"] >= 1


class TestLLMIntegration:
    """Tests for LLM integration with mocks"""

    @patch("app.utils.openai_client.get_openai_client")
    def test_call_llm_uses_correct_model(self, mock_client, db):
        """Test that _call_llm uses the configured model"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(MOCK_QUALITY_SCORES)
        mock_client.chat.completions.create.return_value = mock_response

        agent = ContentQualityAgent(db, model="gpt-4o-mini")
        result = agent._call_llm("System prompt", "User prompt")

        # Verify model was passed correctly
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"

    @patch("app.utils.openai_client.get_openai_client")
    def test_call_llm_handles_temperature(self, mock_client, db):
        """Test that temperature is passed correctly"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "{}"
        mock_client.chat.completions.create.return_value = mock_response

        agent = ContentQualityAgent(db)
        agent._call_llm("System", "User", temperature=0.5)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.5


class TestQualityLogging:
    """Tests for quality logging functionality"""

    def test_creates_quality_log(self, db, test_question):
        """Test that validation creates quality log entries"""
        agent = ContentQualityAgent(db)

        # Clear any existing logs
        db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.question_id == test_question.id
        ).delete()
        db.commit()

        # Validate with logging
        agent.batch_validate_questions(
            question_ids=[test_question.id],
            log_results=True
        )

        # Check log was created
        log = db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.question_id == test_question.id
        ).first()

        assert log is not None
        assert log.validated_at is not None


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_handles_empty_explanation_dict(self, db):
        """Test handling of empty explanation dict"""
        q = Question(
            id="empty-dict",
            vignette="Test",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation={},  # Empty dict
            source="Test"
        )
        db.add(q)
        db.commit()

        agent = ContentQualityAgent(db)
        # Should not raise
        overview = agent.get_quality_overview()
        assert "total_questions" in overview

    def test_handles_malformed_explanation(self, db):
        """Test handling of malformed explanation"""
        q = Question(
            id="malformed",
            vignette="Test",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            explanation={"random": "fields", "no": "structure"},
            source="Test"
        )
        db.add(q)
        db.commit()

        agent = ContentQualityAgent(db)
        results = agent.identify_questions_needing_attention()
        # Should be identified as missing distractors
        assert results["summary"]["missing_distractors"] >= 1

    def test_handles_large_batch(self, db):
        """Test handling of large question batches"""
        # Create 200 questions
        for i in range(200):
            q = Question(
                id=f"batch-{i}",
                vignette=f"Test vignette {i}",
                answer_key="A",
                choices=["A", "B", "C", "D", "E"],
                explanation=None,
                source="Test"
            )
            db.add(q)
        db.commit()

        agent = ContentQualityAgent(db)
        # Should handle limit correctly
        results = agent.identify_questions_needing_attention(limit=50)
        assert results["summary"]["missing_explanation"] <= 50
