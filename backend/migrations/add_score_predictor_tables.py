"""
Migration: Add NBME-Calibrated Score Predictor Tables

Creates:
- external_assessment_scores table: Stores user-entered NBME/UWSA scores
- score_prediction_history table: Tracks predictions over time

Safe to run multiple times - checks if tables exist first.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_external_assessment_scores_table():
    """Create the external_assessment_scores table."""
    if table_exists("external_assessment_scores"):
        print("  ✓ Table 'external_assessment_scores' already exists, skipping")
        return False

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE external_assessment_scores (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                assessment_type VARCHAR NOT NULL,
                assessment_name VARCHAR NOT NULL,
                score INTEGER NOT NULL,
                percentile INTEGER,
                date_taken DATETIME NOT NULL,
                shelfsense_accuracy_at_time FLOAT,
                shelfsense_questions_at_time INTEGER,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        # Create indexes
        conn.execute(text("""
            CREATE INDEX ix_external_assessment_scores_user_id
            ON external_assessment_scores(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX ix_external_assessment_scores_assessment_type
            ON external_assessment_scores(assessment_type)
        """))
        conn.execute(text("""
            CREATE INDEX ix_external_assessment_scores_created_at
            ON external_assessment_scores(created_at)
        """))

        conn.commit()

    print("  + Created table 'external_assessment_scores'")
    return True


def create_score_prediction_history_table():
    """Create the score_prediction_history table."""
    if table_exists("score_prediction_history"):
        print("  ✓ Table 'score_prediction_history' already exists, skipping")
        return False

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE score_prediction_history (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                predicted_score INTEGER NOT NULL,
                confidence_interval_low INTEGER NOT NULL,
                confidence_interval_high INTEGER NOT NULL,
                confidence_level VARCHAR NOT NULL,
                shelfsense_accuracy FLOAT NOT NULL,
                shelfsense_questions INTEGER NOT NULL,
                external_score_count INTEGER DEFAULT 0,
                external_score_avg FLOAT,
                weight_breakdown JSON,
                algorithm_version VARCHAR DEFAULT 'v1.0',
                calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        # Create indexes
        conn.execute(text("""
            CREATE INDEX ix_score_prediction_history_user_id
            ON score_prediction_history(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX ix_score_prediction_history_calculated_at
            ON score_prediction_history(calculated_at)
        """))

        conn.commit()

    print("  + Created table 'score_prediction_history'")
    return True


def migrate():
    """Run the migration to create score predictor tables."""

    print("=" * 80)
    print("ShelfSense - Add NBME-Calibrated Score Predictor Tables Migration")
    print("=" * 80)
    print()

    # Check if users table exists (dependency)
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        print("ERROR: 'users' table does not exist!")
        print("Please run the main migration first.")
        return False

    print("Creating score predictor tables...")
    print()

    created_count = 0

    if create_external_assessment_scores_table():
        created_count += 1

    if create_score_prediction_history_table():
        created_count += 1

    print()
    if created_count > 0:
        print(f"✓ Created {created_count} new table(s)")
    else:
        print("✓ All tables already exist, nothing to do")

    print()
    print("=" * 80)
    print("Migration complete!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    migrate()
