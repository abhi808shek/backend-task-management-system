from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# ────────────────────────────────────────────────────────────────
# ENUMS
# ────────────────────────────────────────────────────────────────

class ProjectStatusEnum(str, Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class ProjectPriorityEnum(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


# ────────────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(default=None, max_length=2000, description="Project description")
    organization_id: int = Field(..., gt=0, description="Organization ID")
    start_date: date = Field(..., description="Project start date")
    end_date: date = Field(..., description="Project end date")
    status: ProjectStatusEnum = Field(default=ProjectStatusEnum.NOT_STARTED, description="Project status")
    priority: ProjectPriorityEnum = Field(default=ProjectPriorityEnum.MEDIUM, description="Project priority")
    project_owner_id: int = Field(..., gt=0, description="Project owner/manager user ID")
    team_member_ids: Optional[List[int]] = Field(default=None, description="List of team member user IDs")
    
    @field_validator('end_date')
    @classmethod
    def end_date_must_be_after_start_date(cls, v, info):
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError('End date must be after start date')
        return v


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatusEnum] = None
    priority: Optional[ProjectPriorityEnum] = None
    project_owner_id: Optional[int] = Field(default=None, gt=0)
    team_member_ids: Optional[List[int]] = None
    
    @field_validator('end_date')
    @classmethod
    def end_date_must_be_after_start_date(cls, v, info):
        """Validate that end_date is after start_date"""
        if 'start_date' in info.data and info.data['start_date'] is not None:
            if v <= info.data['start_date']:
                raise ValueError('End date must be after start date')
        return v


class AssignTeamMembersRequest(BaseModel):
    team_member_ids: List[int] = Field(..., min_length=1, description="List of user IDs to assign")


# ────────────────────────────────────────────────────────────────
# RESPONSE SCHEMAS
# ────────────────────────────────────────────────────────────────

class UserMinimalResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    
    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    organization_id: int
    start_date: date
    end_date: date
    status: ProjectStatusEnum
    priority: ProjectPriorityEnum
    project_owner: UserMinimalResponse
    team_members: List[UserMinimalResponse]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    organization_id: int
    start_date: date
    end_date: date
    status: ProjectStatusEnum
    priority: ProjectPriorityEnum
    project_owner: UserMinimalResponse
    team_members_count: int
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectCreateResponse(BaseModel):
    id: int
    name: str
    organization_id: int
    status: ProjectStatusEnum
    priority: ProjectPriorityEnum
    created_at: datetime
    
    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}