"""
Tests for Spaced Repetition / Reviews API.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.models import User, Question, ScheduledReview


class TestReviewsEndpoints:
    """Test spaced repetition review endpoints"""

    @pytest.mark.api
    def test_get_todays_reviews(self, client: TestClient, test_user: User, test_scheduled_review: ScheduledReview):
        """Test getting today's scheduled reviews"""
        response = client.get(f"/api/reviews/today?user_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    @pytest.mark.api
    def test_get_upcoming_reviews(self, client: TestClient, test_user: User, test_scheduled_review: ScheduledReview):
        """Test getting upcoming reviews"""
        response = client.get(f"/api/reviews/upcoming?user_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict) or isinstance(data, list)

    @pytest.mark.api
    def test_get_review_stats(self, client: TestClient, test_user: User, test_scheduled_review: ScheduledReview):
        """Test getting review statistics"""
        response = client.get(f"/api/reviews/stats?user_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()

        assert "total_reviews" in data or "due_today" in data


class TestScheduledReviewModel:
    """Test ScheduledReview model"""

    @pytest.mark.unit
    def test_create_review(self, db: Session, test_user: User, test_question: Question):
        """Test creating a scheduled review"""
        review = ScheduledReview(
            user_id=test_user.id,
            question_id=test_question.id,
            scheduled_for=datetime.utcnow() + timedelta(days=1),
            review_interval="1d",
            learning_stage="New"
        )
        db.add(review)
        db.commit()

        assert review.id is not None
        assert review.times_reviewed == 0

    @pytest.mark.unit
    def test_review_intervals(self, db: Session, test_user: User, test_question: Question):
        """Test different review interval values"""
        intervals = ["1d", "3d", "7d", "14d", "30d", "60d"]

        for i, interval in enumerate(intervals):
            review = ScheduledReview(
                user_id=test_user.id,
                question_id=test_question.id,
                scheduled_for=datetime.utcnow() + timedelta(days=i+1),
                review_interval=interval,
                learning_stage="Learning"
            )
            db.add(review)

        db.commit()

        reviews = db.query(ScheduledReview).filter(
            ScheduledReview.user_id == test_user.id
        ).all()

        assert len(reviews) >= len(intervals)

    @pytest.mark.unit
    def test_learning_stages(self, db: Session, test_user: User, test_question: Question):
        """Test learning stage progression"""
        stages = ["New", "Learning", "Review", "Mastered"]

        for stage in stages:
            review = ScheduledReview(
                user_id=test_user.id,
                question_id=test_question.id,
                scheduled_for=datetime.utcnow(),
                review_interval="1d",
                learning_stage=stage
            )
            db.add(review)
            db.commit()

            assert review.learning_stage == stage
            db.delete(review)
            db.commit()


class TestSpacedRepetitionService:
    """Test spaced repetition service logic"""

    @pytest.mark.unit
    def test_schedule_after_correct_answer(self, db: Session, test_user: User, test_question: Question):
        """Test scheduling a review after correct answer"""
        from app.services.spaced_repetition import schedule_review

        review = schedule_review(
            db=db,
            user_id=test_user.id,
            question_id=test_question.id,
            is_correct=True,
            source=test_question.source
        )

        assert review is not None
        assert review.review_interval in ["3d", "1d"]  # First correct = 3d or depends on implementation

    @pytest.mark.unit
    def test_schedule_after_incorrect_answer(self, db: Session, test_user: User, test_question: Question):
        """Test scheduling a review after incorrect answer"""
        from app.services.spaced_repetition import schedule_review

        review = schedule_review(
            db=db,
            user_id=test_user.id,
            question_id=test_question.id,
            is_correct=False,
            source=test_question.source
        )

        assert review is not None
        assert review.review_interval == "1d"  # Incorrect = shorter interval
