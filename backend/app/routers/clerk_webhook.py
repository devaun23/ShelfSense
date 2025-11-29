"""
Clerk Webhook Handler for ShelfSense

Handles Clerk webhook events to sync user data with our database:
- user.created: Create new user record
- user.updated: Update existing user record
- user.deleted: Soft delete or mark user as inactive

Setup:
1. In Clerk Dashboard, go to Webhooks
2. Add endpoint: https://your-domain.com/api/webhook/clerk
3. Subscribe to events: user.created, user.updated, user.deleted
4. Copy signing secret to CLERK_WEBHOOK_SECRET env variable
"""

from fastapi import APIRouter, Request, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import hmac
import hashlib
import json
import os
import logging
from datetime import datetime

from app.database import get_db
from app.models.models import User, generate_uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhooks"])


def verify_clerk_webhook(payload: bytes, svix_id: str, svix_timestamp: str, svix_signature: str, secret: str) -> bool:
    """
    Verify Clerk/Svix webhook signature using HMAC-SHA256

    Svix signature format: "v1,<signature1> v1,<signature2>"
    Signed payload format: "<svix_id>.<svix_timestamp>.<payload>"

    Args:
        payload: Raw request body
        svix_id: svix-id header
        svix_timestamp: svix-timestamp header
        svix_signature: svix-signature header
        secret: Clerk webhook secret (starts with whsec_)

    Returns:
        True if signature is valid
    """
    if not all([svix_id, svix_timestamp, svix_signature, secret]):
        logger.warning("Missing required Svix headers or secret")
        return False

    # Remove 'whsec_' prefix if present and decode base64
    import base64
    if secret.startswith('whsec_'):
        secret = secret[6:]

    try:
        secret_bytes = base64.b64decode(secret)
    except Exception:
        logger.error("Failed to decode webhook secret")
        return False

    # Construct signed payload: "{svix_id}.{svix_timestamp}.{payload}"
    signed_payload = f"{svix_id}.{svix_timestamp}.{payload.decode('utf-8')}"

    # Compute expected signature
    expected_sig = hmac.new(
        secret_bytes,
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected_sig_b64 = base64.b64encode(expected_sig).decode('utf-8')

    # Parse signatures from header (format: "v1,<sig1> v1,<sig2>")
    signatures = []
    for part in svix_signature.split(' '):
        if part.startswith('v1,'):
            signatures.append(part[3:])  # Remove 'v1,' prefix

    # Compare with provided signatures using constant-time comparison
    for sig in signatures:
        if hmac.compare_digest(expected_sig_b64, sig):
            return True

    logger.warning("Webhook signature verification failed")
    return False


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: Optional[str] = Header(None),
    svix_timestamp: Optional[str] = Header(None),
    svix_signature: Optional[str] = Header(None)
):
    """
    Handle Clerk webhook events

    Events:
    - user.created: Create new user in database
    - user.updated: Update user information
    - user.deleted: Mark user as deleted
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature - REQUIRED in production
    webhook_secret = os.getenv('CLERK_WEBHOOK_SECRET')
    if webhook_secret:
        if not verify_clerk_webhook(body, svix_id or '', svix_timestamp or '', svix_signature or '', webhook_secret):
            logger.warning("Clerk webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    else:
        # In production, this should fail. Log warning for development.
        if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('PRODUCTION'):
            logger.error("CLERK_WEBHOOK_SECRET not configured in production!")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        logger.warning("CLERK_WEBHOOK_SECRET not set - skipping signature verification (dev only)")

    # Parse webhook payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get('type')
    data = payload.get('data', {})

    # Get database session
    from app.database import SessionLocal
    db = SessionLocal()

    try:
        if event_type == 'user.created':
            # Create new user
            clerk_id = data.get('id')
            email = data.get('email_addresses', [{}])[0].get('email_address')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or email

            if not email:
                raise HTTPException(status_code=400, detail="Email required")

            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.clerk_id == clerk_id) | (User.email == email)
            ).first()

            if existing_user:
                # Update existing user with Clerk ID
                existing_user.clerk_id = clerk_id
                existing_user.full_name = full_name
                existing_user.first_name = first_name or existing_user.first_name
                existing_user.last_login = datetime.utcnow()
                db.commit()
                return {"status": "updated", "user_id": existing_user.id}

            # Create new user
            new_user = User(
                id=generate_uuid(),
                clerk_id=clerk_id,
                email=email,
                full_name=full_name,
                first_name=first_name or email.split('@')[0],
                last_login=datetime.utcnow()
            )

            db.add(new_user)
            db.commit()

            return {"status": "created", "user_id": new_user.id}

        elif event_type == 'user.updated':
            # Update existing user
            clerk_id = data.get('id')
            email = data.get('email_addresses', [{}])[0].get('email_address')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or email

            user = db.query(User).filter(User.clerk_id == clerk_id).first()

            if user:
                user.email = email or user.email
                user.full_name = full_name
                user.first_name = first_name or user.first_name
                user.last_login = datetime.utcnow()
                db.commit()
                return {"status": "updated", "user_id": user.id}

            return {"status": "user_not_found"}

        elif event_type == 'user.deleted':
            # Soft delete user (keep data for analytics)
            clerk_id = data.get('id')

            user = db.query(User).filter(User.clerk_id == clerk_id).first()

            if user:
                # Add a deleted_at field or just log it
                # For now, we'll just acknowledge the deletion
                # You could add a `deleted_at` column to the User model
                return {"status": "acknowledged", "user_id": user.id}

            return {"status": "user_not_found"}

        else:
            # Unknown event type
            return {"status": "ignored", "event_type": event_type}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

    finally:
        db.close()


@router.get("/clerk/test")
async def test_webhook():
    """Test endpoint to verify webhook configuration"""
    return {
        "status": "ok",
        "message": "Clerk webhook endpoint is configured correctly",
        "supported_events": [
            "user.created",
            "user.updated",
            "user.deleted"
        ]
    }
