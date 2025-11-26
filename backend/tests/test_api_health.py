"""
Tests for API health and basic endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test basic health and status endpoints"""

    @pytest.mark.unit
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "ShelfSense API"
        assert "version" in data

    @pytest.mark.unit
    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.unit
    def test_docs_available(self, client: TestClient):
        """Test OpenAPI docs are available"""
        response = client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_openapi_json(self, client: TestClient):
        """Test OpenAPI schema is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "info" in data
