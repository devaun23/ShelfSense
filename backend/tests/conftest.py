"""
Pytest configuration and fixtures for ShelfSense backend tests.

Provides:
- Test database setup/teardown
- FastAPI test client
- Mock user and question fixtures
- OpenAI mock for AI tests
"""

import pytest
import os
from typing import Generator, Dict, Any
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Set test environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_shelfsense.db"
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["ENABLE_POOL_WARMING"] = "false"

from app.main import app
from app.database import Base, get_db
from app.models.models import (
    User, Question, QuestionAttempt, UserPerformance,
    ScheduledReview, ChatMessage, QuestionRating, ErrorAnalysis,
    LearningMetricsCache, ExplanationQualityLog, UserSession, UserSettings
)


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_shelfsense.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency for tests"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database tables once per test session"""
    Base.metadata.create_all(bind=test_engine)
    yield
    # Cleanup after all tests
    Base.metadata.drop_all(bind=test_engine)
    # Remove test database file
    if os.path.exists("./test_shelfsense.db"):
        os.remove("./test_shelfsense.db")


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Provide a database session for each test, with rollback after"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Provide FastAPI test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Don't close - let the fixture handle it

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# User Fixtures
# =========================================================================

@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user"""
    user = User(
        id="test-user-123",
        full_name="Test User",
        first_name="Test",
        email="test@shelfsense.com",
        password_hash="hashed_password_here",
        target_score=250,
        exam_date=datetime.utcnow() + timedelta(days=90)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_with_settings(db: Session, test_user: User) -> User:
    """Create a test user with settings"""
    settings = UserSettings(
        user_id=test_user.id,
        show_timer=True,
        keyboard_shortcuts=True,
        questions_per_session=20,
        theme="dark"
    )
    db.add(settings)
    db.commit()
    return test_user


# =========================================================================
# Question Fixtures
# =========================================================================

@pytest.fixture
def sample_explanation() -> Dict[str, Any]:
    """Sample structured explanation following ShelfSense framework"""
    return {
        "type": "TYPE_A_STABILITY",
        "principle": "Acute cholecystitis with hemodynamic instability requires urgent surgical intervention.",
        "clinical_reasoning": "BP 82/48 (systolic <90) → septic shock from cholecystitis → source control required. Stable patients get antibiotics and elective surgery within 72 hours, but hypotension changes this to urgent.",
        "correct_answer_explanation": "Emergent cholecystectomy is indicated because the patient has signs of septic shock (hypotension, tachycardia) from an infected gallbladder. Source control takes priority over medical optimization.",
        "distractor_explanations": {
            "A": "IV antibiotics alone are insufficient when septic shock is present - source control is required.",
            "B": "ERCP is for choledocholithiasis, not primary cholecystitis management.",
            "C": "Percutaneous drainage is for patients too unstable for surgery, but this patient needs definitive source control.",
            "E": "Observation is inappropriate in septic shock - delay increases mortality."
        },
        "educational_objective": "Recognize that hemodynamic instability in cholecystitis mandates urgent surgical intervention.",
        "concept": "Acute Care Surgery"
    }


@pytest.fixture
def test_question(db: Session, sample_explanation: Dict) -> Question:
    """Create a test question with proper structure"""
    question = Question(
        id="test-question-123",
        vignette="A 45-year-old woman presents to the emergency department with 2 days of right upper quadrant pain, fever, and nausea. Temperature is 38.9°C, blood pressure is 82/48 mm Hg, and pulse is 118/min. Physical examination shows right upper quadrant tenderness with a positive Murphy sign. Laboratory studies show WBC 18,000/μL. Ultrasound shows gallbladder wall thickening and pericholecystic fluid. Which of the following is the most appropriate next step in management?",
        answer_key="D",
        choices=[
            "IV antibiotics and observation",
            "ERCP with sphincterotomy",
            "Percutaneous cholecystostomy",
            "Emergent cholecystectomy",
            "Repeat ultrasound in 24 hours"
        ],
        explanation=sample_explanation,
        source="Internal Medicine - Test",
        recency_tier=1,
        recency_weight=1.0
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@pytest.fixture
def test_questions_batch(db: Session, sample_explanation: Dict) -> list[Question]:
    """Create multiple test questions for batch testing"""
    questions = []
    specialties = ["Internal Medicine", "Surgery", "Pediatrics", "Psychiatry", "OBGYN"]

    for i, specialty in enumerate(specialties):
        q = Question(
            id=f"test-question-batch-{i}",
            vignette=f"Test vignette for {specialty} question {i}...",
            answer_key="A",
            choices=["Choice A", "Choice B", "Choice C", "Choice D", "Choice E"],
            explanation=sample_explanation if i % 2 == 0 else None,  # Some without explanation
            source=f"{specialty} - NBME",
            recency_tier=i % 6 + 1,
            recency_weight=1.0 - (i * 0.1)
        )
        questions.append(q)
        db.add(q)

    db.commit()
    for q in questions:
        db.refresh(q)
    return questions


# =========================================================================
# Attempt Fixtures
# =========================================================================

@pytest.fixture
def test_attempt(db: Session, test_user: User, test_question: Question) -> QuestionAttempt:
    """Create a test question attempt"""
    attempt = QuestionAttempt(
        id="test-attempt-123",
        user_id=test_user.id,
        question_id=test_question.id,
        user_answer="D",
        is_correct=True,
        time_spent_seconds=90,
        confidence_level=4,
        attempted_at=datetime.utcnow()
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@pytest.fixture
def test_attempts_history(db: Session, test_user: User, test_questions_batch: list[Question]) -> list[QuestionAttempt]:
    """Create multiple attempts to simulate user history"""
    attempts = []
    for i, question in enumerate(test_questions_batch):
        attempt = QuestionAttempt(
            id=f"test-attempt-history-{i}",
            user_id=test_user.id,
            question_id=question.id,
            user_answer="A" if i % 3 != 0 else "B",  # Some wrong
            is_correct=(i % 3 != 0),  # ~67% accuracy
            time_spent_seconds=60 + (i * 10),
            confidence_level=(i % 5) + 1,
            attempted_at=datetime.utcnow() - timedelta(days=i)
        )
        attempts.append(attempt)
        db.add(attempt)

    db.commit()
    for a in attempts:
        db.refresh(a)
    return attempts


# =========================================================================
# Review Fixtures
# =========================================================================

@pytest.fixture
def test_scheduled_review(db: Session, test_user: User, test_question: Question) -> ScheduledReview:
    """Create a scheduled review"""
    review = ScheduledReview(
        id="test-review-123",
        user_id=test_user.id,
        question_id=test_question.id,
        scheduled_for=datetime.utcnow(),
        review_interval="1d",
        times_reviewed=0,
        learning_stage="New",
        source=test_question.source
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


# =========================================================================
# Mock Fixtures
# =========================================================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls for testing without API costs"""
    import app.utils.openai_client as openai_module

    # Reset the cached client
    openai_module._client = None

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "mocked response"}'

    mock_instance = MagicMock()
    mock_instance.chat.completions.create.return_value = mock_response

    # Patch the _client directly to bypass the get_openai_client function
    with patch.object(openai_module, '_client', mock_instance):
        with patch.object(openai_module, 'get_openai_client', return_value=mock_instance):
            yield mock_instance

    # Reset after test to avoid affecting other tests
    openai_module._client = None


