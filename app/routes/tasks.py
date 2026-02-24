TASK_PREFIX = "/api/v1/tasks"
TASK_TAG = "Tasks"

TASK_ROUTES = {
    "create": "",  
    "list": "", 
    "get": "/{task_id}", 
    "my_tasks": "/my-tasks",  
    "project_tasks": "/project/{project_id}",  
    "eligible_users": "/{task_id}/eligible-users", 
    "update": "/{task_id}", 
    "update_status": "/{task_id}/status",
    "add_subtask": "/{task_id}/subtasks", 
    "recompute": "/{task_id}/recompute",  
    "delete": "/{task_id}", 
}


# ────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────────

def get_task_endpoint(action: str) -> str:
    """Get full endpoint path for a task action"""
    return TASK_PREFIX + TASK_ROUTES.get(action, "")