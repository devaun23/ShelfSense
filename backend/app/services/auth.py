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
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class PasswordValidationError(Exception):
    """Raised when password doesn't meet requirements"""
    pass


class TokenError(Exception):
    """Raised when token is invalid or expired"""
    pass


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


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password meets security requirements.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number

    Args:
        password: Password to validate

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
