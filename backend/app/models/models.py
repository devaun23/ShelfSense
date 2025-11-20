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
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
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
    explanation = Column(Text, nullable=True)
    source = Column(String, nullable=True, index=True)  # Indexed for filtering by specialty
    recency_tier = Column(Integer, nullable=True, index=True)  # Indexed for filtering by tier
    recency_weight = Column(Float, nullable=True, index=True)  # Indexed for sorting by recency
    extra_data = Column(JSON, nullable=True)  # Additional data

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="question")


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
