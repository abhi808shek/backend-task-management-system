# Project Management Module - Complete Documentation

Production-ready FastAPI + PostgreSQL project management system with multi-organization and team collaboration support.

## Overview

This module provides a comprehensive project management system with:
- Project CRUD operations
- Multi-organization support
- Team member assignment and management
- Status and priority tracking
- Date-based project scheduling
- Comprehensive permission system
- Activity logging and audit trails

## Architecture

### Layered Architecture

```
API Layer (api.py)
    ↓
Service Layer (service.py)
    ↓
Data Access Layer (model.py)
    ↓
Database (PostgreSQL)
```

### Module Components

| File | Purpose |
|------|---------|
| **model.py** | Project, Organization entities and relationships |
| **schema.py** | Pydantic request/response validation |
| **service.py** | CRUD operations, validations, business logic |
| **api.py** | FastAPI endpoints |
| **utils.py** | Status transitions, dates, permissions |
| **routes.py** | Route configuration |

## Database Schema

### Project Table

Projects store work at an organizational level. Each project belongs to an organization and has an owner.

**Fields:**
- `id` - Primary key
- `name` - Project name (required, max 255 chars)
- `description` - Project details (optional, max 2000 chars)
- `organization_id` - Organization reference
- `start_date` - Project start date
- `end_date` - Project end date
- `status` - Current status (Not Started, In Progress, On Hold, Completed, Cancelled)
- `priority` - Project priority (Low, Medium, High, Critical)
- `project_owner_id` - User who owns project
- `is_active` - Soft delete flag
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

**Indexes:**
- organization_id - For filtering by organization
- project_owner_id - For owner queries
- status - For status filtering
- priority - For priority filtering
- is_active - For active projects only

### Project Team Members (Many-to-Many)

Associates users with projects as team members. Allows one project to have multiple team members and users to be on multiple projects.

**Relationship:** One project can have multiple team members. One user can be on multiple project teams.

## Data Models

### Project Model

```python
class Project(Base):
    # Identifiers
    id: int                          # Primary key
    
    # Content
    name: str                        # Project name (required)
    description: Optional[str]       # Project details
    
    # Organization & Dates
    organization_id: int             # FK to organizations
    start_date: date                 # Project start
    end_date: date                   # Project end (must be after start)
    
    # Status & Priority
    status: ProjectStatus enum       # Not Started, In Progress, On Hold, Completed, Cancelled
    priority: ProjectPriority enum   # Low, Medium, High, Critical
    
    # Users
    project_owner_id: int            # FK to users (project owner)
    team_members: List[User]         # Many-to-many relationship
    
    # Metadata
    is_active: bool                  # Soft delete flag
    created_at: datetime             # Created timestamp
    updated_at: datetime             # Updated timestamp
    
    # Relationships
    project_owner: User              # Owner relationship
    organization: Organization       # Organization relationship
```

### Status Enumeration

```python
class ProjectStatus(str, enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
```

**Status Transitions (State Machine):**
- Not Started → In Progress, On Hold, Cancelled
- In Progress → On Hold, Completed, Cancelled
- On Hold → In Progress, Cancelled
- Completed → (no transitions, terminal state)
- Cancelled → (no transitions, terminal state)

### Priority Enumeration

```python
class ProjectPriority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"
```

## API Endpoints

### Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /projects | Create project |
| GET | /projects | List projects |
| GET | /projects/{id} | Get project details |
| GET | /projects/organization/{id} | List organization projects |
| GET | /projects/my-projects | Get user's projects |
| PATCH | /projects/{id} | Update project |
| POST | /projects/{id}/assign-team | Assign team members |
| DELETE | /projects/{id} | Delete project |

## Create Project

### Request

**Endpoint:** POST /projects

**Body:**
```
{
  "name": "Website Redesign",
  "description": "Complete redesign of company website with modern UI/UX",
  "organization_id": 1,
  "start_date": "2026-03-15",
  "end_date": "2026-06-30",
  "status": "Not Started",
  "priority": "High",
  "project_owner_id": 5,
  "team_member_ids": [2, 3, 4]
}
```

