from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.database import engine, Base
from app.routers import questions, analytics, users, reviews, chat, adaptive_engine, auth, profile, sessions, subscription, content_quality, study_plan, content, batch_generation, testing_qa, study_modes, flagged
from app.middleware.rate_limiter import RateLimitMiddleware

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ShelfSense API",
    description="Adaptive learning platform for USMLE Step 2 CK",
    version="1.0.0"
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
