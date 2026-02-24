"""
app/modules/projects/utils.py

Utility functions for project management:
- Date calculations and validations
- Project status transitions
- Permission checks
- Data formatting helpers
"""

from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.modules.projects.model import Project, ProjectStatus, ProjectPriority
from app.modules.auth.model import User
from app.core.logger import logger


# ────────────────────────────────────────────────────────────────
# DATE UTILITIES
# ────────────────────────────────────────────────────────────────

def validate_date_range(start_date: date, end_date: date) -> bool:
    """
    Validate that end_date is after start_date.
    
    Args:
        start_date: Project start date
        end_date: Project end date
        
    Returns:
        True if valid, raises HTTPException otherwise
    """
    if end_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )
    return True


def calculate_project_duration(start_date: date, end_date: date) -> int:
    """
    Calculate project duration in days.
    
    Args:
        start_date: Project start date
        end_date: Project end date
        
    Returns:
        Number of days between start and end date
    """
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    
    return (end_date - start_date).days


def is_project_overdue(project: Project) -> bool:
    today = date.today()
    is_not_completed = project.status not in [
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED
    ]
    return project.end_date < today and is_not_completed


def get_days_until_deadline(project: Project) -> int:
    today = date.today()
    return (project.end_date - today).days


def is_project_starting_soon(project: Project, days_threshold: int = 7) -> bool:
    today = date.today()
    start_soon_date = today + timedelta(days=days_threshold)
    
    return today <= project.start_date <= start_soon_date


# ────────────────────────────────────────────────────────────────
# STATUS & PRIORITY UTILITIES
# ────────────────────────────────────────────────────────────────

def get_valid_status_transitions(current_status: ProjectStatus) -> list[ProjectStatus]:
    transitions = {
        ProjectStatus.NOT_STARTED: [
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.ON_HOLD,
            ProjectStatus.CANCELLED
        ],
        ProjectStatus.IN_PROGRESS: [
            ProjectStatus.ON_HOLD,
            ProjectStatus.COMPLETED,
            ProjectStatus.CANCELLED
        ],
        ProjectStatus.ON_HOLD: [
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.CANCELLED
        ],
        ProjectStatus.COMPLETED: [],
        ProjectStatus.CANCELLED: [],
    }
    
    return transitions.get(current_status, [])


def can_transition_status(
    current_status: ProjectStatus,
    target_status: ProjectStatus
) -> bool:
    if current_status == target_status:
        return True
    
    valid_transitions = get_valid_status_transitions(current_status)
    return target_status in valid_transitions


# ────────────────────────────────────────────────────────────────
# PERMISSION UTILITIES
# ────────────────────────────────────────────────────────────────

def can_user_edit_project(project: Project, user: User) -> bool:
    # Project owner can always edit
    if project.project_owner_id == user.id:
        return True
    
    # Admin can edit any project
    if user.role == "admin":
        return True
    
    return False


def can_user_view_project(project: Project, user: User) -> bool:
    # Owner can view
    if project.project_owner_id == user.id:
        return True
    
    # Team member can view
    if any(member.id == user.id for member in project.team_members):
        return True
    
    # Admin can view any project
    if user.role == "admin":
        return True
    
    return False


# ────────────────────────────────────────────────────────────────
# DATA FORMATTING UTILITIES
# ────────────────────────────────────────────────────────────────

def format_project_summary(project: Project) -> dict:
    duration_days = calculate_project_duration(project.start_date, project.end_date)
    is_overdue = is_project_overdue(project)
    days_until = get_days_until_deadline(project)
    
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status.value,
        "priority": project.priority.value,
        "start_date": project.start_date.isoformat(),
        "end_date": project.end_date.isoformat(),
        "duration_days": duration_days,
        "is_overdue": is_overdue,
        "days_until_deadline": days_until,
        "team_size": len(project.team_members),
        "owner_id": project.project_owner_id,
    }


def get_project_health_status(project: Project) -> str:
    if project.status == ProjectStatus.COMPLETED:
        return "completed"
    
    if project.status == ProjectStatus.CANCELLED:
        return "cancelled"
    
    if is_project_overdue(project):
        return "overdue"
    
    days_until = get_days_until_deadline(project)
    
    if days_until < 0:
        return "overdue"
    elif days_until <= 7:
        return "at_risk"
    elif is_project_starting_soon(project):
        return "at_risk"
    else:
        return "healthy"


# ────────────────────────────────────────────────────────────────
# VALIDATION UTILITIES
# ────────────────────────────────────────────────────────────────

def validate_project_ownership(
    project: Project,
    user: User,
    raise_error: bool = True
) -> bool:
    is_owner = project.project_owner_id == user.id or user.role == "admin"
    
    if not is_owner and raise_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can perform this action"
        )
    
    return is_owner


def validate_project_team_membership(
    project: Project,
    user: User,
    raise_error: bool = True
) -> bool:
    is_member = any(member.id == user.id for member in project.team_members)
    
    if not is_member and raise_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a team member of this project"
        )
    
    return is_member


def validate_project_access(
    project: Project,
    user: User,
    raise_error: bool = True
) -> bool:
    can_access = can_user_view_project(project, user)
    
    if not can_access and raise_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project"
        )
    
    return can_access


# ────────────────────────────────────────────────────────────────
# LOGGING UTILITIES
# ────────────────────────────────────────────────────────────────

def log_project_activity(
    project_id: int,
    action: str,
    user_id: int,
    details: dict = None
) -> None:
    message = f"Project {project_id}: {action} by user {user_id}"
    if details:
        message += f" - {details}"
    
    logger.info(message)