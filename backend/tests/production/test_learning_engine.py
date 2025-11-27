"""
Production Tests for Learning Engine Endpoints

Tests all 12+ learning engine endpoints on Railway deployment:

Gap 1: Per-Specialty Difficulty (2 endpoints)
- GET /specialty-difficulty/{user_id}/{specialty}
- GET /specialty-difficulties/{user_id}

Gap 2: Personalized SM-2 Intervals (2 endpoints)
- GET /retention-metrics/{user_id}
- GET /calculate-interval/{user_id}

Gap 3: Interleaving Strategy (2 endpoints)
- GET /session-mix/{user_id}
- GET /interleaved-question/{user_id}

Gap 4: Ebbinghaus Forgetting Curve (3 endpoints)
- GET /concepts-needing-review/{user_id}
- POST /update-concept-retentions/{user_id}
- GET /calculate-retention

Gap 5: Confidence-Weighted Selection (1 endpoint)
- GET /confidence-calibration/{user_id}

Combined Endpoints (3 endpoints)
- GET /next-question/{user_id}
- POST /process-answer/{user_id}
- GET /dashboard/{user_id}

Run with:
    pytest tests/production/test_learning_engine.py -v
"""

import pytest
import httpx


class TestLearningEngineHealth:
    """Basic health check for learning engine endpoints."""

    @pytest.mark.production
    def test_learning_engine_root_accessible(self, production_client: httpx.Client):
        """Test that learning engine router is registered."""
        response = production_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestGap1SpecialtyDifficulty:
    """Gap 1: Per-Specialty Difficulty Tracking Tests"""

    @pytest.mark.production
    def test_get_specialty_difficulty(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /specialty-difficulty/{user_id}/{specialty}"""
        response = authenticated_client.get(
            f"/api/learning-engine/specialty-difficulty/{test_user_id}/Internal Medicine"
        )
        assert response.status_code == 200

        data = response.json()
        assert "difficulty_level" in data
        assert "accuracy" in data
        assert "trend" in data

    @pytest.mark.production
    def test_get_all_specialty_difficulties(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /specialty-difficulties/{user_id}"""
        response = authenticated_client.get(
            f"/api/learning-engine/specialty-difficulties/{test_user_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # May be empty for new users
        if data:
            assert "specialty" in data[0]
            assert "difficulty_level" in data[0]


class TestGap2PersonalizedSM2:
    """Gap 2: Personalized SM-2 Interval Tests"""

    @pytest.mark.production
    def test_get_retention_metrics(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /retention-metrics/{user_id}"""
        response = authenticated_client.get(
            f"/api/learning-engine/retention-metrics/{test_user_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert "easiness_factor" in data
        # Default easiness factor is 2.5
        assert data["easiness_factor"] >= 1.3  # Minimum per SM-2

    @pytest.mark.production
    def test_calculate_interval(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /calculate-interval/{user_id}"""
        response = authenticated_client.get(
            f"/api/learning-engine/calculate-interval/{test_user_id}",
            params={"current_interval_days": 1, "is_correct": True}
        )
        assert response.status_code == 200

        data = response.json()
        assert "next_interval_days" in data
        assert data["next_interval_days"] > 0


class TestGap3Interleaving:
    """Gap 3: Interleaving Strategy Tests"""

    @pytest.mark.production
    def test_get_session_mix(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /session-mix/{user_id}"""
        response = authenticated_client.get(
            f"/api/learning-engine/session-mix/{test_user_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert "new_ratio" in data or "new_question_ratio" in data
        assert "review_ratio" in data or "review_question_ratio" in data

    @pytest.mark.production
    def test_get_interleaved_question(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /interleaved-question/{user_id}"""
        response = authenticated_client.get(
            f"/api/learning-engine/interleaved-question/{test_user_id}"
        )
        # May return 200 (question) or 404 (no questions available)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should have question selection info
            assert "selection_type" in data or "question" in data or "question_id" in data


class TestGap4ForgettingCurve:
    """Gap 4: Ebbinghaus Forgetting Curve Tests"""

    @pytest.mark.production
    def test_get_concepts_needing_review(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /concepts-needing-review/{user_id}"""
        response = authenticated_client.get(
            f"/api/learning-engine/concepts-needing-review/{test_user_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # May be empty for new users

    @pytest.mark.production
    def test_update_concept_retentions(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test POST /update-concept-retentions/{user_id}"""
        response = authenticated_client.post(
            f"/api/learning-engine/update-concept-retentions/{test_user_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert "concepts_updated" in data or "message" in data

    @pytest.mark.production
    def test_calculate_retention(self, authenticated_client: httpx.Client):
        """Test GET /calculate-retention"""
        response = authenticated_client.get(
            "/api/learning-engine/calculate-retention",
            params={"stability": 2.0, "days_since_review": 1.0}
        )
        assert response.status_code == 200

        data = response.json()
        assert "retention" in data
        # Retention should be between 0 and 1
        assert 0 <= data["retention"] <= 1


class TestGap5ConfidenceCalibration:
    """Gap 5: Confidence-Weighted Selection Tests"""

    @pytest.mark.production
    def test_get_confidence_calibration(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /confidence-calibration/{user_id}"""
        response = authenticated_client.get(
            f"/api/learning-engine/confidence-calibration/{test_user_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert "calibration_score" in data or "calibration" in data


class TestCombinedEndpoints:
    """Combined/Advanced Learning Engine Endpoints"""

    @pytest.mark.production
    @pytest.mark.slow
    def test_get_next_question_advanced(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /next-question/{user_id} - uses all 5 algorithms"""
        response = authenticated_client.get(
            f"/api/learning-engine/next-question/{test_user_id}"
        )
        # May return 200 (question) or 404 (no questions)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should indicate which algorithms were used
            assert "algorithms_used" in data or "selection_info" in data or "question" in data

    @pytest.mark.production
    def test_process_answer(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test POST /process-answer/{user_id}"""
        # Note: This may fail if question_id doesn't exist
        response = authenticated_client.post(
            f"/api/learning-engine/process-answer/{test_user_id}",
            json={
                "question_id": "test-question-id-nonexistent",
                "is_correct": True,
                "confidence_level": 4
            }
        )
        # May return 200 (processed) or 404 (question not found)
        assert response.status_code in [200, 404, 422]

    @pytest.mark.production
    def test_get_learning_dashboard(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test GET /dashboard/{user_id} - comprehensive learning stats"""
        response = authenticated_client.get(
            f"/api/learning-engine/dashboard/{test_user_id}"
        )
        assert response.status_code == 200

        data = response.json()
        # Dashboard should include data from all 5 gaps
        expected_keys = ["specialty_difficulties", "recommendations", "session_mix"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"


class TestErrorHandling:
    """Test graceful error handling"""

    @pytest.mark.production
    def test_invalid_user_id_returns_graceful_error(
        self,
        authenticated_client: httpx.Client
    ):
        """Test that invalid user IDs don't cause 500 errors"""
        response = authenticated_client.get(
            "/api/learning-engine/dashboard/nonexistent-user-12345"
        )
        # Should return 200 (with empty data) or 404, not 500
        assert response.status_code in [200, 404]
        assert response.status_code != 500

    @pytest.mark.production
    def test_invalid_specialty_handled(
        self,
        authenticated_client: httpx.Client,
        test_user_id: str
    ):
        """Test that invalid specialty names are handled"""
        response = authenticated_client.get(
            f"/api/learning-engine/specialty-difficulty/{test_user_id}/InvalidSpecialty123"
        )
        # Should return 200 (with default values) or 404, not 500
        assert response.status_code in [200, 404]
        assert response.status_code != 500


class TestOpenAIResilience:
    """Test OpenAI service resilience"""

    @pytest.mark.production
    def test_openai_status_endpoint_exists(
        self,
        authenticated_client: httpx.Client
    ):
        """Test that OpenAI status endpoint is accessible to admins"""
        response = authenticated_client.get("/api/admin/openai-status")
        # Will return 200 for admins, 403 for non-admins
        assert response.status_code in [200, 403]

        if response.status_code == 200:
            data = response.json()
            assert "circuit_breaker" in data
            assert "state" in data["circuit_breaker"]

    @pytest.mark.production
    @pytest.mark.slow
    @pytest.mark.requires_openai
    def test_question_generation_returns_valid_structure(
        self,
        authenticated_client: httpx.Client
    ):
        """Test that question generation returns valid structure"""
        response = authenticated_client.post(
            "/api/questions/generate",
            json={"specialty": "Internal Medicine"}
        )
        # Should return 200 (success), 429 (rate limited), or 503 (circuit open)
        assert response.status_code in [200, 429, 503]

        if response.status_code == 200:
            data = response.json()
            assert "vignette" in data
            assert "choices" in data
            # Choices should have 5 options
            if isinstance(data["choices"], list):
                assert len(data["choices"]) == 5
