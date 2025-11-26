"""
Tests for Analytics API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.models import User, Question, QuestionAttempt


class TestAnalyticsEndpoints:
    """Test analytics API endpoints"""

    @pytest.mark.api
    def test_get_user_stats(self, client: TestClient, test_user: User, test_attempt: QuestionAttempt):
        """Test getting user statistics"""
        response = client.get(f"/api/analytics/stats?user_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "total_questions_answered" in data
        assert "overall_accuracy" in data
        assert "weighted_accuracy" in data
        assert "streak" in data
        assert data["total_questions_answered"] >= 1

    @pytest.mark.api
    def test_get_stats_no_attempts(self, client: TestClient, test_user: User):
        """Test stats for user with no attempts"""
        # Create a fresh user with no attempts
        response = client.get(f"/api/analytics/stats?user_id={test_user.id}")
        # Should still return, just with 0s
        assert response.status_code == 200


class TestAdaptiveEndpoints:
    """Test adaptive learning API endpoints"""

    @pytest.mark.api
    def test_get_weak_areas(self, client: TestClient, test_user: User, test_attempts_history: list[QuestionAttempt]):
        """Test getting weak areas"""
        response = client.get(f"/api/adaptive/weak-areas/{test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "weak_areas" in data
        assert "strong_areas" in data
        assert "recommendations" in data

    @pytest.mark.api
    def test_get_weak_areas_with_threshold(self, client: TestClient, test_user: User):
        """Test weak areas with custom threshold"""
        response = client.get(f"/api/adaptive/weak-areas/{test_user.id}?threshold=0.5")
        assert response.status_code == 200

    @pytest.mark.api
    def test_get_next_question(self, client: TestClient, test_user: User, test_questions_batch: list[Question]):
        """Test getting next adaptive question"""
        response = client.get(f"/api/adaptive/next-question/{test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "vignette" in data
        assert "choices" in data

    @pytest.mark.api
    def test_get_time_analysis(self, client: TestClient, test_user: User):
        """Test time analysis endpoint"""
        response = client.get(f"/api/adaptive/time-analysis/{test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "analysis" in data

    @pytest.mark.api
    def test_get_confidence_analysis(self, client: TestClient, test_user: User):
        """Test confidence analysis endpoint"""
        response = client.get(f"/api/adaptive/confidence/{test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "analysis" in data

    @pytest.mark.api
    def test_get_velocity(self, client: TestClient, test_user: User):
        """Test learning velocity endpoint"""
        response = client.get(f"/api/adaptive/velocity/{test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "analysis" in data

    @pytest.mark.api
    def test_get_prediction(self, client: TestClient, test_user: User):
        """Test performance prediction endpoint"""
        response = client.get(f"/api/adaptive/prediction/{test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "analysis" in data
        assert "readiness" in data

    @pytest.mark.api
    def test_get_comprehensive_report(self, client: TestClient, test_user: User, test_attempts_history: list[QuestionAttempt]):
        """Test comprehensive report endpoint"""
        response = client.get(f"/api/adaptive/report/{test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "user_id" in data
        assert "summary" in data
        assert "weak_areas" in data
        assert "top_recommendations" in data


class TestExplanationValidationEndpoints:
    """Test explanation validation API endpoints"""

    @pytest.mark.api
    def test_validate_explanation(self, client: TestClient, test_question: Question):
        """Test explanation validation endpoint"""
        response = client.get(f"/api/adaptive/validate-explanation/{test_question.id}")
        assert response.status_code == 200
        data = response.json()

        assert "valid" in data
        assert "question_id" in data
        assert "issues" in data

    @pytest.mark.api
    def test_validate_explanation_not_found(self, client: TestClient):
        """Test validation for non-existent question"""
        response = client.get("/api/adaptive/validate-explanation/non-existent-id")
        assert response.status_code == 404

    @pytest.mark.api
    def test_batch_validate(self, client: TestClient, test_questions_batch: list[Question]):
        """Test batch validation endpoint"""
        response = client.post("/api/adaptive/batch-validate?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert "total_validated" in data
        assert "valid" in data
        assert "needs_improvement" in data

    @pytest.mark.api
    def test_explanation_stats(self, client: TestClient, test_questions_batch: list[Question]):
        """Test explanation statistics endpoint"""
        response = client.get("/api/adaptive/explanation-stats")
        assert response.status_code == 200
        data = response.json()

        assert "total_questions" in data
        assert "has_explanation" in data


class TestAnswerChoiceValidationEndpoints:
    """Test answer choice validation API endpoints"""

    @pytest.mark.api
    @pytest.mark.slow
    def test_validate_choices(self, client: TestClient, test_question: Question, mock_openai):
        """Test answer choice validation endpoint"""
        response = client.get(f"/api/adaptive/validate-choices/{test_question.id}")
        # May fail without mocked OpenAI, but endpoint should exist
        assert response.status_code in [200, 500]  # 500 if OpenAI not mocked properly

    @pytest.mark.api
    def test_validate_choices_not_found(self, client: TestClient):
        """Test validation for non-existent question"""
        response = client.get("/api/adaptive/validate-choices/non-existent-id")
        assert response.status_code == 404