**Required Fields:**
- `name` - Project name
- `organization_id` - Organization ID
- `start_date` - Project start date
- `end_date` - Project end date (must be after start_date)
- `project_owner_id` - User ID of project owner

**Optional Fields:**
- `description` - Project description
- `status` - Project status (default: Not Started)
- `priority` - Project priority (default: Medium)
- `team_member_ids` - List of user IDs to assign as team members

### Response

**Status: 201 Created**

```
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "Website Redesign",
    "organization_id": 1,
    "status": "Not Started",
    "priority": "High",
    "created_at": "2026-02-24T10:30:00Z"
  },
  "message": "Project created successfully"
}
```

**Error Status Codes:**
- 400 - Invalid data or validation failed
- 401 - Unauthorized
- 404 - Organization, owner, or team member not found
- 422 - Validation error

## Get Project Details

### Request

**Endpoint:** GET /projects/{project_id}

**Path Parameters:**
- `project_id` - Project ID

### Response

**Status: 200 OK**

```
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "Website Redesign",
    "description": "Complete redesign of company website with modern UI/UX",
    "organization_id": 1,
    "start_date": "2026-03-15",
    "end_date": "2026-06-30",
    "status": "Not Started",
    "priority": "High",
    "project_owner": {
      "id": 5,
      "name": "Alice Johnson",
      "email": "alice@company.com",
      "role": "manager"
    },
    "team_members": [
      {
        "id": 2,
        "name": "Bob Martinez",
        "email": "bob@company.com",
        "role": "user"
      },
      {
        "id": 3,
        "name": "Carol White",
        "email": "carol@company.com",
        "role": "user"
      }
    ],
    "is_active": true,
    "created_at": "2026-02-24T10:30:00Z",
    "updated_at": "2026-02-24T10:30:00Z"
  },
  "message": "Project retrieved successfully"
}
```

## List Projects by Organization

### Request

**Endpoint:** GET /projects/organization/{org_id}

**Path Parameters:**
- `org_id` - Organization ID

**Query Parameters:**
- `skip` - Pagination offset (default: 0)
- `limit` - Results per page (default: 20, max: 100)
- `status` - Filter by status (optional)
- `priority` - Filter by priority (optional)

**Examples:**
```
GET /projects/organization/1
GET /projects/organization/1?status=In%20Progress
GET /projects/organization/1?priority=High
GET /projects/organization/1?skip=20&limit=10
```

### Response

**Status: 200 OK**

```
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Website Redesign",
      "description": "Complete redesign of company website with modern UI/UX",
      "organization_id": 1,
      "start_date": "2026-03-15",
      "end_date": "2026-06-30",
      "status": "Not Started",
      "priority": "High",
      "project_owner": {
        "id": 5,
        "name": "Alice Johnson",
        "email": "alice@company.com",
        "role": "manager"
      },
      "team_members_count": 3,
      "is_active": true,
      "created_at": "2026-02-24T10:30:00Z"
    }
  ],
  "message": "Retrieved 5 projects from organization",
  "meta": {
    "total": 5,
    "skip": 0,
    "limit": 20
  }
}
```

## Get User's Projects

### Request

**Endpoint:** GET /projects/my-projects

**Query Parameters:**
- `skip` - Pagination offset (default: 0)
- `limit` - Results per page (default: 20, max: 100)

### Response

**Status: 200 OK**

Returns all projects where current user is either owner or team member.

```
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Website Redesign",
      "description": "...",
      "organization_id": 1,
      "start_date": "2026-03-15",
      "end_date": "2026-06-30",
      "status": "Not Started",
      "priority": "High",
      "project_owner": { ... },
      "team_members_count": 3,
      "is_active": true,
      "created_at": "2026-02-24T10:30:00Z"
    }
  ],
  "message": "Retrieved 2 projects for user",
  "meta": {
    "total": 2,
    "skip": 0,
    "limit": 20
  }
}
```

## Update Project

### Request

**Endpoint:** PATCH /projects/{project_id}

