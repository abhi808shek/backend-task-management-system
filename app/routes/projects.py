PROJECT_PREFIX = "/api/v1/projects"
PROJECT_TAG = "Projects"

PROJECT_ROUTES = {
    "create": "",
    "get": "/{project_id}",
    "list_org": "/organization/{org_id}",
    "list_user": "/my-projects",
    "update": "/{project_id}",
    "assign_team": "/{project_id}/assign-team",
    "delete": "/{project_id}",
}