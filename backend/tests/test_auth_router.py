"""
Tests for authentication router endpoints.

Tests cover:
- User registration (with and without password)
- Login with credentials
- Token refresh
- Logout
- Password change
- Error handling and validation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.models import User, UserSession, UserSettings
from app.services.auth import hash_password, verify_password, create_access_token


class TestRegistration:
    """Tests for user registration endpoint"""

    def test_register_new_user_success(self, client, db):
        """Test successful registration of new user"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test User",
                "email": "newuser@test.com",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["full_name"] == "Test User"
        assert data["user"]["first_name"] == "Test"
        assert data["tokens"]["access_token"] is not None
        assert data["tokens"]["refresh_token"] is not None

    def test_register_creates_user_in_db(self, client, db):
        """Test that registration creates user in database"""
        client.post(
            "/api/auth/register",
            json={
                "full_name": "DB Test User",
                "email": "dbtest@test.com",
                "password": "SecurePass123"
            }
        )

        user = db.query(User).filter(User.email == "dbtest@test.com").first()
        assert user is not None
        assert user.password_hash is not None
        assert verify_password("SecurePass123", user.password_hash)

    def test_register_creates_default_settings(self, client, db):
        """Test that registration creates default user settings"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Settings User",
                "email": "settings@test.com",
                "password": "SecurePass123"
            }
        )

        data = response.json()
        user_id = data["user"]["user_id"]

        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        assert settings is not None
        assert settings.theme == "dark"

    def test_register_creates_session(self, client, db):
        """Test that registration creates a session"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Session User",
                "email": "session@test.com",
                "password": "SecurePass123"
            }
        )

        data = response.json()
        user_id = data["user"]["user_id"]

        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).all()
        assert len(sessions) == 1

    def test_register_weak_password_rejected(self, client):
        """Test that weak passwords are rejected"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Weak Pass User",
                "email": "weak@test.com",
                "password": "weak"  # Too short, no uppercase, no number
            }
        )

        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]

    def test_register_password_no_uppercase(self, client):
        """Test password without uppercase is rejected"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test",
                "email": "test@test.com",
                "password": "nouppercase123"
            }
        )

        assert response.status_code == 400
        assert "uppercase" in response.json()["detail"]

    def test_register_password_no_lowercase(self, client):
        """Test password without lowercase is rejected"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test",
                "email": "test@test.com",
                "password": "NOLOWERCASE123"
            }
        )

        assert response.status_code == 400
        assert "lowercase" in response.json()["detail"]

    def test_register_password_no_number(self, client):
        """Test password without number is rejected"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test",
                "email": "test@test.com",
                "password": "NoNumberHere"
            }
        )

        assert response.status_code == 400
        assert "number" in response.json()["detail"]

    def test_register_duplicate_email_fails(self, client, test_user):
        """Test that duplicate email registration fails"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Duplicate User",
                "email": test_user.email,
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_invalid_email_fails(self, client):
        """Test that invalid email is rejected"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test User",
                "email": "not-an-email",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 422  # Validation error


