"""
Rate Limiting Middleware for ShelfSense

Enforces daily usage limits based on subscription tier:
- Free: 10 AI questions/day, 50 chat messages/day, 100 questions/day
- Student: 50 AI questions/day, 200 chat messages/day, unlimited questions
- Premium: Unlimited everything

Uses DailyUsage model to track and enforce limits.
"""

from datetime import datetime, date
from typing import Optional, Dict, Callable, Tuple
from functools import wraps
from collections import defaultdict
import time

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.models import DailyUsage, Subscription, User


# ============================================================================
# RATE LIMITS BY TIER
# ============================================================================

RATE_LIMITS = {
    "free": {
        "ai_questions_generated": 10,
        "ai_chat_messages": 50,
        "questions_answered": 100,
    },
    "student": {
        "ai_questions_generated": 50,
        "ai_chat_messages": 200,
        "questions_answered": None,  # Unlimited
    },
    "premium": {
        "ai_questions_generated": None,  # Unlimited
        "ai_chat_messages": None,
        "questions_answered": None,
    },
}

# Endpoint to usage type mapping
ENDPOINT_USAGE_MAP = {
    "/api/questions/generate": "ai_questions_generated",
    "/api/batch/generate": "ai_questions_generated",
    "/api/chat": "ai_chat_messages",
    "/api/chat/message": "ai_chat_messages",
    "/api/questions/submit": "questions_answered",
    "/api/questions/answer": "questions_answered",
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_tier(db: Session, user_id: str) -> str:
    """Get user's subscription tier, defaulting to 'free'."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription:
        return "free"

    # Check if subscription is expired
    if subscription.expires_at and subscription.expires_at < datetime.utcnow():
        return "free"

    # Check if cancelled
    if subscription.cancelled_at:
        return "free"

    return subscription.tier


def get_or_create_daily_usage(db: Session, user_id: str) -> DailyUsage:
    """Get or create today's usage record for user."""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    usage = db.query(DailyUsage).filter(
        DailyUsage.user_id == user_id,
        DailyUsage.date >= today_start
    ).first()

    if not usage:
        from app.models.models import generate_uuid
        usage = DailyUsage(
            id=generate_uuid(),
            user_id=user_id,
            date=today_start,
            questions_answered=0,
            ai_chat_messages=0,
            ai_questions_generated=0
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)

    return usage


def check_rate_limit(
    db: Session,
    user_id: str,
    usage_type: str
) -> Dict[str, any]:
    """
    Check if user has exceeded their rate limit.

    Returns:
        {
            "allowed": bool,
            "current": int,
            "limit": int or None,
            "remaining": int or None,
            "reset_at": datetime
        }
    """
    tier = get_user_tier(db, user_id)
    limit = RATE_LIMITS.get(tier, RATE_LIMITS["free"]).get(usage_type)

    usage = get_or_create_daily_usage(db, user_id)
    current = getattr(usage, usage_type, 0)

    # Calculate reset time (midnight UTC)
    tomorrow = date.today()
    from datetime import timedelta
    reset_at = datetime.combine(tomorrow + timedelta(days=1), datetime.min.time())

    if limit is None:
        # Unlimited
        return {
            "allowed": True,
            "current": current,
            "limit": None,
            "remaining": None,
            "reset_at": reset_at
        }

    remaining = max(0, limit - current)
    allowed = current < limit

    return {
        "allowed": allowed,
        "current": current,
        "limit": limit,
        "remaining": remaining,
        "reset_at": reset_at
    }


def increment_usage(db: Session, user_id: str, usage_type: str, amount: int = 1):
    """Increment the usage counter for a user."""
    usage = get_or_create_daily_usage(db, user_id)
    current = getattr(usage, usage_type, 0)
    setattr(usage, usage_type, current + amount)
    usage.updated_at = datetime.utcnow()
    db.commit()


