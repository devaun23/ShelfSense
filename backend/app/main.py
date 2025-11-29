# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
import logging
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies.auth import get_admin_user
from app.database import engine, Base
from app.routers import questions, analytics, users, reviews, chat, adaptive_engine, auth, profile, sessions, subscription, content_quality, study_plan, content, batch_generation, testing_qa, study_modes, flagged, admin, admin_analytics, payments, webhooks, email, learning_engine, score_predictor, gamification, notifications, self_assessment, curriculum
from app.middleware.rate_limiter import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Sentry for error monitoring
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,  # 10% of sampled transactions for profiling
        environment=os.getenv("ENVIRONMENT", "development"),
        enable_tracing=True,
    )

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs on startup and shutdown."""
    # STARTUP: Initialize the massive question pool
    if os.getenv("ENABLE_POOL_WARMING", "true").lower() == "true":
        try:
            from app.services.massive_pool import initialize_massive_pool
            logger.info("Initializing massive question pool...")
            initialize_massive_pool()
            logger.info("Massive pool initialized successfully")
        except Exception as e:
            logger.warning("Pool initialization failed: %s", e)
            # Don't crash on pool init failure - app can still work
    else:
        logger.info("Pool warming disabled via ENABLE_POOL_WARMING=false")

    # Start email schedulers if Resend API key is configured
    if os.getenv("RESEND_API_KEY"):
        try:
            from app.services.email import run_hourly_reminder_check, run_weekly_digest_scheduler
            asyncio.create_task(run_hourly_reminder_check())
            asyncio.create_task(run_weekly_digest_scheduler())
            logger.info("Email reminder and weekly digest schedulers started")
        except Exception as e:
            logger.warning("Email schedulers failed to start: %s", e)
    else:
        logger.info("Email features disabled (no RESEND_API_KEY)")

    # Start push notification reminder scheduler if VAPID keys are configured
    if os.getenv("VAPID_PRIVATE_KEY") and os.getenv("VAPID_PUBLIC_KEY"):
        try:
            from app.services.notification_scheduler import run_hourly_push_reminder_check
            asyncio.create_task(run_hourly_push_reminder_check())
            logger.info("Push notification scheduler started")
        except Exception as e:
            logger.warning("Push notification scheduler failed to start: %s", e)
    else:
        logger.info("Push notifications disabled (no VAPID keys)")

    # Warm Redis question cache if enabled
    if os.getenv("ENABLE_CACHE_WARMING", "true").lower() == "true":
        try:
            from app.services.cache_service import question_cache
            if question_cache.is_connected:
                from app.database import SessionLocal
                from app.services.question_generator import generate_question

                logger.info("Warming question cache...")
                db = SessionLocal()
                specialties_to_warm = ["Internal Medicine", "Surgery", "Pediatrics"]
                warmed_count = 0

                for specialty in specialties_to_warm:
                    for _ in range(2):  # 2 questions per specialty
                        try:
                            q = generate_question(db, specialty, use_cache=False)
                            if question_cache.cache_question(q, specialty):
                                warmed_count += 1
                        except Exception as e:
                            logger.warning("Cache warm failed for %s: %s", specialty, e)
                            continue

                db.close()
                logger.info("Cache warmed with %d questions", warmed_count)
            else:
                logger.info("Redis not connected - cache warming skipped")
        except Exception as e:
            logger.warning("Cache warming failed: %s", e)
    else:
        logger.info("Cache warming disabled via ENABLE_CACHE_WARMING=false")

    yield  # Application runs here

    # SHUTDOWN: Cleanup if needed
    logger.info("Shutting down...")

# OpenAPI tag metadata for organized documentation
tags_metadata = [
    {
        "name": "auth",
        "description": "User registration, login, logout, and token management.",
    },
    {
        "name": "questions",
        "description": "Question bank operations including adaptive selection, answer submission, and AI-generated questions.",
    },
    {
        "name": "analytics",
        "description": "User performance analytics, trends, peer comparison, and predicted scores.",
    },
    {
        "name": "study-modes",
        "description": "Study session management with modes: Practice, Timed, Tutor, Challenge, Review.",
    },
    {
        "name": "chat",
        "description": "AI-powered tutoring chat using clinical reasoning frameworks.",
    },
    {
        "name": "reviews",
        "description": "Spaced repetition system for scheduled question reviews.",
    },
    {
        "name": "learning-engine",
        "description": "Advanced learning algorithms: per-specialty difficulty, retention curves, interleaving.",
    },
    {
        "name": "profile",
        "description": "User profile and settings management.",
    },
    {
        "name": "subscription",
        "description": "Subscription tier management and usage tracking.",
    },
    {
        "name": "payments",
        "description": "Stripe payment integration for subscriptions.",
    },
    {
        "name": "admin",
        "description": "Admin dashboard operations. **Requires admin access.**",
    },
    {
        "name": "content",
        "description": "Content management for questions and explanations.",
    },
    {
        "name": "batch",
        "description": "Batch question generation jobs.",
    },
]

app = FastAPI(
    title="ShelfPass API",
    description="""
