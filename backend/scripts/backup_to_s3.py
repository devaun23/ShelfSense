#!/usr/bin/env python3
"""
Database Backup Script with S3/R2 Upload for ShelfSense

Backs up PostgreSQL database and uploads to cloud storage.
Designed to run as a Railway Cron Job.

Usage:
    python scripts/backup_to_s3.py

Required Environment Variables:
    DATABASE_URL: PostgreSQL connection string

Optional (for cloud storage):
    AWS_ACCESS_KEY_ID: S3/R2 access key
    AWS_SECRET_ACCESS_KEY: S3/R2 secret key
    AWS_S3_BUCKET: Bucket name (default: shelfsense-backups)
    AWS_S3_ENDPOINT: Custom endpoint for R2/MinIO (optional)
    AWS_REGION: AWS region (default: us-east-1)

    BACKUP_RETENTION_DAYS: Days to keep backups (default: 30)
"""

import os
import sys
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# Try to import boto3 for S3 uploads
try:
    import boto3
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    print("Warning: boto3 not installed. Backups will only be stored locally.")

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

# S3/R2 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "shelfsense-backups")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT")  # For Cloudflare R2
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def get_timestamp():
    """Get formatted timestamp for backup filename."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_postgresql(db_url: str, output_path: Path) -> Path:
    """Backup PostgreSQL database using pg_dump."""
    parsed = urlparse(db_url)

    # Build pg_dump command
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""

    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/"),
        "-f", str(output_path),
        "--no-owner",
        "--no-acl",
        "--clean",  # Include DROP statements
        "--if-exists",  # Add IF EXISTS to DROP
    ]

    print(f"Running pg_dump to {output_path}...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")

    # Compress the backup
    print("Compressing backup...")
    subprocess.run(["gzip", "-f", str(output_path)], check=True)

    compressed_path = Path(str(output_path) + ".gz")
    size_mb = compressed_path.stat().st_size / (1024 * 1024)
    print(f"Backup created: {compressed_path.name} ({size_mb:.2f} MB)")

    return compressed_path


def upload_to_s3(file_path: Path, bucket: str, key: str) -> str:
    """Upload backup file to S3/R2."""
    if not HAS_BOTO3:
        print("Skipping S3 upload (boto3 not installed)")
        return ""

    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("Skipping S3 upload (credentials not configured)")
        return ""

    print(f"Uploading to s3://{bucket}/{key}...")

    # Configure S3 client
    config = Config(
        signature_version='s3v4',
        retries={'max_attempts': 3}
    )

    client_kwargs = {
        'aws_access_key_id': AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
        'region_name': AWS_REGION,
        'config': config,
    }

    # Support Cloudflare R2 or other S3-compatible storage
    if AWS_S3_ENDPOINT:
        client_kwargs['endpoint_url'] = AWS_S3_ENDPOINT

    s3_client = boto3.client('s3', **client_kwargs)

    # Upload with metadata
    s3_client.upload_file(
        str(file_path),
        bucket,
        key,
        ExtraArgs={
            'ContentType': 'application/gzip',
            'Metadata': {
                'backup-date': datetime.now().isoformat(),
                'source': 'shelfsense-backup-script'
            }
        }
    )

    print(f"Upload complete: s3://{bucket}/{key}")
    return f"s3://{bucket}/{key}"


def cleanup_old_backups_s3(bucket: str, prefix: str = "backups/"):
    """Remove backups older than RETENTION_DAYS from S3."""
    if not HAS_BOTO3 or not AWS_ACCESS_KEY_ID:
        return

    print(f"Cleaning up backups older than {RETENTION_DAYS} days...")

    client_kwargs = {
        'aws_access_key_id': AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
        'region_name': AWS_REGION,
    }
    if AWS_S3_ENDPOINT:
        client_kwargs['endpoint_url'] = AWS_S3_ENDPOINT

    s3_client = boto3.client('s3', **client_kwargs)
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)

    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        if 'Contents' not in response:
            return

        deleted = 0
        for obj in response['Contents']:
            if obj['LastModified'].replace(tzinfo=None) < cutoff:
                s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
                print(f"Deleted old backup: {obj['Key']}")
                deleted += 1

        if deleted:
            print(f"Cleaned up {deleted} old backup(s)")
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")


def send_notification(success: bool, message: str):
    """Send backup status notification (optional)."""
    webhook_url = os.getenv("BACKUP_WEBHOOK_URL")
    if not webhook_url:
        return

    try:
        import urllib.request
        import json

        payload = {
            "text": f"{'✅' if success else '❌'} ShelfSense Backup: {message}",
            "timestamp": datetime.now().isoformat()
        }

        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Warning: Failed to send notification: {e}")


def main():
    """Run database backup."""
    start_time = datetime.now()
    print(f"=" * 50)
    print(f"ShelfSense Database Backup")
    print(f"Started: {start_time.isoformat()}")
    print(f"=" * 50)

    if not DATABASE_URL:
        print("Error: DATABASE_URL not set", file=sys.stderr)
        send_notification(False, "DATABASE_URL not configured")
        return 1

    if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
        print("Error: Only PostgreSQL is supported for cloud backups", file=sys.stderr)
        send_notification(False, "Invalid database type")
        return 1

    try:
        # Create backup in temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            timestamp = get_timestamp()
            backup_name = f"shelfsense_{timestamp}.sql"
            backup_path = Path(tmpdir) / backup_name

            # Create backup
            compressed_path = backup_postgresql(DATABASE_URL, backup_path)

            # Upload to S3/R2
            s3_key = f"backups/{compressed_path.name}"
            upload_url = upload_to_s3(compressed_path, AWS_S3_BUCKET, s3_key)

            # Cleanup old backups
            cleanup_old_backups_s3(AWS_S3_BUCKET)

        duration = (datetime.now() - start_time).total_seconds()
        success_msg = f"Completed in {duration:.1f}s"
        if upload_url:
            success_msg += f" → {upload_url}"

        print(f"\n✅ Backup successful! {success_msg}")
        send_notification(True, success_msg)
        return 0

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Backup failed: {error_msg}", file=sys.stderr)
        send_notification(False, error_msg)
        return 1


if __name__ == "__main__":
    sys.exit(main())
