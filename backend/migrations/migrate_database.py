"""
Database Migration Script for ShelfSense

This script:
1. Adds missing columns to existing tables
2. Creates missing indexes for performance
3. Adds composite indexes for common query patterns

Run with: python -m migrations.migrate_database
"""

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'shelfsense.db')


def get_connection():
    """Get database connection."""
    return sqlite3.connect(DATABASE_PATH)


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def index_exists(cursor, index_name):
    """Check if an index exists."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None


def add_column_if_missing(cursor, table, column, column_def):
    """Add a column if it doesn't exist."""
    if not column_exists(cursor, table, column):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
            print(f"  ✓ Added column {table}.{column}")
            return True
        except sqlite3.OperationalError as e:
            print(f"  ✗ Failed to add {table}.{column}: {e}")
            return False
    return False


def create_index_if_missing(cursor, index_name, table, columns, unique=False):
    """Create an index if it doesn't exist."""
    if not index_exists(cursor, index_name):
        try:
            unique_str = "UNIQUE " if unique else ""
            cols = columns if isinstance(columns, str) else ", ".join(columns)
            cursor.execute(f"CREATE {unique_str}INDEX {index_name} ON {table} ({cols})")
            print(f"  ✓ Created index {index_name}")
            return True
        except sqlite3.OperationalError as e:
            print(f"  ✗ Failed to create index {index_name}: {e}")
            return False
    return False


def migrate_users_table(cursor):
    """Add missing columns to users table."""
    print("\n[Users Table]")

    # Security columns
    add_column_if_missing(cursor, "users", "email_verified", "BOOLEAN DEFAULT 0")
    add_column_if_missing(cursor, "users", "failed_login_attempts", "INTEGER DEFAULT 0")
    add_column_if_missing(cursor, "users", "locked_until", "DATETIME")

    # Profile columns
    add_column_if_missing(cursor, "users", "avatar_url", "VARCHAR")
    add_column_if_missing(cursor, "users", "updated_at", "DATETIME")


def migrate_questions_table(cursor):
    """Add missing columns to questions table."""
    print("\n[Questions Table]")

    # Content management fields
    add_column_if_missing(cursor, "questions", "content_status", "VARCHAR DEFAULT 'active'")
    add_column_if_missing(cursor, "questions", "source_type", "VARCHAR")
    add_column_if_missing(cursor, "questions", "specialty", "VARCHAR")
    add_column_if_missing(cursor, "questions", "difficulty_level", "VARCHAR")
    add_column_if_missing(cursor, "questions", "version", "INTEGER DEFAULT 1")
    add_column_if_missing(cursor, "questions", "created_by", "VARCHAR")
    add_column_if_missing(cursor, "questions", "last_edited_by", "VARCHAR")
    add_column_if_missing(cursor, "questions", "last_edited_at", "DATETIME")
    add_column_if_missing(cursor, "questions", "created_at", "DATETIME")

    # Quality metrics
    add_column_if_missing(cursor, "questions", "quality_score", "FLOAT")
    add_column_if_missing(cursor, "questions", "clinical_accuracy_verified", "BOOLEAN DEFAULT 0")
    add_column_if_missing(cursor, "questions", "expert_reviewed", "BOOLEAN DEFAULT 0")
    add_column_if_missing(cursor, "questions", "expert_reviewed_at", "DATETIME")
    add_column_if_missing(cursor, "questions", "expert_reviewer_id", "VARCHAR")


def migrate_question_attempts_table(cursor):
    """Add missing columns to question_attempts table."""
    print("\n[Question Attempts Table]")

    add_column_if_missing(cursor, "question_attempts", "created_at", "DATETIME")


def create_performance_indexes(cursor):
    """Create indexes for common query patterns."""
    print("\n[Performance Indexes]")

    # Questions table indexes
    create_index_if_missing(cursor, "ix_questions_content_status", "questions", "content_status")
    create_index_if_missing(cursor, "ix_questions_source_type", "questions", "source_type")
    create_index_if_missing(cursor, "ix_questions_specialty", "questions", "specialty")
    create_index_if_missing(cursor, "ix_questions_difficulty_level", "questions", "difficulty_level")
    create_index_if_missing(cursor, "ix_questions_quality_score", "questions", "quality_score")
    create_index_if_missing(cursor, "ix_questions_expert_reviewed", "questions", "expert_reviewed")
    create_index_if_missing(cursor, "ix_questions_created_at", "questions", "created_at")
    create_index_if_missing(cursor, "ix_questions_rejected", "questions", "rejected")

    # Question attempts indexes
    create_index_if_missing(cursor, "ix_attempts_user_id", "question_attempts", "user_id")
    create_index_if_missing(cursor, "ix_attempts_question_id", "question_attempts", "question_id")
    create_index_if_missing(cursor, "ix_attempts_is_correct", "question_attempts", "is_correct")
    create_index_if_missing(cursor, "ix_attempts_attempted_at", "question_attempts", "attempted_at")

    # Error analyses indexes
    create_index_if_missing(cursor, "ix_error_analyses_error_type", "error_analyses", "error_type")

    # Scheduled reviews indexes (ensure all exist)
    create_index_if_missing(cursor, "ix_reviews_user_question", "scheduled_reviews", ["user_id", "question_id"])

    # Question ratings indexes
    create_index_if_missing(cursor, "ix_ratings_user_id", "question_ratings", "user_id")


