import os
import asyncio
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.database import engine, Base
from app.routers import questions, analytics, users, reviews, chat, adaptive_engine, auth, profile, sessions, subscription, content_quality, study_plan, content, batch_generation, testing_qa, study_modes, flagged, admin, payments, webhooks, email
from app.middleware.rate_limiter import RateLimitMiddleware

# Load environment variables
load_dotenv()

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
            print("[Startup] Initializing massive question pool...")
            initialize_massive_pool()
            print("[Startup] Massive pool initialized successfully")
        except Exception as e:
            print(f"[Startup] Warning: Pool initialization failed: {e}")
            # Don't crash on pool init failure - app can still work
    else:
        print("[Startup] Pool warming disabled via ENABLE_POOL_WARMING=false")

    # Start email reminder scheduler if Resend API key is configured
    if os.getenv("RESEND_API_KEY"):
        try:
            from app.services.email import run_hourly_reminder_check
            asyncio.create_task(run_hourly_reminder_check())
            print("[Startup] Email reminder scheduler started")
        except Exception as e:
            print(f"[Startup] Warning: Email scheduler failed to start: {e}")
    else:
        print("[Startup] Email reminders disabled (no RESEND_API_KEY)")

    yield  # Application runs here

    # SHUTDOWN: Cleanup if needed
    print("[Shutdown] Cleaning up...")

app = FastAPI(
    title="ShelfSense API",
    description="Adaptive learning platform for USMLE Step 2 CK",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "https://shelfsense99.netlify.app",  # Production frontend
        "https://*.netlify.app",  # Any Netlify preview deploys
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(payments.router)  # Stripe payments
app.include_router(webhooks.router)  # Stripe webhooks
app.include_router(email.router)  # Email notifications


@app.get("/")
def root():
    return {
        "message": "ShelfSense API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/sentry-debug")
async def trigger_error():
    """Test endpoint to verify Sentry is capturing errors."""
    division_by_zero = 1 / 0
    return {"error": "This should not be reached"}
