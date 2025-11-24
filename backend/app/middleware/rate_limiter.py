"""
Rate Limiting Middleware for ShelfSense

Prevents API abuse by limiting:
1. AI question generation requests per user
2. Overall API request rate

Configuration:
- Max 10 AI questions per user per hour
- Max 100 general API requests per user per minute
"""

import time
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class RateLimiter:
    """Simple in-memory rate limiter with sliding window"""

    def __init__(self):
        # Store: {user_id: [(timestamp, endpoint), ...]}
        self._requests: Dict[str, list] = defaultdict(list)

        # Rate limit configurations
        self._limits = {
            "ai_generation": {
                "max_requests": 10,
                "window_seconds": 3600,  # 1 hour
                "endpoints": ["/api/questions/random"]
            },
            "general_api": {
                "max_requests": 100,
                "window_seconds": 60,  # 1 minute
                "endpoints": ["*"]  # All endpoints
            }
        }

    def _clean_old_requests(self, user_id: str, window_seconds: int):
        """Remove requests outside the time window"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        if user_id in self._requests:
            self._requests[user_id] = [
                (ts, endpoint) for ts, endpoint in self._requests[user_id]
                if ts > cutoff_time
            ]

    def check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        limit_type: str = "general_api"
    ) -> Tuple[bool, Dict]:
        """
        Check if request is within rate limits

        Args:
            user_id: User identifier
            endpoint: API endpoint being accessed
            limit_type: Type of rate limit to apply

        Returns:
            Tuple of (is_allowed, info_dict)
            - is_allowed: True if request is within limits
            - info_dict: Contains current usage and limit information
        """
        if limit_type not in self._limits:
            return True, {}

        limit_config = self._limits[limit_type]
        max_requests = limit_config["max_requests"]
        window_seconds = limit_config["window_seconds"]

        # Clean old requests
        self._clean_old_requests(user_id, window_seconds)

        # Count relevant requests in window
        current_time = time.time()
        relevant_requests = [
            ts for ts, ep in self._requests[user_id]
            if ep == endpoint or "*" in limit_config["endpoints"]
        ]

        current_count = len(relevant_requests)

        # Check if limit exceeded
        is_allowed = current_count < max_requests

        # Calculate reset time
        if relevant_requests:
            oldest_request = min(relevant_requests)
            reset_time = oldest_request + window_seconds
        else:
            reset_time = current_time + window_seconds

        info = {
            "limit": max_requests,
            "remaining": max(0, max_requests - current_count),
            "reset": int(reset_time),
            "window_seconds": window_seconds
        }

        if is_allowed:
            # Record this request
            self._requests[user_id].append((current_time, endpoint))

        return is_allowed, info

    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        total_users = len(self._requests)
        total_requests = sum(len(reqs) for reqs in self._requests.values())

        return {
            "total_users_tracked": total_users,
            "total_active_requests": total_requests,
            "rate_limits": {
                name: {
                    "max_requests": config["max_requests"],
                    "window_seconds": config["window_seconds"]
                }
                for name, config in self._limits.items()
            }
        }

    def reset_user(self, user_id: str):
        """Reset rate limit for a specific user"""
        if user_id in self._requests:
            del self._requests[user_id]


# Global rate limiter instance
_limiter = RateLimiter()


def check_ai_generation_rate_limit(user_id: str) -> Dict:
    """
    Check rate limit for AI question generation

    Args:
        user_id: User ID to check

    Returns:
        Rate limit info dict

    Raises:
        HTTPException: If rate limit exceeded
    """
    is_allowed, info = _limiter.check_rate_limit(
        user_id=user_id,
        endpoint="/api/questions/random",
        limit_type="ai_generation"
    )

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Maximum {info['limit']} AI questions per hour. Please try again later.",
                "limit": info["limit"],
                "reset": info["reset"],
                "retry_after": info["reset"] - int(time.time())
            }
        )

    return info


def check_general_rate_limit(user_id: str, endpoint: str) -> Dict:
    """
    Check general API rate limit

    Args:
        user_id: User ID to check
        endpoint: Endpoint being accessed

    Returns:
        Rate limit info dict

    Raises:
        HTTPException: If rate limit exceeded
    """
    is_allowed, info = _limiter.check_rate_limit(
        user_id=user_id,
        endpoint=endpoint,
        limit_type="general_api"
    )

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please slow down.",
                "limit": info["limit"],
                "reset": info["reset"],
                "retry_after": info["reset"] - int(time.time())
            }
        )

    return info


def get_rate_limiter_stats() -> Dict:
    """Get rate limiter statistics"""
    return _limiter.get_stats()


def reset_user_rate_limit(user_id: str):
    """Reset rate limit for a user (admin function)"""
    _limiter.reset_user(user_id)


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to apply rate limiting to all requests

    Note: This is a basic implementation. For production, consider:
    - Redis-based rate limiting for multi-server deployments
    - More sophisticated rate limiting strategies
    - IP-based limiting for anonymous users
    """
    # Skip rate limiting for health checks and docs
    if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
        return await call_next(request)

    # Extract user_id from query params or default
    user_id = request.query_params.get("user_id", "anonymous")

    try:
        # Apply general rate limit
        info = check_general_rate_limit(user_id, request.url.path)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response

    except HTTPException as e:
        # Return rate limit error
        return JSONResponse(
            status_code=e.status_code,
            content=e.detail
        )
