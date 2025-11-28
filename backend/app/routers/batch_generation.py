"""
Batch Generation API Router

Provides endpoints for:
- Starting batch question generation jobs
- Checking job status and progress
- Listing user's jobs
- Cancelling running jobs
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.models import GenerationJob, User
from app.services.background_tasks import (
    create_generation_job,
    start_batch_generation,
    get_job,
    cancel_job,
    get_user_jobs,
    get_running_jobs,
    get_generation_stats,
    cleanup_stale_jobs
)
from app.middleware.rate_limiter import check_rate_limit, increment_usage

router = APIRouter(prefix="/api/batch", tags=["batch-generation"])


# ============================================================================
# Request/Response Models
# ============================================================================

class BatchGenerateRequest(BaseModel):
    """Request to start batch generation."""
    count: int = Field(..., ge=1, le=50, description="Number of questions to generate (1-50)")
    specialty: Optional[str] = Field(None, description="Target specialty (null for mixed)")
    difficulty: Optional[str] = Field(None, description="Difficulty level: easy, medium, hard")


class JobResponse(BaseModel):
    """Response with job details."""
    id: str
    user_id: str
    status: str
    specialty: Optional[str]
    difficulty: Optional[str]
    count: int
    completed: int
    failed: int
    progress_percent: float
    question_ids: List[str]
    errors: List[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


class JobListResponse(BaseModel):
    """Response with list of jobs."""
    jobs: List[JobResponse]
    total: int


class GenerationStatsResponse(BaseModel):
    """Response with generation statistics."""
    total_jobs: int
    total_generated: int
    total_failed: int
    success_rate: float
    by_status: Dict[str, int]


# ============================================================================
# Helper Functions
# ============================================================================

def job_to_response(job: GenerationJob) -> JobResponse:
    """Convert a GenerationJob to response format."""
    total = job.count or 1
    progress = ((job.completed or 0) + (job.failed or 0)) / total * 100

    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        status=job.status,
        specialty=job.specialty,
        difficulty=job.difficulty,
        count=job.count,
        completed=job.completed or 0,
        failed=job.failed or 0,
        progress_percent=min(progress, 100.0),
        question_ids=job.question_ids or [],
        errors=job.errors or [],
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/generate", response_model=JobResponse)
async def start_batch_generation_endpoint(
    request: BatchGenerateRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Start a batch question generation job.

    Creates an async job that generates multiple questions in the background.
    Returns immediately with job ID for status polling.

    Rate limited: counts against ai_questions_generated limit.
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check rate limit (pre-check for the total count)
    rate_check = check_rate_limit(db, user_id, "ai_questions_generated")
    if not rate_check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": rate_check["limit"],
                "current": rate_check["current"],
                "reset_at": rate_check["reset_at"].isoformat()
            }
        )

    # Check if remaining quota is enough
    if rate_check["remaining"] is not None and rate_check["remaining"] < request.count:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Insufficient quota",
                "requested": request.count,
                "remaining": rate_check["remaining"],
                "reset_at": rate_check["reset_at"].isoformat()
            }
        )

    # Check for existing running jobs (limit concurrent jobs)
    running = get_running_jobs(db, user_id)
    if len(running) >= 2:
        raise HTTPException(
            status_code=429,
            detail="Maximum 2 concurrent jobs allowed. Wait for existing jobs to complete."
        )

    # Validate specialty if provided
    valid_specialties = [
        "Internal Medicine", "Surgery", "Pediatrics", "Psychiatry",
        "OBGYN", "Family Medicine", "Emergency Medicine", "Preventive Medicine"
    ]
    if request.specialty and request.specialty not in valid_specialties:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid specialty. Must be one of: {', '.join(valid_specialties)}"
        )

    # Validate difficulty if provided
    if request.difficulty and request.difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty. Must be: easy, medium, or hard"
        )

    # Create the job
    job = create_generation_job(
        db=db,
        user_id=user_id,
        count=request.count,
        specialty=request.specialty,
        difficulty=request.difficulty
    )

    # Start background generation
    start_batch_generation(
        job_id=job.id,
        user_id=user_id,
        count=request.count,
        specialty=request.specialty,
        difficulty=request.difficulty
    )

    return job_to_response(job)


@router.get("/status/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the status and progress of a generation job.

    Poll this endpoint to track job progress.
    """
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_to_response(job)


@router.get("/jobs/{user_id}", response_model=JobListResponse)
async def list_user_jobs(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Max jobs to return"),
    db: Session = Depends(get_db)
):
    """
    List generation jobs for a user.

    Can filter by status: pending, running, completed, failed, cancelled
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate status if provided
    valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    jobs = get_user_jobs(db, user_id, status=status, limit=limit)

    return JobListResponse(
        jobs=[job_to_response(j) for j in jobs],
        total=len(jobs)
    )


@router.delete("/cancel/{job_id}")
async def cancel_generation_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Cancel a running generation job.

    Only pending or running jobs can be cancelled.
    """
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )

    success = cancel_job(db, job_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel job")

    return {
        "message": "Job cancelled successfully",
        "job_id": job_id,
        "completed_before_cancel": job.completed
    }


@router.get("/stats/{user_id}", response_model=GenerationStatsResponse)
async def get_user_generation_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get generation statistics for a user.

    Shows total generated, failed, success rate, etc.
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stats = get_generation_stats(db, user_id)
    return GenerationStatsResponse(**stats)


@router.get("/running/{user_id}")
async def get_running_generation_jobs(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get currently running jobs for a user.

    Useful for showing active generation status in UI.
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    jobs = get_running_jobs(db, user_id)

    return {
        "running_count": len(jobs),
        "jobs": [job_to_response(j) for j in jobs]
    }


@router.post("/cleanup")
async def cleanup_stale_generation_jobs(
    max_age_hours: int = Query(24, ge=1, le=168, description="Max job age in hours"),
    db: Session = Depends(get_db)
):
    """
    Clean up stale generation jobs.

    Marks jobs that have been running too long as failed.
    Admin endpoint for maintenance.
    """
    cleaned = cleanup_stale_jobs(db, max_age_hours=max_age_hours)

    return {
        "message": f"Cleaned up {cleaned} stale jobs",
        "cleaned_count": cleaned
    }
