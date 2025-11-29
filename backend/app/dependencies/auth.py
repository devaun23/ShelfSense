"""
Authentication Dependencies for ShelfSense

Provides FastAPI dependencies for:
- Clerk JWT verification
- User authentication
- Admin authorization
- IDOR protection

Usage:
    @router.get("/protected")
    def protected_endpoint(current_user: User = Depends(get_current_user)):
        return {"user_id": current_user.id}
"""

import os
import logging
import httpx
import time
import threading
from typing import Optional, Tuple
from datetime import datetime

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError, jwk
from jose.exceptions import JWKError

from app.database import get_db
from app.models.models import User

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for extracting tokens
security = HTTPBearer(auto_error=False)

# Clerk configuration
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://clerk.shelfsense.com")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
# SECURITY: Audience validation - set to your app's URL in production
CLERK_AUDIENCE = os.getenv("CLERK_AUDIENCE")  # e.g., "https://shelfsense.com"

# JWKS cache with TTL (1 hour) and thread-safe locking
_jwks_cache: Tuple[Optional[dict], float] = (None, 0)
_jwks_lock = threading.Lock()
JWKS_CACHE_TTL_SECONDS = 3600  # 1 hour
JWKS_MAX_STALE_SECONDS = 3600  # 1 hour max stale (reduced from 24h for faster key rotation response)


def get_clerk_jwks(force_refresh: bool = False) -> dict:
    """
    Fetch and cache Clerk's JWKS (JSON Web Key Set) for token verification.

    Uses TTL-based caching (1 hour) with thread-safe locking to prevent
    thundering herd problem during cache refresh.

    Args:
        force_refresh: If True, bypass cache and fetch fresh keys

    Returns:
        dict: JWKS containing public keys for verification
    """
    global _jwks_cache
    cached_jwks, cache_time = _jwks_cache
    current_time = time.time()
    cache_age = current_time - cache_time

    # Return cached value if still valid and not forcing refresh
    if not force_refresh and cached_jwks is not None:
        if cache_age < JWKS_CACHE_TTL_SECONDS:
            return cached_jwks

    # Use lock to prevent thundering herd (multiple concurrent refreshes)
    with _jwks_lock:
        # Double-check: another thread might have refreshed while we waited
        cached_jwks, cache_time = _jwks_cache
        cache_age = time.time() - cache_time

        if not force_refresh and cached_jwks is not None:
            if cache_age < JWKS_CACHE_TTL_SECONDS:
                return cached_jwks

        # Construct JWKS URL from Clerk frontend API
        # SECURITY: Prioritize manually configured JWKS URL for custom domains
        if CLERK_JWKS_URL:
            jwks_url = CLERK_JWKS_URL
            logger.debug(f"Using manually configured JWKS URL: {jwks_url}")
        else:
            clerk_pub_key = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")

            if clerk_pub_key.startswith("pk_test_") or clerk_pub_key.startswith("pk_live_"):
                # Extract the Clerk instance identifier
                # Format: pk_test_xxxxx or pk_live_xxxxx
                # The JWKS is at https://{instance}.clerk.accounts.dev/.well-known/jwks.json
                import base64
                try:
                    # Clerk publishable key contains base64-encoded instance URL
                    key_part = clerk_pub_key.split("_", 2)[2] if "_" in clerk_pub_key else clerk_pub_key
                    # Add padding if needed
                    padding = 4 - len(key_part) % 4
                    if padding != 4:
                        key_part += "=" * padding
                    decoded = base64.b64decode(key_part).decode('utf-8')
                    # Validate it looks like a Clerk domain
                    if not decoded.endswith('.clerk.accounts.dev'):
                        logger.warning(f"Unexpected Clerk domain format: {decoded}")
                    jwks_url = f"https://{decoded}/.well-known/jwks.json"
                except Exception as e:
                    logger.error(f"Failed to parse Clerk publishable key: {e}")
                    jwks_url = None
            else:
                jwks_url = None

        if not jwks_url:
            logger.error("No JWKS URL configured for Clerk")
            return {"keys": []}

        try:
            response = httpx.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            jwks = response.json()
            # Update cache
            _jwks_cache = (jwks, time.time())
            logger.debug("JWKS cache refreshed successfully")
            return jwks
        except Exception as e:
            logger.error(f"Failed to fetch Clerk JWKS: {e}")
            # Return stale cache if available and not too stale
            if cached_jwks is not None:
                if cache_age < JWKS_MAX_STALE_SECONDS:
                    logger.warning(f"Returning stale JWKS cache (age: {cache_age:.0f}s) due to fetch failure")
                    return cached_jwks
                else:
                    logger.error(f"Stale cache too old ({cache_age:.0f}s), refusing to use")
            return {"keys": []}


