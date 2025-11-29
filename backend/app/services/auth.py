"""
Authentication Service
Handles password hashing, JWT token generation, and session management.
"""
import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "CRITICAL: JWT_SECRET_KEY environment variable must be set to a secure value "
        "(at least 32 characters). "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# =============================================================================
# SESSION TIMEOUT CONFIGURATION
# =============================================================================
# SECURITY: Configure session timeouts based on security requirements
#
# Access Token: Short-lived token for API requests (default: 60 minutes)
# - Shorter is more secure but requires more frequent refreshes
# - Consider 15-30 minutes for high-security applications
#
# Refresh Token: Long-lived token for obtaining new access tokens (default: 7 days)
# - Used for "remember me" functionality
# - Should be stored securely (httpOnly cookie or secure storage)
#
# Idle Session Timeout: Time before inactive session expires (default: 30 minutes)
# - Sessions inactive longer than this will require re-authentication
#
# Absolute Session Timeout: Maximum session lifetime regardless of activity (default: 24 hours)
# - Forces re-authentication even for active sessions

IDLE_SESSION_TIMEOUT_MINUTES = int(os.getenv("IDLE_SESSION_TIMEOUT_MINUTES", "30"))
ABSOLUTE_SESSION_TIMEOUT_HOURS = int(os.getenv("ABSOLUTE_SESSION_TIMEOUT_HOURS", "24"))

# Maximum concurrent sessions per user (0 = unlimited)
# SECURITY: Limiting sessions prevents session spreading attacks
MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", "5"))

# Session security settings
SESSION_BIND_IP = os.getenv("SESSION_BIND_IP", "false").lower() == "true"  # Bind sessions to IP
REQUIRE_FRESH_LOGIN_FOR_SENSITIVE_OPS = True  # Require recent auth for password changes, etc.


class PasswordValidationError(Exception):
    """Raised when password doesn't meet requirements"""
    pass


class TokenError(Exception):
    """Raised when token is invalid or expired"""
    pass


class SessionError(Exception):
    """Raised when session validation fails"""
    pass


def is_session_valid(session, current_ip: str = None) -> Tuple[bool, str]:
    """
    Validate a session against security constraints.

    SECURITY: Checks for:
    - Session expiration
    - Idle timeout (no activity for too long)
    - Absolute timeout (max session lifetime)
    - IP binding (if enabled)

    Args:
        session: UserSession object
        current_ip: Current request IP for binding check

    Returns:
        Tuple of (is_valid, error_reason)
    """
    now = datetime.utcnow()

    # Check if session is expired
    if session.expires_at and session.expires_at < now:
        return False, "Session expired"

    # Check idle timeout
    if session.last_used:
        idle_delta = now - session.last_used
        if idle_delta.total_seconds() > (IDLE_SESSION_TIMEOUT_MINUTES * 60):
            return False, "Session inactive for too long"

    # Check absolute timeout
    if session.created_at:
        age_delta = now - session.created_at
        if age_delta.total_seconds() > (ABSOLUTE_SESSION_TIMEOUT_HOURS * 3600):
            return False, "Session exceeded maximum lifetime"

    # Check IP binding if enabled
    if SESSION_BIND_IP and current_ip and session.ip_address:
        if session.ip_address != current_ip:
            return False, "Session IP mismatch"

    return True, ""