**Body (all optional):**
```
{
  "name": "Updated Project Name",
  "description": "Updated description",
  "status": "In Progress",
  "priority": "Critical",
  "start_date": "2026-03-10",
  "end_date": "2026-07-15",
  "project_owner_id": 6,
  "team_member_ids": [2, 3, 5, 8]
}
```

### Response

**Status: 200 OK**

Returns updated project details.

**Validation Rules:**
- If both start_date and end_date provided, end_date must be after start_date
- Project owner must be active user
- All team members must exist and be active

## Assign Team Members

### Request

**Endpoint:** POST /projects/{project_id}/assign-team

**Body:**
```
{
  "team_member_ids": [2, 3, 4, 5]
}
```

**Notes:**
- Replaces the entire team member list
- All users must exist and be active
- Minimum 1 team member required

### Response

**Status: 200 OK**

Returns updated project with new team members.

```
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "Website Redesign",
    "organization_id": 1,
    "status": "Not Started",
    "priority": "High",
    "project_owner": { ... },
    "team_members": [
      {
        "id": 2,
        "name": "Bob Martinez",
        "email": "bob@company.com",
        "role": "user"
      },
      {
        "id": 3,
        "name": "Carol White",
        "email": "carol@company.com",
        "role": "user"
      },
      {
        "id": 4,
        "name": "David Kim",
        "email": "david@company.com",
        "role": "user"
      },
      {
        "id": 5,
        "name": "Emma Davis",
        "email": "emma@company.com",
        "role": "user"
      }
    ],
    "is_active": true,
    "created_at": "2026-02-24T10:30:00Z",
    "updated_at": "2026-02-24T11:00:00Z"
  },
  "message": "Team members assigned successfully"
}
```

## Delete Project

### Request

**Endpoint:** DELETE /projects/{project_id}

### Response

**Status: 204 No Content**

```
{
  "status": "success",
  "message": "Project deleted successfully"
}
```

**Notes:**
- Soft delete - project marked as inactive, not removed from database
- Can be reactivated by updating is_active field

## Permission Model

### Project Permissions

**Who can create projects:**
- Admin
- Manager
- Authorized users

**Who can view a project:**
- Project owner
- Team members
- Admin/Manager

**Who can edit a project:**
- Project owner
- Admin/Manager

**Who can delete a project:**
- Project owner
- Admin/Manager

## Utility Functions

### Status Utilities

```python
# Get valid next statuses
allowed = get_valid_status_transitions(ProjectStatus.NOT_STARTED)
# Returns: [IN_PROGRESS, ON_HOLD, CANCELLED]

# Check if transition is valid
valid = can_transition_status(ProjectStatus.IN_PROGRESS, ProjectStatus.COMPLETED)
# Returns: True
```

### Date Utilities

```python
# Check if project is overdue
overdue = is_project_overdue(project)

# Get days until deadline
days = get_days_until_deadline(project)

# Calculate project duration
duration = calculate_project_duration(start_date, end_date)

# Check if starting soon
soon = is_project_starting_soon(project, days_threshold=7)

# Validate date range
validate_date_range(start_date, end_date)
```

### Permission Utilities

```python
# Check if user can edit
can_edit = can_user_edit_project(project, user)

# Check if user can view
can_view = can_user_view_project(project, user)

# Validate ownership
validate_project_ownership(project, user)

# Validate team membership
validate_project_team_membership(project, user)

# Validate general access
validate_project_access(project, user)
```

### Health & Metrics

```python
# Get project health status
health = get_project_health_status(project)
# Returns: "healthy", "at_risk", "overdue", "completed", "cancelled"

# Get project summary
summary = format_project_summary(project)
# Returns: dict with key metrics
```

## Error Handling

### Common Errors

**400 Bad Request - Invalid Date Range**
```
{
  "status": "error",
  "detail": "End date must be after start date"
}
```

**400 Bad Request - Invalid Owner**
```
{
  "status": "error",
  "detail": "Project owner is inactive"
}
```

**401 Unauthorized**
```
{
  "detail": "Not authenticated"
}
```

