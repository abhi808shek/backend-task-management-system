from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, Table
from sqlalchemy.dialects.postgresql import JSONB  # Updated to JSONB for Postgres
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


# Association table for task subtasks (many-to-many)
task_subtasks = Table(
    'task_subtasks',
    Base.metadata,
    Column('parent_task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('subtask_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
)


# Association table for task comments/collaborators
task_comments = Table(
    'task_comments',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
)


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, enum.Enum):
    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    TASK = "task"


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    task_type = Column(Enum(TaskType), nullable=False, default=TaskType.TASK)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    status = Column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.TODO,
        index=True
    )
    priority = Column(
        Enum(TaskPriority),
        nullable=False,
        default=TaskPriority.MEDIUM,
        index=True
    )
    
    start_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    reporter_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    assignment_rules = Column(JSONB, nullable=False, default=dict)
    
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    creator = relationship("User", foreign_keys=[created_by], backref="created_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_tasks")
    reporter = relationship("User", foreign_keys=[reporter_id], backref="reported_tasks")
    organization = relationship("Organization", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    subtasks = relationship(
        "Task",
        secondary=task_subtasks,
        primaryjoin=id == task_subtasks.c.parent_task_id,
        secondaryjoin=id == task_subtasks.c.subtask_id,
        backref="parent_tasks"
    )
    comments = relationship(
        "User",
        secondary=task_comments,
        backref="task_comments"
    )
    
    def __repr__(self):
        return (
            f"<Task id={self.id} title='{self.title}' "
            f"project_id={self.project_id} org_id={self.organization_id} "
            f"status={self.status} assigned_to={self.assigned_to}>"
        )