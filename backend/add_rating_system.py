"""
Database migration to add question rating system
"""
import sqlite3
from datetime import datetime

def migrate_database():
    conn = sqlite3.connect('shelfsense.db')
    cursor = conn.cursor()

    # Create question_ratings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_ratings (
            id TEXT PRIMARY KEY,
            question_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            rating BOOLEAN NOT NULL,
            feedback_text TEXT,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')

    # Add rejected column to questions table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE questions ADD COLUMN rejected BOOLEAN DEFAULT 0')
        print("✅ Added 'rejected' column to questions table")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("ℹ️  'rejected' column already exists")
        else:
            raise

    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_question ON question_ratings(question_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_user ON question_ratings(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_rejected ON questions(rejected)')

    conn.commit()
    conn.close()

    print("✅ Database migration completed successfully")
    print("✅ Created 'question_ratings' table")
    print("✅ Created indexes for performance")

if __name__ == "__main__":
    migrate_database()
