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
    password_hash = Column(String, nullable=True)  # Optional for backwards compatibility
    email_verified = Column(Boolean, default=False)

    # Profile
    target_score = Column(Integer, nullable=True)  # Goal score (200-280)
    exam_date = Column(DateTime, nullable=True)
    avatar_url = Column(String, nullable=True)

    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="user")
    performance = relationship("UserPerformance", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)


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

    # Content Management fields
    content_status = Column(String, default="active", index=True)  # "draft", "pending_review", "active", "archived"
    source_type = Column(String, nullable=True, index=True)  # "nbme", "ai_generated", "community", "imported"
    specialty = Column(String, nullable=True, index=True)  # Normalized specialty: "internal_medicine", "surgery", etc.
    difficulty_level = Column(String, nullable=True, index=True)  # "easy", "medium", "hard"
    version = Column(Integer, default=1)  # Current version number
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # Who created this question
    last_edited_by = Column(String, ForeignKey("users.id"), nullable=True)
    last_edited_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Quality metrics (updated by Content Management Agent)
    quality_score = Column(Float, nullable=True, index=True)  # 0-100 composite score
    clinical_accuracy_verified = Column(Boolean, default=False)  # Expert-verified accuracy
    expert_reviewed = Column(Boolean, default=False, index=True)  # Has been reviewed by expert
    expert_reviewed_at = Column(DateTime, nullable=True)
    expert_reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="question")
    ratings = relationship("QuestionRating", back_populates="question")
    creator = relationship("User", foreign_keys=[created_by])
    editor = relationship("User", foreign_keys=[last_edited_by])
    expert_reviewer = relationship("User", foreign_keys=[expert_reviewer_id])


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


class LearningMetricsCache(Base):
    """
    Caches computed learning analytics to reduce computation on repeated requests.
    Updated periodically or when significant changes occur.
    """
    __tablename__ = "learning_metrics_cache"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Cached metrics
    velocity_score = Column(Float, nullable=True)  # 0-100 learning velocity score
    velocity_per_week = Column(Float, nullable=True)  # Weekly improvement rate
    calibration_score = Column(Float, nullable=True)  # 0-100 confidence calibration
    predicted_score = Column(Integer, nullable=True)  # Predicted Step 2 CK score
    score_confidence_interval = Column(Integer, nullable=True)  # +/- points

    # Weak areas (JSON list of sources with <60% accuracy)
    weak_areas = Column(JSON, nullable=True)
    # Strong areas (JSON list of sources with >70% accuracy)
    strong_areas = Column(JSON, nullable=True)

    # Time analysis cache
    optimal_time_range = Column(String, nullable=True)  # e.g., "60-120s"
    avg_time_correct = Column(Float, nullable=True)
    avg_time_incorrect = Column(Float, nullable=True)

    # Metadata
    attempts_at_calculation = Column(Integer, default=0)  # Number of attempts when calculated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    is_stale = Column(Boolean, default=False, index=True)  # Marked stale when new attempts added

    # Relationships
    user = relationship("User")


class ExplanationQualityLog(Base):
    """
    Logs explanation quality validation results for tracking and improvement.
    Used to identify patterns in explanation quality issues.
    """
    __tablename__ = "explanation_quality_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)

    # Validation results
    quality_score = Column(Float, nullable=True)  # 0-100 quality score
    is_valid = Column(Boolean, default=False, index=True)
    needs_regeneration = Column(Boolean, default=False, index=True)

    # Issues found (JSON array of issue strings)
    issues = Column(JSON, nullable=True)
    # Suggestions for improvement (JSON array)
    suggestions = Column(JSON, nullable=True)

    # Explanation type detected
    explanation_type = Column(String, nullable=True, index=True)  # TYPE_A through TYPE_F
    has_distractor_explanations = Column(Boolean, default=False)

    # Improvement tracking
    was_improved = Column(Boolean, default=False)
    improved_at = Column(DateTime, nullable=True)
    improved_by = Column(String, nullable=True)  # "auto" or user_id

    # Metadata
    validated_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    question = relationship("Question")


class UserSession(Base):
    """Tracks user login sessions for multi-device management"""
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_hash = Column(String, nullable=False)
    device_info = Column(String, nullable=True)  # Browser/device identifier
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_used = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")


