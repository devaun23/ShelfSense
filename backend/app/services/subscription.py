"""
Subscription Service

Manages user subscriptions, tier limits, and feature gating.
Implements the ShelfSense monetization model.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Subscription, DailyUsage, User


# =============================================================================
# TIER CONFIGURATION
# =============================================================================

TIER_LIMITS = {
    "free": {
        "daily_questions": 20,
        "ai_chat_messages": 5,
        "specialties": ["Internal Medicine"],  # Only 1 specialty for free tier
        "analytics": "basic",
        "spaced_repetition": False,
        "error_analysis": False,
        "predicted_score": False,
        "price_monthly": 0,
        "price_yearly": 0
    },
    "student": {
        "daily_questions": float('inf'),
        "ai_chat_messages": float('inf'),
        "specialties": "all",
        "analytics": "advanced",
        "spaced_repetition": True,
        "error_analysis": True,
        "predicted_score": True,
        "price_monthly": 29,
        "price_yearly": 199
    },
    "premium": {
        "daily_questions": float('inf'),
        "ai_chat_messages": float('inf'),
        "specialties": "all",
        "analytics": "advanced",
        "spaced_repetition": True,
        "error_analysis": True,
        "predicted_score": True,
        "priority_ai": True,
        "study_plans": True,
        "weekly_reports": True,
        "test_simulation": True,
        "price_monthly": 49,
        "price_yearly": 349
    }
}

# Specialties available to all tiers
ALL_SPECIALTIES = [
    "Internal Medicine",
    "Surgery",
    "Pediatrics",
    "Psychiatry",
    "Obstetrics and Gynecology",
    "Family Medicine",
    "Emergency Medicine",
    "Preventive Medicine"
]

# Free tier specialty limit (only 1 specialty)
FREE_SPECIALTIES = ["Internal Medicine"]


# =============================================================================
# SUBSCRIPTION MANAGEMENT
# =============================================================================

def get_or_create_subscription(db: Session, user_id: str) -> Subscription:
    """Get user's subscription or create free tier if none exists."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription:
        subscription = Subscription(
            user_id=user_id,
            tier="free",
            started_at=datetime.utcnow()
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

    return subscription


def get_user_tier(db: Session, user_id: str) -> str:
    """Get user's current subscription tier."""
    subscription = get_or_create_subscription(db, user_id)

    # Check if subscription has expired
    if subscription.expires_at and subscription.expires_at < datetime.utcnow():
        # Downgrade to free tier
        subscription.tier = "free"
        subscription.expires_at = None
        db.commit()

    return subscription.tier


def get_tier_limits(tier: str) -> Dict[str, Any]:
    """Get limits for a specific tier."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


def upgrade_subscription(
    db: Session,
    user_id: str,
    new_tier: str,
    billing_cycle: str = "monthly",
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None
) -> Subscription:
    """Upgrade user's subscription to a new tier."""
    subscription = get_or_create_subscription(db, user_id)

    subscription.tier = new_tier
    subscription.billing_cycle = billing_cycle
    subscription.started_at = datetime.utcnow()

    # Set expiration based on billing cycle
    if billing_cycle == "monthly":
        subscription.expires_at = datetime.utcnow() + timedelta(days=30)
    elif billing_cycle == "yearly":
        subscription.expires_at = datetime.utcnow() + timedelta(days=365)

    # Store Stripe IDs if provided
    if stripe_customer_id:
        subscription.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        subscription.stripe_subscription_id = stripe_subscription_id

    subscription.cancelled_at = None
    subscription.cancel_reason = None

    db.commit()
    db.refresh(subscription)

    return subscription


def cancel_subscription(
    db: Session,
    user_id: str,
    reason: Optional[str] = None
) -> Subscription:
    """Cancel user's subscription (downgrade to free at end of period)."""
    subscription = get_or_create_subscription(db, user_id)

    subscription.cancelled_at = datetime.utcnow()
    subscription.cancel_reason = reason

    db.commit()
    db.refresh(subscription)

    return subscription


def start_trial(db: Session, user_id: str, trial_days: int = 7) -> Subscription:
    """Start a free trial of premium features."""
    subscription = get_or_create_subscription(db, user_id)

    if subscription.has_used_trial:
        raise ValueError("User has already used their free trial")

    subscription.tier = "student"  # Trial gives student tier
    subscription.trial_started_at = datetime.utcnow()
    subscription.trial_ends_at = datetime.utcnow() + timedelta(days=trial_days)
    subscription.expires_at = subscription.trial_ends_at
    subscription.has_used_trial = True

    db.commit()
    db.refresh(subscription)

    return subscription


# =============================================================================
# USAGE TRACKING
# =============================================================================

def get_or_create_daily_usage(db: Session, user_id: str) -> DailyUsage:
    """Get or create today's usage record for a user."""
    today = datetime.utcnow().date()

    usage = db.query(DailyUsage).filter(
        DailyUsage.user_id == user_id,
        func.date(DailyUsage.date) == today
    ).first()

    if not usage:
        usage = DailyUsage(
            user_id=user_id,
            date=datetime.utcnow()
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)

    return usage


def increment_question_count(db: Session, user_id: str) -> int:
    """Increment daily question count and return new total."""
    usage = get_or_create_daily_usage(db, user_id)
    usage.questions_answered += 1
    db.commit()
    return usage.questions_answered


def increment_chat_count(db: Session, user_id: str) -> int:
    """Increment daily chat message count and return new total."""
    usage = get_or_create_daily_usage(db, user_id)
    usage.ai_chat_messages += 1
    db.commit()
    return usage.ai_chat_messages


def get_remaining_usage(db: Session, user_id: str) -> Dict[str, Any]:
    """Get user's remaining usage for today."""
    tier = get_user_tier(db, user_id)
    limits = get_tier_limits(tier)
    usage = get_or_create_daily_usage(db, user_id)

    daily_question_limit = limits["daily_questions"]
    daily_chat_limit = limits["ai_chat_messages"]

    return {
        "tier": tier,
        "questions": {
            "used": usage.questions_answered,
            "limit": daily_question_limit if daily_question_limit != float('inf') else -1,
            "remaining": max(0, daily_question_limit - usage.questions_answered) if daily_question_limit != float('inf') else -1,
            "unlimited": daily_question_limit == float('inf')
        },
        "chat_messages": {
            "used": usage.ai_chat_messages,
            "limit": daily_chat_limit if daily_chat_limit != float('inf') else -1,
            "remaining": max(0, daily_chat_limit - usage.ai_chat_messages) if daily_chat_limit != float('inf') else -1,
            "unlimited": daily_chat_limit == float('inf')
        }
    }


# =============================================================================
# FEATURE GATING
# =============================================================================

def can_answer_question(db: Session, user_id: str) -> Dict[str, Any]:
    """Check if user can answer another question today."""
    tier = get_user_tier(db, user_id)
    limits = get_tier_limits(tier)
    usage = get_or_create_daily_usage(db, user_id)

    daily_limit = limits["daily_questions"]

    if daily_limit == float('inf'):
        return {"allowed": True, "reason": None}

    if usage.questions_answered >= daily_limit:
        return {
            "allowed": False,
            "reason": "daily_limit_reached",
            "limit": daily_limit,
            "used": usage.questions_answered,
            "upgrade_message": f"You've reached your daily limit of {daily_limit} questions. Upgrade to Student for unlimited questions."
        }

    return {"allowed": True, "reason": None}


def can_send_chat_message(db: Session, user_id: str) -> Dict[str, Any]:
    """Check if user can send another AI chat message today."""
    tier = get_user_tier(db, user_id)
    limits = get_tier_limits(tier)
    usage = get_or_create_daily_usage(db, user_id)

    daily_limit = limits["ai_chat_messages"]

    if daily_limit == float('inf'):
        return {"allowed": True, "reason": None}

    if usage.ai_chat_messages >= daily_limit:
        return {
            "allowed": False,
            "reason": "daily_limit_reached",
            "limit": daily_limit,
            "used": usage.ai_chat_messages,
            "upgrade_message": f"You've reached your daily limit of {daily_limit} AI chat messages. Upgrade for unlimited chat."
        }

    return {"allowed": True, "reason": None}


def can_access_specialty(db: Session, user_id: str, specialty: str) -> Dict[str, Any]:
    """Check if user can access a specific specialty."""
    tier = get_user_tier(db, user_id)
    limits = get_tier_limits(tier)

    allowed_specialties = limits["specialties"]

    if allowed_specialties == "all":
        return {"allowed": True, "reason": None}

    if specialty in allowed_specialties:
        return {"allowed": True, "reason": None}

    return {
        "allowed": False,
        "reason": "specialty_locked",
        "specialty": specialty,
        "allowed_specialties": allowed_specialties,
        "upgrade_message": f"{specialty} is only available with a Student or Premium subscription."
    }


def can_access_feature(db: Session, user_id: str, feature: str) -> Dict[str, Any]:
    """Check if user can access a specific feature."""
    tier = get_user_tier(db, user_id)
    limits = get_tier_limits(tier)

    feature_map = {
        "spaced_repetition": limits.get("spaced_repetition", False),
        "error_analysis": limits.get("error_analysis", False),
        "predicted_score": limits.get("predicted_score", False),
        "advanced_analytics": limits.get("analytics") == "advanced",
        "priority_ai": limits.get("priority_ai", False),
        "study_plans": limits.get("study_plans", False),
        "weekly_reports": limits.get("weekly_reports", False),
        "test_simulation": limits.get("test_simulation", False)
    }

    if feature not in feature_map:
        return {"allowed": True, "reason": None}  # Unknown feature, allow by default

    if feature_map[feature]:
        return {"allowed": True, "reason": None}

    feature_names = {
        "spaced_repetition": "Spaced Repetition",
        "error_analysis": "Error Analysis",
        "predicted_score": "Score Prediction",
        "advanced_analytics": "Advanced Analytics",
        "priority_ai": "Priority AI Generation",
        "study_plans": "Personalized Study Plans",
        "weekly_reports": "Weekly Progress Reports",
        "test_simulation": "Test Simulation Mode"
    }

    return {
        "allowed": False,
        "reason": "feature_locked",
        "feature": feature,
        "feature_name": feature_names.get(feature, feature),
        "upgrade_message": f"{feature_names.get(feature, feature)} requires a paid subscription."
    }


# =============================================================================
# SUBSCRIPTION INFO
# =============================================================================

def get_subscription_status(db: Session, user_id: str) -> Dict[str, Any]:
    """Get comprehensive subscription status for a user."""
    subscription = get_or_create_subscription(db, user_id)
    tier = get_user_tier(db, user_id)
    limits = get_tier_limits(tier)
    usage = get_remaining_usage(db, user_id)

    # Check if on trial
    is_trial = (
        subscription.trial_ends_at is not None and
        subscription.trial_ends_at > datetime.utcnow()
    )

    # Calculate days remaining
    days_remaining = None
    if subscription.expires_at:
        delta = subscription.expires_at - datetime.utcnow()
        days_remaining = max(0, delta.days)

    return {
        "tier": tier,
        "is_active": tier != "free",
        "is_trial": is_trial,
        "trial_days_remaining": (subscription.trial_ends_at - datetime.utcnow()).days if is_trial else None,
        "billing_cycle": subscription.billing_cycle,
        "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
        "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        "days_remaining": days_remaining,
        "is_cancelled": subscription.cancelled_at is not None,
        "can_start_trial": not subscription.has_used_trial,
        "usage": usage,
        "features": {
            "daily_questions": limits["daily_questions"] if limits["daily_questions"] != float('inf') else "unlimited",
            "ai_chat_messages": limits["ai_chat_messages"] if limits["ai_chat_messages"] != float('inf') else "unlimited",
            "specialties": limits["specialties"] if limits["specialties"] == "all" else len(limits["specialties"]),
            "analytics": limits["analytics"],
            "spaced_repetition": limits.get("spaced_repetition", False),
            "error_analysis": limits.get("error_analysis", False),
            "predicted_score": limits.get("predicted_score", False),
            "priority_ai": limits.get("priority_ai", False),
            "study_plans": limits.get("study_plans", False),
            "weekly_reports": limits.get("weekly_reports", False),
            "test_simulation": limits.get("test_simulation", False)
        }
    }


def get_available_plans() -> List[Dict[str, Any]]:
    """Get list of available subscription plans."""
    return [
        {
            "tier": "free",
            "name": "Free",
            "description": "Get started with basic features",
            "price_monthly": 0,
            "price_yearly": 0,
            "features": [
                "20 questions per day",
                "5 AI chat messages per day",
                "1 specialty (Internal Medicine)",
                "Basic analytics"
            ],
            "limitations": [
                "No spaced repetition",
                "No error analysis",
                "No score prediction"
            ]
        },
        {
            "tier": "student",
            "name": "Student",
            "description": "Everything you need to ace Step 2 CK",
            "price_monthly": 29,
            "price_yearly": 199,
            "yearly_savings": 149,
            "features": [
                "Unlimited questions",
                "Unlimited AI chat",
                "All 8 specialties",
                "Advanced analytics dashboard",
                "Full spaced repetition system",
                "Predicted score tracking",
                "Error analysis"
            ],
            "popular": True
        },
        {
            "tier": "premium",
            "name": "Premium",
            "description": "Maximum preparation with premium features",
            "price_monthly": 49,
            "price_yearly": 349,
            "yearly_savings": 239,
            "features": [
                "Everything in Student",
                "Priority AI generation",
                "Personalized study plans",
                "Weekly progress reports",
                "Test simulation mode",
                "Priority support"
            ]
        }
    ]
