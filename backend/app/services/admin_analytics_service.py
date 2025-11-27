"""
Admin Analytics Service

Platform-wide usage analytics for the admin dashboard.
Includes:
- Activity metrics (DAU/WAU/MAU, sessions, feature usage)
- Retention metrics (cohort analysis, churn prediction)
- Health scoring (per-user engagement classification)
- Daily batch processing for pre-aggregated metrics
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, and_, Integer, cast

from app.models.models import (
    User, QuestionAttempt, DailyUsage, StudySession, UserSession,
    DailyPlatformMetrics, UserEngagementScore, CohortRetention, ChatMessage
)


# =============================================================================
# ACTIVITY METRICS
# =============================================================================

def get_activity_overview(db: Session, days: int = 30) -> Dict[str, Any]:
    """Get platform activity overview for admin dashboard."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # DAU/WAU/MAU
    dau = _count_active_users(db, days=1)
    wau = _count_active_users(db, days=7)
    mau = _count_active_users(db, days=30)

    # Session metrics from StudySession
    sessions = db.query(StudySession).filter(
        StudySession.started_at >= start_date
    ).all()

    total_sessions = len(sessions)
    completed_sessions = len([s for s in sessions if s.status == 'completed'])
    total_time = sum((s.time_spent_seconds or 0) for s in sessions)
    avg_duration = total_time / max(total_sessions, 1)

    # Questions answered
    total_questions = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.attempted_at >= start_date
    ).scalar() or 0

    # Total registered users
    total_users = db.query(func.count(User.id)).scalar() or 0

    # Stickiness ratio (DAU/MAU)
    stickiness = round(dau / max(mau, 1) * 100, 1)

    return {
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "total_users": total_users,
        "stickiness": stickiness,
        "sessions": {
            "total": total_sessions,
            "completed": completed_sessions,
            "completion_rate": round(completed_sessions / max(total_sessions, 1) * 100, 1),
            "avg_duration_minutes": round(avg_duration / 60, 1),
            "total_time_hours": round(total_time / 3600, 1)
        },
        "questions_answered": total_questions,
        "avg_questions_per_dau": round(total_questions / max(dau, 1), 1),
        "period_days": days
    }


def _count_active_users(db: Session, days: int) -> int:
    """Count unique users with activity in the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    return db.query(func.count(distinct(QuestionAttempt.user_id))).filter(
        QuestionAttempt.attempted_at >= cutoff
    ).scalar() or 0


def get_activity_trends(db: Session, days: int = 30) -> Dict[str, Any]:
    """Get daily activity trends for charting."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Daily active users and questions
    daily_stats = db.query(
        func.date(QuestionAttempt.attempted_at).label('date'),
        func.count(distinct(QuestionAttempt.user_id)).label('active_users'),
        func.count(QuestionAttempt.id).label('questions_answered')
    ).filter(
        QuestionAttempt.attempted_at >= start_date
    ).group_by(
        func.date(QuestionAttempt.attempted_at)
    ).order_by(
        func.date(QuestionAttempt.attempted_at)
    ).all()

    return {
        "daily_data": [
            {
                "date": str(row.date),
                "active_users": row.active_users,
                "questions_answered": row.questions_answered
            }
            for row in daily_stats
        ],
        "period_days": days
    }


def get_feature_usage(db: Session, days: int = 30) -> Dict[str, Any]:
    """Get feature usage breakdown."""
    start_date = datetime.utcnow() - timedelta(days=days)

    # Study modes usage
    mode_usage = db.query(
        StudySession.mode,
        func.count(StudySession.id).label('count')
    ).filter(
        StudySession.started_at >= start_date
    ).group_by(StudySession.mode).all()

    # AI chat usage
    ai_chats = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.created_at >= start_date,
        ChatMessage.role == "user"
    ).scalar() or 0

    # DailyUsage aggregation
    usage_agg = db.query(
        func.sum(DailyUsage.ai_chat_messages).label('ai_chats'),
        func.sum(DailyUsage.ai_questions_generated).label('ai_generated')
    ).filter(
        DailyUsage.date >= start_date
    ).first()

    return {
        "study_modes": {row.mode: row.count for row in mode_usage if row.mode},
        "ai_chat_messages": ai_chats,
        "ai_questions_generated": usage_agg.ai_generated if usage_agg and usage_agg.ai_generated else 0,
        "period_days": days
    }


