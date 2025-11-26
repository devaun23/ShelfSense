"""
Migration script to add error_analyses table
"""

import sqlite3
import os

# Path to database
DB_PATH = "shelfsense.db"

def migrate():
    """Add error_analyses table to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create error_analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_analyses (
                id TEXT PRIMARY KEY,
                attempt_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                error_type TEXT NOT NULL,
                confidence REAL,
                explanation TEXT NOT NULL,
                missed_detail TEXT,
                correct_reasoning TEXT,
                coaching_question TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY (attempt_id) REFERENCES question_attempts (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_analyses_attempt ON error_analyses(attempt_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_analyses_user ON error_analyses(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_analyses_question ON error_analyses(question_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_analyses_error_type ON error_analyses(error_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_analyses_created_at ON error_analyses(created_at)")

        conn.commit()
        print("✅ Successfully created error_analyses table and indexes")

    except sqlite3.Error as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        exit(1)

    print(f"Running migration on {DB_PATH}...")
    migrate()
    print("Migration complete!")
