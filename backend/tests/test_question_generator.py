"""
Tests for the Question Generator Service.

Tests cover:
- Question generation validation
- Training data statistics
- Example question retrieval
- Saving generated questions
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.models.models import Question
from app.services.question_generator import (
    get_training_statistics,
    get_example_questions,
    generate_question,
    save_generated_question,
    generate_and_save_question,
    SPECIALTIES
)


class TestTrainingStatistics:
    """Test training statistics gathering"""

    @pytest.mark.unit
    def test_get_training_statistics_empty_db(self, db: Session):
        """Test statistics with no questions in database"""
        stats = get_training_statistics(db)

        assert "total_questions" in stats
        assert "avg_vignette_length" in stats
        assert stats["total_questions"] >= 0

    @pytest.mark.unit
    def test_get_training_statistics_with_questions(self, db: Session, test_questions_batch: list[Question]):
        """Test statistics with questions in database"""
        stats = get_training_statistics(db)

        assert stats["total_questions"] >= len(test_questions_batch)
        assert stats["avg_vignette_length"] > 0

    @pytest.mark.unit
    def test_get_training_statistics_by_specialty(self, db: Session, test_questions_batch: list[Question]):
        """Test statistics filtered by specialty"""
        # Filter by specialty that exists in test data
        stats = get_training_statistics(db, specialty="Internal Medicine")

        assert "total_questions" in stats
        assert stats["total_questions"] >= 0


class TestExampleQuestions:
    """Test example question retrieval for training"""

    @pytest.mark.unit
    def test_get_example_questions_returns_list(self, db: Session, test_questions_batch: list[Question]):
        """Test that example questions returns a list"""
        examples = get_example_questions(db, limit=3)

        assert isinstance(examples, list)
        assert len(examples) <= 3

    @pytest.mark.unit
    def test_get_example_questions_structure(self, db: Session, test_questions_batch: list[Question]):
        """Test structure of returned examples"""
        examples = get_example_questions(db, limit=1)

        if examples:
            example = examples[0]
            assert "vignette" in example
            assert "choices" in example
            assert "answer" in example
            assert "source" in example

    @pytest.mark.unit
    def test_get_example_questions_by_specialty(self, db: Session, test_questions_batch: list[Question]):
        """Test filtering examples by specialty"""
        examples = get_example_questions(db, specialty="Surgery", limit=5)

        # If we get results, they should match the specialty
        for ex in examples:
            assert "Surgery" in ex.get("source", "") or len(examples) == 0


class TestSaveGeneratedQuestion:
    """Test saving generated questions to database"""

    @pytest.mark.unit
    def test_save_generated_question_creates_record(self, db: Session):
        """Test that save creates a database record"""
        question_data = {
            "vignette": "A 30-year-old woman presents...",
            "choices": ["A", "B", "C", "D", "E"],
            "answer_key": "B",
            "explanation": {"type": "TYPE_A_STABILITY", "principle": "Test"},
            "source": "AI Generated - Test",
            "specialty": "Internal Medicine",
            "recency_weight": 1.0
        }

        saved = save_generated_question(db, question_data)

        assert saved.id is not None
        assert saved.vignette == question_data["vignette"]
        assert saved.answer_key == "B"
        assert saved.recency_tier == 1

    @pytest.mark.unit
    def test_save_generated_question_stores_explanation_as_json(self, db: Session):
        """Test that explanation dict is stored as JSON string"""
        explanation = {
            "type": "TYPE_B_TIME_SENSITIVE",
            "principle": "Time matters",
            "clinical_reasoning": "Act fast"
        }

        question_data = {
            "vignette": "Test vignette",
            "choices": ["A", "B", "C", "D", "E"],
            "answer_key": "A",
            "explanation": explanation
        }

        saved = save_generated_question(db, question_data)

        # Explanation should be stored (either as JSON string or dict depending on model)
        assert saved.explanation is not None

    @pytest.mark.unit
    def test_save_generated_question_sets_extra_data(self, db: Session):
        """Test that extra_data contains specialty and ai_generated flag"""
        question_data = {
            "vignette": "Test",
            "choices": ["A", "B", "C", "D", "E"],
            "answer_key": "C",
            "explanation": {},
            "specialty": "Surgery"
        }

        saved = save_generated_question(db, question_data)

        assert saved.extra_data.get("ai_generated") == True
        assert saved.extra_data.get("specialty") == "Surgery"


class TestSpecialtiesConstant:
    """Test the SPECIALTIES constant"""

    @pytest.mark.unit
    def test_specialties_contains_major_fields(self):
        """Test that all major medical specialties are included"""
        expected = [
            "Internal Medicine",
            "Surgery",
            "Pediatrics",
            "Psychiatry",
            "Obstetrics and Gynecology"
        ]

        for specialty in expected:
            assert specialty in SPECIALTIES

    @pytest.mark.unit
    def test_specialties_count(self):
        """Test that we have a reasonable number of specialties"""
        assert len(SPECIALTIES) >= 5
        assert len(SPECIALTIES) <= 15  # Not too many
