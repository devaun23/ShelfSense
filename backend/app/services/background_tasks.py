"""
Background Tasks Service for ShelfSense

Handles asynchronous job processing for:
- Batch question generation
- Long-running AI operations
- Scheduled maintenance tasks
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import GenerationJob, Question, generate_uuid
from app.services.question_agent import QuestionAgent
from app.utils.api_retry import openai_retry, RetryConfig

# Configure logging
logger = logging.getLogger(__name__)

# Thread pool for background tasks
_executor = ThreadPoolExecutor(max_workers=3)


# ============================================================================
# JOB MANAGEMENT
# ============================================================================

def get_job(db: Session, job_id: str) -> Optional[GenerationJob]:
    """Get a generation job by ID."""
    return db.query(GenerationJob).filter(GenerationJob.id == job_id).first()


def create_generation_job(
    db: Session,
    user_id: str,
    count: int,
    specialty: Optional[str] = None,
    difficulty: Optional[str] = None
) -> GenerationJob:
    """Create a new generation job."""
    job = GenerationJob(
        id=generate_uuid(),
        user_id=user_id,
        count=count,
        specialty=specialty,
        difficulty=difficulty,
        status="pending",
        completed=0,
        failed=0,
        question_ids=[],
        errors=[]
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job_status(
    db: Session,
    job_id: str,
    status: str,
    completed: Optional[int] = None,
    failed: Optional[int] = None,
    question_ids: Optional[List[str]] = None,
    errors: Optional[List[str]] = None
):
    """Update job progress and status."""
    job = get_job(db, job_id)
    if not job:
        return

    job.status = status
    job.updated_at = datetime.utcnow()

    if completed is not None:
        job.completed = completed
    if failed is not None:
        job.failed = failed
    if question_ids is not None:
        job.question_ids = question_ids
    if errors is not None:
        job.errors = errors

    if status == "running" and not job.started_at:
        job.started_at = datetime.utcnow()
    elif status in ["completed", "failed", "cancelled"]:
        job.completed_at = datetime.utcnow()

    db.commit()


def cancel_job(db: Session, job_id: str) -> bool:
    """Cancel a running job."""
    job = get_job(db, job_id)
    if not job:
        return False

    if job.status in ["completed", "failed", "cancelled"]:
        return False

    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    db.commit()
    return True


# ============================================================================
# BATCH GENERATION
# ============================================================================

async def run_batch_generation(
    job_id: str,
    user_id: str,
    count: int,
    specialty: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """
    Run batch question generation asynchronously.

    This function is designed to be run as a background task.
    It generates questions one at a time, updating progress after each.
    """
    db = SessionLocal()
    try:
        # Mark job as running
        update_job_status(db, job_id, "running")

        question_ids = []
        errors = []
        completed = 0
        failed = 0

        # Create question agent
        agent = QuestionAgent(db)

        for i in range(count):
            # Check if job was cancelled
            job = get_job(db, job_id)
            if not job or job.status == "cancelled":
                logger.info(f"Job {job_id} was cancelled at question {i+1}/{count}")
                break

            try:
                # Generate a question
                logger.info(f"Job {job_id}: Generating question {i+1}/{count}")

                # Use the question agent to generate
                question_data = agent.generate_question(
                    specialty=specialty,
                    difficulty=difficulty
                )

                if question_data and "id" in question_data:
                    question_ids.append(question_data["id"])
                    completed += 1
                    logger.info(f"Job {job_id}: Generated question {question_data['id']}")
                else:
                    failed += 1
                    errors.append(f"Question {i+1}: Generation returned no data")

            except Exception as e:
                failed += 1
                error_msg = f"Question {i+1}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Job {job_id}: {error_msg}")

            # Update progress after each question
            update_job_status(
                db, job_id, "running",
                completed=completed,
                failed=failed,
                question_ids=question_ids,
                errors=errors
            )

            # Small delay to avoid rate limiting
            await asyncio.sleep(1)

        # Mark job as completed
        final_status = "completed" if completed > 0 else "failed"
        update_job_status(
            db, job_id, final_status,
            completed=completed,
            failed=failed,
            question_ids=question_ids,
            errors=errors
        )

        logger.info(
            f"Job {job_id} finished: {completed} generated, {failed} failed"
        )

    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {str(e)}")
        update_job_status(
            db, job_id, "failed",
            errors=[str(e)]
        )
    finally:
        db.close()


def start_batch_generation(
    job_id: str,
    user_id: str,
    count: int,
    specialty: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """
    Start batch generation in a background thread.

    This is a synchronous function that schedules the async work.
    """
    loop = asyncio.new_event_loop()

    def run_in_thread():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            run_batch_generation(job_id, user_id, count, specialty, difficulty)
        )
        loop.close()

    _executor.submit(run_in_thread)


# ============================================================================
# JOB QUERIES
# ============================================================================

def get_user_jobs(
    db: Session,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 20
) -> List[GenerationJob]:
    """Get jobs for a user, optionally filtered by status."""
    query = db.query(GenerationJob).filter(GenerationJob.user_id == user_id)

    if status:
        query = query.filter(GenerationJob.status == status)

    return query.order_by(GenerationJob.created_at.desc()).limit(limit).all()


def get_running_jobs(db: Session, user_id: str) -> List[GenerationJob]:
    """Get all currently running jobs for a user."""
    return db.query(GenerationJob).filter(
        GenerationJob.user_id == user_id,
        GenerationJob.status.in_(["pending", "running"])
    ).all()


def cleanup_stale_jobs(db: Session, max_age_hours: int = 24):
    """
    Mark old running jobs as failed.

    Jobs that have been running for too long are likely stuck.
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

    stale_jobs = db.query(GenerationJob).filter(
        GenerationJob.status.in_(["pending", "running"]),
        GenerationJob.created_at < cutoff
    ).all()

    for job in stale_jobs:
        job.status = "failed"
        job.errors = (job.errors or []) + ["Job timed out after 24 hours"]
        job.completed_at = datetime.utcnow()

    if stale_jobs:
        db.commit()
        logger.info(f"Cleaned up {len(stale_jobs)} stale jobs")

    return len(stale_jobs)


# ============================================================================
# STATISTICS
# ============================================================================

def get_generation_stats(db: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get statistics about generation jobs."""
    query = db.query(GenerationJob)

    if user_id:
        query = query.filter(GenerationJob.user_id == user_id)

    jobs = query.all()

    if not jobs:
        return {
            "total_jobs": 0,
            "total_generated": 0,
            "total_failed": 0,
            "success_rate": 0.0,
            "by_status": {}
        }

    total_generated = sum(job.completed or 0 for job in jobs)
    total_failed = sum(job.failed or 0 for job in jobs)
    total_attempted = total_generated + total_failed

    by_status = {}
    for job in jobs:
        by_status[job.status] = by_status.get(job.status, 0) + 1

    return {
        "total_jobs": len(jobs),
        "total_generated": total_generated,
        "total_failed": total_failed,
        "success_rate": (total_generated / total_attempted * 100) if total_attempted > 0 else 0.0,
        "by_status": by_status
    }
