"""
OpenAI Fine-Tuning Upload and Training Script for ShelfSense

This script handles the complete fine-tuning workflow:
1. Upload training and validation files to OpenAI
2. Create fine-tuning job
3. Monitor training progress
4. Output the fine-tuned model ID

Usage:
    python scripts/upload_and_train.py                  # Upload and start training
    python scripts/upload_and_train.py --status <job>   # Check job status
    python scripts/upload_and_train.py --list           # List all fine-tuning jobs

Requirements:
    - OPENAI_API_KEY environment variable set
    - training_data.jsonl and validation_data.jsonl in backend/ directory
"""

import os
import sys
import time
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


def get_client():
    """Get OpenAI client"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def upload_file(client, file_path: str, purpose: str = "fine-tune"):
    """Upload a file to OpenAI"""
    print(f"Uploading {file_path}...")

    with open(file_path, "rb") as f:
        response = client.files.create(file=f, purpose=purpose)

    print(f"  Uploaded: {response.id}")
    return response.id


def create_fine_tuning_job(client, training_file_id: str, validation_file_id: str = None,
                            model: str = "gpt-3.5-turbo", suffix: str = "shelfsense-usmle"):
    """Create a fine-tuning job"""
    print(f"\nCreating fine-tuning job...")
    print(f"  Base model: {model}")
    print(f"  Training file: {training_file_id}")
    if validation_file_id:
        print(f"  Validation file: {validation_file_id}")

    kwargs = {
        "training_file": training_file_id,
        "model": model,
        "suffix": suffix
    }

    if validation_file_id:
        kwargs["validation_file"] = validation_file_id

    job = client.fine_tuning.jobs.create(**kwargs)

    print(f"\nFine-tuning job created!")
    print(f"  Job ID: {job.id}")
    print(f"  Status: {job.status}")
    print(f"  Model: {job.model}")

    return job.id


def check_job_status(client, job_id: str):
    """Check the status of a fine-tuning job"""
    job = client.fine_tuning.jobs.retrieve(job_id)

    print(f"\nJob Status: {job.id}")
    print(f"  Status: {job.status}")
    print(f"  Model: {job.model}")
    print(f"  Created: {datetime.fromtimestamp(job.created_at)}")

    if job.finished_at:
        print(f"  Finished: {datetime.fromtimestamp(job.finished_at)}")

    if job.fine_tuned_model:
        print(f"\n  FINE-TUNED MODEL ID: {job.fine_tuned_model}")
        print(f"\n  Use this model ID in your application!")

    if job.error:
        print(f"\n  ERROR: {job.error}")

    # Get recent events
    events = client.fine_tuning.jobs.list_events(fine_tuning_job_id=job_id, limit=10)
    if events.data:
        print(f"\nRecent Events:")
        for event in reversed(events.data):
            print(f"  [{datetime.fromtimestamp(event.created_at)}] {event.message}")

    return job


def monitor_job(client, job_id: str, poll_interval: int = 30):
    """Monitor a fine-tuning job until completion"""
    print(f"\nMonitoring job {job_id}...")
    print(f"(Press Ctrl+C to stop monitoring - job will continue in background)")

    try:
        while True:
            job = client.fine_tuning.jobs.retrieve(job_id)

            status_line = f"[{datetime.now().strftime('%H:%M:%S')}] Status: {job.status}"
            if job.trained_tokens:
                status_line += f" | Tokens trained: {job.trained_tokens}"

            print(status_line)

            if job.status in ["succeeded", "failed", "cancelled"]:
                print(f"\nJob completed with status: {job.status}")

                if job.fine_tuned_model:
                    print(f"\n{'='*60}")
                    print("SUCCESS! Fine-tuned model is ready:")
                    print(f"  Model ID: {job.fine_tuned_model}")
                    print(f"{'='*60}")

                    # Save model ID to file
                    save_model_id(job.fine_tuned_model)

                if job.error:
                    print(f"\nError details: {job.error}")

                return job

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print(f"\n\nStopped monitoring. Job {job_id} continues in background.")
        print(f"Check status with: python scripts/upload_and_train.py --status {job_id}")
        return None


def save_model_id(model_id: str):
    """Save the fine-tuned model ID to a config file"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".fine_tuned_model")

    with open(config_path, "w") as f:
        f.write(model_id)

    print(f"\nModel ID saved to: {config_path}")


def list_jobs(client, limit: int = 10):
    """List recent fine-tuning jobs"""
    jobs = client.fine_tuning.jobs.list(limit=limit)

    print(f"\nRecent Fine-Tuning Jobs:")
    print("-" * 80)

    for job in jobs.data:
        created = datetime.fromtimestamp(job.created_at).strftime("%Y-%m-%d %H:%M")
        model = job.fine_tuned_model or "(not ready)"

        print(f"  {job.id}")
        print(f"    Status: {job.status} | Created: {created}")
        print(f"    Base: {job.model} | Fine-tuned: {model}")
        print()


def main():
    parser = argparse.ArgumentParser(description="OpenAI Fine-Tuning for ShelfSense")
    parser.add_argument("--status", metavar="JOB_ID", help="Check status of a job")
    parser.add_argument("--monitor", metavar="JOB_ID", help="Monitor a job until completion")
    parser.add_argument("--list", action="store_true", help="List recent fine-tuning jobs")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="Base model to fine-tune")
    parser.add_argument("--suffix", default="shelfsense-usmle-v1", help="Model suffix")
    parser.add_argument("--training-file", default="training_data.jsonl", help="Training file")
    parser.add_argument("--validation-file", default="validation_data.jsonl", help="Validation file")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation file")
    args = parser.parse_args()

    try:
        client = get_client()
    except ValueError as e:
        print(f"Error: {e}")
        print("Set your OpenAI API key: export OPENAI_API_KEY='your-key'")
        sys.exit(1)

    print("=" * 60)
    print("ShelfSense Fine-Tuning Manager")
    print("=" * 60)

    # Check status of specific job
    if args.status:
        check_job_status(client, args.status)
        return

    # Monitor specific job
    if args.monitor:
        monitor_job(client, args.monitor)
        return

    # List all jobs
    if args.list:
        list_jobs(client)
        return

    # Default: Upload and create new job
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    training_path = os.path.join(backend_dir, args.training_file)
    validation_path = os.path.join(backend_dir, args.validation_file)

    # Check files exist
    if not os.path.exists(training_path):
        print(f"Error: Training file not found: {training_path}")
        print("Run prepare_fine_tuning_data.py first!")
        sys.exit(1)

    # Upload files
    print("\nStep 1: Uploading files to OpenAI...")
    training_file_id = upload_file(client, training_path)

    validation_file_id = None
    if not args.skip_validation and os.path.exists(validation_path):
        validation_file_id = upload_file(client, validation_path)
    else:
        print("  Skipping validation file")

    # Create fine-tuning job
    print("\nStep 2: Creating fine-tuning job...")
    job_id = create_fine_tuning_job(
        client,
        training_file_id,
        validation_file_id,
        model=args.model,
        suffix=args.suffix
    )

    # Monitor the job
    print("\nStep 3: Monitoring training progress...")
    monitor_job(client, job_id)


if __name__ == "__main__":
    main()
