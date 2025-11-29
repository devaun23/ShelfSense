from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.database import get_db
from app.models.models import User
from app.dependencies.auth import get_current_user, verify_user_access

router = APIRouter(prefix="/api/users", tags=["users"])


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr


class UserResponse(BaseModel):
    user_id: str
    full_name: str
    first_name: str
    email: str

    class Config:
        from_attributes = True


@router.post("/register", response_model=UserResponse)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register or login a user with full name and email
    If email exists, return existing user and update last_login
    """
    # Extract first name from full name
    first_name = request.full_name.strip().split(' ')[0]

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        # Update last login and return existing user
        existing_user.last_login = datetime.utcnow()
        existing_user.full_name = request.full_name  # Update in case name changed
        existing_user.first_name = first_name
        db.commit()
        db.refresh(existing_user)

        return UserResponse(
            user_id=existing_user.id,
            full_name=existing_user.full_name,
            first_name=existing_user.first_name,
            email=existing_user.email
        )

    # Create new user
    new_user = User(
        full_name=request.full_name,
        first_name=first_name,
        email=request.email,
        last_login=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        user_id=new_user.id,
        full_name=new_user.full_name,
        first_name=new_user.first_name,
        email=new_user.email
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user information by ID.

    SECURITY: Requires authentication. Users can only access their own data.
    Admins can access any user.
    """
    # IDOR protection: verify user has access to this data
    verify_user_access(current_user, user_id)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=user.id,
        full_name=user.full_name,
        first_name=user.first_name,
        email=user.email
    )
