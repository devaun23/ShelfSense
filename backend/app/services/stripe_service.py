"""
Stripe Service

Handles Stripe API interactions for payment processing:
- Customer management
- Checkout session creation
- Customer portal sessions
- Subscription synchronization from webhooks
"""

import os
import stripe
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.models import Subscription, User

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Price ID mapping from environment
PRICE_IDS = {
    "student": {
        "monthly": os.getenv("STRIPE_PRICE_STUDENT_MONTHLY"),
        "yearly": os.getenv("STRIPE_PRICE_STUDENT_YEARLY"),
    },
    "premium": {
        "monthly": os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY"),
        "yearly": os.getenv("STRIPE_PRICE_PREMIUM_YEARLY"),
    }
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Grace period configuration
GRACE_PERIOD_DAYS = 7


def get_price_id(tier: str, billing_cycle: str) -> Optional[str]:
    """Get Stripe price ID for a tier and billing cycle."""
    return PRICE_IDS.get(tier, {}).get(billing_cycle)


def get_tier_from_price_id(price_id: str) -> Tuple[str, str]:
    """
    Reverse lookup: get tier and billing cycle from price ID.
    Returns ("free", None) if not found.
    """
    for tier, cycles in PRICE_IDS.items():
        for cycle, pid in cycles.items():
            if pid == price_id:
                return tier, cycle
    return "free", None


def get_or_create_customer(
    db: Session,
    user: User,
    subscription: Subscription
) -> str:
    """
    Get existing Stripe customer or create a new one.
    Returns the Stripe customer ID.
    """
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id

    # Create new Stripe customer
    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name,
        metadata={
            "user_id": user.id,
            "platform": "shelfsense"
        }
    )

    # Store customer ID
    subscription.stripe_customer_id = customer.id
    db.commit()

    return customer.id


def create_checkout_session(
    db: Session,
    user: User,
    subscription: Subscription,
    tier: str,
    billing_cycle: str
) -> Dict[str, Any]:
    """
    Create a Stripe Checkout session for subscription purchase.
    Returns dict with checkout_url and session_id.
    """
    price_id = get_price_id(tier, billing_cycle)
    if not price_id:
        raise ValueError(f"Invalid tier/billing_cycle: {tier}/{billing_cycle}")

    customer_id = get_or_create_customer(db, user, subscription)

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{
            "price": price_id,
            "quantity": 1,
        }],
        success_url=f"{FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/subscription/cancel",
        metadata={
            "user_id": user.id,
            "tier": tier,
            "billing_cycle": billing_cycle,
        },
        subscription_data={
            "metadata": {
                "user_id": user.id,
                "tier": tier,
            }
        },
        allow_promotion_codes=True,
        billing_address_collection="auto",
    )

    return {
        "checkout_url": checkout_session.url,
        "session_id": checkout_session.id,
    }


def create_portal_session(customer_id: str) -> Dict[str, Any]:
    """
    Create a Stripe Customer Portal session.
    Allows users to manage subscription, update payment method, etc.
    """
    if not customer_id:
        raise ValueError("No Stripe customer ID found")

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL}/settings",
    )

    return {
        "portal_url": portal_session.url,
    }


def sync_subscription_from_stripe(
    db: Session,
    stripe_subscription: stripe.Subscription,
) -> Optional[Subscription]:
    """
    Synchronize local subscription state from Stripe subscription object.
    Called from webhook handlers to keep database in sync.
    """
    user_id = stripe_subscription.metadata.get("user_id")
    if not user_id:
        return None

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription:
        return None

    # Get tier from price ID
    price_id = stripe_subscription["items"]["data"][0].price.id
    tier, billing_cycle = get_tier_from_price_id(price_id)

    # Update subscription fields
    subscription.stripe_subscription_id = stripe_subscription.id
    subscription.stripe_status = stripe_subscription.status
    subscription.stripe_price_id = price_id
    subscription.billing_cycle = billing_cycle

    # Update expiration
    subscription.expires_at = datetime.fromtimestamp(
        stripe_subscription.current_period_end
    )

    # Handle status-based updates
    if stripe_subscription.status in ["active", "trialing"]:
        subscription.tier = tier
        subscription.payment_status = "ok"
        subscription.grace_period_ends_at = None
    elif stripe_subscription.status == "past_due":
        # Keep tier but mark payment as past_due
        subscription.payment_status = "past_due"
        if not subscription.grace_period_ends_at:
            subscription.grace_period_ends_at = datetime.utcnow() + timedelta(days=GRACE_PERIOD_DAYS)
    elif stripe_subscription.status in ["canceled", "unpaid"]:
        subscription.tier = "free"
        subscription.payment_status = "failed"

    # Handle cancellation state
    if stripe_subscription.cancel_at_period_end:
        if not subscription.cancelled_at:
            subscription.cancelled_at = datetime.utcnow()
    else:
        # Reactivated
        subscription.cancelled_at = None
        subscription.cancel_reason = None

    db.commit()
    db.refresh(subscription)

    return subscription


def handle_checkout_completed(
    db: Session,
    session: stripe.checkout.Session
) -> Optional[Subscription]:
    """
    Handle successful checkout completion.
    Retrieves the subscription and syncs state.
    """
    if session.mode != "subscription":
        return None

    subscription_id = session.subscription
    if not subscription_id:
        return None

    # Retrieve the full subscription from Stripe
    stripe_subscription = stripe.Subscription.retrieve(subscription_id)

    return sync_subscription_from_stripe(db, stripe_subscription)


def handle_subscription_deleted(
    db: Session,
    stripe_subscription: stripe.Subscription
) -> Optional[Subscription]:
    """
    Handle subscription cancellation/deletion.
    Downgrades user to free tier.
    """
    user_id = stripe_subscription.metadata.get("user_id")
    if not user_id:
        return None

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if subscription:
        subscription.tier = "free"
        subscription.stripe_status = "canceled"
        subscription.payment_status = "failed"
        subscription.stripe_subscription_id = None
        subscription.expires_at = None
        subscription.cancelled_at = datetime.utcnow()
        db.commit()
        db.refresh(subscription)

    return subscription


def handle_invoice_payment_failed(
    db: Session,
    invoice: stripe.Invoice
) -> Optional[Subscription]:
    """
    Handle failed payment.
    Starts grace period if not already started.
    """
    subscription_id = invoice.subscription
    if not subscription_id:
        return None

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()

    if subscription:
        subscription.payment_status = "past_due"

        # Start grace period if not already started
        if not subscription.grace_period_ends_at:
            subscription.grace_period_ends_at = datetime.utcnow() + timedelta(days=GRACE_PERIOD_DAYS)

        db.commit()
        db.refresh(subscription)

    return subscription


def handle_invoice_payment_succeeded(
    db: Session,
    invoice: stripe.Invoice
) -> Optional[Subscription]:
    """
    Handle successful payment.
    Clears grace period and confirms active status.
    """
    subscription_id = invoice.subscription
    if not subscription_id:
        return None

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()

    if subscription:
        subscription.payment_status = "ok"
        subscription.grace_period_ends_at = None

        # Refresh expiration from Stripe
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        subscription.expires_at = datetime.fromtimestamp(stripe_sub.current_period_end)

        db.commit()
        db.refresh(subscription)

    return subscription
