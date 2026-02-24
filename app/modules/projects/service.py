from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import date, datetime
from app.modules.projects.model import Project, Organization, ProjectStatus, ProjectPriority
from app.modules.auth.model import User
from app.modules.projects.schema import (
    CreateProjectRequest,
    UpdateProjectRequest,
    AssignTeamMembersRequest,
)
from app.core.logger import logger


def create_project(db: Session, data: CreateProjectRequest) -> Project:
    org = db.query(Organization).filter(Organization.id == data.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with id {data.organization_id} not found",
        )
    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create project in an inactive organization",
        )
    
    owner = db.query(User).filter(User.id == data.project_owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project owner with id {data.project_owner_id} not found",
        )
    if not owner.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project owner is inactive",
        )
    
    team_members = []
    if data.team_member_ids:
        team_members = db.query(User).filter(
            User.id.in_(data.team_member_ids),
            User.is_active == True
        ).all()
        
        if len(team_members) != len(data.team_member_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more team members not found or inactive",
            )
    
    project = Project(
        name=data.name,
        description=data.description,
        organization_id=data.organization_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        priority=data.priority,
        project_owner_id=data.project_owner_id,
        is_active=True,
    )
    
    # Assign team members
    if team_members:
        project.team_members = team_members
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    logger.info(
        f"Project created: id={project.id} name={project.name} "
        f"org_id={project.organization_id} owner_id={project.project_owner_id}"
    )
    
    # Trigger any necessary background processes (e.g., notifications, rule engine)
    _trigger_project_created(project.id)
    
    return project


def update_project(db: Session, project_id: int, data: UpdateProjectRequest) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    
    changed_fields = []
    
    if data.name is not None and data.name != project.name:
        project.name = data.name
        changed_fields.append("name")
    
    if data.description is not None and data.description != project.description:
        project.description = data.description
        changed_fields.append("description")
    
    if data.start_date is not None and data.start_date != project.start_date:
        project.start_date = data.start_date
        changed_fields.append("start_date")
    
    if data.end_date is not None and data.end_date != project.end_date:
        project.end_date = data.end_date
        changed_fields.append("end_date")
    
    if data.status is not None and data.status != project.status:
        project.status = data.status
        changed_fields.append("status")
    
    if data.priority is not None and data.priority != project.priority:
        project.priority = data.priority
        changed_fields.append("priority")
    
    if data.project_owner_id is not None and data.project_owner_id != project.project_owner_id:
        owner = db.query(User).filter(User.id == data.project_owner_id).first()
        if not owner or not owner.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive project owner",
            )
        project.project_owner_id = data.project_owner_id
        changed_fields.append("project_owner_id")
    
    if data.team_member_ids is not None:
        team_members = db.query(User).filter(
            User.id.in_(data.team_member_ids),
            User.is_active == True
        ).all()
        
        if len(team_members) != len(data.team_member_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more team members not found or inactive",
            )
        
        project.team_members = team_members
        changed_fields.append("team_members")
    
    db.commit()
    db.refresh(project)
    
    if changed_fields:
        logger.info(
            f"Project {project_id} updated. Changed fields: {changed_fields}"
        )
        _trigger_project_updated(project.id, changed_fields)
    
    return project


def get_project(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    return project


def get_projects_by_organization(
    db: Session,
    organization_id: int,
    skip: int = 0,
    limit: int = 20,
    status_filter: ProjectStatus = None,
    priority_filter: ProjectPriority = None,
) -> tuple[list[Project], int]:
    query = db.query(Project).filter(
        Project.organization_id == organization_id,
        Project.is_active == True
    )
    
    if status_filter:
        query = query.filter(Project.status == status_filter)
    
    if priority_filter:
        query = query.filter(Project.priority == priority_filter)
    
    total = query.count()
    projects = query.offset(skip).limit(limit).all()
    
    return projects, total


def get_user_projects(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Project], int]:
    query = db.query(Project).filter(
        or_(
            Project.project_owner_id == user_id,
            Project.team_members.any(User.id == user_id)
        ),
        Project.is_active == True
    )
    
    total = query.count()
    projects = query.offset(skip).limit(limit).all()
    
    return projects, total


def assign_team_members(
    db: Session,
    project_id: int,
    data: AssignTeamMembersRequest,
) -> Project:
    project = get_project(db, project_id)
    
    team_members = db.query(User).filter(
        User.id.in_(data.team_member_ids),
        User.is_active == True
    ).all()
    
    if len(team_members) != len(data.team_member_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more team members not found or inactive",
        )
    
    project.team_members = team_members
    db.commit()
    db.refresh(project)
    
    logger.info(f"Team members assigned to project {project_id}")
    
    return project


def delete_project(db: Session, project_id: int) -> None:
    project = get_project(db, project_id)
    project.is_active = False
    db.commit()
    
    logger.info(f"Project {project_id} deleted (soft delete)")


def _trigger_project_created(project_id: int) -> None:
    try:
        logger.info(f"Project creation side effects triggered for project {project_id}")
    except Exception as e:
        logger.error(f"Failed to trigger project creation side effects: {e}")


def _trigger_project_updated(project_id: int, changed_fields: list) -> None:
    try:
        logger.info(
            f"Project update side effects triggered for project {project_id}. "
            f"Changed fields: {changed_fields}"
        )
    except Exception as e:
        logger.error(f"Failed to trigger project update side effects: {e}")