# ============================================================================
# MIDDLEWARE
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware to enforce rate limits on specific endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        # Get the path
        path = request.url.path

        # Check if this endpoint has rate limiting
        usage_type = None
        for endpoint_prefix, u_type in ENDPOINT_USAGE_MAP.items():
            if path.startswith(endpoint_prefix):
                usage_type = u_type
                break

        if not usage_type:
            # No rate limiting for this endpoint
            return await call_next(request)

        # Get user ID from request (try multiple sources)
        user_id = self._extract_user_id(request)

        if not user_id:
            # No user ID, allow request (auth will handle it)
            return await call_next(request)

        # Check rate limit
        db = SessionLocal()
        try:
            result = check_rate_limit(db, user_id, usage_type)

            if not result["allowed"]:
                # Calculate seconds until reset
                seconds_until_reset = int(
                    (result["reset_at"] - datetime.utcnow()).total_seconds()
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"You have exceeded your daily limit for this action",
                        "limit": result["limit"],
                        "current": result["current"],
                        "reset_at": result["reset_at"].isoformat(),
                        "retry_after": seconds_until_reset
                    },
                    headers={
                        "Retry-After": str(seconds_until_reset),
                        "X-RateLimit-Limit": str(result["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(result["reset_at"].timestamp()))
                    }
                )

            # Add rate limit headers to response
            response = await call_next(request)

            if result["limit"]:
                response.headers["X-RateLimit-Limit"] = str(result["limit"])
                response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(int(result["reset_at"].timestamp()))

            return response

        finally:
            db.close()

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request headers, query params, or path."""
        # Try Authorization header (JWT would be decoded here in production)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # In production, decode JWT and extract user_id
            # For now, check if there's a user_id in query params
            pass

        # Try query parameter
        user_id = request.query_params.get("user_id")
        if user_id:
            return user_id

        # Try path parameter (e.g., /api/users/{user_id}/...)
        path_parts = request.url.path.split("/")
        for i, part in enumerate(path_parts):
            if part == "users" and i + 1 < len(path_parts):
                return path_parts[i + 1]

        # Try X-User-ID header (for internal services)
        return request.headers.get("X-User-ID")


# ============================================================================
# DECORATOR FOR ROUTE-LEVEL RATE LIMITING
# ============================================================================

def rate_limit(usage_type: str):
    """
    Decorator for applying rate limits to specific routes.

    Usage:
        @router.post("/generate")
        @rate_limit("ai_questions_generated")
        async def generate_question(user_id: str, db: Session = Depends(get_db)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract db and user_id from kwargs
            db = kwargs.get("db")
            user_id = kwargs.get("user_id")

            if not db or not user_id:
                # Can't check rate limit without these
                return await func(*args, **kwargs)

            result = check_rate_limit(db, user_id, usage_type)

            if not result["allowed"]:
                seconds_until_reset = int(
                    (result["reset_at"] - datetime.utcnow()).total_seconds()
                )
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": result["limit"],
                        "current": result["current"],
                        "reset_at": result["reset_at"].isoformat(),
                        "retry_after": seconds_until_reset
                    },
                    headers={"Retry-After": str(seconds_until_reset)}
                )

            # Execute the function
            response = await func(*args, **kwargs)

            # Increment usage after successful execution
            increment_usage(db, user_id, usage_type)

            return response

        return wrapper
    return decorator


# ============================================================================
# DEPENDENCY FOR MANUAL RATE LIMIT CHECKS
# ============================================================================

class RateLimitChecker:
    """
    Dependency class for checking rate limits in routes.

    Usage:
        @router.post("/generate")
        async def generate(
            user_id: str,
            rate_check: dict = Depends(RateLimitChecker("ai_questions_generated")),
            db: Session = Depends(get_db)
        ):
            if not rate_check["allowed"]:
                raise HTTPException(429, detail="Rate limited")
    """

    def __init__(self, usage_type: str):
        self.usage_type = usage_type

    async def __call__(
        self,
        user_id: str = None,
        db: Session = Depends(get_db)
    ) -> Dict:
        if not user_id:
            return {"allowed": True, "limit": None, "remaining": None}

        return check_rate_limit(db, user_id, self.usage_type)


# ============================================================================
# OPENAI BURST LIMITER (Per-Minute Rate Limiting)
# ============================================================================