def enforce_session_limit(db, user_id: str, max_sessions: int = None) -> int:
    """
    Enforce maximum concurrent sessions per user.

    SECURITY: Prevents session spreading attacks where an attacker
    creates many sessions to maintain persistent access.

    Args:
        db: Database session
        user_id: User ID
        max_sessions: Override for max sessions (uses config default if None)

    Returns:
        Number of sessions terminated
    """
    from app.models.models import UserSession

    limit = max_sessions if max_sessions is not None else MAX_SESSIONS_PER_USER
    if limit <= 0:
        return 0  # Unlimited sessions

    # Get all active sessions for user, ordered by last_used (oldest first)
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.expires_at > datetime.utcnow()
    ).order_by(UserSession.last_used.asc()).all()

    # If under limit, no action needed
    if len(sessions) < limit:
        return 0

    # Remove oldest sessions to get under limit
    # Keep the most recent (limit - 1) to allow for new session
    to_remove = sessions[:-(limit - 1)] if limit > 1 else sessions
    removed_count = 0

    for session in to_remove:
        db.delete(session)
        removed_count += 1

    return removed_count


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_token(token: str) -> str:
    """
    Hash a token using SHA256 (for refresh tokens which exceed bcrypt's 72 byte limit).

    Args:
        token: Plain text token (e.g., JWT refresh token)

    Returns:
        SHA256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(plain_token: str, hashed_token: str) -> bool:
    """
    Verify a token against its SHA256 hash.

    Args:
        plain_token: Plain text token
        hashed_token: SHA256 hash to verify against

    Returns:
        True if token matches, False otherwise
    """
    return hashlib.sha256(plain_token.encode()).hexdigest() == hashed_token


def validate_password_strength(password: str, email: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate password meets security requirements.

    SECURITY: Strong password requirements per NIST/OWASP guidelines.

    Requirements:
    - At least 8 characters (12+ recommended)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    - Not a commonly used password
    - Not containing email/username parts

    Args:
        password: Password to validate
        email: Optional email to check for inclusion in password

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    # SECURITY: Require at least one special character
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\/'`~;]", password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>-_=+)"

    # SECURITY: Check against common passwords (top 100 most common)
    common_passwords = {
        "password", "password1", "password123", "123456", "12345678", "123456789",
        "qwerty", "abc123", "monkey", "1234567", "letmein", "trustno1", "dragon",
        "baseball", "iloveyou", "master", "sunshine", "ashley", "bailey", "shadow",
        "123123", "654321", "superman", "qazwsx", "michael", "football", "password1!",
        "password123!", "welcome", "welcome1", "admin", "login", "passw0rd", "hello",
        "charlie", "donald", "loveme", "beer", "access", "mustang", "whatever",
        "qwerty123", "starwars", "zaq1zaq1", "qwerty1", "1qaz2wsx", "hunter",
        "hunter2", "hunter1", "test", "test123", "pass", "pass123", "root", "toor",
        "1234567890", "0987654321", "changeme", "changethis", "secret", "temp123",
        "guest", "demo", "sample", "example"
    }
    if password.lower() in common_passwords:
        return False, "This password is too common. Please choose a more unique password."

    # SECURITY: Check for sequential/repeated characters
    if re.search(r"(.)\1{3,}", password):  # 4+ repeated chars
        return False, "Password cannot contain 4 or more repeated characters"

    if re.search(r"(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)", password.lower()):
        return False, "Password cannot contain sequential characters (123, abc, etc.)"

    # SECURITY: Check if password contains email parts
    if email:
        email_local = email.split("@")[0].lower()
        if len(email_local) >= 4 and email_local in password.lower():
            return False, "Password cannot contain your email address"

    return True, ""


def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        JWT access token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }

    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        JWT refresh token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16)  # Unique token ID
    }

    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload

    Raises:
        TokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != token_type:
            raise TokenError(f"Invalid token type. Expected {token_type}")

        if "sub" not in payload:
            raise TokenError("Token missing user ID")

        return payload

    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenError("Token has expired")
        raise TokenError(f"Invalid token: {str(e)}")


def get_user_id_from_token(token: str) -> str:
    """
    Extract user ID from an access token.

    Args:
        token: JWT access token

    Returns:
        User ID string

    Raises:
        TokenError: If token is invalid
    """
    payload = verify_token(token, "access")
    return payload["sub"]


def generate_password_reset_token() -> str:
    """
    Generate a secure random token for password reset.

    Returns:
        URL-safe random token string
    """
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    """
    Hash a password reset token for storage.

    Args:
        token: Plain reset token

    Returns:
        Hashed token
    """
    return pwd_context.hash(token)


def verify_reset_token(plain_token: str, hashed_token: str) -> bool:
    """
    Verify a password reset token.

    Args:
        plain_token: Token from URL
        hashed_token: Hashed token from database

    Returns:
        True if tokens match
    """
    return pwd_context.verify(plain_token, hashed_token)


class AuthService:
    """
    Service class for authentication operations.
    Provides a clean interface for auth-related functionality.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        return hash_password(password)

    @staticmethod
    def verify_password(password: str, hash: str) -> bool:
        return verify_password(password, hash)

    @staticmethod
    def create_access_token(user_id: str) -> str:
        return create_access_token(user_id)

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        return create_refresh_token(user_id)

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> dict:
        return verify_token(token, token_type)

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        return validate_password_strength(password)

    @staticmethod
    def generate_reset_token() -> str:
        return generate_password_reset_token()