# =============================================================================
# RETENTION METRICS
# =============================================================================

def get_retention_overview(db: Session) -> Dict[str, Any]:
    """Get retention metrics overview."""
    now = datetime.utcnow()

    # Get all users with their first activity
    users_with_activity = db.query(
        User.id,
        User.created_at,
        func.min(QuestionAttempt.attempted_at).label('first_activity')
    ).outerjoin(
        QuestionAttempt, User.id == QuestionAttempt.user_id
    ).group_by(User.id, User.created_at).all()

    total_users = len(users_with_activity)
    users_with_any_activity = len([u for u in users_with_activity if u.first_activity])

    # Calculate retention at different intervals
    day1_retained = 0
    day7_retained = 0
    day30_retained = 0

    for user in users_with_activity:
        if not user.created_at or not user.first_activity:
            continue

        user_id = user.id
        signup_date = user.created_at

        # Check for activity in day 1 (24-48 hours after signup)
        day1_start = signup_date + timedelta(days=1)
        day1_end = signup_date + timedelta(days=2)

        has_day1 = db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= day1_start,
            QuestionAttempt.attempted_at < day1_end
        ).first() is not None

        if has_day1:
            day1_retained += 1

        # Check for activity in day 7 window (days 6-8)
        day7_start = signup_date + timedelta(days=6)
        day7_end = signup_date + timedelta(days=8)

        has_day7 = db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= day7_start,
            QuestionAttempt.attempted_at < day7_end
        ).first() is not None

        if has_day7:
            day7_retained += 1

        # Check for activity in day 30 window (days 28-32)
        day30_start = signup_date + timedelta(days=28)
        day30_end = signup_date + timedelta(days=32)

        has_day30 = db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= day30_start,
            QuestionAttempt.attempted_at < day30_end
        ).first() is not None

        if has_day30:
            day30_retained += 1

    activated = max(users_with_any_activity, 1)

    return {
        "total_users": total_users,
        "activated_users": users_with_any_activity,
        "activation_rate": round(users_with_any_activity / max(total_users, 1) * 100, 1),
        "day1_retention": round(day1_retained / activated * 100, 1),
        "day7_retention": round(day7_retained / activated * 100, 1),
        "day30_retention": round(day30_retained / activated * 100, 1),
        "retained_day1": day1_retained,
        "retained_day7": day7_retained,
        "retained_day30": day30_retained
    }


def calculate_cohort_retention(db: Session, weeks_back: int = 12) -> List[Dict]:
    """Calculate weekly cohort retention."""
    cohorts = []
    now = datetime.utcnow()

    for week_offset in range(weeks_back):
        # Calculate week boundaries
        week_end = now - timedelta(weeks=week_offset)
        week_start = week_end - timedelta(weeks=1)

        # Users who signed up this week
        cohort_users = db.query(User).filter(
            User.created_at >= week_start,
            User.created_at < week_end
        ).all()

        if not cohort_users:
            continue

        cohort_size = len(cohort_users)
        user_ids = [u.id for u in cohort_users]

        # Calculate retention for each subsequent week (up to 8 weeks)
        retention_weeks = []
        max_retention_weeks = min(week_offset + 1, 8)

        for retention_week in range(max_retention_weeks):
            retention_start = week_end + timedelta(weeks=retention_week)
            retention_end = retention_start + timedelta(weeks=1)

            # Don't calculate future retention
            if retention_start > now:
                break

            retained = db.query(func.count(distinct(QuestionAttempt.user_id))).filter(
                QuestionAttempt.user_id.in_(user_ids),
                QuestionAttempt.attempted_at >= retention_start,
                QuestionAttempt.attempted_at < retention_end
            ).scalar() or 0

            retention_weeks.append({
                "week": retention_week,
                "retained": retained,
                "rate": round(retained / cohort_size * 100, 1)
            })

        cohorts.append({
            "cohort_week": week_start.strftime("%Y-%m-%d"),
            "cohort_size": cohort_size,
            "retention": retention_weeks
        })

    return cohorts