**403 Forbidden - Permission Denied**
```
{
  "detail": "Only project owner can perform this action"
}
```

**404 Not Found - Project**
```
{
  "status": "error",
  "detail": "Project with id 999 not found"
}
```

**404 Not Found - Organization**
```
{
  "status": "error",
  "detail": "Organization with id 1 not found"
}
```

**404 Not Found - Team Member**
```
{
  "status": "error",
  "detail": "One or more team members not found or inactive"
}
```

**422 Validation Error**
```
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "name"],
      "msg": "string should have at least 1 character"
    }
  ]
}
```

## Best Practices

### Project Planning

- Set realistic start and end dates
- Use appropriate priority based on business impact
  - CRITICAL - must finish on time, high impact
  - HIGH - important projects
  - MEDIUM - normal priority projects
  - LOW - nice to have projects
- Assign experienced team members to critical projects

### Team Management

- Assign at least one team member to every project
- Keep team size reasonable (3-7 people typically)
- Match team skills to project requirements
- Include project owner in team members list

### Status Management

- Follow the status state machine
- Mark On Hold if blocked or paused
- Mark Completed only when truly finished
- Mark Cancelled only if project is abandoned

### Pagination

- Use pagination for large datasets
- Default limit is 20, max is 100
- Implement pagination for scalability

### Filtering

- Filter by status for dashboard displays
- Filter by priority for critical path analysis
- Combine filters for specific searches

## Service Functions

### create_project(db, data)

Creates a new project with full validation.

**Validations:**
- Organization must exist and be active
- Project owner must exist and be active
- All team members must exist and be active
- End date must be after start date

**Side Effects:**
- Logs project creation
- Triggers background processes if configured

### update_project(db, project_id, data)

Updates project with change tracking.

**Features:**
- Tracks which fields changed
- Validates all updates
- Triggers side effects if critical fields change

### get_project(db, project_id)

Retrieves a single project by ID.

**Raises:**
- 404 if project not found

### get_projects_by_organization(db, organization_id, skip, limit, status_filter, priority_filter)

Lists projects for organization with optional filters.

**Returns:** (projects_list, total_count)

### get_user_projects(db, user_id, skip, limit)

Lists projects where user is owner or team member.

**Returns:** (projects_list, total_count)

### assign_team_members(db, project_id, data)

Assigns or updates team members for a project.

**Notes:**
- Replaces entire team member list
- Validates all users exist and are active

### delete_project(db, project_id)

Soft deletes a project (marks as inactive).

**Notes:**
- Project not removed from database
- Can be reactivated if needed

## Setup Instructions

### 1. Copy Files

Create project module directory and copy files:
```
app/modules/projects/
  ├── __init__.py
  ├── model.py
  ├── schema.py
  ├── service.py
  ├── api.py
  ├── utils.py
  └── routes.py
```

### 2. Update Models

Add project relationships to User model:
```python
owned_projects = relationship("Project", foreign_keys="Project.project_owner_id")
assigned_projects = relationship("Project", secondary="project_team_members")
```

### 3. Register Router

Add to main.py:
```python
from app.modules.projects.api import router as projects_router
app.include_router(projects_router)
```

### 4. Run Migrations

```
alembic revision --autogenerate -m "Add projects"
alembic upgrade head
```

### 5. Test

```
curl http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"
```

## Performance Notes

### Database Indexes

Used for optimal query performance:
- organization_id - Filter by organization
- project_owner_id - Find owned projects
- status - Filter by status
- priority - Filter by priority
- is_active - Filter active projects

### Query Optimization

- Use filters to narrow results
- Paginate large result sets
- Avoid N+1 queries with selectinload
- Index composite queries

## Summary

The Project Management module provides:

✅ Complete project lifecycle management
✅ Multi-organization support
✅ Team member assignment and management
✅ Status transition validation with state machine
✅ Priority-based project tracking
✅ Comprehensive permission system
✅ Extensive logging and audit trails
✅ Production-ready implementation

Ready to use immediately in production environments!

---

**Last Updated:** February 24, 2026
**Version:** 1.0.0
**Status:** Production Ready