from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.modules.projects.model import Project, ProjectStatus, ProjectPriority
from app.modules.projects.schema import (
    CreateProjectRequest,
    UpdateProjectRequest,
    AssignTeamMembersRequest,
    ProjectResponse,
    ProjectListResponse,
    ProjectCreateResponse,
)
from app.modules.projects import service
from app.core.dependencies import get_current_user
from app.core.response import success
from app.modules.auth.model import User
from app.routes.projects import PROJECT_PREFIX, PROJECT_TAG,PROJECT_ROUTES



# ── Clean response config ────────────────────────────────
_CLEAN_RESPONSES = {
    422: {"description": "excluded"},
    500: {"description": "excluded"},
}

router = APIRouter(prefix=PROJECT_PREFIX, tags=[PROJECT_TAG])


# ════════════════════════════════════════════════════════
# CREATE PROJECT
# ════════════════════════════════════════════════════════

@router.post(
    PROJECT_ROUTES["create"],
    status_code=201,
    response_model=ProjectCreateResponse,
    responses={
        201: {"description": "Project created successfully"},
        400: {"description": "Invalid request data"},
        404: {"description": "Organization, owner, or team member not found"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def create_project(
    data: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = service.create_project(db, data)
    return success(
        data=ProjectCreateResponse.from_orm(project),
        message="Project created successfully",
        status_code=201
    )


# ════════════════════════════════════════════════════════
# GET PROJECT
# ════════════════════════════════════════════════════════

@router.get(
    PROJECT_ROUTES["get"],
    response_model=ProjectResponse,
    responses={
        200: {"description": "Project found"},
        404: {"description": "Project not found"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific project"""
    project = service.get_project(db, project_id)
    return success(
        data=ProjectResponse.from_orm(project),
        message="Project retrieved successfully"
    )


# ════════════════════════════════════════════════════════
# LIST PROJECTS FOR ORGANIZATION
# ════════════════════════════════════════════════════════

@router.get(
    PROJECT_ROUTES["list_org"],
    response_model=list[ProjectListResponse],
    responses={
        200: {"description": "Projects retrieved"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def list_org_projects(
    org_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: ProjectStatus = Query(None, description="Filter by status"),
    priority: ProjectPriority = Query(None, description="Filter by priority"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects, total = service.get_projects_by_organization(
        db,
        org_id,
        skip=skip,
        limit=limit,
        status_filter=status,
        priority_filter=priority,
    )
    
    return success(
        data=[ProjectListResponse.from_orm(p) for p in projects],
        message=f"Retrieved {len(projects)} projects from organization",
        meta={"total": total, "skip": skip, "limit": limit}
    )


# ════════════════════════════════════════════════════════
# LIST USER'S PROJECTS
# ════════════════════════════════════════════════════════

@router.get(
    PROJECT_ROUTES["list_user"],
    response_model=list[ProjectListResponse],
    responses={
        200: {"description": "User's projects retrieved"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def list_user_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects, total = service.get_user_projects(
        db,
        current_user.id,
        skip=skip,
        limit=limit,
    )
    
    return success(
        data=[ProjectListResponse.from_orm(p) for p in projects],
        message=f"Retrieved {len(projects)} projects for user",
        meta={"total": total, "skip": skip, "limit": limit}
    )


# ════════════════════════════════════════════════════════
# UPDATE PROJECT
# ════════════════════════════════════════════════════════

@router.patch(
    PROJECT_ROUTES["update"],
    response_model=ProjectResponse,
    responses={
        200: {"description": "Project updated"},
        400: {"description": "Invalid request data"},
        404: {"description": "Project or related entity not found"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def update_project(
    project_id: int,
    data: UpdateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = service.update_project(db, project_id, data)
    return success(
        data=ProjectResponse.from_orm(project),
        message="Project updated successfully"
    )


# ════════════════════════════════════════════════════════
# ASSIGN TEAM MEMBERS
# ════════════════════════════════════════════════════════

@router.post(
    PROJECT_ROUTES["assign_team"],
    response_model=ProjectResponse,
    responses={
        200: {"description": "Team members assigned"},
        400: {"description": "Invalid team members"},
        404: {"description": "Project not found"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def assign_team_members(
    project_id: int,
    data: AssignTeamMembersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = service.assign_team_members(db, project_id, data)
    return success(
        data=ProjectResponse.from_orm(project),
        message="Team members assigned successfully"
    )


# ════════════════════════════════════════════════════════
# DELETE PROJECT
# ════════════════════════════════════════════════════════

@router.delete(
    PROJECT_ROUTES["delete"],
    status_code=204,
    responses={
        204: {"description": "Project deleted"},
        404: {"description": "Project not found"},
        401: {"description": "Unauthorized"},
        **_CLEAN_RESPONSES,
    },
)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_project(db, project_id)
    return success(message="Project deleted successfully", status_code=204)
