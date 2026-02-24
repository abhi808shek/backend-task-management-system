from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.session import get_db
from app.modules.auth.model import User
from app.modules.auth.schema import (
    RegisterRequest, LoginRequest, RefreshRequest, UpdateProfileRequest,
)
from app.modules.auth import service
from app.core.security import verify_password
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.response import success

from app.routes.auth import AUTH_ROUTES, AUTH_PREFIX, AUTH_TAG

router = APIRouter(prefix=AUTH_PREFIX, tags=[AUTH_TAG])

_CLEAN_RESPONSES = {
    422: {"description": "excluded"},
    500: {"description": "excluded"},
}


@router.post(
    AUTH_ROUTES["signup"],
    status_code=201,
    responses={
        201: {"description": "User registered successfully"},
        400: {"description": "Email already registered"},
        **_CLEAN_RESPONSES,
    },
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    user = service.register_user(db, data)
    return success(data=_serialize_user(user), message="User registered successfully", status_code=201)


@router.post(
    AUTH_ROUTES["login"],
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account inactive"},
        **_CLEAN_RESPONSES,
    },
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact support.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return success(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": _serialize_user(user),
        },
        message="Login successful",
    )


@router.post(
    AUTH_ROUTES["refresh"],
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
        **_CLEAN_RESPONSES,
    },
)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired",
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — must use refresh token",
        )

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access = create_access_token(
        data={"sub": str(user.id), "type": "access"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh = create_refresh_token(
        data={"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return success(
        data={"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"},
        message="Token refreshed successfully",
    )


@router.get(
    AUTH_ROUTES["profile"],
    responses={
        200: {"description": "Current user info"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def me(current_user: User = Depends(get_current_user)):
    return success(data=_serialize_user(current_user), message="User fetched successfully")


@router.patch(
    AUTH_ROUTES["update_profile"],
    responses={
        200: {"description": "Profile updated"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def update_profile(
    data: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = service.update_user_profile(db, current_user.id, data)
    return success(data=_serialize_user(user), message="Profile updated successfully")


# ================================================================
# SERIALIZER
# ================================================================

def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "department": user.department,
        "experience_years": user.experience_years,
        "location": user.location,
        "is_active": user.is_active,
        "created_at": str(user.created_at),
    }