"""
auth/service.py

Story 3 — User Data Changes:
  When department / experience_years / location changes:
    → dispatch_user_recompute(user_id) called immediately
    → Celery picks it up (or runs sync if Redis down)
    → recompute_for_user_profile_change() re-evaluates ALL unassigned tasks
    → Tasks that now match the updated user get assigned to them
    → User's cache invalidated so next GET /my-eligible-tasks is fresh
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.modules.auth.model import User
from app.modules.auth.schema import RegisterRequest, UpdateProfileRequest
from app.core.security import hash_password
from app.core.logger import logger

ELIGIBILITY_FIELDS = {"department", "experience_years", "location"}


def register_user(db: Session, data: RegisterRequest) -> User:
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        department=data.department,
        experience_years=data.experience_years,
        location=data.location,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # New user may be eligible for existing unassigned tasks — trigger recompute
    logger.info(f"New user registered: {user.email} (role={user.role}). Triggering recompute.")
    _trigger_recompute(user.id)

    return user


def update_user_profile(db: Session, user_id: int, data: UpdateProfileRequest) -> User:
    """
    Story 3 — User Data Changes:
    Detects which eligibility fields changed, triggers background recompute if any did.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Track which eligibility-affecting fields actually changed
    changed_fields = []

    if data.name is not None:
        user.name = data.name

    if data.department is not None and data.department != user.department:
        user.department = data.department
        changed_fields.append("department")

    if data.experience_years is not None and data.experience_years != user.experience_years:
        user.experience_years = data.experience_years
        changed_fields.append("experience_years")

    if data.location is not None and data.location != user.location:
        user.location = data.location
        changed_fields.append("location")

    db.commit()
    db.refresh(user)

    if changed_fields:
        logger.info(
            f"User {user_id} eligibility fields changed: {changed_fields}. "
            f"Triggering background recompute."
        )
        # Story 3: automatically recompute eligibility
        _trigger_recompute(user_id)
    else:
        logger.info(f"User {user_id} profile updated. No eligibility fields changed — skipping recompute.")

    return user


def _trigger_recompute(user_id: int) -> None:
    """
    Dispatches recompute via Celery (or sync fallback if Redis is down).
    Never raises — profile update always succeeds regardless of Redis state.
    """
    try:
        from app.workers.celery_worker import dispatch_user_recompute
        dispatch_user_recompute(user_id)
    except Exception as e:
        logger.error(f"[Story3] Recompute dispatch failed for user {user_id}: {e}")