# =============================================================================
# USER HEALTH SCORING
# =============================================================================

def get_user_health_distribution(db: Session) -> Dict[str, Any]:
    """Get distribution of user engagement health."""
    # First check if we have pre-computed scores
    scores = db.query(UserEngagementScore).all()

    if scores:
        # Use pre-computed scores
        distribution = {"active": 0, "at_risk": 0, "churned": 0, "new": 0}
        for score in scores:
            status = score.engagement_status or "new"
            distribution[status] = distribution.get(status, 0) + 1
    else:
        # Calculate on the fly
        distribution = _calculate_health_distribution(db)

    total = sum(distribution.values()) or 1

    return {
        "distribution": distribution,
        "percentages": {k: round(v / total * 100, 1) for k, v in distribution.items()},
        "total_users": total
    }


def _calculate_health_distribution(db: Session) -> Dict[str, int]:
    """Calculate health distribution from scratch."""
    now = datetime.utcnow()
    distribution = {"active": 0, "at_risk": 0, "churned": 0, "new": 0}

    users = db.query(User).all()

    for user in users:
        status = _classify_user_engagement(db, user.id, now)
        distribution[status] += 1

    return distribution


def _classify_user_engagement(db: Session, user_id: str, now: datetime) -> str:
    """Classify a single user's engagement status."""
    # Get last activity
    last_attempt = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id
    ).order_by(QuestionAttempt.attempted_at.desc()).first()

    if not last_attempt:
        return "new"

    days_since_last = (now - last_attempt.attempted_at).days

    # Count questions in last 7 days
    questions_7d = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= now - timedelta(days=7)
    ).scalar() or 0

    # Classification logic
    if days_since_last <= 3 and questions_7d >= 5:
        return "active"
    elif days_since_last <= 7:
        return "active"
    elif days_since_last <= 14:
        return "at_risk"
    else:
        return "churned"