## ShelfPass USMLE Step 2 CK Adaptive Learning Platform

ShelfPass is an AI-powered adaptive learning platform for medical students preparing for USMLE Step 2 CK.

### Features
- **Adaptive Question Selection** - Questions tailored to your weak areas
- **AI Tutoring Chat** - Socratic method coaching with clinical reasoning frameworks
- **Performance Analytics** - Predicted scores, trends, and peer comparison
- **Spaced Repetition** - Optimal review scheduling for retention
- **Multiple Study Modes** - Practice, Timed, Tutor, Challenge, Review

### Rate Limits
| Tier | AI Questions/Day | Chat Messages/Day | Questions/Day |
|------|------------------|-------------------|---------------|
| Free | 10 | 50 | 100 |
| Student | 50 | 200 | Unlimited |
| Premium | Unlimited | Unlimited | Unlimited |
    """,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# CORS middleware for Next.js frontend
# SECURITY: Explicitly list allowed origins - no wildcards
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Next.js dev server
    "http://localhost:3001",  # Next.js dev server (alternate port)
    "https://shelfpass.com",  # Production custom domain
    "https://www.shelfpass.com",  # www subdomain
    "https://shelfsense99.netlify.app",  # Netlify production
]

# Allow additional origins from environment (for preview deploys)
extra_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
if extra_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth.router)  # Authentication
app.include_router(profile.router)  # User profile & settings
app.include_router(sessions.router)  # Session management
app.include_router(users.router)  # Legacy user endpoints
app.include_router(questions.router)
app.include_router(analytics.router)
app.include_router(reviews.router)  # Spaced repetition
app.include_router(chat.router)  # AI chat
app.include_router(adaptive_engine.router)  # Adaptive learning engine
app.include_router(subscription.router)  # Subscription & monetization
app.include_router(content_quality.router)  # Content quality management
app.include_router(study_plan.router)  # Personalized study plans
app.include_router(content.router)  # Content Management Agent
app.include_router(batch_generation.router)  # Batch question generation
app.include_router(testing_qa.router)  # Testing/QA Agent
app.include_router(study_modes.router)  # Study Modes (Timed, Tutor, Challenge)
app.include_router(flagged.router)  # Question flagging/marking system
app.include_router(admin.router)  # Admin dashboard
app.include_router(admin_analytics.router)  # Admin usage analytics
app.include_router(payments.router)  # Stripe payments
app.include_router(webhooks.router)  # Stripe webhooks
app.include_router(email.router)  # Email notifications
app.include_router(learning_engine.router)  # Advanced learning engine (Gaps 1-5)
app.include_router(score_predictor.router)  # NBME-calibrated score predictor
app.include_router(gamification.router)  # Streaks, badges, achievements
app.include_router(notifications.router)  # Push notifications
app.include_router(self_assessment.router)  # NBME Self-Assessment Simulator
app.include_router(curriculum.router)  # StudySync AI - Curriculum mapping


@app.get("/")
def root():
    return {
        "message": "ShelfPass API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/sentry-debug")
async def trigger_error(admin=Depends(get_admin_user)):
    """
    Test endpoint to verify Sentry is capturing errors. ADMIN ONLY.
    Disabled in production to prevent accidental crashes.
    """
    # SECURITY: Disable in production environment
    if os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("ENVIRONMENT") == "production":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="Sentry debug endpoint is disabled in production"
        )

    logger.warning(f"Sentry debug endpoint triggered by admin user_id={admin.id}")
    division_by_zero = 1 / 0
    return {"error": "This should not be reached"}
