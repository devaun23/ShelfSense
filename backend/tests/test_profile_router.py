"""
Tests for profile router endpoints.

Tests cover:
- Profile retrieval and update
- Target score management
- Exam date management
- User settings CRUD
- Data export (GDPR compliance)
- Account deletion
"""

import pytest
from datetime import datetime, timedelta

from app.models.models import User, UserSettings, QuestionAttempt, Question
from app.services.auth import hash_password, create_access_token


class TestGetProfile:
    """Tests for GET /api/profile/me endpoint"""

    def test_get_profile_success(self, client, db):
        """Test successful profile retrieval"""
        # Create user
        user = User(
            id="profile-user-1",
            full_name="Test User",
            first_name="Test",
            email="profile@test.com",
            password_hash=hash_password("SecurePass123"),
            target_score=250,
            exam_date=datetime.utcnow() + timedelta(days=90)
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.get(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@test.com"
        assert data["full_name"] == "Test User"
        assert data["first_name"] == "Test"
        assert data["target_score"] == 250

    def test_get_profile_no_auth(self, client):
        """Test profile retrieval without auth fails"""
        response = client.get("/api/profile/me")
        assert response.status_code == 401


class TestUpdateProfile:
    """Tests for PUT /api/profile/me endpoint"""

    def test_update_full_name_success(self, client, db):
        """Test successful full name update"""
        user = User(
            id="update-profile-1",
            full_name="Original Name",
            first_name="Original",
            email="updateprofile@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"full_name": "Updated Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["first_name"] == "Updated"

    def test_update_email_success(self, client, db):
        """Test successful email update"""
        user = User(
            id="update-email-1",
            full_name="Test User",
            first_name="Test",
            email="oldemail@test.com",
            password_hash=hash_password("SecurePass123"),
            email_verified=True
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "newemail@test.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@test.com"
        assert data["email_verified"] is False  # Reset on change

    def test_update_email_duplicate_fails(self, client, db):
        """Test that duplicate email update fails"""
        user1 = User(
            id="dup-email-1",
            full_name="User One",
            first_name="User",
            email="existing@test.com",
            password_hash=hash_password("SecurePass123")
        )
        user2 = User(
            id="dup-email-2",
            full_name="User Two",
            first_name="User",
            email="current@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add_all([user1, user2])
        db.commit()

        token = create_access_token(user2.id)

        response = client.put(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "existing@test.com"}
        )

        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]

    def test_update_name_too_short(self, client, db):
        """Test that short name is rejected"""
        user = User(
            id="short-name-1",
            full_name="Test User",
            first_name="Test",
            email="shortname@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"full_name": "A"}  # Too short
        )

        assert response.status_code == 422  # Validation error


class TestTargetScore:
    """Tests for PUT /api/profile/me/target endpoint"""

    def test_update_target_score_success(self, client, db):
        """Test successful target score update"""
        user = User(
            id="target-score-1",
            full_name="Test User",
            first_name="Test",
            email="targetscore@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me/target",
            headers={"Authorization": f"Bearer {token}"},
            json={"target_score": 260}
        )

        assert response.status_code == 200
        assert "260" in response.json()["message"]

        # Verify in database
        db.refresh(user)
        assert user.target_score == 260

    def test_target_score_too_low(self, client, db):
        """Test that score below 200 is rejected"""
        user = User(
            id="low-target-1",
            full_name="Test",
            first_name="Test",
            email="lowtarget@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me/target",
            headers={"Authorization": f"Bearer {token}"},
            json={"target_score": 150}
        )

        assert response.status_code == 422

    def test_target_score_too_high(self, client, db):
        """Test that score above 280 is rejected"""
        user = User(
            id="high-target-1",
            full_name="Test",
            first_name="Test",
            email="hightarget@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me/target",
            headers={"Authorization": f"Bearer {token}"},
            json={"target_score": 300}
        )

        assert response.status_code == 422


class TestExamDate:
    """Tests for exam date endpoints"""

    def test_update_exam_date_success(self, client, db):
        """Test successful exam date update"""
        user = User(
            id="exam-date-1",
            full_name="Test User",
            first_name="Test",
            email="examdate@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)
        future_date = (datetime.utcnow() + timedelta(days=120)).isoformat()

        response = client.put(
            "/api/profile/me/exam-date",
            headers={"Authorization": f"Bearer {token}"},
            json={"exam_date": future_date}
        )

        assert response.status_code == 200
        assert "updated" in response.json()["message"]

    def test_exam_date_in_past_fails(self, client, db):
        """Test that past exam date is rejected"""
        user = User(
            id="past-exam-1",
            full_name="Test User",
            first_name="Test",
            email="pastexam@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)
        past_date = (datetime.utcnow() - timedelta(days=30)).isoformat()

        response = client.put(
            "/api/profile/me/exam-date",
            headers={"Authorization": f"Bearer {token}"},
            json={"exam_date": past_date}
        )

        assert response.status_code == 400
        assert "future" in response.json()["detail"]

    def test_get_countdown(self, client, db):
        """Test exam countdown calculation"""
        exam_date = datetime.utcnow() + timedelta(days=90)
        user = User(
            id="countdown-1",
            full_name="Test User",
            first_name="Test",
            email="countdown@test.com",
            password_hash=hash_password("SecurePass123"),
            exam_date=exam_date,
            target_score=250
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.get(
            "/api/profile/me/countdown",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days_remaining"] >= 89  # Allow for test execution time
        assert data["target_score"] == 250

    def test_countdown_no_exam_date(self, client, db):
        """Test countdown when no exam date set"""
        user = User(
            id="no-exam-1",
            full_name="Test User",
            first_name="Test",
            email="noexam@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.get(
            "/api/profile/me/countdown",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exam_date"] is None
        assert data["days_remaining"] is None


class TestSettings:
    """Tests for settings endpoints"""

    def test_get_settings_creates_defaults(self, client, db):
        """Test that getting settings creates defaults if none exist"""
        user = User(
            id="settings-default-1",
            full_name="Test User",
            first_name="Test",
            email="settingsdefault@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.get(
            "/api/profile/me/settings",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"  # Default
        assert data["show_timer"] is True  # Default
        assert data["questions_per_session"] == 40  # Default

    def test_update_settings_partial(self, client, db):
        """Test partial settings update"""
        user = User(
            id="settings-partial-1",
            full_name="Test User",
            first_name="Test",
            email="settingspartial@test.com",
            password_hash=hash_password("SecurePass123")
        )
        settings = UserSettings(user_id=user.id, theme="dark", show_timer=True)
        db.add_all([user, settings])
        db.commit()

        token = create_access_token(user.id)

        # Only update theme
        response = client.put(
            "/api/profile/me/settings",
            headers={"Authorization": f"Bearer {token}"},
            json={"theme": "light"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["show_timer"] is True  # Unchanged

    def test_update_settings_invalid_theme(self, client, db):
        """Test that invalid theme is rejected"""
        user = User(
            id="settings-invalid-1",
            full_name="Test User",
            first_name="Test",
            email="settingsinvalid@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me/settings",
            headers={"Authorization": f"Bearer {token}"},
            json={"theme": "rainbow"}  # Invalid
        )

        assert response.status_code == 400
        assert "Invalid theme" in response.json()["detail"]

    def test_update_settings_invalid_font_size(self, client, db):
        """Test that invalid font size is rejected"""
        user = User(
            id="settings-font-1",
            full_name="Test User",
            first_name="Test",
            email="settingsfont@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me/settings",
            headers={"Authorization": f"Bearer {token}"},
            json={"font_size": "huge"}  # Invalid
        )

        assert response.status_code == 400
        assert "Invalid font size" in response.json()["detail"]

    def test_update_settings_invalid_reminder_time(self, client, db):
        """Test that invalid reminder time format is rejected"""
        user = User(
            id="settings-time-1",
            full_name="Test User",
            first_name="Test",
            email="settingstime@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me/settings",
            headers={"Authorization": f"Bearer {token}"},
            json={"reminder_time": "9am"}  # Invalid format
        )

        assert response.status_code == 400
        assert "Invalid time format" in response.json()["detail"]

    def test_update_settings_valid_reminder_time(self, client, db):
        """Test valid reminder time format"""
        user = User(
            id="settings-validtime-1",
            full_name="Test User",
            first_name="Test",
            email="settingsvalidtime@test.com",
            password_hash=hash_password("SecurePass123")
        )
        settings = UserSettings(user_id=user.id)
        db.add_all([user, settings])
        db.commit()

        token = create_access_token(user.id)

        response = client.put(
            "/api/profile/me/settings",
            headers={"Authorization": f"Bearer {token}"},
            json={"reminder_time": "09:30"}
        )

        assert response.status_code == 200
        assert response.json()["reminder_time"] == "09:30"


class TestDeleteAccount:
    """Tests for DELETE /api/profile/me endpoint"""

    def test_delete_account_success(self, client, db):
        """Test successful account deletion"""
        user = User(
            id="delete-user-1",
            full_name="Delete Me",
            first_name="Delete",
            email="deleteme@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.delete(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "deleted" in response.json()["message"]

        # Verify user is gone
        deleted_user = db.query(User).filter(User.id == "delete-user-1").first()
        assert deleted_user is None


class TestDataExport:
    """Tests for GET /api/profile/me/export endpoint (GDPR)"""

    def test_export_user_data(self, client, db):
        """Test data export returns all user data"""
        # Create user with settings
        user = User(
            id="export-user-1",
            full_name="Export User",
            first_name="Export",
            email="export@test.com",
            password_hash=hash_password("SecurePass123"),
            target_score=250,
            exam_date=datetime.utcnow() + timedelta(days=90)
        )
        settings = UserSettings(
            user_id=user.id,
            theme="light",
            questions_per_session=50
        )

        # Create a question and attempt
        question = Question(
            id="export-q-1",
            vignette="Test vignette",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            source="Test"
        )
        db.add_all([user, settings, question])
        db.commit()

        attempt = QuestionAttempt(
            id="export-attempt-1",
            user_id=user.id,
            question_id=question.id,
            user_answer="A",
            is_correct=True,
            time_spent_seconds=45
        )
        db.add(attempt)
        db.commit()

        token = create_access_token(user.id)

        response = client.get(
            "/api/profile/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check profile data
        assert data["profile"]["email"] == "export@test.com"
        assert data["profile"]["target_score"] == 250

        # Check settings data
        assert data["settings"]["theme"] == "light"
        assert data["settings"]["questions_per_session"] == 50

        # Check attempt data
        assert len(data["question_attempts"]) == 1
        assert data["question_attempts"][0]["user_answer"] == "A"

        # Check timestamp
        assert "exported_at" in data

    def test_export_empty_data(self, client, db):
        """Test export with minimal data"""
        user = User(
            id="export-empty-1",
            full_name="Empty User",
            first_name="Empty",
            email="emptyexport@test.com",
            password_hash=hash_password("SecurePass123")
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id)

        response = client.get(
            "/api/profile/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["profile"]["email"] == "emptyexport@test.com"
        assert data["settings"] is None
        assert data["question_attempts"] == []
        assert data["performance_records"] == []
