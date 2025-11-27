"""
Webhooks Router

Handles Stripe webhook events for subscription lifecycle management.
This is the source of truth for keeping local subscription state in sync with Stripe.

Events handled:
- checkout.session.completed - New subscription via checkout
- customer.subscription.created - Subscription created
- customer.subscription.updated - Subscription changed (upgrade/downgrade/renewal)
- customer.subscription.deleted - Subscription canceled/expired
- invoice.payment_succeeded - Payment successful
- invoice.payment_failed - Payment failed
"""

import os
import logging
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.database import get_db
from app.services.stripe_service import (
    handle_checkout_completed,
    sync_subscription_from_stripe,
    handle_subscription_deleted,
    handle_invoice_payment_failed,
    handle_invoice_payment_succeeded,
)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events.

    Webhook signature is verified to ensure requests are from Stripe.
    Events are processed to keep local subscription state in sync.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    if not STRIPE_WEBHOOK_SECRET:
        # In development, you might not have webhook secret configured
        logger.warning("STRIPE_WEBHOOK_SECRET not configured. Skipping signature verification.")
        try:
            event = stripe.Event.construct_from(
                stripe.util.convert_to_dict(stripe.util.json.loads(payload)),
                stripe.api_key
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info("Processing Stripe webhook: event_type=%s", event_type)

    try:
        if event_type == "checkout.session.completed":
            # New subscription via checkout
            handle_checkout_completed(db, data_object)
            logger.info("Checkout completed for session_id=%s", data_object.get('id'))

        elif event_type == "customer.subscription.created":
            # New subscription created
            sync_subscription_from_stripe(db, data_object)
            logger.info("Subscription created: subscription_id=%s", data_object.get('id'))

        elif event_type == "customer.subscription.updated":
            # Subscription updated (upgrade, downgrade, renewal, cancellation scheduled)
            sync_subscription_from_stripe(db, data_object)
            logger.info("Subscription updated: subscription_id=%s", data_object.get('id'))

        elif event_type == "customer.subscription.deleted":
            # Subscription canceled or expired
            handle_subscription_deleted(db, data_object)
            logger.info("Subscription deleted: subscription_id=%s", data_object.get('id'))

        elif event_type == "invoice.payment_succeeded":
            # Payment successful - extend subscription
            handle_invoice_payment_succeeded(db, data_object)
            logger.info("Payment succeeded for invoice_id=%s", data_object.get('id'))

        elif event_type == "invoice.payment_failed":
            # Payment failed - start grace period
            handle_invoice_payment_failed(db, data_object)
            logger.warning("Payment failed for invoice_id=%s", data_object.get('id'))

        else:
            # Log unhandled events for monitoring
            logger.debug("Unhandled Stripe event type: %s", event_type)

    except Exception as e:
        # Log error but return 200 to prevent Stripe retries for handled events
        # Stripe will retry on 5xx errors, so we only raise for critical failures
        logger.error("Webhook processing error for event_type=%s: %s", event_type, str(e), exc_info=True)
        # Don't raise - let Stripe think it succeeded to prevent infinite retries
        # Error is captured by Sentry via exc_info=True

    return {"status": "success", "event_type": event_type}
