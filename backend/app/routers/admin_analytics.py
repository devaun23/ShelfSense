"""
Admin Analytics Router

Protected admin-only endpoints for platform-wide usage analytics.
All endpoints require admin authentication via get_admin_user dependency.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.routers.auth import get_admin_user
from app.models.models import User
from app.services.admin_analytics_service import (
    get_activity_overview,
    get_activity_trends,
    get_feature_usage,
    get_retention_overview,
    calculate_cohort_retention,
    get_user_health_distribution,
    get_users_at_risk,
    calculate_user_engagement_score,
    run_daily_metrics_batch,
    run_user_engagement_batch,
    run_cohort_retention_batch,
    get_historical_metrics
)


router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])


# =============================================================================
# Response Models
# =============================================================================

class ActivityOverviewResponse(BaseModel):
    dau: int
    wau: int
    mau: int
    total_users: int
    stickiness: float
    sessions: dict
    questions_answered: int
    avg_questions_per_dau: float
    period_days: int


class ActivityTrendsResponse(BaseModel):
    daily_data: List[dict]
    period_days: int


class FeatureUsageResponse(BaseModel):
    study_modes: dict
    ai_chat_messages: int
    ai_questions_generated: int
    period_days: int


class RetentionOverviewResponse(BaseModel):
    total_users: int
    activated_users: int
    activation_rate: float
    day1_retention: float
    day7_retention: float
    day30_retention: float
    retained_day1: int
    retained_day7: int
    retained_day30: int


class UserHealthDistributionResponse(BaseModel):
    distribution: dict
    percentages: dict
    total_users: int


class BatchJobResponse(BaseModel):
    status: str
    date: Optional[str] = None
    metrics: Optional[dict] = None
    users_processed: Optional[int] = None
    distribution: Optional[dict] = None
    cohorts_processed: Optional[int] = None
    records_updated: Optional[int] = None


# =============================================================================
# ACTIVITY METRICS ENDPOINTS
# =============================================================================

@router.get("/overview", response_model=ActivityOverviewResponse)
def get_overview(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get platform activity overview.

    Returns DAU/WAU/MAU, session metrics, stickiness ratio, and question activity.
    """
    return get_activity_overview(db, days)


@router.get("/trends", response_model=ActivityTrendsResponse)
def get_trends(
    days: int = Query(default=30, ge=7, le=90, description="Number of days for trend data"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get daily activity trends for charting.

    Returns daily active users and questions answered for each day.
    """
    return get_activity_trends(db, days)


@router.get("/feature-usage", response_model=FeatureUsageResponse)
def get_features(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get feature usage breakdown.

    Returns usage counts for study modes, AI chat, and AI question generation.
    """
    return get_feature_usage(db, days)


@router.get("/historical")
def get_historical(
    days: int = Query(default=30, ge=7, le=90, description="Number of days of history"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get historical daily metrics from pre-computed data.

    Returns daily snapshots of DAU/WAU/MAU, sessions, and signups.
    Requires batch jobs to be run first.
    """
    return get_historical_metrics(db, days)


# =============================================================================
# RETENTION METRICS ENDPOINTS
# =============================================================================

@router.get("/retention", response_model=RetentionOverviewResponse)
def get_retention(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get retention metrics overview.

    Returns day 1, 7, and 30 retention rates based on user activity patterns.
    """
    return get_retention_overview(db)


@router.get("/cohorts")
def get_cohorts(
    weeks: int = Query(default=12, ge=4, le=52, description="Number of weeks to analyze"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get cohort retention analysis.

    Returns weekly cohort data with retention rates for each subsequent week.
    Useful for building cohort retention charts.
    """
    return calculate_cohort_retention(db, weeks)


# =============================================================================
# USER HEALTH ENDPOINTS
# =============================================================================

@router.get("/user-health", response_model=UserHealthDistributionResponse)
def get_health_distribution(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user engagement health distribution.

    Returns counts and percentages for each status: active, at_risk, churned, new.
    """
    return get_user_health_distribution(db)


@router.get("/users-at-risk")
def get_at_risk_users(
    limit: int = Query(default=50, ge=10, le=200, description="Maximum users to return"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get list of at-risk users for outreach.

    Returns users classified as at-risk, sorted by churn risk score.
    Includes risk factors and activity metrics for each user.
    """
    return get_users_at_risk(db, limit)


@router.get("/user-health/{user_id}")
def get_user_health(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get engagement health for a specific user.

    Returns detailed engagement metrics including activity counts,
    engagement score, and churn risk factors.
    """
    result = calculate_user_engagement_score(db, user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# =============================================================================
# BATCH JOB ENDPOINTS (Manual Triggers)
# =============================================================================

@router.post("/batch/daily-metrics", response_model=BatchJobResponse)
def trigger_daily_metrics(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger daily metrics batch job.

    Computes and stores platform-wide metrics in DailyPlatformMetrics table.
    Safe to run multiple times - will update existing record for today.
    """
    return run_daily_metrics_batch(db)


@router.post("/batch/user-engagement", response_model=BatchJobResponse)
def trigger_user_engagement(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger user engagement scoring batch job.

    Updates engagement scores for all users in UserEngagementScore table.
    Safe to run multiple times - will update existing records.
    """
    return run_user_engagement_batch(db)


@router.post("/batch/cohort-retention", response_model=BatchJobResponse)
def trigger_cohort_retention(
    weeks: int = Query(default=12, ge=4, le=52, description="Number of weeks to process"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger cohort retention batch job.

    Updates cohort retention data in CohortRetention table.
    Safe to run multiple times - will update existing records.
    """
    return run_cohort_retention_batch(db, weeks)


@router.post("/batch/all")
def trigger_all_batch_jobs(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Run all batch jobs in sequence.

    Convenience endpoint to update all analytics data at once.
    """
    daily_result = run_daily_metrics_batch(db)
    engagement_result = run_user_engagement_batch(db)
    cohort_result = run_cohort_retention_batch(db, 12)

    return {
        "status": "success",
        "jobs_completed": {
            "daily_metrics": daily_result,
            "user_engagement": engagement_result,
            "cohort_retention": cohort_result
        }
    }
