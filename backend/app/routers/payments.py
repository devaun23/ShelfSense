"""
Payments Router

Handles Stripe payment endpoints:
- Create checkout sessions for subscription purchase
- Create customer portal sessions for subscription management
- Get payment/subscription status

SECURITY: All endpoints require authentication and IDOR protection.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.models import User, Subscription
from app.dependencies.auth import get_current_user, verify_user_access
from app.services.subscription import get_or_create_subscription
from app.services.stripe_service import (
    create_checkout_session,
    create_portal_session,
    get_price_id,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


# Request/Response models
class CheckoutRequest(BaseModel):
    tier: str  # "student" or "premium"
    billing_cycle: str  # "monthly" or "yearly"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    portal_url: str


class PaymentStatusResponse(BaseModel):
    tier: str
    stripe_status: Optional[str]
    payment_status: str
    billing_cycle: Optional[str]
    expires_at: Optional[str]
    cancelled_at: Optional[str]
    grace_period_ends_at: Optional[str]
    in_grace_period: bool
    days_remaining_in_grace: Optional[int]


@router.post("/create-checkout-session", response_model=CheckoutResponse)
def create_checkout(
    user_id: str,
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription purchase.
    Returns a URL to redirect the user to Stripe's hosted checkout page.

    SECURITY: Requires authentication. Users can only create sessions for themselves.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
    # Validate tier
    valid_tiers = ["student", "premium"]
    if request.tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )

    # Validate billing cycle
    valid_cycles = ["monthly", "yearly"]
    if request.billing_cycle not in valid_cycles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid billing cycle. Must be one of: {valid_cycles}"
        )

    # Validate price ID exists
    price_id = get_price_id(request.tier, request.billing_cycle)
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail="Price configuration missing. Please contact support."
        )

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create subscription
    subscription = get_or_create_subscription(db, user_id)

    # Check if user already has an active paid subscription
    if subscription.stripe_subscription_id and subscription.stripe_status == "active":
        raise HTTPException(
            status_code=400,
            detail="You already have an active subscription. Use the customer portal to manage it."
        )

    try:
        result = create_checkout_session(
            db, user, subscription, request.tier, request.billing_cycle
        )
        return CheckoutResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@router.post("/create-portal-session", response_model=PortalResponse)
def create_portal(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session.
    Allows users to manage their subscription, update payment method, etc.

    SECURITY: Requires authentication. Users can only access their own billing portal.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
    subscription = get_or_create_subscription(db, user_id)

    if not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No payment account found. Please subscribe first."
        )

    try:
        result = create_portal_session(subscription.stripe_customer_id)
        return PortalResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")


@router.get("/status", response_model=PaymentStatusResponse)
def get_payment_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current payment and subscription status.
    Includes grace period information if applicable.

    SECURITY: Requires authentication. Users can only access their own payment status.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
    subscription = get_or_create_subscription(db, user_id)

    # Calculate grace period info
    in_grace_period = False
    days_remaining = None

    if subscription.payment_status == "past_due" and subscription.grace_period_ends_at:
        from datetime import datetime
        now = datetime.utcnow()
        if now < subscription.grace_period_ends_at:
            in_grace_period = True
            days_remaining = (subscription.grace_period_ends_at - now).days

    return PaymentStatusResponse(
        tier=subscription.tier,
        stripe_status=subscription.stripe_status,
        payment_status=subscription.payment_status or "ok",
        billing_cycle=subscription.billing_cycle,
        expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        cancelled_at=subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
        grace_period_ends_at=subscription.grace_period_ends_at.isoformat() if subscription.grace_period_ends_at else None,
        in_grace_period=in_grace_period,
        days_remaining_in_grace=days_remaining,
    )


@router.get("/verify-session/{session_id}")
def verify_checkout_session(
    session_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify a checkout session completed successfully.
    Called from success page to confirm subscription activation.

    SECURITY: Requires authentication. Users can only verify their own sessions.
    """
    # IDOR protection
    verify_user_access(current_user, user_id)
    import stripe
    import os

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != "paid":
            return {
                "success": False,
                "status": session.payment_status,
                "message": "Payment not completed"
            }

        # Get updated subscription status
        subscription = get_or_create_subscription(db, user_id)

        return {
            "success": True,
            "status": "paid",
            "tier": subscription.tier,
            "billing_cycle": subscription.billing_cycle,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