@pytest.fixture
def mock_openai_explanation(sample_explanation: Dict):
    """Mock OpenAI to return a proper explanation"""
    import json
    import app.utils.openai_client as openai_module

    # Reset the cached client
    openai_module._client = None

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(sample_explanation)

    mock_instance = MagicMock()
    mock_instance.chat.completions.create.return_value = mock_response

    # Patch the _client directly to bypass the get_openai_client function
    with patch.object(openai_module, '_client', mock_instance):
        with patch.object(openai_module, 'get_openai_client', return_value=mock_instance):
            yield mock_instance

    # Reset after test
    openai_module._client = None


# =========================================================================
# Helper Functions
# =========================================================================

def create_user_with_performance(db: Session, accuracy: float = 0.7, num_attempts: int = 50) -> tuple[User, list[QuestionAttempt]]:
    """Helper to create a user with specific performance characteristics"""
    import uuid

    user = User(
        id=str(uuid.uuid4()),
        full_name="Performance Test User",
        first_name="Perf",
        email=f"perf_{uuid.uuid4().hex[:8]}@test.com"
    )
    db.add(user)

    attempts = []
    for i in range(num_attempts):
        # Create question
        q = Question(
            id=str(uuid.uuid4()),
            vignette=f"Test question {i}",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            source="Test Source",
            recency_weight=0.8
        )
        db.add(q)

        # Create attempt based on accuracy
        is_correct = (i / num_attempts) < accuracy
        attempt = QuestionAttempt(
            id=str(uuid.uuid4()),
            user_id=user.id,
            question_id=q.id,
            user_answer="A" if is_correct else "B",
            is_correct=is_correct,
            time_spent_seconds=90,
            confidence_level=3,
            attempted_at=datetime.utcnow() - timedelta(days=num_attempts - i)
        )
        attempts.append(attempt)
        db.add(attempt)

    db.commit()
    db.refresh(user)
    return user, attempts