class OpenAIBurstLimiter:
    """
    Per-minute rate limiting to prevent hitting OpenAI rate limits.
    Complements daily limits with short-term burst protection.

    This is an in-memory limiter that resets on server restart.
    For distributed systems, use Redis-backed implementation.

    Usage:
        allowed, wait_time = openai_burst_limiter.can_make_request(user_id, tier)
        if not allowed:
            raise HTTPException(429, detail=f"Wait {wait_time} seconds")
        # Make OpenAI request
        openai_burst_limiter.record_request(user_id)
    """

    # Requests per minute by tier
    REQUESTS_PER_MINUTE = {
        "free": 5,
        "student": 15,
        "premium": 30
    }

    def __init__(self):
        # Store request timestamps per user: {user_id: [timestamp1, timestamp2, ...]}
        self._requests: Dict[str, list] = defaultdict(list)

    def can_make_request(self, user_id: str, tier: str = "free") -> Tuple[bool, int]:
        """
        Check if user can make an OpenAI request right now.

        Args:
            user_id: User identifier
            tier: Subscription tier (free/student/premium)

        Returns:
            Tuple of (allowed: bool, seconds_to_wait: int)
            If allowed=True, seconds_to_wait=0
            If allowed=False, seconds_to_wait indicates when to retry
        """
        limit = self.REQUESTS_PER_MINUTE.get(tier, 5)
        now = time.time()

        # Clean old requests (older than 60 seconds)
        self._requests[user_id] = [
            t for t in self._requests[user_id]
            if now - t < 60
        ]

        if len(self._requests[user_id]) >= limit:
            # Calculate wait time based on oldest request
            oldest = min(self._requests[user_id])
            wait_time = int(60 - (now - oldest)) + 1
            return False, wait_time

        return True, 0

    def record_request(self, user_id: str):
        """Record a successful request for rate limiting."""
        self._requests[user_id].append(time.time())

    def get_remaining(self, user_id: str, tier: str = "free") -> int:
        """Get remaining requests in current minute."""
        limit = self.REQUESTS_PER_MINUTE.get(tier, 5)
        now = time.time()

        # Count recent requests
        recent = [t for t in self._requests[user_id] if now - t < 60]
        return max(0, limit - len(recent))

    def clear_user(self, user_id: str):
        """Clear rate limit history for a user (admin function)."""
        if user_id in self._requests:
            del self._requests[user_id]


# Global singleton instance
openai_burst_limiter = OpenAIBurstLimiter()


def check_openai_burst_limit(user_id: str, db: Session) -> Tuple[bool, int]:
    """
    Convenience function to check burst limit using user's tier.

    Args:
        user_id: User identifier
        db: Database session for tier lookup

    Returns:
        Tuple of (allowed: bool, seconds_to_wait: int)
    """
    tier = get_user_tier(db, user_id)
    return openai_burst_limiter.can_make_request(user_id, tier)


# ============================================================================
# UTILITY FUNCTIONS FOR ROUTES
# ============================================================================

async def get_user_usage_summary(
    user_id: str,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get complete usage summary for a user.

    Returns all usage types with their limits and current values.
    """
    tier = get_user_tier(db, user_id)
    usage = get_or_create_daily_usage(db, user_id)
    limits = RATE_LIMITS.get(tier, RATE_LIMITS["free"])

    tomorrow = date.today()
    from datetime import timedelta
    reset_at = datetime.combine(tomorrow + timedelta(days=1), datetime.min.time())

    return {
        "user_id": user_id,
        "tier": tier,
        "reset_at": reset_at.isoformat(),
        "usage": {
            "ai_questions_generated": {
                "current": usage.ai_questions_generated,
                "limit": limits["ai_questions_generated"],
                "remaining": (
                    limits["ai_questions_generated"] - usage.ai_questions_generated
                    if limits["ai_questions_generated"] else None
                )
            },
            "ai_chat_messages": {
                "current": usage.ai_chat_messages,
                "limit": limits["ai_chat_messages"],
                "remaining": (
                    limits["ai_chat_messages"] - usage.ai_chat_messages
                    if limits["ai_chat_messages"] else None
                )
            },
            "questions_answered": {
                "current": usage.questions_answered,
                "limit": limits["questions_answered"],
                "remaining": (
                    limits["questions_answered"] - usage.questions_answered
                    if limits["questions_answered"] else None
                )
            }
        }
    }