def get_users_at_risk(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    """Get list of at-risk users for outreach."""
    now = datetime.utcnow()

    # Check pre-computed scores first
    at_risk_scores = db.query(UserEngagementScore).filter(
        UserEngagementScore.engagement_status == "at_risk"
    ).order_by(UserEngagementScore.churn_risk_score.desc()).limit(limit).all()

    if at_risk_scores:
        result = []
        for score in at_risk_scores:
            user = db.query(User).filter(User.id == score.user_id).first()
            if user:
                result.append({
                    "user_id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "days_since_activity": score.days_since_last_activity,
                    "questions_last_7_days": score.questions_last_7_days,
                    "churn_risk_score": score.churn_risk_score,
                    "risk_factors": score.churn_risk_factors or []
                })
        return result

    # Calculate on the fly
    users = db.query(User).all()
    at_risk = []

    for user in users:
        status = _classify_user_engagement(db, user.id, now)
        if status == "at_risk":
            engagement = calculate_user_engagement_score(db, user.id)
            at_risk.append({
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "days_since_activity": engagement.get("days_since_last_activity"),
                "questions_last_7_days": engagement.get("questions_last_7_days", 0),
                "churn_risk_score": engagement.get("churn_risk_score", 0.5),
                "risk_factors": engagement.get("churn_risk_factors", [])
            })

    # Sort by risk score and limit
    at_risk.sort(key=lambda x: x.get("churn_risk_score", 0), reverse=True)
    return at_risk[:limit]


def calculate_user_engagement_score(db: Session, user_id: str) -> Dict[str, Any]:
    """Calculate engagement score for a single user."""
    now = datetime.utcnow()

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    # Activity counts
    questions_7d = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= now - timedelta(days=7)
    ).scalar() or 0

    questions_30d = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= now - timedelta(days=30)
    ).scalar() or 0

    sessions_7d = db.query(func.count(StudySession.id)).filter(
        StudySession.user_id == user_id,
        StudySession.started_at >= now - timedelta(days=7)
    ).scalar() or 0

    sessions_30d = db.query(func.count(StudySession.id)).filter(
        StudySession.user_id == user_id,
        StudySession.started_at >= now - timedelta(days=30)
    ).scalar() or 0

    # Last activity
    last_attempt = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id
    ).order_by(QuestionAttempt.attempted_at.desc()).first()

    first_attempt = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id
    ).order_by(QuestionAttempt.attempted_at.asc()).first()

    days_since_last = None
    if last_attempt:
        days_since_last = (now - last_attempt.attempted_at).days

    # Calculate engagement status and score
    if days_since_last is None:
        status = "new"
        score = 0
    elif days_since_last <= 3 and questions_7d >= 5:
        status = "active"
        score = 80 + min(questions_7d, 20)
    elif days_since_last <= 7:
        status = "active"
        score = 60 + min(questions_7d * 2, 20)
    elif days_since_last <= 14:
        status = "at_risk"
        score = 30 + min(questions_30d, 20)
    else:
        status = "churned"
        score = max(0, 30 - days_since_last)

    # Churn risk factors
    risk_factors = []
    if days_since_last and days_since_last > 5:
        risk_factors.append(f"no_activity_{days_since_last}_days")
    if questions_7d < 3:
        risk_factors.append("low_weekly_activity")
    if sessions_7d == 0:
        risk_factors.append("no_sessions_this_week")

    return {
        "user_id": user_id,
        "email": user.email,
        "full_name": user.full_name,
        "engagement_status": status,
        "engagement_score": min(100, score),
        "questions_last_7_days": questions_7d,
        "questions_last_30_days": questions_30d,
        "sessions_last_7_days": sessions_7d,
        "sessions_last_30_days": sessions_30d,
        "days_since_last_activity": days_since_last,
        "first_activity_at": first_attempt.attempted_at.isoformat() if first_attempt else None,
        "last_activity_at": last_attempt.attempted_at.isoformat() if last_attempt else None,
        "churn_risk_score": round(1.0 - (score / 100), 2),
        "churn_risk_factors": risk_factors
    }


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def run_daily_metrics_batch(db: Session) -> Dict[str, Any]:
    """Run daily batch job to compute and store platform metrics."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    # Check if already computed today
    existing = db.query(DailyPlatformMetrics).filter(
        DailyPlatformMetrics.date == today
    ).first()

    if existing:
        metrics = existing
    else:
        metrics = DailyPlatformMetrics(date=today)
        db.add(metrics)

    # Compute metrics
    metrics.dau = _count_active_users(db, days=1)
    metrics.wau = _count_active_users(db, days=7)
    metrics.mau = _count_active_users(db, days=30)

    # Sessions from yesterday
    sessions = db.query(StudySession).filter(
        StudySession.started_at >= yesterday,
        StudySession.started_at < today
    ).all()
    metrics.total_sessions = len(sessions)
    metrics.avg_session_duration_seconds = sum(
        (s.time_spent_seconds or 0) for s in sessions
    ) / max(len(sessions), 1)

    # Questions answered yesterday
    metrics.total_questions_answered = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.attempted_at >= yesterday,
        QuestionAttempt.attempted_at < today
    ).scalar() or 0

    # AI chats yesterday
    metrics.total_ai_chats = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.created_at >= yesterday,
        ChatMessage.created_at < today,
        ChatMessage.role == "user"
    ).scalar() or 0

    # New signups yesterday
    metrics.new_signups = db.query(func.count(User.id)).filter(
        User.created_at >= yesterday,
        User.created_at < today
    ).scalar() or 0

    # Feature usage breakdown
    mode_usage = db.query(
        StudySession.mode,
        func.count(StudySession.id).label('count')
    ).filter(
        StudySession.started_at >= yesterday,
        StudySession.started_at < today
    ).group_by(StudySession.mode).all()
    metrics.feature_usage = {row.mode: row.count for row in mode_usage if row.mode}

    metrics.updated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "success",
        "date": today.isoformat(),
        "metrics": {
            "dau": metrics.dau,
            "wau": metrics.wau,
            "mau": metrics.mau,
            "total_sessions": metrics.total_sessions,
            "questions_answered": metrics.total_questions_answered,
            "new_signups": metrics.new_signups
        }
    }


def run_user_engagement_batch(db: Session) -> Dict[str, Any]:
    """Batch update all user engagement scores."""
    users = db.query(User).all()
    updated = 0
    now = datetime.utcnow()

    for user in users:
        engagement = calculate_user_engagement_score(db, user.id)

        if "error" in engagement:
            continue

        # Upsert engagement score
        existing = db.query(UserEngagementScore).filter(
            UserEngagementScore.user_id == user.id
        ).first()

        if existing:
            existing.engagement_status = engagement["engagement_status"]
            existing.engagement_score = engagement["engagement_score"]
            existing.questions_last_7_days = engagement["questions_last_7_days"]
            existing.questions_last_30_days = engagement["questions_last_30_days"]
            existing.sessions_last_7_days = engagement["sessions_last_7_days"]
            existing.sessions_last_30_days = engagement["sessions_last_30_days"]
            existing.days_since_last_activity = engagement["days_since_last_activity"]
            existing.churn_risk_score = engagement["churn_risk_score"]
            existing.churn_risk_factors = engagement["churn_risk_factors"]
            existing.first_activity_at = datetime.fromisoformat(engagement["first_activity_at"]) if engagement["first_activity_at"] else None
            existing.last_activity_at = datetime.fromisoformat(engagement["last_activity_at"]) if engagement["last_activity_at"] else None
            existing.calculated_at = now
        else:
            score = UserEngagementScore(
                user_id=user.id,
                engagement_status=engagement["engagement_status"],
                engagement_score=engagement["engagement_score"],
                questions_last_7_days=engagement["questions_last_7_days"],
                questions_last_30_days=engagement["questions_last_30_days"],
                sessions_last_7_days=engagement["sessions_last_7_days"],
                sessions_last_30_days=engagement["sessions_last_30_days"],
                days_since_last_activity=engagement["days_since_last_activity"],
                churn_risk_score=engagement["churn_risk_score"],
                churn_risk_factors=engagement["churn_risk_factors"],
                first_activity_at=datetime.fromisoformat(engagement["first_activity_at"]) if engagement["first_activity_at"] else None,
                last_activity_at=datetime.fromisoformat(engagement["last_activity_at"]) if engagement["last_activity_at"] else None,
                calculated_at=now
            )
            db.add(score)

        updated += 1

    db.commit()

    # Get distribution summary
    distribution = get_user_health_distribution(db)

    return {
        "status": "success",
        "users_processed": updated,
        "distribution": distribution["distribution"]
    }


def run_cohort_retention_batch(db: Session, weeks_back: int = 12) -> Dict[str, Any]:
    """Update cohort retention table."""
    cohorts = calculate_cohort_retention(db, weeks_back)

    updated = 0
    for cohort in cohorts:
        cohort_week = datetime.strptime(cohort["cohort_week"], "%Y-%m-%d")

        for retention in cohort["retention"]:
            # Check if exists
            existing = db.query(CohortRetention).filter(
                CohortRetention.cohort_week == cohort_week,
                CohortRetention.week_number == retention["week"]
            ).first()

            if existing:
                existing.retained_users = retention["retained"]
                existing.retention_rate = retention["rate"]
                existing.updated_at = datetime.utcnow()
            else:
                record = CohortRetention(
                    cohort_week=cohort_week,
                    week_number=retention["week"],
                    cohort_size=cohort["cohort_size"],
                    retained_users=retention["retained"],
                    retention_rate=retention["rate"]
                )
                db.add(record)

            updated += 1

    db.commit()

    return {
        "status": "success",
        "cohorts_processed": len(cohorts),
        "records_updated": updated
    }


def get_historical_metrics(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """Get historical daily metrics for charting."""
    start_date = datetime.utcnow() - timedelta(days=days)

    metrics = db.query(DailyPlatformMetrics).filter(
        DailyPlatformMetrics.date >= start_date
    ).order_by(DailyPlatformMetrics.date).all()

    return [
        {
            "date": m.date.strftime("%Y-%m-%d"),
            "dau": m.dau,
            "wau": m.wau,
            "mau": m.mau,
            "total_sessions": m.total_sessions,
            "questions_answered": m.total_questions_answered,
            "new_signups": m.new_signups
        }
        for m in metrics
    ]
