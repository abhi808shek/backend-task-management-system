from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.modules.auth.model import User
from app.modules.tasks.schema import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskStatusUpdateRequest,
    SubTaskCreateRequest,
    TaskResponse,
    TaskDetailResponse,
    TaskListResponse,
    TaskCreateResponse,
    EligibleUserResponse,
)
from app.modules.tasks import service
from app.core.dependencies import get_current_user, require_admin_or_manager
from app.core.response import success
from app.routes.tasks import TASK_ROUTES, TASK_PREFIX, TASK_TAG

router = APIRouter(prefix=TASK_PREFIX, tags=[TASK_TAG])

_CLEAN_RESPONSES = {
    422: {"description": "excluded"},
    500: {"description": "excluded"},
}


# ════════════════════════════════════════════════════════
# CREATE TASK
# ════════════════════════════════════════════════════════

@router.post(
    TASK_ROUTES["create"],
    status_code=201,
    response_model=TaskCreateResponse,
    responses={
        201: {"description": "Task created successfully"},
        403: {"description": "Admin or Manager access required"},
        404: {"description": "Organization or Project not found"},
        **_CLEAN_RESPONSES,
    },
)
def create_task(
    data: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    # Override reporter/creator
    data_dict = data.model_dump()
    data_dict['created_by'] = current_user.id
    if not data_dict.get('reporter_id'):
        data_dict['reporter_id'] = current_user.id
    
    task = service.create_task(db, TaskCreateRequest(**data_dict), created_by=current_user.id)
    return success(
        data=TaskCreateResponse.model_validate(task),
        message="Task created successfully",
        status_code=201
    )


# ════════════════════════════════════════════════════════
# LIST TASKS
# ════════════════════════════════════════════════════════

@router.get(
    TASK_ROUTES["list"],
    response_model=list[TaskListResponse],
    responses={
        200: {"description": "Tasks fetched successfully"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def list_tasks(
    organization_id: int = Query(None, gt=0, description="Filter by organization"),
    project_id: int = Query(None, gt=0, description="Filter by project"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: str = Query(default=None, description="Filter by status"),
    priority: str = Query(default=None, description="Filter by priority"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks, total = service.get_all_tasks(
        db,
        organization_id=organization_id,
        project_id=project_id,
        skip=skip,
        limit=limit,
        status_filter=status,
        priority_filter=priority,
    )
    
    return success(
        data=[TaskListResponse.model_validate(t) for t in tasks],
        message=f"Retrieved {len(tasks)} tasks",
        meta={"total": total, "skip": skip, "limit": limit}
    )


# ════════════════════════════════════════════════════════
# GET USER'S TASKS
# ════════════════════════════════════════════════════════

@router.get(
    TASK_ROUTES["my_tasks"],
    responses={
        200: {"description": "Your assigned tasks"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = service.get_my_tasks(db, current_user.id)
    return success(
        data=tasks,
        message=f"Retrieved {len(tasks)} tasks assigned to you"
    )


# ════════════════════════════════════════════════════════
# GET PROJECT TASKS
# ════════════════════════════════════════════════════════

@router.get(
    TASK_ROUTES["project_tasks"],
    response_model=list[TaskListResponse],
    responses={
        200: {"description": "Project tasks retrieved"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def get_project_tasks(
    project_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
   
    tasks, total = service.get_project_tasks(
        db,
        project_id,
        skip=skip,
        limit=limit,
        status_filter=status,
    )
    
    return success(
        data=[TaskListResponse.model_validate(t) for t in tasks],
        message=f"Retrieved {len(tasks)} tasks from project",
        meta={"total": total, "skip": skip, "limit": limit}
    )


# ════════════════════════════════════════════════════════
# GET TASK DETAILS
# ════════════════════════════════════════════════════════

@router.get(
    TASK_ROUTES["get"],
    response_model=TaskDetailResponse,
    responses={
        200: {"description": "Task fetched successfully"},
        404: {"description": "Task not found"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = service.get_task_or_404(db, task_id)
    return success(
        data=TaskDetailResponse.model_validate(task),
        message="Task retrieved successfully"
    )


# ════════════════════════════════════════════════════════
# UPDATE TASK
# ════════════════════════════════════════════════════════

@router.patch(
    TASK_ROUTES["update"],
    response_model=TaskDetailResponse,
    responses={
        200: {"description": "Task updated successfully"},
        400: {"description": "Invalid request data"},
        404: {"description": "Task not found"},
        403: {"description": "Admin or Manager access required"},
        **_CLEAN_RESPONSES,
    },
)
def update_task(
    task_id: int,
    data: TaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    task = service.update_task(db, task_id, data)
    return success(
        data=TaskDetailResponse.model_validate(task),
        message="Task updated successfully"
    )


# ════════════════════════════════════════════════════════
# UPDATE TASK STATUS
# ════════════════════════════════════════════════════════

@router.patch(
    TASK_ROUTES["update_status"],
    response_model=TaskResponse,
    responses={
        200: {"description": "Status updated"},
        400: {"description": "Invalid status transition"},
        403: {"description": "Not authorized"},
        404: {"description": "Task not found"},
        **_CLEAN_RESPONSES,
    },
)
def update_task_status(
    task_id: int,
    data: TaskStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = service.get_task_or_404(db, task_id)

    if task.assigned_to != current_user.id and current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned user or admin/manager can update task status",
        )

    transitions = {
        "todo": ["in_progress"],
        "in_progress": ["done", "todo"],
        "done": [],
    }
    allowed = transitions.get(task.status.value, [])
    if data.status.value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition '{task.status.value}' → '{data.status.value}'. Allowed: {allowed}",
        )

    task = service.update_task_status(db, task, data.status.value)
    return success(
        data=TaskResponse.model_validate(task),
        message=f"Task status updated to '{data.status.value}'"
    )


# ════════════════════════════════════════════════════════
# ADD SUBTASK
# ════════════════════════════════════════════════════════

@router.post(
    TASK_ROUTES["add_subtask"],
    response_model=TaskDetailResponse,
    responses={
        201: {"description": "Subtask created"},
        404: {"description": "Parent task not found"},
        403: {"description": "Admin or Manager access required"},
        **_CLEAN_RESPONSES,
    },
)
def add_subtask(
    task_id: int,
    data: SubTaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    service.create_subtask(db, task_id, data)
    task = service.get_task_or_404(db, task_id)
    return success(
        data=TaskDetailResponse.model_validate(task),
        message="Subtask created successfully",
        status_code=201
    )


# ════════════════════════════════════════════════════════
# DELETE TASK
# ════════════════════════════════════════════════════════

@router.delete(
    TASK_ROUTES["delete"],
    responses={
        200: {"description": "Task deleted"},
        404: {"description": "Task not found"},
        403: {"description": "Admin or Manager access required"},
        **_CLEAN_RESPONSES,
    },
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    result = service.delete_task(db, task_id)
    return success(data=None, message=result["message"])


# ════════════════════════════════════════════════════════
# GET ELIGIBLE USERS
# ════════════════════════════════════════════════════════

@router.get(
    TASK_ROUTES["eligible_users"],
    response_model=list[EligibleUserResponse],
    responses={
        200: {"description": "Eligible users list"},
        404: {"description": "Task not found"},
        403: {"description": "Admin or Manager access required"},
        **_CLEAN_RESPONSES,
    },
)
def get_eligible_users(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
  
    users = service.get_eligible_users_for_task(db, task_id)
    return success(
        data=users,
        message=f"{len(users)} eligible user(s) found"
    )


# ════════════════════════════════════════════════════════
# RECOMPUTE ELIGIBILITY
# ════════════════════════════════════════════════════════

@router.post(
    TASK_ROUTES["recompute"],
    responses={
        200: {"description": "Recompute completed"},
        404: {"description": "Task not found"},
        403: {"description": "Admin or Manager access required"},
        **_CLEAN_RESPONSES,
    },
)
def recompute_eligibility(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
 
    from app.modules.tasks.rule_engine import find_eligible_users, recompute_single
    from app.db.session import SessionLocal

    task = service.get_task_or_404(db, task_id)
    eligible = find_eligible_users(db, task.assignment_rules or {})
    
    db2 = SessionLocal()
    try:
        assigned_to = recompute_single(db2, task_id)
    finally:
        db2.close()

    return success(
        data={
            "task_id": task_id,
            "assigned_to": assigned_to,
            "eligible_count": len(eligible)
        },
        message="Assigned successfully" if assigned_to else "No eligible user found",
    )