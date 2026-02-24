from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import datetime
from app.modules.tasks.model import Task, TaskStatus, TaskPriority, TaskType
from app.modules.tasks.schema import (
    TaskCreateRequest,
    TaskUpdateRequest,
    SubTaskCreateRequest,
)
from app.core import cache
from app.core.logger import logger


# ================================================================
# BASIC CRUD OPERATIONS
# ================================================================

def get_task_or_404(db: Session, task_id: int) -> Task:
    """Get a task by ID or raise 404"""
    task = db.query(Task).filter(Task.id == task_id, Task.is_active == True).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return task


# ================================================================
# STORY 1 — Admin Creates Task with Rules
# ================================================================

def create_task(db: Session, data: TaskCreateRequest, created_by: int) -> Task:
    # Validate organization and project exist
    from app.modules.projects.model import Project
    from app.modules.projects.model import Organization
    
    org = db.query(Organization).filter(Organization.id == data.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {data.organization_id} not found",
        )
    
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {data.project_id} not found",
        )
    
    if project.organization_id != data.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project {data.project_id} does not belong to organization {data.organization_id}",
        )
    
    # Validate assigned user if provided
    if data.assigned_to:
        from app.modules.auth.model import User
        user = db.query(User).filter(User.id == data.assigned_to).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assigned user {data.assigned_to} not found or inactive",
            )
    
    try:
        task = Task(
            title=data.title,
            description=data.description,
            task_type=data.task_type,
            organization_id=data.organization_id,
            project_id=data.project_id,
            status=data.status,
            priority=data.priority,
            start_date=data.start_date,
            due_date=data.due_date,
            created_by=created_by,
            assigned_to=data.assigned_to,
            reporter_id=data.reporter_id,
            assignment_rules=data.assignment_rules.model_dump(exclude_none=True) if data.assignment_rules else {},
        )
        db.add(task)
        db.commit()
        db.refresh(task)
    except Exception as e:
        db.rollback()
        logger.error(f"[CreateTask] DB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task. Please try again.",
        )
    
    # Create subtasks if provided
    if data.subtasks:
        for subtask_data in data.subtasks:
            create_subtask(db, task.id, subtask_data)
    
    # Story 1: background assignment — never blocks the API
    _dispatch(task.id, queue="critical")
    logger.info(
        f"[Story1] Task {task.id} created by User {created_by} "
        f"in Project {data.project_id}. Assignment dispatched."
    )
    
    return task


def create_subtask(db: Session, parent_task_id: int, data: SubTaskCreateRequest) -> Task:
    parent_task = get_task_or_404(db, parent_task_id)
    
    try:
        subtask = Task(
            title=data.title,
            description=data.description,
            task_type=TaskType.TASK,
            organization_id=parent_task.organization_id,
            project_id=parent_task.project_id,
            status=TaskStatus.TODO,
            priority=data.priority,
            due_date=data.due_date,
            created_by=parent_task.created_by,
            assigned_to=data.assigned_to,
            assignment_rules={},
        )
        db.add(subtask)
        parent_task.subtasks.append(subtask)
        db.commit()
        db.refresh(subtask)
    except Exception as e:
        db.rollback()
        logger.error(f"[CreateSubtask] DB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subtask",
        )
    
    return subtask


# ================================================================
# STORY 4 — Admin Updates Rules → Recompute
# ================================================================

def update_task(db: Session, task_id: int, data: TaskUpdateRequest) -> Task:
    task = get_task_or_404(db, task_id)
    rules_changed = False
    old_assignee = task.assigned_to

    try:
        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
        if data.task_type is not None:
            task.task_type = data.task_type
        if data.status is not None:
            task.status = data.status
        if data.priority is not None:
            task.priority = data.priority
        if data.start_date is not None:
            task.start_date = data.start_date
        if data.due_date is not None:
            task.due_date = data.due_date
        if data.assigned_to is not None:
            task.assigned_to = data.assigned_to
        if data.reporter_id is not None:
            task.reporter_id = data.reporter_id
        
        if data.assignment_rules is not None:
            new_rules = data.assignment_rules.model_dump(exclude_none=True)
            if new_rules != task.assignment_rules:
                task.assignment_rules = new_rules
                rules_changed = True

        db.commit()
        db.refresh(task)
    except Exception as e:
        db.rollback()
        logger.error(f"[UpdateTask] DB error for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task. Please try again.",
        )

    if rules_changed:
        # Story 4: clear stale cache for both task and old assignee
        cache.invalidate_task(task_id)
        if old_assignee:
            cache.invalidate_user(old_assignee)

        # Story 4: recompute with new rules
        _dispatch(task.id, queue="critical")
        logger.info(
            f"[Story4] Task {task_id} rules changed. "
            f"Cache cleared. Recompute dispatched. Old assignee={old_assignee}"
        )

    return task