def verify_clerk_jwt(token: str) -> dict:
    """
    Verify a Clerk JWT token and return the claims.

    Args:
        token: JWT token from Authorization header

    Returns:
        dict: Decoded JWT claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Get unverified header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID"
            )

        # Fetch JWKS and find matching key
        jwks = get_clerk_jwks()
        rsa_key = None

        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            # Key not found - force refresh and retry (handles key rotation)
            jwks = get_clerk_jwks(force_refresh=True)
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key"
            )

        # Build decode options
        # SECURITY: Validate audience if configured to prevent token reuse across apps
        decode_options = {}
        decode_kwargs = {
            "algorithms": ["RS256"],
        }

        if CLERK_AUDIENCE:
            # Audience validation enabled
            decode_kwargs["audience"] = CLERK_AUDIENCE
        else:
            # SECURITY: Check if we're in production
            # Railway sets RAILWAY_ENVIRONMENT="production" in production
            railway_env = os.getenv("RAILWAY_ENVIRONMENT", "").lower()
            is_production = (
                railway_env == "production" or
                os.getenv("PRODUCTION", "").lower() == "true" or
                os.getenv("ENVIRONMENT", "").lower() == "production"
            )

            if is_production:
                # SECURITY: Hard failure in production - audience MUST be configured
                # to prevent token reuse attacks across Clerk applications
                logger.critical(
                    "SECURITY CRITICAL: CLERK_AUDIENCE not configured in production! "
                    "Authentication is disabled until this is fixed. "
                    "Set CLERK_AUDIENCE=https://shelfpass.com in Railway environment variables."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication configuration error. Please contact support."
                )
            else:
                # Development only - skip audience validation with warning
                logger.warning(
                    "CLERK_AUDIENCE not set - skipping audience validation (development mode only)"
                )
                decode_options["verify_aud"] = False

        if decode_options:
            decode_kwargs["options"] = decode_options

        # Verify and decode the token
        payload = jwt.decode(token, rsa_key, **decode_kwargs)

        return payload

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except JWKError as e:
        logger.error(f"JWK error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the currently authenticated user.

    Validates the Clerk JWT and returns the corresponding user from the database.

    Args:
        credentials: Bearer token from HTTPBearer
        authorization: Raw Authorization header (fallback)
        db: Database session

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: If not authenticated or user not found
    """
    # Extract token
    token = None
    if credentials:
        token = credentials.credentials
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify Clerk JWT
    claims = verify_clerk_jwt(token)

    # Get user ID from claims (Clerk uses 'sub' for user ID)
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims"
        )

    # Find user in database
    user = db.query(User).filter(
        (User.clerk_id == clerk_user_id) | (User.id == clerk_user_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns None if not authenticated.

    Use for endpoints that work both with and without authentication.
    """
    try:
        return await get_current_user(credentials, authorization, db)
    except HTTPException:
        return None


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to require admin privileges.

    Args:
        current_user: The authenticated user

    Returns:
        User: The admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def verify_user_access(current_user: User, user_id: str) -> None:
    """
    Verify that the current user has access to the requested user's data.

    Prevents IDOR (Insecure Direct Object Reference) attacks.

    Args:
        current_user: The authenticated user
        user_id: The user ID being accessed

    Raises:
        HTTPException: If access is denied or user_id is invalid
    """
    # SECURITY: Validate user_id is not empty/None to prevent bypass
    if not user_id or not str(user_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Admin can access any user
    if current_user.is_admin:
        return

    # User can only access their own data
    if current_user.id != user_id and current_user.clerk_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
