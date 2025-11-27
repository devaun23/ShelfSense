"""
Production Test Fixtures for ShelfSense

Provides fixtures for testing against a live Railway deployment.

Environment variables required:
- RAILWAY_URL: Base URL of the Railway deployment
- TEST_USER_EMAIL: Email for test user account
- TEST_USER_PASSWORD: Password for test user account

Usage:
    RAILWAY_URL=https://shelfsense-backend.up.railway.app \
    TEST_USER_EMAIL=test@example.com \
    TEST_USER_PASSWORD=testpass123 \
    pytest tests/production/ -v
"""

import os
import pytest
import httpx
from typing import Optional


# Default Railway URL (can be overridden via environment)
DEFAULT_RAILWAY_URL = "https://shelfsense-backend.up.railway.app"


@pytest.fixture(scope="session")
def railway_url() -> str:
    """Get the Railway deployment URL."""
    return os.getenv("RAILWAY_URL", DEFAULT_RAILWAY_URL)


@pytest.fixture(scope="session")
def test_credentials() -> dict:
    """Get test user credentials."""
    email = os.getenv("TEST_USER_EMAIL")
    password = os.getenv("TEST_USER_PASSWORD")

    if not email or not password:
        pytest.skip(
            "TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables required"
        )

    return {"email": email, "password": password}


@pytest.fixture(scope="session")
def production_client(railway_url: str) -> httpx.Client:
    """
    HTTP client configured for production testing.

    Uses a 30-second timeout to accommodate potential cold starts
    and slow AI-generated responses.
    """
    return httpx.Client(
        base_url=railway_url,
        timeout=30.0,
        follow_redirects=True
    )


@pytest.fixture(scope="session")
def auth_token(production_client: httpx.Client, test_credentials: dict) -> str:
    """
    Get authentication token for test user.

    This fixture logs in the test user and returns the JWT token.
    """
    response = production_client.post(
        "/api/auth/login",
        json={
            "email": test_credentials["email"],
            "password": test_credentials["password"]
        }
    )

    if response.status_code != 200:
        pytest.skip(
            f"Could not authenticate test user: {response.status_code} - {response.text}"
        )

    data = response.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture
def authenticated_client(
    production_client: httpx.Client,
    auth_token: str
) -> httpx.Client:
    """
    Client with authentication header set.

    Use this fixture for endpoints that require authentication.
    """
    production_client.headers["Authorization"] = f"Bearer {auth_token}"
    return production_client


@pytest.fixture
def test_user_id(auth_token: str) -> str:
    """
    Get the test user's ID.

    For simplicity, we use a known test user ID.
    In production, this would be decoded from the JWT.
    """
    return os.getenv("TEST_USER_ID", "test-user-production")


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "production: marks tests as production tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests that may take >5 seconds"
    )
    config.addinivalue_line(
        "markers", "requires_openai: marks tests that require OpenAI API"
    )


# Skip all tests if RAILWAY_URL is not set and we're running production tests
def pytest_collection_modifyitems(config, items):
    """Skip production tests if environment is not configured."""
    if not os.getenv("RAILWAY_URL"):
        skip_production = pytest.mark.skip(
            reason="RAILWAY_URL environment variable not set"
        )
        for item in items:
            if "production" in str(item.fspath):
                item.add_marker(skip_production)
