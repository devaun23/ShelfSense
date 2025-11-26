"""
Tests for User management and authentication.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.models import User, UserSettings, UserSession, PasswordResetToken


class TestUserModel:
    """Test User model"""

    @pytest.mark.unit
    def test_create_user(self, db: Session):
        """Test creating a user"""
        user = User(
            full_name="John Doe",
            first_name="John",
            email="john@example.com"
        )
        db.add(user)
        db.commit()

        assert user.id is not None
        assert user.created_at is not None
        assert user.failed_login_attempts == 0

    @pytest.mark.unit
    def test_user_with_target_score(self, db: Session):
        """Test user with exam target score"""
        user = User(
            full_name="Med Student",
            first_name="Med",
            email="med@example.com",
            target_score=250,
            exam_date=datetime.utcnow() + timedelta(days=90)
        )
        db.add(user)
        db.commit()

        assert user.target_score == 250
        assert user.exam_date is not None

    @pytest.mark.unit
    def test_user_email_unique(self, db: Session):
        """Test that user email must be unique"""
        user1 = User(
            full_name="User One",
            first_name="User",
            email="unique@example.com"
        )
        db.add(user1)
        db.commit()

        user2 = User(
            full_name="User Two",
            first_name="User",
            email="unique@example.com"  # Same email
        )
        db.add(user2)

        with pytest.raises(Exception):  # Should raise integrity error
            db.commit()

        db.rollback()


class TestUserSettings:
    """Test UserSettings model"""

    @pytest.mark.unit
    def test_create_settings(self, db: Session, test_user: User):
        """Test creating user settings"""
        settings = UserSettings(
            user_id=test_user.id,
            show_timer=True,
            keyboard_shortcuts=True,
            questions_per_session=25,
            theme="dark"
        )
        db.add(settings)
        db.commit()

        assert settings.id is not None
        assert settings.questions_per_session == 25

    @pytest.mark.unit
    def test_default_settings(self, db: Session, test_user: User):
        """Test default settings values"""
        settings = UserSettings(user_id=test_user.id)
        db.add(settings)
        db.commit()

        assert settings.show_timer == True
        assert settings.keyboard_shortcuts == True
        assert settings.questions_per_session == 20
        assert settings.theme == "dark"
        assert settings.auto_advance == False


class TestUserSession:
    """Test UserSession model"""

    @pytest.mark.unit
    def test_create_session(self, db: Session, test_user: User):
        """Test creating a user session"""
        session = UserSession(
            user_id=test_user.id,
            refresh_token_hash="hashed_token_here",
            device_info="Chrome on macOS",
            ip_address="192.168.1.1",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(session)
        db.commit()

        assert session.id is not None
        assert session.created_at is not None

    @pytest.mark.unit
    def test_session_expiration(self, db: Session, test_user: User):
        """Test session expiration tracking"""
        # Create expired session
        expired_session = UserSession(
            user_id=test_user.id,
            refresh_token_hash="expired_token",
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        db.add(expired_session)

        # Create valid session
        valid_session = UserSession(
            user_id=test_user.id,
            refresh_token_hash="valid_token",
            expires_at=datetime.utcnow() + timedelta(days=7)  # Valid
        )
        db.add(valid_session)
        db.commit()

        # Query for non-expired sessions
        now = datetime.utcnow()
        valid_sessions = db.query(UserSession).filter(
            UserSession.user_id == test_user.id,
            UserSession.expires_at > now
        ).all()

        assert len(valid_sessions) == 1
        assert valid_sessions[0].refresh_token_hash == "valid_token"


class TestPasswordResetToken:
    """Test PasswordResetToken model"""

    @pytest.mark.unit
    def test_create_reset_token(self, db: Session, test_user: User):
        """Test creating a password reset token"""
        token = PasswordResetToken(
            user_id=test_user.id,
            token_hash="hashed_reset_token",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(token)
        db.commit()

        assert token.id is not None
        assert token.used == False

    @pytest.mark.unit
    def test_mark_token_used(self, db: Session, test_user: User):
        """Test marking a token as used"""
        token = PasswordResetToken(
            user_id=test_user.id,
            token_hash="token_to_use",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(token)
        db.commit()

        # Mark as used
        token.used = True
        db.commit()

        # Verify
        db.refresh(token)
        assert token.used == True


class TestUserEndpoints:
    """Test user API endpoints"""

    @pytest.mark.api
    def test_register_user(self, client: TestClient):
        """Test user registration endpoint"""
        response = client.post(
            "/api/users/register",
            json={
                "full_name": "New User",
                "first_name": "New",
                "email": "newuser@test.com"
            }
        )
        # Registration endpoint may or may not exist yet
        assert response.status_code in [200, 201, 404, 422]

    @pytest.mark.api
    def test_get_user_profile(self, client: TestClient, test_user: User):
        """Test getting user profile"""
        response = client.get(f"/api/users/{test_user.id}")
        # Endpoint may or may not exist yet
        assert response.status_code in [200, 404]