class UserSettings(Base):
    """Stores user preferences and settings"""
    __tablename__ = "user_settings"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Study preferences
    show_timer = Column(Boolean, default=True)
    keyboard_shortcuts = Column(Boolean, default=True)
    questions_per_session = Column(Integer, default=20)
    auto_advance = Column(Boolean, default=False)  # Auto-advance after answering

    # Notifications
    email_notifications = Column(Boolean, default=True)
    daily_reminder = Column(Boolean, default=False)
    reminder_time = Column(String, nullable=True)  # e.g., "09:00"

    # Display
    theme = Column(String, default="dark")  # "dark", "light", "system"
    font_size = Column(String, default="medium")  # "small", "medium", "large"

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="settings")


class PasswordResetToken(Base):
    """Stores password reset tokens"""
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    # Relationships
    user = relationship("User")


# ============================================================================
# CONTENT MANAGEMENT AGENT MODELS
# ============================================================================

class ContentVersion(Base):
    """
    Tracks version history for question content changes.
    Enables rollback and audit trails for content modifications.
    """
    __tablename__ = "content_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)

    # Snapshot of question content at this version
    vignette_snapshot = Column(Text, nullable=False)
    choices_snapshot = Column(JSON, nullable=False)
    answer_key_snapshot = Column(String, nullable=False)
    explanation_snapshot = Column(JSON, nullable=True)

    # Change metadata
    change_type = Column(String, nullable=False, index=True)  # "created", "edited", "regenerated", "imported"
    change_reason = Column(Text, nullable=True)  # Why the change was made
    changed_by = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # User who made change (null for system)
    changed_by_system = Column(Boolean, default=False)  # True if system/AI made the change

    # Diff information (what changed from previous version)
    fields_changed = Column(JSON, nullable=True)  # ["vignette", "explanation", etc.]

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    question = relationship("Question")
    user = relationship("User")


class ReviewQueue(Base):
    """
    Manages the content review/approval workflow.
    Tracks questions pending expert review, assigned reviewers, and decisions.
    """
    __tablename__ = "review_queue"

    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)

    # Review status
    status = Column(String, nullable=False, default="pending", index=True)  # "pending", "in_review", "approved", "rejected", "needs_revision"
    priority = Column(Integer, default=5, index=True)  # 1 (highest) to 10 (lowest)

    # Assignment
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # Expert reviewer
    assigned_at = Column(DateTime, nullable=True)

    # Review decision
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decision = Column(String, nullable=True)  # "approve", "reject", "revise"
    decision_notes = Column(Text, nullable=True)  # Reviewer's comments

    # Quality scores from reviewer
    clinical_accuracy_score = Column(Integer, nullable=True)  # 1-5
    question_clarity_score = Column(Integer, nullable=True)  # 1-5
    distractor_quality_score = Column(Integer, nullable=True)  # 1-5
    explanation_quality_score = Column(Integer, nullable=True)  # 1-5

    # Revision tracking
    revision_requested = Column(Boolean, default=False)
    revision_notes = Column(Text, nullable=True)
    revision_count = Column(Integer, default=0)

    # Source of submission
    submission_source = Column(String, nullable=True, index=True)  # "ai_generated", "community", "import", "nbme"
    submitted_by = Column(String, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    question = relationship("Question")
    assignee = relationship("User", foreign_keys=[assigned_to])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    submitter = relationship("User", foreign_keys=[submitted_by])


class ContentAuditLog(Base):
    """
    Comprehensive audit trail for all content management operations.
    Records who did what, when, and why for compliance and debugging.
    """
    __tablename__ = "content_audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)

    # What happened
    action = Column(String, nullable=False, index=True)  # "create", "update", "delete", "import", "export", "approve", "reject", "archive", "restore", "bulk_update"
    entity_type = Column(String, nullable=False, index=True)  # "question", "review", "batch"
    entity_id = Column(String, nullable=True, index=True)  # ID of affected entity

    # Who did it
    performed_by = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    performed_by_system = Column(Boolean, default=False)  # True for automated actions

    # Details
    details = Column(JSON, nullable=True)  # Action-specific data (e.g., fields changed, filter criteria)
    affected_count = Column(Integer, nullable=True)  # Number of records affected (for bulk ops)

    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")


class CommunityContribution(Base):
    """
    Manages community-submitted questions.
    Tracks submissions from users before they enter the review pipeline.
    """
    __tablename__ = "community_contributions"

    id = Column(String, primary_key=True, default=generate_uuid)

    # Contributor info
    submitted_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Question content (before approval becomes a Question)
    vignette = Column(Text, nullable=False)
    choices = Column(JSON, nullable=False)
    answer_key = Column(String, nullable=False)
    explanation = Column(JSON, nullable=True)
    specialty = Column(String, nullable=True, index=True)

    # Source attribution
    source_reference = Column(Text, nullable=True)  # Where contributor found/based this
    is_original = Column(Boolean, default=True)  # True if original content

    # Status tracking
    status = Column(String, nullable=False, default="submitted", index=True)  # "submitted", "in_review", "approved", "rejected", "needs_revision"

    # Review linkage (once submitted to review queue)
    review_queue_id = Column(String, ForeignKey("review_queue.id"), nullable=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=True)  # Set when approved

    # Feedback to contributor
    reviewer_feedback = Column(Text, nullable=True)

    # Contributor reputation tracking
    contribution_quality_score = Column(Float, nullable=True)  # Calculated after review

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contributor = relationship("User")
    review = relationship("ReviewQueue")
    question = relationship("Question")


class ContentFreshnessScore(Base):
    """
    Tracks content freshness and relevance scoring.
    Used to prioritize content updates and identify stale material.
    """
    __tablename__ = "content_freshness_scores"

    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, unique=True, index=True)

    # Freshness metrics
    freshness_score = Column(Float, nullable=False, default=100.0, index=True)  # 0-100, decays over time
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_reviewed = Column(DateTime, nullable=True)  # Last expert review

    # Usage metrics (affect freshness)
    times_attempted = Column(Integer, default=0)
    times_reported = Column(Integer, default=0)  # User reports of issues
    average_rating = Column(Float, nullable=True)  # From QuestionRating
    rating_count = Column(Integer, default=0)

    # Performance metrics
    discrimination_index = Column(Float, nullable=True)  # How well it differentiates skill levels
    difficulty_index = Column(Float, nullable=True)  # Actual difficulty from attempts

    # Quality flags
    needs_review = Column(Boolean, default=False, index=True)  # Flagged for review
    review_reason = Column(String, nullable=True)  # "low_rating", "high_report", "outdated", "low_discrimination"

    # Decay parameters
    decay_rate = Column(Float, default=0.01)  # How fast freshness decays
    last_decay_calculation = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    question = relationship("Question")


