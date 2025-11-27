from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.database import engine, Base
from app.routers import questions, analytics, users, reviews, chat, clerk_webhook, study_modes
from app.middleware.performance_monitor import PerformanceMonitorMiddleware, get_performance_stats, get_slow_requests

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ShelfSense API",
    description="Adaptive learning platform for USMLE Step 2 CK",
    version="1.0.0"
)

# Performance monitoring middleware (must be first)
app.add_middleware(PerformanceMonitorMiddleware)

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

# Include routers
app.include_router(users.router)
app.include_router(questions.router)
app.include_router(analytics.router)
app.include_router(reviews.router)  # Spaced repetition
app.include_router(chat.router)  # AI chat
app.include_router(clerk_webhook.router)  # Clerk webhooks
app.include_router(study_modes.router)  # Study modes


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


@app.get("/debug/db-stats")
def debug_db_stats():
    """Debug endpoint to check database status"""
    from app.database import SessionLocal, DATABASE_URL
    from app.models.models import Question
    import os

    db = SessionLocal()
    try:
        nbme_count = db.query(Question).filter(
            ~Question.source.like('%AI Generated%')
        ).count()

        ai_count = db.query(Question).filter(
            Question.source.like('%AI Generated%')
        ).count()

        total = db.query(Question).count()

        return {
            "database_url": DATABASE_URL,
            "openai_key_set": bool(os.getenv('OPENAI_API_KEY')),
            "openai_key_prefix": os.getenv('OPENAI_API_KEY', '')[:15] + "..." if os.getenv('OPENAI_API_KEY') else None,
            "nbme_questions": nbme_count,
            "ai_questions": ai_count,
            "total_questions": total
        }
    except Exception as e:
        return {
            "error": str(e),
            "database_url": DATABASE_URL,
            "openai_key_set": bool(os.getenv('OPENAI_API_KEY'))
        }
    finally:
        db.close()


@app.get("/debug/test-openai")
def test_openai_connection():
    """Test OpenAI API connection"""
    import os
    from openai import OpenAI

    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Try a simple API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=10
        )

        return {
            "status": "success",
            "api_key_prefix": os.getenv('OPENAI_API_KEY', '')[:15] + "...",
            "response": response.choices[0].message.content
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "api_key_set": bool(os.getenv('OPENAI_API_KEY')),
            "api_key_prefix": os.getenv('OPENAI_API_KEY', '')[:15] + "..." if os.getenv('OPENAI_API_KEY') else None
        }


@app.get("/debug/performance-stats")
def debug_performance_stats(endpoint: str = None):
    """
    Get performance statistics for API endpoints

    Tracks:
    - Request count
    - Average, min, max latency
    - 95th percentile latency
    - Slow requests (> 3s)
    """
    return get_performance_stats(endpoint)


@app.get("/debug/slow-requests")
def debug_slow_requests(threshold_seconds: float = 3.0):
    """
    Get list of slow requests above threshold

    Default threshold: 3 seconds (AI generation target)
    """
    slow_requests = get_slow_requests(threshold_seconds)
    return {
        "threshold_seconds": threshold_seconds,
        "count": len(slow_requests),
        "requests": slow_requests
    }
