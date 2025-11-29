"""
Migration: Add clerk_id Column to Users Table

Adds the clerk_id column to the users table for Clerk SSO authentication.
This column stores the Clerk user ID to link users authenticated via Clerk.

CRITICAL: This migration must be run before the application can authenticate
users via Clerk JWT tokens.

Safe to run multiple times - checks if column exists first.
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

def create_index_if_not_exists(table: str, column: str, unique: bool = False):
    """Create an index on a column if it doesn't exist."""
    index_name = f"ix_{table}_{column}"
    unique_str = "UNIQUE " if unique else ""

    with engine.connect() as conn:
        # Check if index exists
        result = conn.execute(text(
            f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
        ))
        if result.fetchone():
            print(f"  ✓ Index '{index_name}' already exists, skipping")
            return False

        # Create the index
        conn.execute(text(f"CREATE {unique_str}INDEX {index_name} ON {table}({column})"))
        conn.commit()

    print(f"  + Created {'unique ' if unique else ''}index '{index_name}'")
    return True

def migrate():
    """Add clerk_id column to users table."""

    print("=" * 80)
    print("ShelfSense - Add Clerk ID Column Migration")
    print("=" * 80)
    print()

    # Check if users table exists
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        print("ERROR: 'users' table does not exist!")
        print("Please run the main migration first.")
        return False

    print("Adding clerk_id column to 'users' table...")
    print()

    # Add the clerk_id column
    # Note: SQLite doesn't enforce UNIQUE in ALTER TABLE, so we create a unique index separately
    added = add_column_if_not_exists("users", "clerk_id", "VARCHAR")

    # Create unique index for clerk_id
    indexed = create_index_if_not_exists("users", "clerk_id", unique=True)

    print()
    if added or indexed:
        print("✓ Migration applied successfully")
    else:
        print("✓ Column and index already exist, nothing to do")

    print()
    print("=" * 80)
    print("Migration complete!")
    print("=" * 80)

    return True

if __name__ == "__main__":
    migrate()
