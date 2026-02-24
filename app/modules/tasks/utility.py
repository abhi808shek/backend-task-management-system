from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.modules.tasks.model import Task, TaskStatus, TaskPriority
from app.modules.auth.model import User
from app.core.logger import logger


# ────────────────────────────────────────────────────────────────
# STATUS & TRANSITIONS
# ────────────────────────────────────────────────────────────────

def get_valid_status_transitions(current_status: str) -> list[str]:
    transitions = {
        "todo": ["in_progress"],
        "in_progress": ["done", "todo"],
        "done": [],
    }
    
    return transitions.get(current_status, [])


def can_transition_status(current_status: str, target_status: str) -> bool:
    if current_status == target_status:
        return True
    
    valid_transitions = get_valid_status_transitions(current_status)
    return target_status in valid_transitions


def validate_status_transition(current_status: str, target_status: str) -> None:
    if not can_transition_status(current_status, target_status):
        allowed = get_valid_status_transitions(current_status)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition '{current_status}' → '{target_status}'. Allowed: {allowed}",
        )


# ────────────────────────────────────────────────────────────────
# DATE UTILITIES
# ────────────────────────────────────────────────────────────────

def validate_date_range(start_date: datetime, due_date: datetime) -> bool:
    if due_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Due date must be after start date"
        )
    return True


def get_days_until_due(task: Task) -> int:
    if not task.due_date:
        return None
    
    today = datetime.now(task.due_date.tzinfo).date()
    due_date = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
    
    return (due_date - today).days


def is_task_overdue(task: Task) -> bool:
    if not task.due_date or task.status == TaskStatus.DONE:
        return False
    
    today = datetime.now(task.due_date.tzinfo).date()
    due_date = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
    
    return today > due_date


def is_task_due_soon(task: Task, days: int = 3) -> bool:
    if not task.due_date or task.status == TaskStatus.DONE:
        return False
    
    today = datetime.now(task.due_date.tzinfo).date()
    due_date = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
    days_until = (due_date - today).days
    
    return 0 <= days_until <= days


def get_task_progress(task: Task, subtasks: list) -> dict:
    if not subtasks:
        return {
            "total_subtasks": 0,
            "completed_subtasks": 0,
            "progress_percent": 100 if task.status == TaskStatus.DONE else 0
        }
    
    completed = sum(1 for st in subtasks if st.status == TaskStatus.DONE)
    total = len(subtasks)
    percent = int((completed / total) * 100) if total > 0 else 0
    
    return {
        "total_subtasks": total,
        "completed_subtasks": completed,
        "progress_percent": percent
    }


# ────────────────────────────────────────────────────────────────
# PERMISSION UTILITIES
# ────────────────────────────────────────────────────────────────

def can_user_edit_task(task: Task, user: User) -> bool:
    if task.created_by == user.id:
        return True
    
    if user.role == "admin":
        return True
    
    return False


def can_user_view_task(task: Task, user: User) -> bool:
    if task.created_by == user.id:
        return True
    
    if task.assigned_to == user.id:
        return True
    
    if user.role in ["admin", "manager"]:
        return True
    
    return False


def can_user_update_status(task: Task, user: User) -> bool:
    if task.assigned_to == user.id:
        return True
    
    if user.role in ["admin", "manager"]:
        return True
    
    return False


def validate_task_access(task: Task, user: User, require_edit: bool = False) -> None:
    if require_edit:
        if not can_user_edit_task(task, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this task"
            )
    else:
        if not can_user_view_task(task, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this task"
            )


# ────────────────────────────────────────────────────────────────
# TASK HEALTH & SUMMARY
# ────────────────────────────────────────────────────────────────

def get_task_health_status(task: Task) -> str:
    if task.status == TaskStatus.DONE:
        return "completed"
    
    if is_task_overdue(task):
        return "overdue"
    
    if is_task_due_soon(task, days=7):
        return "at_risk"
    
    return "healthy"


def format_task_summary(task: Task) -> dict:
    days_until = get_days_until_due(task)
    health = get_task_health_status(task)
    
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value if hasattr(task.status, 'value') else task.status,
        "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "days_until_due": days_until,
        "health_status": health,
        "assigned_to": task.assigned_to,
        "created_by": task.created_by,
    }


def get_task_metrics(db: Session, organization_id: int = None, project_id: int = None) -> dict:
    query = db.query(Task).filter(Task.is_active == True)
    
    if organization_id:
        query = query.filter(Task.organization_id == organization_id)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    tasks = query.all()
    
    total = len(tasks)
    todo = sum(1 for t in tasks if t.status == TaskStatus.TODO)
    in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    
    high_priority = sum(1 for t in tasks if t.priority == TaskPriority.HIGH and t.status != TaskStatus.DONE)
    overdue = sum(1 for t in tasks if is_task_overdue(t))
    
    return {
        "total_tasks": total,
        "todo_tasks": todo,
        "in_progress_tasks": in_progress,
        "completed_tasks": done,
        "high_priority_tasks": high_priority,
        "overdue_tasks": overdue,
    }


# ────────────────────────────────────────────────────────────────
# PRIORITY UTILITIES
# ────────────────────────────────────────────────────────────────

def get_priority_order(priority: str) -> int:
    order = {
        "low": 1,
        "medium": 2,
        "high": 3,
    }
    return order.get(priority, 0)


def sort_tasks_by_priority(tasks: list[Task]) -> list[Task]:
    return sorted(
        tasks,
        key=lambda t: (
            -get_priority_order(t.priority.value if hasattr(t.priority, 'value') else t.priority),
            t.due_date or datetime.max
        )
    )


# ────────────────────────────────────────────────────────────────
# VALIDATION UTILITIES
# ────────────────────────────────────────────────────────────────

def validate_task_ownership(task: Task, user: User, raise_error: bool = True) -> bool:
    is_creator = task.created_by == user.id or user.role == "admin"
    
    if not is_creator and raise_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only task creator can perform this action"
        )
    
    return is_creator


def validate_task_assignment(task: Task, user: User, raise_error: bool = True) -> bool:
    is_assigned = task.assigned_to == user.id
    
    if not is_assigned and raise_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to this task"
        )
    
    return is_assigned


# ────────────────────────────────────────────────────────────────
# LOGGING UTILITIES
# ────────────────────────────────────────────────────────────────

def log_task_activity(
    task_id: int,
    action: str,
    user_id: int,
    details: dict = None
) -> None:
    message = f"Task {task_id}: {action} by user {user_id}"
    if details:
        message += f" - {details}"
    
    logger.info(message)


def log_assignment(task_id: int, user_id: int, old_user_id: int = None) -> None:
    if old_user_id:
        logger.info(f"Task {task_id} reassigned: {old_user_id} → {user_id}")
    else:
        logger.info(f"Task {task_id} assigned to user {user_id}")