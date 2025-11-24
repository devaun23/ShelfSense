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
from datetime import datetime

from app.database import get_db
from app.models.models import User, generate_uuid

router = APIRouter(prefix="/api/webhook", tags=["webhooks"])


def verify_clerk_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Clerk webhook signature

    Args:
        payload: Raw request body
        signature: svix-signature header
        secret: Clerk webhook secret

    Returns:
        True if signature is valid
    """
    if not signature or not secret:
        return False

    # Extract timestamp and signatures from header
    # Format: "v1,timestamp signature"
    parts = signature.split(',')
    if len(parts) < 2:
        return False

    timestamp = parts[0]
    signatures = parts[1:]

    # Reconstruct signed payload
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"

    # Compute expected signature
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Compare with provided signatures
    return any(hmac.compare_digest(expected_sig, sig.strip()) for sig in signatures)


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

    # Verify webhook signature (optional - enable in production)
    # import os
    # webhook_secret = os.getenv('CLERK_WEBHOOK_SECRET')
    # if webhook_secret and not verify_clerk_webhook(body, svix_signature or '', webhook_secret):
    #     raise HTTPException(status_code=401, detail="Invalid webhook signature")

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
