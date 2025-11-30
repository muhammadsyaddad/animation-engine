from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from db.session import get_db
from api.auth.security import (
    JWTError,
    JWTExpiredError,
    create_access_token,
    create_refresh_token,
    decode_jwt,
    get_auth_secret,
)
from api.auth.repository import (
    EmailAlreadyExists,
    get_profile,
    get_user_by_email,
    get_user_by_id,
    create_user,
    upsert_profile,
    verify_user_credentials,
    User as RepoUser,
    Profile as RepoProfile,
)

# Define router (mounted under /v1 by the top-level v1_router)
auth_router = APIRouter(prefix="/auth", tags=["Auth"])

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


# =========================
# Pydantic models
# =========================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, description="Minimum 6 characters")
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class MeResponse(BaseModel):
    user: UserOut


# =========================
# Helpers
# =========================
def normalize_email(email: str) -> str:
    return email.strip().lower()


def to_user_out(user: RepoUser, profile: Optional[RepoProfile]) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=(profile.display_name if profile else None),
        avatar_url=(profile.avatar_url if profile else None),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> RepoUser:
    if not credentials or (credentials.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = credentials.credentials
    secret = get_auth_secret()
    try:
        payload = decode_jwt(token, secret, verify_exp=True)
    except JWTExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    user = get_user_by_id(db, subject)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[RepoUser]:
    """
    Optional auth dependency:
    - Returns RepoUser if valid bearer token supplied
    - Returns None if no header, wrong scheme, expired token, invalid signature, or user missing.
    Does NOT raise HTTPException (caller can decide fallback behavior).
    """
    if not credentials or (credentials.scheme or "").lower() != "bearer":
        return None
    token = credentials.credentials
    secret = get_auth_secret()
    try:
        payload = decode_jwt(token, secret, verify_exp=True)
    except (JWTExpiredError, JWTError):
        return None
    subject = payload.get("sub")
    if not subject:
        return None
    return get_user_by_id(db, subject)


# =========================
# Routes
# =========================
@auth_router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Local registration endpoint (dev only).
    - Creates a user with hashed password in public.users
    - Optionally upserts profile (display_name)
    - Returns access + refresh tokens and user info
    """
    email = normalize_email(body.email)
    try:
        user = create_user(db, email=email, password=body.password, commit=True)
    except EmailAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register user: {e}")

    profile = None
    try:
        if body.display_name:
            profile = upsert_profile(
                db,
                user_id=user.id,
                display_name=body.display_name,
                avatar_url=None,
                commit=True,
            )
        else:
            profile = get_profile(db, user_id=user.id)
    except Exception as e:
        # Non-fatal: user is created; fail profile silently with a warning detail
        profile = None

    secret = get_auth_secret()
    access = create_access_token(subject=user.id, secret=secret)
    refresh = create_refresh_token(subject=user.id, secret=secret)

    return AuthResponse(
        access_token=access,
        refresh_token=refresh,
        user=to_user_out(user, profile),
    )


@auth_router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Local login endpoint (dev only).
    - Verifies email/password
    - Updates last_login_at on success
    - Returns access + refresh tokens and user info
    """
    email = normalize_email(body.email)
    user = verify_user_credentials(
        db, email=email, password=body.password, update_last_login=True, commit=True
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    profile = get_profile(db, user_id=user.id)
    secret = get_auth_secret()
    access = create_access_token(subject=user.id, secret=secret)
    refresh = create_refresh_token(subject=user.id, secret=secret)

    return AuthResponse(
        access_token=access,
        refresh_token=refresh,
        user=to_user_out(user, profile),
    )


@auth_router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
)
def me(
    current_user: RepoUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return current authenticated user's info.
    Authorization: Bearer <access_token>
    """
    profile = get_profile(db, user_id=current_user.id)
    return MeResponse(user=to_user_out(current_user, profile))


# For compatibility with import styles like:
# from api.routes.auth import router
router = auth_router
