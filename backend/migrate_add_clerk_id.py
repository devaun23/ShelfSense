"""
Database migration: Add clerk_id column to users table

Run this script ONCE to add Clerk integration to existing databases:
    python migrate_add_clerk_id.py
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """Add clerk_id column to users table"""
    db = SessionLocal()

    try:
        # Check if column already exists
        result = db.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result]

        if 'clerk_id' in columns:
            print("✅ clerk_id column already exists. No migration needed.")
            return

        print("Adding clerk_id column to users table...")

        # Add clerk_id column
        db.execute(text("""
            ALTER TABLE users
            ADD COLUMN clerk_id TEXT UNIQUE
        """))

        # Create index for clerk_id
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_users_clerk_id
            ON users(clerk_id)
        """))

        db.commit()

        print("✅ Migration complete!")
        print("   - Added clerk_id column to users table")
        print("   - Created index on clerk_id")
        print("\nNext steps:")
        print("   1. Set up Clerk account at https://dashboard.clerk.com")
        print("   2. Add Clerk API keys to backend/.env")
        print("   3. Add Clerk publishable key to frontend/.env.local")
        print("   4. Configure Clerk webhook in dashboard")

    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    print("ShelfSense Database Migration: Add Clerk Integration")
    print("=" * 60)
    migrate()