class TestLogin:
    """Tests for login endpoint"""

    def test_login_success(self, client, db):
        """Test successful login"""
        # First create a user
        user = User(
            id="login-test-user",
            full_name="Login Test",
            first_name="Login",
            email="logintest@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={
                "email": "logintest@test.com",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "logintest@test.com"

    def test_login_wrong_password(self, client, db):
        """Test login with wrong password fails"""
        user = User(
            id="wrong-pass-user",
            full_name="Wrong Pass",
            first_name="Wrong",
            email="wrongpass@test.com",
            password_hash=hash_password("CorrectPass123")
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongpass@test.com",
                "password": "WrongPassword123"
            }
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_email(self, client):
        """Test login with non-existent email fails"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "AnyPassword123"
            }
        )

        assert response.status_code == 401

    def test_login_no_password_set(self, client, db):
        """Test login fails when user has no password"""
        user = User(
            id="no-pass-user",
            full_name="No Password",
            first_name="No",
            email="nopass@test.com",
            password_hash=None  # No password set
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={
                "email": "nopass@test.com",
                "password": "AnyPassword123"
            }
        )

        assert response.status_code == 400
        assert "set a password" in response.json()["detail"]

    def test_login_updates_last_login(self, client, db):
        """Test that login updates last_login timestamp"""
        user = User(
            id="timestamp-user",
            full_name="Timestamp Test",
            first_name="Time",
            email="timestamp@test.com",
            password_hash=hash_password("SecurePass123"),
            last_login=datetime.utcnow() - timedelta(days=7)
        )
        db.add(user)
        db.commit()

        old_login = user.last_login

        client.post(
            "/api/auth/login",
            json={
                "email": "timestamp@test.com",
                "password": "SecurePass123"
            }
        )

        db.refresh(user)
        assert user.last_login > old_login

    def test_login_increments_failed_attempts(self, client, db):
        """Test that failed login increments attempt counter"""
        user = User(
            id="failed-attempt-user",
            full_name="Failed Attempt",
            first_name="Failed",
            email="failedattempt@test.com",
            password_hash=hash_password("SecurePass123"),
            failed_login_attempts=0
        )
        db.add(user)
        db.commit()

        # Fail a login
        client.post(
            "/api/auth/login",
            json={
                "email": "failedattempt@test.com",
                "password": "WrongPass123"
            }
        )

        db.refresh(user)
        assert user.failed_login_attempts == 1

    def test_login_resets_failed_attempts_on_success(self, client, db):
        """Test that successful login resets failed attempt counter"""
        user = User(
            id="reset-attempts-user",
            full_name="Reset Attempts",
            first_name="Reset",
            email="resetattempts@test.com",
            password_hash=hash_password("SecurePass123"),
            failed_login_attempts=5
        )
        db.add(user)
        db.commit()

        client.post(
            "/api/auth/login",
            json={
                "email": "resetattempts@test.com",
                "password": "SecurePass123"
            }
        )

        db.refresh(user)
        assert user.failed_login_attempts == 0

    def test_login_locked_account(self, client, db):
        """Test that locked account cannot login"""
        user = User(
            id="locked-user",
            full_name="Locked User",
            first_name="Locked",
            email="locked@test.com",
            password_hash=hash_password("SecurePass123"),
            locked_until=datetime.utcnow() + timedelta(minutes=30)
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={
                "email": "locked@test.com",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()


class TestTokenRefresh:
    """Tests for token refresh endpoint"""

    def test_refresh_token_success(self, client, db):
        """Test successful token refresh"""
        # Register to get tokens
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Refresh Test",
                "email": "refresh@test.com",
                "password": "SecurePass123"
            }
        )
        tokens = response.json()["tokens"]

        # Refresh tokens
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )

        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert new_tokens["access_token"] is not None
        assert new_tokens["refresh_token"] is not None
        # New tokens should be different
        assert new_tokens["access_token"] != tokens["access_token"]

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token fails"""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )

        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoint"""

    def test_logout_success(self, client, db):
        """Test successful logout"""
        # Register to get tokens
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Logout Test",
                "email": "logout@test.com",
                "password": "SecurePass123"
            }
        )
        tokens = response.json()["tokens"]
        user_id = response.json()["user"]["user_id"]

        # Verify session exists
        sessions_before = db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).count()
        assert sessions_before >= 1

        # Logout
        logout_response = client.post(
            "/api/auth/logout",
            json={"refresh_token": tokens["refresh_token"]}
        )

        assert logout_response.status_code == 200
        assert "Logged out" in logout_response.json()["message"]

    def test_logout_invalid_token_still_succeeds(self, client):
        """Test that logout with invalid token still returns success"""
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": "invalid-token"}
        )

        # Should still succeed (user is effectively logged out)
        assert response.status_code == 200


class TestPasswordChange:
    """Tests for password change endpoint"""

    def test_change_password_success(self, client, db):
        """Test successful password change"""
        # Register user
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Password Change",
                "email": "passchange@test.com",
                "password": "OldPassword123"
            }
        )
        tokens = response.json()["tokens"]

        # Change password
        change_response = client.put(
            "/api/auth/me/password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": "OldPassword123",
                "new_password": "NewPassword123"
            }
        )

        assert change_response.status_code == 200
        assert "changed successfully" in change_response.json()["message"]

        # Verify new password works
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "passchange@test.com",
                "password": "NewPassword123"
            }
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, client, db):
        """Test password change with wrong current password fails"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Wrong Current",
                "email": "wrongcurrent@test.com",
                "password": "CorrectPass123"
            }
        )
        tokens = response.json()["tokens"]

        change_response = client.put(
            "/api/auth/me/password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": "WrongPass123",
                "new_password": "NewPassword123"
            }
        )

        assert change_response.status_code == 400
        assert "incorrect" in change_response.json()["detail"]

    def test_change_password_weak_new_password(self, client, db):
        """Test password change with weak new password fails"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Weak New Pass",
                "email": "weaknew@test.com",
                "password": "StrongPass123"
            }
        )
        tokens = response.json()["tokens"]

        change_response = client.put(
            "/api/auth/me/password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": "StrongPass123",
                "new_password": "weak"
            }
        )

        assert change_response.status_code == 400


class TestSimpleRegistration:
    """Tests for backwards-compatible simple registration"""

    def test_simple_register_success(self, client, db):
        """Test simple registration without password"""
        response = client.post(
            "/api/auth/simple-register",
            json={
                "full_name": "Simple User",
                "email": "simple@test.com"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "simple@test.com"
        assert data["full_name"] == "Simple User"

    def test_simple_register_returns_existing_user(self, client, db):
        """Test that simple register returns existing user"""
        # First registration
        client.post(
            "/api/auth/simple-register",
            json={
                "full_name": "Existing Simple",
                "email": "existingsimple@test.com"
            }
        )

        # Second registration with same email
        response = client.post(
            "/api/auth/simple-register",
            json={
                "full_name": "Updated Name",
                "email": "existingsimple@test.com"
            }
        )

        assert response.status_code == 200
        # Name should be updated
        assert response.json()["full_name"] == "Updated Name"


class TestGetCurrentUser:
    """Tests for get current user endpoint"""

    def test_get_current_user_success(self, client, db):
        """Test getting current user with valid token"""
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Current User",
                "email": "current@test.com",
                "password": "SecurePass123"
            }
        )
        tokens = response.json()["tokens"]

        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert me_response.status_code == 200
        assert me_response.json()["email"] == "current@test.com"

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token fails"""
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token fails"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401
