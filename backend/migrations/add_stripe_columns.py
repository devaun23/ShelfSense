"""
Migration: Add Stripe Payment Columns to Subscription Table

Adds the following columns to the subscriptions table:
- stripe_status: Stripe subscription status ("active", "past_due", "canceled", etc.)
- stripe_price_id: Current Stripe price ID
- payment_status: Local payment status ("ok", "past_due", "failed")
- grace_period_ends_at: When the 7-day grace period expires

Safe to run multiple times - checks if columns exist first.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.database import engine

def get_existing_columns(table_name: str) -> set:
    """Get set of existing column names for a table."""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {col['name'] for col in columns}

def add_column_if_not_exists(table: str, column: str, column_def: str):
    """Add a column if it doesn't already exist."""
    existing_columns = get_existing_columns(table)

    if column in existing_columns:
        print(f"  ✓ Column '{column}' already exists, skipping")
        return False

    with engine.connect() as conn:
        # SQLite uses a simpler ALTER TABLE syntax
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}"))
        conn.commit()

    print(f"  + Added column '{column}'")
    return True

def migrate():
    """Add Stripe-related columns to subscriptions table."""

    print("=" * 80)
    print("ShelfSense - Add Stripe Payment Columns Migration")
    print("=" * 80)
    print()

    # Check if subscriptions table exists
    inspector = inspect(engine)
    if 'subscriptions' not in inspector.get_table_names():
        print("ERROR: 'subscriptions' table does not exist!")
        print("Please run the main migration first.")
        return False

    print("Adding Stripe columns to 'subscriptions' table...")
    print()

    # Add new columns
    # Note: SQLite doesn't support DEFAULT in ALTER TABLE, so we use nullable columns
    columns_to_add = [
        ("stripe_status", "VARCHAR"),
        ("stripe_price_id", "VARCHAR"),
        ("payment_status", "VARCHAR DEFAULT 'ok'"),
        ("grace_period_ends_at", "DATETIME"),
    ]

    added_count = 0
    for column_name, column_def in columns_to_add:
        if add_column_if_not_exists("subscriptions", column_name, column_def):
            added_count += 1

    print()
    if added_count > 0:
        print(f"✓ Added {added_count} new column(s)")
    else:
        print("✓ All columns already exist, nothing to do")

    print()
    print("=" * 80)
    print("Migration complete!")
    print("=" * 80)

    return True

if __name__ == "__main__":
    migrate()
