import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from forensicstack.api.schemas import TokenResponse, UserCreate, UserResponse
from forensicstack.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from forensicstack.core.database import get_db
from forensicstack.core.models.user_model import User
from forensicstack.core.ratelimit import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])

# Throttle the credential surface. Defaults are generous enough for real use but
# stop scripted brute-force / enumeration; both are env-tunable per deployment.
_login_limit = rate_limit(
    "login",
    limit=int(os.getenv("RATELIMIT_LOGIN", "10")),
    window_seconds=int(os.getenv("RATELIMIT_LOGIN_WINDOW", "300")),
)
_register_limit = rate_limit(
    "register",
    limit=int(os.getenv("RATELIMIT_REGISTER", "5")),
    window_seconds=int(os.getenv("RATELIMIT_REGISTER_WINDOW", "3600")),
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(_register_limit)],
)
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new investigator account."""
    # Username uniqueness
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    # Email uniqueness (if provided)
    if user_in.email and db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role="analyst",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(_login_limit)],
)
async def login(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Authenticate and receive a JWT access token.

    Use the returned `access_token` as a Bearer token on all protected endpoints:
        Authorization: Bearer <access_token>
    """
    user = db.query(User).filter(User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "username": user.username,
        "role": user.role,
    }


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
