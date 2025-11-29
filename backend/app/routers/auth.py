"""
Authentication Router
Handles user registration, login, logout, and token management.
"""
import os
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.models.models import User, UserSession, UserSettings, PasswordResetToken
from app.dependencies.auth import get_current_user, verify_clerk_jwt
from app.services.auth import (
    AuthService,
    TokenError,
    hash_password,
    verify_password,
    hash_token,
    verify_token_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_user_id_from_token,
    validate_password_strength,
    generate_password_reset_token,
    hash_reset_token,
    verify_reset_token,
    enforce_session_limit,
    REFRESH_TOKEN_EXPIRE_DAYS,
    MAX_SESSIONS_PER_USER
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

# Security scheme for protected routes
security = HTTPBearer(auto_error=False)


# Rate limiting constants
MAX_LOGIN_ATTEMPTS = 10
LOCKOUT_DURATION_MINUTES = 30


# ==================== Request/Response Models ====================

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    user_id: str
    full_name: str
    first_name: str
    email: str
    email_verified: bool
    target_score: Optional[int] = None
    exam_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class MessageResponse(BaseModel):
    message: str


# ==================== Helper Functions ====================

def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and user agent from request"""
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return ip, user_agent


def create_user_response(user: User) -> UserResponse:
    """Create a UserResponse from a User model"""
    return UserResponse(
        user_id=user.id,
        full_name=user.full_name,
        first_name=user.first_name,
        email=user.email,
        email_verified=user.email_verified or False,
        target_score=user.target_score,
        exam_date=user.exam_date,
        created_at=user.created_at
    )


def create_token_response(access_token: str, refresh_token: str) -> TokenResponse:
    """Create a TokenResponse with tokens"""
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600  # 1 hour in seconds
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    Use this in protected routes.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_id = get_user_id_from_token(credentials.credentials)
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get current user.
    Returns None if not authenticated (for backwards compatibility).
    """
    if not credentials:
        return None

    try:
        user_id = get_user_id_from_token(credentials.credentials)
        return db.query(User).filter(User.id == user_id).first()
    except (TokenError, Exception):
        return None


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require admin access.
    Use this in admin-only routes.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ==================== Auth Endpoints ====================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email and password.
    Returns user info and auth tokens.
    """
    # Validate password strength (with email check for security)
    is_valid, error_msg = validate_password_strength(request.password, request.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        # If user exists but has no password, allow setting password
        if existing_user.password_hash is None:
            existing_user.password_hash = hash_password(request.password)
            existing_user.full_name = request.full_name
            existing_user.first_name = request.full_name.strip().split(' ')[0]
            existing_user.last_login = datetime.utcnow()
            db.commit()
            db.refresh(existing_user)

            # Create tokens
            access_token = create_access_token(existing_user.id)
            refresh_token = create_refresh_token(existing_user.id)

            # Create session
            ip, device = get_client_info(req)
            session = UserSession(
                user_id=existing_user.id,
                refresh_token_hash=hash_token(refresh_token),
                device_info=device[:200] if device else None,
                ip_address=ip,
                expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            )
            db.add(session)
            db.commit()

            return AuthResponse(
                user=create_user_response(existing_user),
                tokens=create_token_response(access_token, refresh_token)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists"
            )

    # Create new user
    first_name = request.full_name.strip().split(' ')[0]
    new_user = User(
        full_name=request.full_name,
        first_name=first_name,
        email=request.email,
        password_hash=hash_password(request.password),
        last_login=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create default settings
    settings = UserSettings(user_id=new_user.id)
    db.add(settings)
    db.commit()

    # Create tokens
    access_token = create_access_token(new_user.id)
    refresh_token = create_refresh_token(new_user.id)

    # Create session
    ip, device = get_client_info(req)
    session = UserSession(
        user_id=new_user.id,
        refresh_token_hash=hash_token(refresh_token),
        device_info=device[:200] if device else None,
        ip_address=ip,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    # Send welcome email (non-blocking)
    try:
        from app.services.email.email_service import get_email_service
        email_service = get_email_service()
        asyncio.create_task(email_service.send_welcome_email(db, new_user))
    except Exception as e:
        logger.warning(f"Failed to queue welcome email: {e}")
        # Don't fail registration if email fails

    return AuthResponse(
        user=create_user_response(new_user),
        tokens=create_token_response(access_token, refresh_token)
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns user info and auth tokens.
    """
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account temporarily locked. Try again in {minutes_left} minutes."
        )

    # Check if user has a password set
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please set a password first by registering"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

        # Lock account if too many failures
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # SECURITY: Enforce session limit before creating new session
    terminated = enforce_session_limit(db, user.id)
    if terminated > 0:
        logger.info(f"Terminated {terminated} old sessions for user {user.id} (max: {MAX_SESSIONS_PER_USER})")

    # Create session
    ip, device = get_client_info(req)
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        device_info=device[:200] if device else None,
        ip_address=ip,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    return AuthResponse(
        user=create_user_response(user),
        tokens=create_token_response(access_token, refresh_token)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Returns new access and refresh tokens.
    """
    try:
        payload = verify_token(request.refresh_token, "refresh")
        user_id = payload["sub"]
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new tokens
    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    # Update session with new refresh token
    ip, device = get_client_info(req)

    # Find existing session or create new
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id
    ).all()

    # Verify refresh token against stored sessions
    valid_session = None
    for session in sessions:
        if verify_token_hash(request.refresh_token, session.refresh_token_hash):
            valid_session = session
            break

    if valid_session:
        valid_session.refresh_token_hash = hash_token(new_refresh_token)
        valid_session.last_used = datetime.utcnow()
        valid_session.expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        # Create new session
        new_session = UserSession(
            user_id=user.id,
            refresh_token_hash=hash_token(new_refresh_token),
            device_info=device[:200] if device else None,
            ip_address=ip,
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(new_session)

    db.commit()

    return create_token_response(access_token, new_refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Logout by invalidating the refresh token.
    """
    try:
        payload = verify_token(request.refresh_token, "refresh")
        user_id = payload["sub"]
    except TokenError:
        # Even if token is invalid, return success (user is logged out)
        return MessageResponse(message="Logged out successfully")

    # Find and delete session
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id
    ).all()

    for session in sessions:
        if verify_token_hash(request.refresh_token, session.refresh_token_hash):
            db.delete(session)
            break

    db.commit()

    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's information.
    """
    return create_user_response(current_user)


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    """
    # Verify current password
    if not current_user.password_hash or not verify_password(
        request.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password (with email check for security)
    is_valid, error_msg = validate_password_strength(request.new_password, current_user.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Update password
    current_user.password_hash = hash_password(request.new_password)
    db.commit()

    return MessageResponse(message="Password changed successfully")


# ==================== Password Reset ====================

# Rate limiting for password reset
PASSWORD_RESET_EXPIRE_HOURS = 1
MAX_RESET_REQUESTS_PER_HOUR = 3


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset email.
    Always returns success to prevent email enumeration.
    """
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success to prevent email enumeration attacks
    success_message = "If an account with that email exists, we've sent password reset instructions."

    if not user:
        # SECURITY: Log hashed email prefix to avoid PII in logs
        import hashlib
        email_hash = hashlib.sha256(request.email.lower().encode()).hexdigest()[:8]
        logger.info(f"Password reset requested for non-existent email (hash: {email_hash})")
        return MessageResponse(message=success_message)

    # Check if user has a password (not Clerk-only user)
    # Clerk users should reset password through Clerk
    if user.password_hash is None and user.id.startswith("user_"):
        logger.info(f"Password reset requested for Clerk-only user: {user.id}")
        return MessageResponse(message=success_message)

    # Rate limit: check recent reset requests
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_requests = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.created_at > one_hour_ago
    ).count()

    if recent_requests >= MAX_RESET_REQUESTS_PER_HOUR:
        logger.warning(f"Rate limit exceeded for password reset: {user.id}")
        return MessageResponse(message=success_message)

    # Invalidate any existing unused tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})
    db.commit()

    # Generate new token
    raw_token = generate_password_reset_token()
    hashed_token = hash_reset_token(raw_token)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hashed_token,
        expires_at=datetime.utcnow() + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
    )
    db.add(reset_token)
    db.commit()

    # Send email (non-blocking)
    try:
        from app.services.email.email_service import get_email_service
        email_service = get_email_service()
        asyncio.create_task(
            email_service.send_password_reset_email(
                db, user, raw_token, PASSWORD_RESET_EXPIRE_HOURS
            )
        )
    except Exception as e:
        logger.error(f"Failed to queue password reset email: {e}")

    logger.info(f"Password reset email queued for user: {user.id}")
    return MessageResponse(message=success_message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using a valid reset token.
    """
    # Find all unused tokens (we'll check each one)
    tokens = db.query(PasswordResetToken).filter(
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).all()

    # Find matching token
    valid_token = None
    for token in tokens:
        if verify_reset_token(request.token, token.token_hash):
            valid_token = token
            break

    if not valid_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Get the user
    user = db.query(User).filter(User.id == valid_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Validate new password (with email check for security)
    is_valid, error_msg = validate_password_strength(request.new_password, user.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Update password
    user.password_hash = hash_password(request.new_password)

    # Mark token as used
    valid_token.used = True

    # Clear any account lockout
    user.failed_login_attempts = 0
    user.locked_until = None

    db.commit()

    logger.info(f"Password reset successful for user: {user.id}")
    return MessageResponse(message="Password reset successfully. You can now log in with your new password.")


# ==================== Simple Auth (Backwards Compatible) ====================

class SimpleRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr


class SimpleUserResponse(BaseModel):
    user_id: str
    full_name: str
    first_name: str
    email: str

    class Config:
        from_attributes = True


@router.post("/simple-register", response_model=SimpleUserResponse)
async def simple_register(
    request: SimpleRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Simple registration without password (backwards compatible).
    For email-only login flow.
    """
    first_name = request.full_name.strip().split(' ')[0]

    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        # Update and return existing user
        existing_user.last_login = datetime.utcnow()
        existing_user.full_name = request.full_name
        existing_user.first_name = first_name
        db.commit()
        db.refresh(existing_user)

        return SimpleUserResponse(
            user_id=existing_user.id,
            full_name=existing_user.full_name,
            first_name=existing_user.first_name,
            email=existing_user.email
        )

    # Create new user without password
    new_user = User(
        full_name=request.full_name,
        first_name=first_name,
        email=request.email,
        last_login=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create default settings
    settings = UserSettings(user_id=new_user.id)
    db.add(settings)
    db.commit()

    return SimpleUserResponse(
        user_id=new_user.id,
        full_name=new_user.full_name,
        first_name=new_user.first_name,
        email=new_user.email
    )


# ==================== Clerk Auth Integration ====================

class ClerkSyncRequest(BaseModel):
    clerk_user_id: str
    email: Optional[EmailStr] = None
    full_name: str
    first_name: str
    image_url: Optional[str] = None


class ClerkSyncResponse(BaseModel):
    user_id: str
    clerk_user_id: str
    full_name: str
    first_name: str
    email: Optional[str] = None
    is_admin: bool = False
    synced: bool

    class Config:
        from_attributes = True


@router.post("/clerk-sync", response_model=ClerkSyncResponse)
async def clerk_sync(
    request: ClerkSyncRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Sync user from Clerk authentication.
    Creates or updates a user based on their Clerk ID.
    Called automatically when a user signs in via Clerk.

    SECURITY: Requires valid Clerk JWT. Token's user ID must match request.
    Admin privileges are NOT auto-granted - must be set manually in database.
    """
    # Extract and verify Clerk JWT
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Verify the Clerk JWT
    try:
        claims = verify_clerk_jwt(token)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Clerk JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    # SECURITY: Ensure token's user ID matches the request
    token_user_id = claims.get("sub")
    if token_user_id != request.clerk_user_id:
        logger.warning(f"Token user ID mismatch: token={token_user_id}, request={request.clerk_user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot sync a different user's data"
        )

    # First, try to find user by Clerk ID (stored in id field now)
    existing_user = db.query(User).filter(User.id == request.clerk_user_id).first()

    # SECURITY: Admin auto-promotion REMOVED - admin must be set manually
    # admin_email check removed to prevent privilege escalation

    if existing_user:
        # Update existing user
        existing_user.full_name = request.full_name
        existing_user.first_name = request.first_name
        if request.email:
            existing_user.email = request.email
        existing_user.last_login = datetime.utcnow()

        # NOTE: is_admin is NOT modified here - must be set via admin panel/database

        db.commit()
        db.refresh(existing_user)

        return ClerkSyncResponse(
            user_id=existing_user.id,
            clerk_user_id=request.clerk_user_id,
            full_name=existing_user.full_name,
            first_name=existing_user.first_name,
            email=existing_user.email,
            is_admin=existing_user.is_admin or False,
            synced=True
        )

    # If not found by Clerk ID, check by email (for migration from old system)
    if request.email:
        email_user = db.query(User).filter(User.email == request.email).first()
        if email_user:
            # Migrate existing email user to Clerk - update their ID
            # This is a one-time migration for existing users
            old_id = email_user.id
            email_user.id = request.clerk_user_id
            email_user.full_name = request.full_name
            email_user.first_name = request.first_name
            email_user.last_login = datetime.utcnow()

            # NOTE: is_admin is NOT modified here - preserves existing admin status

            db.commit()
            db.refresh(email_user)

            return ClerkSyncResponse(
                user_id=email_user.id,
                clerk_user_id=request.clerk_user_id,
                full_name=email_user.full_name,
                first_name=email_user.first_name,
                email=email_user.email,
                is_admin=email_user.is_admin or False,
                synced=True
            )

    # Create new user with Clerk ID
    # SECURITY: New users are NEVER admin - must be promoted manually
    new_user = User(
        id=request.clerk_user_id,  # Use Clerk ID as the user ID
        full_name=request.full_name,
        first_name=request.first_name,
        email=request.email,
        email_verified=True,  # Clerk handles verification
        last_login=datetime.utcnow(),
        is_admin=False  # SECURITY: Never auto-promote to admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create default settings
    settings = UserSettings(user_id=new_user.id)
    db.add(settings)
    db.commit()

    # Send welcome email for new Clerk users (non-blocking)
    try:
        from app.services.email.email_service import get_email_service
        email_service = get_email_service()
        asyncio.create_task(email_service.send_welcome_email(db, new_user))
    except Exception as e:
        logger.warning(f"Failed to queue welcome email for Clerk user: {e}")

    return ClerkSyncResponse(
        user_id=new_user.id,
        clerk_user_id=request.clerk_user_id,
        full_name=new_user.full_name,
        first_name=new_user.first_name,
        email=new_user.email,
        is_admin=new_user.is_admin or False,
        synced=True
    )
