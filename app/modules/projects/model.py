from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Date, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


# Association table for many-to-many relationship between projects and team members
project_team_members = Table(
    'project_team_members',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
)


class ProjectStatus(str, enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class ProjectPriority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(
        Enum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.NOT_STARTED,
        index=True
    )
    priority = Column(
        Enum(ProjectPriority),
        nullable=False,
        default=ProjectPriority.MEDIUM,
        index=True
    )
    project_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    project_owner = relationship("User", foreign_keys=[project_owner_id], back_populates="owned_projects")
    team_members = relationship(
        "User",
        secondary=project_team_members,
        back_populates="assigned_projects",
        lazy="selectin"
    )
    organization = relationship("Organization", back_populates="projects")
    
    def __repr__(self):
        return f"<Project id={self.id} name={self.name} org_id={self.organization_id} status={self.status}>"


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Organization id={self.id} name={self.name}>"