def update_task_status(db: Session, task: Task, new_status: str) -> Task:
    old_assignee = task.assigned_to
    try:
        task.status = new_status
        db.commit()
        db.refresh(task)
    except Exception as e:
        db.rollback()
        logger.error(f"[UpdateStatus] DB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task status.",
        )

    if old_assignee:
        cache.invalidate_user(old_assignee)  # refreshes my_tasks + active_count

    return task


def delete_task(db: Session, task_id: int) -> dict:
    task = get_task_or_404(db, task_id)
    old_assignee = task.assigned_to

    try:
        task.is_active = False
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[DeleteTask] DB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task.",
        )

    cache.invalidate_assignment(old_assignee, None, task_id)
    logger.info(f"Task {task_id} soft-deleted.")
    return {"message": f"Task {task_id} deleted successfully"}


# ================================================================
# QUERY OPERATIONS
# ================================================================

def get_all_tasks(
    db: Session,
    organization_id: int = None,
    project_id: int = None,
    skip: int = 0,
    limit: int = 20,
    status_filter: str = None,
    priority_filter: str = None,
) -> tuple[list[Task], int]:
    query = db.query(Task).filter(Task.is_active == True)
    
    if organization_id:
        query = query.filter(Task.organization_id == organization_id)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    
    return tasks, total


def get_project_tasks(
    db: Session,
    project_id: int,
    skip: int = 0,
    limit: int = 20,
    status_filter: str = None,
) -> tuple[list[Task], int]:
    """Get all tasks for a project"""
    query = db.query(Task).filter(
        Task.project_id == project_id,
        Task.is_active == True
    )
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    total = query.count()
    tasks = query.order_by(Task.priority.desc(), Task.due_date.asc()).offset(skip).limit(limit).all()
    
    return tasks, total


# ================================================================
# STORY 2 — User Views Eligible Tasks (highly optimised)
# ================================================================

def get_my_tasks(db: Session, user_id: int) -> list:
    ck = cache.key_my_tasks(user_id)
    cached = cache.cache_get(ck)
    if cached is not None:
        logger.debug(f"[Story2] my_tasks for user {user_id} → CACHE HIT")
        return cached

    logger.debug(f"[Story2] my_tasks for user {user_id} → DB QUERY")
    tasks = (
        db.query(Task)
        .filter(
            Task.assigned_to == user_id,
            Task.is_active == True,
            Task.status != TaskStatus.DONE,
        )
        .order_by(Task.priority.desc(), Task.due_date.asc())
        .all()
    )

    result = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type.value,
            "status": t.status.value,
            "priority": t.priority.value,
            "due_date": str(t.due_date) if t.due_date else None,
            "organization_id": t.organization_id,
            "project_id": t.project_id,
            "assignment_rules": t.assignment_rules,
            "created_by": t.created_by,
            "assigned_to": t.assigned_to,
            "is_active": t.is_active,
            "created_at": str(t.created_at),
            "updated_at": str(t.updated_at),
        }
        for t in tasks
    ]

    cache.cache_set(ck, result, ttl=60)
    return result


def get_eligible_users_for_task(db: Session, task_id: int) -> list:
    ck = cache.key_eligible_users(task_id)
    cached = cache.cache_get(ck)
    if cached is not None:
        return cached

    task = get_task_or_404(db, task_id)
    from app.modules.tasks.rule_engine import find_eligible_users, get_active_count
    users = find_eligible_users(db, task.assignment_rules or {})

    result = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "department": u.department,
            "experience_years": u.experience_years,
            "location": u.location,
            "active_task_count": get_active_count(db, u.id),
        }
        for u in users
    ]

    cache.cache_set(ck, result, ttl=120)
    return result


# ================================================================
# INTERNAL DISPATCH HELPER
# ================================================================

def _dispatch(task_id: int, queue: str = "critical") -> None:
    try:
        import redis as redis_lib
        from app.core.config import settings
        r = redis_lib.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        r.ping()

        from app.workers.celery_worker import async_assign_task
        async_assign_task.apply_async(args=[task_id], queue=queue, retry=False)
        logger.info(f"[Dispatch] Task {task_id} → Celery [{queue}]")

    except Exception as e:
        logger.warning(f"[Dispatch] Redis down ({e}). Running sync for task {task_id}.")
        _run_sync(task_id)


def _run_sync(task_id: int) -> None:
    from app.db.session import SessionLocal
    from app.modules.tasks.rule_engine import recompute_single
    import time

    db = SessionLocal()
    try:
        start = time.time()
        assigned_to = recompute_single(db, task_id)
        logger.info(
            f"[SyncFallback] Task {task_id} → user={assigned_to} | "
            f"{round((time.time()-start)*1000,2)}ms"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"[SyncFallback] Task {task_id} failed: {e}")
    finally:
        db.close()