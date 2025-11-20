"""
Database Migration Script

Creates new tables for spaced repetition and AI chat features.
Safe to run multiple times (checks if tables exist first).
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, Base
from app.models.models import ScheduledReview, ChatMessage, User, Question, QuestionAttempt, UserPerformance

def migrate():
    """Create all new tables"""

    print("=" * 80)
    print("ShelfSense - Database Migration")
    print("=" * 80)
    print()

    print("Creating database tables...")
    print()

    # This will create any missing tables
    # Existing tables will not be modified
    Base.metadata.create_all(bind=engine)

    print("✓ Tables created/verified:")
    print("  - users")
    print("  - questions")
    print("  - question_attempts")
    print("  - user_performance")
    print("  - scheduled_reviews (NEW)")
    print("  - chat_messages (NEW)")
    print()

    print("=" * 80)
    print("Migration complete!")
    print("=" * 80)


if __name__ == "__main__":
    migrate()
