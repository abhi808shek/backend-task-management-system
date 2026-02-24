from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ────────────────────────────────────────────────────────────────
# ENUMS
# ────────────────────────────────────────────────────────────────
class TaskStatusEnum(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskTypeEnum(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    TASK = "task"


# ────────────────────────────────────────────────────────────────
# ASSIGNMENT RULES
# ────────────────────────────────────────────────────────────────

class AssignmentRules(BaseModel):
    """Rules for automatic task assignment"""
    department: Optional[str] = Field(
        default=None,
        pattern="^(Finance|HR|IT|Operations)$",
        description="Required department"
    )
    min_experience: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum years of experience"
    )
    max_active_tasks: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum active tasks allowed"
    )
    location: Optional[str] = Field(
        default=None,
        description="Required location"
    )

    model_config = {"extra": "allow"}  # forward-compatible: new rules won't break existing code


# ────────────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ────────────────────────────────────────────────────────────────

class SubTaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: int = Field(..., gt=0, description="User ID to assign to")
    priority: TaskPriorityEnum = Field(default=TaskPriorityEnum.MEDIUM)
    due_date: Optional[datetime] = None


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(default=None, max_length=2000, description="Task description")
    
    # Project & Organization
    organization_id: int = Field(..., gt=0, description="Organization ID")
    project_id: int = Field(..., gt=0, description="Project ID")
    
    # Task Details
    task_type: TaskTypeEnum = Field(default=TaskTypeEnum.TASK, description="Type of task")
    status: TaskStatusEnum = Field(default=TaskStatusEnum.TODO, description="Task status")
    priority: TaskPriorityEnum = Field(default=TaskPriorityEnum.MEDIUM, description="Task priority")
    
    # Dates
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    
    # Users
    assigned_to: Optional[int] = Field(default=None, gt=0, description="User ID to assign to")
    reporter_id: Optional[int] = Field(default=None, gt=0, description="Reporter/Creator user ID")
    
    # Rules
    assignment_rules: Optional[AssignmentRules] = Field(
        default_factory=AssignmentRules,
        description="Rules for automatic assignment"
    )
    
    # Subtasks
    subtasks: Optional[List[SubTaskCreateRequest]] = Field(default=None, description="List of subtasks")
    
    @field_validator('due_date')
    @classmethod
    def due_date_after_start_date(cls, v, info):
        if 'start_date' in info.data and info.data['start_date'] and v:
            if v <= info.data['start_date']:
                raise ValueError('Due date must be after start date')
        return v


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[TaskTypeEnum] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[int] = Field(default=None, gt=0)
    reporter_id: Optional[int] = Field(default=None, gt=0)
    assignment_rules: Optional[AssignmentRules] = None
    
    @field_validator('due_date')
    @classmethod
    def due_date_after_start_date(cls, v, info):
        if 'start_date' in info.data and info.data['start_date'] and v:
            if v <= info.data['start_date']:
                raise ValueError('Due date must be after start date')
        return v


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatusEnum = Field(..., description="New task status")


class AssignTaskRequest(BaseModel):
    assigned_to: int = Field(..., gt=0, description="User ID to assign to")


# ────────────────────────────────────────────────────────────────
# RESPONSE SCHEMAS
# ────────────────────────────────────────────────────────────────

class UserMinimalResponse(BaseModel):
    id: int
    name: str
    email: str
    department: Optional[str] = None
    experience_years: Optional[int] = None
    location: Optional[str] = None
    
    model_config = {"from_attributes": True}


class SubTaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    due_date: Optional[datetime]
    assigned_to: Optional[int]
    assignee: Optional[UserMinimalResponse] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    task_type: TaskTypeEnum
    organization_id: int
    project_id: int
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    start_date: Optional[datetime]
    due_date: Optional[datetime]
    assignment_rules: dict
    created_by: int
    assigned_to: Optional[int]
    reporter_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class TaskDetailResponse(TaskResponse):
    creator: Optional[UserMinimalResponse] = None
    assignee: Optional[UserMinimalResponse] = None
    reporter: Optional[UserMinimalResponse] = None
    subtasks: Optional[List[SubTaskResponse]] = None
    
    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    id: int
    title: str
    task_type: TaskTypeEnum
    organization_id: int
    project_id: int
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    due_date: Optional[datetime]
    assigned_to: Optional[int]
    assignee: Optional[UserMinimalResponse] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TaskCreateResponse(BaseModel):
    id: int
    title: str
    organization_id: int
    project_id: int
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    created_at: datetime
    
    model_config = {"from_attributes": True}


class EligibleUserResponse(BaseModel):
    id: int
    name: str
    email: str
    department: Optional[str]
    experience_years: Optional[int]
    location: Optional[str]
    active_task_count: int


class RecomputeResponse(BaseModel):
    task_id: int
    assigned_to: Optional[int]
    eligible_count: int
    message: str