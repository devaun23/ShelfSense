from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.database import engine, Base
from app.routers import questions, analytics, users, reviews, chat

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

# Include routers
app.include_router(users.router)
app.include_router(questions.router)
app.include_router(analytics.router)
app.include_router(reviews.router)  # Spaced repetition
app.include_router(chat.router)  # AI chat


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
