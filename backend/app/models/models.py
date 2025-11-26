from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    full_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # Made optional for simple registration
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    target_score = Column(Integer, nullable=True)
    exam_date = Column(DateTime, nullable=True)

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="user")
    performance = relationship("UserPerformance", back_populates="user")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=generate_uuid)
    vignette = Column(Text, nullable=False)
    answer_key = Column(String, nullable=False)
    choices = Column(JSON, nullable=False)  # List of answer choices
    explanation = Column(JSON, nullable=True)  # Framework-based explanation (JSON) or legacy text
    source = Column(String, nullable=True, index=True)  # Indexed for filtering by specialty
    recency_tier = Column(Integer, nullable=True, index=True)  # Indexed for filtering by tier
    recency_weight = Column(Float, nullable=True, index=True)  # Indexed for sorting by recency
    extra_data = Column(JSON, nullable=True)  # Additional data
    rejected = Column(Boolean, default=False, index=True)  # User rejected this question

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="question")
    ratings = relationship("QuestionRating", back_populates="question")


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    time_spent_seconds = Column(Integer, nullable=True)
    hover_events = Column(JSON, nullable=True)  # Track which choices were hovered
    scroll_events = Column(JSON, nullable=True)  # Track scrolling behavior
    confidence_level = Column(Integer, nullable=True)  # 1-5 scale
    attempted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")


class UserPerformance(Base):
    __tablename__ = "user_performance"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_date = Column(DateTime, default=datetime.utcnow)
    questions_answered = Column(Integer, default=0)
    accuracy_overall = Column(Float, default=0.0)  # Percentage
    accuracy_weighted = Column(Float, default=0.0)  # Recency-weighted accuracy
    predicted_score = Column(Integer, nullable=True)  # Predicted Step 2 CK score
    weak_areas = Column(JSON, nullable=True)  # JSON object of weak sources
    strong_areas = Column(JSON, nullable=True)  # JSON object of strong sources
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="performance")


class ScheduledReview(Base):
    """Tracks spaced repetition schedule for questions"""
    __tablename__ = "scheduled_reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    scheduled_for = Column(DateTime, nullable=False, index=True)  # When to review
    review_interval = Column(String, nullable=False)  # "1d", "3d", "7d", "14d", "30d"
    times_reviewed = Column(Integer, default=0)  # How many times reviewed
    learning_stage = Column(String, default="New")  # "New", "Learning", "Review", "Mastered"
    source = Column(String, nullable=True)  # Topic/source for filtering
    created_at = Column(DateTime, default=datetime.utcnow)
    last_reviewed = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    question = relationship("Question")


class ChatMessage(Base):
    """Stores AI chat conversations about questions"""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)  # Message content
    role = Column(String, nullable=False)  # "user" or "assistant"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")
    question = relationship("Question")


class QuestionRating(Base):
    """Stores user ratings and feedback for questions"""
    __tablename__ = "question_ratings"

    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Boolean, nullable=False)  # TRUE = approved (✓), FALSE = rejected (✗)
    feedback_text = Column(Text, nullable=True)  # User's explanation
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")
    question = relationship("Question", back_populates="ratings")


class ErrorAnalysis(Base):
    """Stores AI-powered error analysis for incorrect question attempts"""
    __tablename__ = "error_analyses"

    id = Column(String, primary_key=True, default=generate_uuid)
    attempt_id = Column(String, ForeignKey("question_attempts.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)

    # Error categorization
    error_type = Column(String, nullable=False, index=True)  # knowledge_gap, premature_closure, etc.
    confidence = Column(Float, nullable=True)  # AI's confidence in categorization (0-1)
    explanation = Column(Text, nullable=False)  # Why this error occurred
    missed_detail = Column(Text, nullable=True)  # Specific fact/symptom student missed
    correct_reasoning = Column(Text, nullable=True)  # Correct clinical reasoning pathway
    coaching_question = Column(Text, nullable=True)  # Socratic question for reasoning coach

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    user_acknowledged = Column(Boolean, default=False)  # Did user view this analysis?

    # Relationships
    user = relationship("User")
    question = relationship("Question")
    attempt = relationship("QuestionAttempt")