class ExpertReviewer(Base):
    """
    Tracks expert reviewers and their qualifications.
    Used for assigning appropriate reviewers to questions.
    """
    __tablename__ = "expert_reviewers"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Qualifications
    specialties = Column(JSON, nullable=False)  # List of specialties they can review
    credentials = Column(String, nullable=True)  # MD, DO, etc.
    institution = Column(String, nullable=True)
    years_experience = Column(Integer, nullable=True)

    # Review capacity
    is_active = Column(Boolean, default=True, index=True)
    max_reviews_per_week = Column(Integer, default=20)
    current_week_reviews = Column(Integer, default=0)

    # Performance tracking
    total_reviews = Column(Integer, default=0)
    avg_review_time_minutes = Column(Float, nullable=True)
    agreement_rate = Column(Float, nullable=True)  # How often their decisions align with consensus

    # Availability
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


# ============================================================================
# MONETIZATION & SUBSCRIPTION MODELS
# ============================================================================

class Subscription(Base):
    """
    Stores user subscription information for monetization.
    Tracks tier, billing, and usage limits.
    """
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Subscription tier: "free", "student", "premium"
    tier = Column(String, nullable=False, default="free", index=True)

    # Billing information
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Null for free tier
    billing_cycle = Column(String, nullable=True)  # "monthly" or "yearly"

    # Stripe integration (for future payment processing)
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)

    # Trial tracking
    trial_started_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    has_used_trial = Column(Boolean, default=False)

    # Cancellation
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


class DailyUsage(Base):
    """
    Tracks daily usage for rate limiting and analytics.
    Reset daily for free tier limits.
    """
    __tablename__ = "daily_usage"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)

    # Usage counts
    questions_answered = Column(Integer, default=0)
    ai_chat_messages = Column(Integer, default=0)
    ai_questions_generated = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


# ============================================================================
# BATCH GENERATION JOB MODEL
# ============================================================================

class GenerationJob(Base):
    """
    Tracks batch question generation jobs.
    Allows users to queue multiple AI questions for async generation.
    """
    __tablename__ = "generation_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Job configuration
    specialty = Column(String, nullable=True, index=True)  # Target specialty (null = mixed)
    difficulty = Column(String, nullable=True)  # easy, medium, hard (null = adaptive)
    count = Column(Integer, nullable=False)  # Total questions to generate

    # Progress tracking
    completed = Column(Integer, default=0)  # Questions successfully generated
    failed = Column(Integer, default=0)  # Questions that failed to generate

    # Status: pending, running, completed, failed, cancelled
    status = Column(String, nullable=False, default="pending", index=True)

    # Results
    question_ids = Column(JSON, nullable=True)  # List of generated question IDs
    errors = Column(JSON, nullable=True)  # List of error messages

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
