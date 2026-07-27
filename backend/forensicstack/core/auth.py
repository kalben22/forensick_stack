"""
JWT authentication helpers for ForensicStack.

Usage in FastAPI routes:
    from forensicstack.core.auth import get_current_user
    ...
    async def my_route(current_user: User = Depends(get_current_user)):
        ...
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from forensicstack.core.database import get_db, require_env
from forensicstack.core.models.user_model import User

# ── Configuration ────────────────────────────────────────────────────────────
# No fallback value: the previous default ("changeme-use-a-real-secret-in-
# production") is a public constant in this repository, so any deployment
# started without a .env signed JWTs with a key an attacker already has —
# tokens for any user, including role=admin, could be forged offline.
# 32 chars is the minimum for HS256 to have full-strength key material.
SECRET_KEY = require_env("SECRET_KEY", min_length=32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# ── Bearer token extractor ────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()


# ── Password utilities (bcrypt direct — avoids passlib/bcrypt version conflict) ─

def hash_password(plain_password: str) -> str:
    return _bcrypt.hashpw(plain_password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ── JWT utilities ─────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extract and validate the Bearer JWT,
    then return the corresponding User from the database.
    """
    payload = decode_token(credentials.credentials)
    username: str = payload.get("sub")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that additionally checks for admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def owner_scope(user: User) -> Optional[int]:
    """
    Return the owner_id that queries must be restricted to for `user`.

    Analysts get their own id; admins get None, meaning "no ownership filter".
    Centralising the rule here prevents the failure the audit found: each route
    open-coding (or, in practice, forgetting) its own authorisation check, so
    that any registered account could read and delete every case in the
    platform. A route that forgets to call this now has no owner_id to pass and
    fails loudly instead of silently returning everyone's evidence.
    """
    return None if user.role == "admin" else user.id