def create_composite_indexes(cursor):
    """Create composite indexes for common multi-column queries."""
    print("\n[Composite Indexes]")

    # User + correct status for accuracy calculations
    create_index_if_missing(
        cursor,
        "ix_attempts_user_correct",
        "question_attempts",
        ["user_id", "is_correct"]
    )

    # User + date for trend analysis
    create_index_if_missing(
        cursor,
        "ix_attempts_user_date",
        "question_attempts",
        ["user_id", "attempted_at"]
    )

    # Question + source for specialty filtering
    create_index_if_missing(
        cursor,
        "ix_questions_source_weight",
        "questions",
        ["source", "recency_weight"]
    )

    # User + question for unique attempt lookup
    create_index_if_missing(
        cursor,
        "ix_attempts_user_question",
        "question_attempts",
        ["user_id", "question_id"]
    )

    # Reviews by user + scheduled date for due reviews
    create_index_if_missing(
        cursor,
        "ix_reviews_user_scheduled",
        "scheduled_reviews",
        ["user_id", "scheduled_for"]
    )

    # Chat messages by user + question
    create_index_if_missing(
        cursor,
        "ix_chat_user_question",
        "chat_messages",
        ["user_id", "question_id"]
    )

    # Error analyses by user + type for pattern analysis
    create_index_if_missing(
        cursor,
        "ix_errors_user_type",
        "error_analyses",
        ["user_id", "error_type"]
    )

    # Flagged questions by user + folder
    create_index_if_missing(
        cursor,
        "ix_flagged_user_folder",
        "flagged_questions",
        ["user_id", "folder"]
    )

    # Study sessions by user + status
    create_index_if_missing(
        cursor,
        "ix_sessions_user_status",
        "study_sessions",
        ["user_id", "status"]
    )


def update_default_values(cursor):
    """Update default values for existing rows."""
    print("\n[Default Values]")

    # Set default content_status for existing questions
    try:
        cursor.execute("""
            UPDATE questions
            SET content_status = 'active'
            WHERE content_status IS NULL
        """)
        print(f"  ✓ Updated {cursor.rowcount} questions with default content_status")
    except Exception as e:
        print(f"  ✗ Failed to update content_status: {e}")

    # Set default version for existing questions
    try:
        cursor.execute("""
            UPDATE questions
            SET version = 1
            WHERE version IS NULL
        """)
        print(f"  ✓ Updated {cursor.rowcount} questions with default version")
    except Exception as e:
        print(f"  ✗ Failed to update version: {e}")

    # Infer specialty from source if not set
    try:
        cursor.execute("""
            UPDATE questions
            SET specialty =
                CASE
                    WHEN source LIKE '%Medicine%' THEN 'internal_medicine'
                    WHEN source LIKE '%Surgery%' THEN 'surgery'
                    WHEN source LIKE '%Pediatric%' THEN 'pediatrics'
                    WHEN source LIKE '%Psychiatry%' THEN 'psychiatry'
                    WHEN source LIKE '%OB%' OR source LIKE '%Gyn%' THEN 'obstetrics_gynecology'
                    WHEN source LIKE '%Emergency%' THEN 'emergency_medicine'
                    WHEN source LIKE '%Neuro%' THEN 'neurology'
                    WHEN source LIKE '%Family%' THEN 'family_medicine'
                    ELSE 'general'
                END
            WHERE specialty IS NULL AND source IS NOT NULL
        """)
        print(f"  ✓ Inferred specialty for {cursor.rowcount} questions")
    except Exception as e:
        print(f"  ✗ Failed to infer specialty: {e}")

    # Infer source_type from source
    try:
        cursor.execute("""
            UPDATE questions
            SET source_type =
                CASE
                    WHEN source LIKE '%AI%' THEN 'ai_generated'
                    WHEN source LIKE '%NBME%' OR source LIKE '%Form%' THEN 'nbme'
                    ELSE 'imported'
                END
            WHERE source_type IS NULL AND source IS NOT NULL
        """)
        print(f"  ✓ Inferred source_type for {cursor.rowcount} questions")
    except Exception as e:
        print(f"  ✗ Failed to infer source_type: {e}")


def print_schema_summary(cursor):
    """Print a summary of the current schema."""
    print("\n" + "="*60)
    print("SCHEMA SUMMARY")
    print("="*60)

    # Count tables
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    table_count = cursor.fetchone()[0]

    # Count indexes
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    index_count = cursor.fetchone()[0]

    # Count questions
    cursor.execute("SELECT COUNT(*) FROM questions")
    question_count = cursor.fetchone()[0]

    # Count users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    # Count attempts
    cursor.execute("SELECT COUNT(*) FROM question_attempts")
    attempt_count = cursor.fetchone()[0]

    print(f"\nDatabase Statistics:")
    print(f"  Tables: {table_count}")
    print(f"  Indexes: {index_count}")
    print(f"  Questions: {question_count:,}")
    print(f"  Users: {user_count}")
    print(f"  Attempts: {attempt_count:,}")


def run_migration():
    """Run the complete migration."""
    print("="*60)
    print("ShelfSense Database Migration")
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Run migrations
        migrate_users_table(cursor)
        migrate_questions_table(cursor)
        migrate_question_attempts_table(cursor)
        create_performance_indexes(cursor)
        create_composite_indexes(cursor)
        update_default_values(cursor)

        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")

        # Print summary
        print_schema_summary(cursor)

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
