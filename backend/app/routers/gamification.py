"""
Gamification API Router.
Endpoints for streaks, badges, achievements, and leaderboards.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.services.streak_service import get_streak_service
from app.services.badge_service import get_badge_service, BADGE_DEFINITIONS

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class StreakData(BaseModel):
    current_streak: int
    best_streak: int
    studied_today: bool
    streak_at_risk: bool
    last_activity_at: Optional[str] = None
    next_milestone: Optional[int] = None
    current_milestone: Optional[int] = None
    days_to_next_milestone: Optional[int] = None

    class Config:
        from_attributes = True


class StreakCelebration(BaseModel):
    type: str  # "first_question", "new_best", "milestone", "streak_restart"
    message: str
    days: Optional[int] = None


class StreakUpdateResponse(BaseModel):
    current_streak: int
    best_streak: int
    streak_increased: bool
    new_best: bool
    celebrations: List[StreakCelebration]


class LeaderboardEntry(BaseModel):
    rank: int
    first_name: str
    current_streak: int
    best_streak: int


class StreakLeaderboardResponse(BaseModel):
    top_streaks: List[LeaderboardEntry]
    user_rank: Optional[int] = None
    user_streak: Optional[int] = None


class BadgeInfo(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    category: str
    earned: bool
    earned_at: Optional[str] = None
    progress: Optional[float] = None  # 0-1 for unearned badges
    requirements: Optional[Dict[str, Any]] = None


class BadgesResponse(BaseModel):
    earned: List[BadgeInfo]
    in_progress: List[BadgeInfo]
    total_earned: int
    total_available: int


# ============================================================================
# STREAK ENDPOINTS
# ============================================================================

@router.get("/streaks", response_model=StreakData)
async def get_streak_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's streak data."""
    streak_service = get_streak_service()
    return streak_service.get_streak_data(db, current_user.id)


@router.get("/streaks/leaderboard", response_model=StreakLeaderboardResponse)
async def get_streak_leaderboard(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get streak leaderboard with top users."""
    if limit < 1 or limit > 50:
        limit = 10

    streak_service = get_streak_service()
    return streak_service.get_streak_leaderboard(db, limit=limit, user_id=current_user.id)


# ============================================================================
# BADGE ENDPOINTS (Placeholder for Achievement Badges feature)
# ============================================================================

@router.get("/badges", response_model=BadgesResponse)
async def get_user_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's badges and progress."""
    badge_service = get_badge_service()
    result = badge_service.get_user_badges(db, current_user.id)

    return BadgesResponse(
        earned=[BadgeInfo(**b) for b in result["earned"]],
        in_progress=[BadgeInfo(**b) for b in result["in_progress"]],
        total_earned=result["total_earned"],
        total_available=result["total_available"]
    )


@router.get("/badges/all")
async def get_all_badges():
    """Get all available badge definitions."""
    badge_service = get_badge_service()
    return {"badges": badge_service.get_all_badges()}


@router.post("/badges/check")
async def check_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger badge check for current user.
    Returns any newly awarded badges.
    """
    badge_service = get_badge_service()
    newly_awarded = badge_service.check_and_award_badges(db, current_user.id)

    return {
        "newly_awarded": newly_awarded,
        "count": len(newly_awarded)
    }


@router.get("/summary")
async def get_gamification_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive gamification summary for the user.
    Combines streaks, badges, and other achievements.
    """
    streak_service = get_streak_service()
    streak_data = streak_service.get_streak_data(db, current_user.id)

    return {
        "streaks": streak_data,
        "badges": {
            "total_earned": 0,
            "recent": []
        },
        "motivational_message": _get_motivational_message(streak_data)
    }


def _get_motivational_message(streak_data: dict) -> str:
    """Generate a motivational message based on streak data."""
    streak = streak_data.get("current_streak", 0)
    studied_today = streak_data.get("studied_today", False)
    at_risk = streak_data.get("streak_at_risk", False)

    if at_risk:
        return f"Don't break your {streak} day streak! Study now to keep it going."
    elif not studied_today and streak == 0:
        return "Start a new streak today! Every journey begins with a single step."
    elif not studied_today:
        return "Keep your momentum! Continue your streak with a quick study session."
    elif streak >= 30:
        return f"Incredible! {streak} days of consistent learning. You're unstoppable!"
    elif streak >= 14:
        return f"{streak} day streak! Your dedication is paying off."
    elif streak >= 7:
        return f"One week strong! {streak} days and counting."
    elif streak >= 3:
        return f"{streak} days in a row. Great start, keep building!"
    else:
        return "Great job studying today! Come back tomorrow to build your streak."
