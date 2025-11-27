#!/usr/bin/env python3
"""
Database Backup Script for ShelfSense

Supports both SQLite (local) and PostgreSQL (production) databases.
Can be run manually or scheduled via cron/Railway scheduled jobs.

Usage:
    python scripts/backup_database.py

Environment Variables:
    DATABASE_URL: Database connection string
    BACKUP_DIR: Directory to store backups (default: ./backups)
    BACKUP_RETENTION_DAYS: Days to keep backups (default: 30)
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# Configuration
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "./backups"))
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shelfsense.db")


def get_timestamp():
    """Get formatted timestamp for backup filename."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_sqlite(db_path: str) -> Path:
    """Backup SQLite database using file copy."""
    source = Path(db_path)
    if not source.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    backup_name = f"shelfsense_sqlite_{get_timestamp()}.db"
    backup_path = BACKUP_DIR / backup_name

    shutil.copy2(source, backup_path)
    print(f"SQLite backup created: {backup_path}")
    return backup_path


def backup_postgresql(db_url: str) -> Path:
    """Backup PostgreSQL database using pg_dump."""
    parsed = urlparse(db_url)

    backup_name = f"shelfsense_pg_{get_timestamp()}.sql"
    backup_path = BACKUP_DIR / backup_name

    # Build pg_dump command
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""

    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/"),
        "-f", str(backup_path),
        "--no-owner",
        "--no-acl",
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")

    # Compress the backup
    compressed_path = backup_path.with_suffix(".sql.gz")
    subprocess.run(["gzip", str(backup_path)], check=True)
    print(f"PostgreSQL backup created: {compressed_path}")
    return compressed_path


def cleanup_old_backups():
    """Remove backups older than RETENTION_DAYS."""
    if not BACKUP_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0

    for backup_file in BACKUP_DIR.glob("shelfsense_*"):
        if backup_file.stat().st_mtime < cutoff.timestamp():
            backup_file.unlink()
            removed += 1
            print(f"Removed old backup: {backup_file.name}")

    if removed:
        print(f"Cleaned up {removed} old backup(s)")


def main():
    """Run database backup."""
    print(f"Starting backup at {datetime.now().isoformat()}")
    print(f"Database URL: {DATABASE_URL[:20]}...")

    # Create backup directory
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if DATABASE_URL.startswith("sqlite"):
            # Extract path from sqlite:///./path.db
            db_path = DATABASE_URL.replace("sqlite:///", "")
            backup_path = backup_sqlite(db_path)
        elif DATABASE_URL.startswith(("postgres://", "postgresql://")):
            backup_path = backup_postgresql(DATABASE_URL)
        else:
            raise ValueError(f"Unsupported database type: {DATABASE_URL}")

        # Get backup size
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"Backup size: {size_mb:.2f} MB")

        # Cleanup old backups
        cleanup_old_backups()

        print("Backup completed successfully!")
        return 0

    except Exception as e:
        print(f"Backup failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
