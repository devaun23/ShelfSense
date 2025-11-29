"""
Subscription Router

API endpoints for subscription management, feature gating, and usage tracking.

SECURITY: All user-specific endpoints require authentication and IDOR protection.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.database import get_db
from app.models.models import User
from app.dependencies.auth import get_current_user, verify_user_access
from app.services.subscription import (
    get_subscription_status,
    get_available_plans,
    get_remaining_usage,
    upgrade_subscription,
    cancel_subscription,
    start_trial,
    can_answer_question,
    can_send_chat_message,
    can_access_specialty,
    can_access_feature,
    get_user_tier
)


router = APIRouter(prefix="/api/subscription", tags=["subscription"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class UpgradeRequest(BaseModel):
    tier: str
    billing_cycle: str = "monthly"  # "monthly" or "yearly"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = None


class FeatureCheckRequest(BaseModel):
    feature: str


class SpecialtyCheckRequest(BaseModel):
    specialty: str


# =============================================================================
# SUBSCRIPTION STATUS ENDPOINTS
# =============================================================================

@router.get("/status")
def get_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive subscription status for a user.

    SECURITY: Requires authentication. Users can only access their own data.

    Returns:
        - Current tier
        - Active features
        - Usage limits and remaining
        - Billing information
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        status = get_subscription_status(db, user_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching subscription status: {str(e)}")


@router.get("/plans")
def get_plans():
    """
    Get list of available subscription plans.

    Returns:
        List of plans with pricing and features.
    """
    return get_available_plans()


@router.get("/usage")
def get_usage(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current daily usage and remaining limits.

    SECURITY: Requires authentication. Users can only access their own data.

    Returns:
        - Questions used/remaining
        - Chat messages used/remaining
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        usage = get_remaining_usage(db, user_id)
        return usage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching usage: {str(e)}")


@router.get("/tier")
def get_tier(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current subscription tier.

    SECURITY: Requires authentication. Users can only access their own data.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        tier = get_user_tier(db, user_id)
        return {"tier": tier}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tier: {str(e)}")


# =============================================================================
# SUBSCRIPTION MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/upgrade")
def upgrade(
    user_id: str,
    request: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upgrade user's subscription to a new tier.

    SECURITY: Requires authentication. Users can only modify their own subscription.

    Note: In production, this would integrate with Stripe for payment processing.
    Currently accepts the upgrade directly for testing purposes.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    valid_tiers = ["student", "premium"]
    if request.tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )

    valid_cycles = ["monthly", "yearly"]
    if request.billing_cycle not in valid_cycles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid billing cycle. Must be one of: {valid_cycles}"
        )

    try:
        subscription = upgrade_subscription(
            db,
            user_id,
            request.tier,
            request.billing_cycle,
            request.stripe_customer_id,
            request.stripe_subscription_id
        )

        return {
            "success": True,
            "message": f"Successfully upgraded to {request.tier} tier",
            "subscription": get_subscription_status(db, user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error upgrading subscription: {str(e)}")


@router.post("/cancel")
def cancel(
    user_id: str,
    request: CancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel user's subscription.

    SECURITY: Requires authentication. Users can only cancel their own subscription.

    The subscription remains active until the end of the billing period,
    then downgrades to free tier.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        subscription = cancel_subscription(db, user_id, request.reason)

        return {
            "success": True,
            "message": "Subscription cancelled. You'll retain access until the end of your billing period.",
            "subscription": get_subscription_status(db, user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling subscription: {str(e)}")


@router.post("/start-trial")
def trial(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a 7-day free trial of the Student tier.

    SECURITY: Requires authentication. Users can only start trial for themselves.

    Users can only use one trial per account.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        subscription = start_trial(db, user_id)

        return {
            "success": True,
            "message": "7-day free trial started! Enjoy full access to all features.",
            "subscription": get_subscription_status(db, user_id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting trial: {str(e)}")


# =============================================================================
# FEATURE GATING ENDPOINTS
# =============================================================================

@router.get("/can-answer-question")
def check_can_answer(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user can answer another question today.

    SECURITY: Requires authentication. Users can only check their own permissions.

    Returns:
        - allowed: boolean
        - reason: why not allowed (if applicable)
        - upgrade_message: CTA for upgrade (if limit reached)
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        result = can_answer_question(db, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking permission: {str(e)}")


@router.get("/can-send-chat")
def check_can_chat(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user can send another AI chat message today.

    SECURITY: Requires authentication. Users can only check their own permissions.

    Returns:
        - allowed: boolean
        - reason: why not allowed (if applicable)
        - upgrade_message: CTA for upgrade (if limit reached)
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        result = can_send_chat_message(db, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking permission: {str(e)}")


@router.post("/can-access-specialty")
def check_specialty_access(
    user_id: str,
    request: SpecialtyCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user can access a specific specialty.

    SECURITY: Requires authentication. Users can only check their own permissions.

    Returns:
        - allowed: boolean
        - reason: why not allowed (if applicable)
        - upgrade_message: CTA for upgrade (if locked)
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        result = can_access_specialty(db, user_id, request.specialty)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking specialty access: {str(e)}")


@router.post("/can-access-feature")
def check_feature_access(
    user_id: str,
    request: FeatureCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user can access a specific feature.

    SECURITY: Requires authentication. Users can only check their own permissions.

    Available features:
        - spaced_repetition
        - error_analysis
        - predicted_score
        - advanced_analytics
        - priority_ai
        - study_plans
        - weekly_reports
        - test_simulation

    Returns:
        - allowed: boolean
        - reason: why not allowed (if applicable)
        - upgrade_message: CTA for upgrade (if locked)
    """
    # IDOR protection
    verify_user_access(current_user, user_id)

    try:
        result = can_access_feature(db, user_id, request.feature)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking feature access: {str(e)}")


# =============================================================================
# PRICING ENDPOINTS
# =============================================================================

@router.get("/pricing")
def get_pricing():
    """
    Get pricing information for all tiers.

    Useful for displaying on a pricing page.
    """
    plans = get_available_plans()

    return {
        "currency": "USD",
        "plans": plans,
        "trial_available": True,
        "trial_days": 7,
        "money_back_guarantee_days": 30
    }
