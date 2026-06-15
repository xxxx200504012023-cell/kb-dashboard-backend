"""Routes for /api/projects/{name}/tasks."""
from fastapi import APIRouter, HTTPException

import kb_service
from routes.helpers import sanitize_error

router = APIRouter(prefix="/api/projects", tags=["tasks"])


@router.get("/{name}/tasks")
def get_tasks(name: str):
    return kb_service.get_tasks(name)


@router.post("/{name}/tasks/{task_id}/claim")
def claim_task(name: str, task_id: str, body: dict | None = None):
    assigned_to = (body or {}).get("assigned_to", "claude-code")
    result = kb_service.claim_task(task_id, assigned_to)
    if result.startswith("ERROR"):
        if "not found" in result.lower():
            raise HTTPException(status_code=404, detail=sanitize_error(result))
        raise HTTPException(status_code=400, detail=sanitize_error(result))
    return {"message": result}


@router.post("/{name}/tasks/{task_id}/complete")
def complete_task(name: str, task_id: str, body: dict | None = None):
    summary = (body or {}).get("summary", "")
    result = kb_service.complete_task(task_id, summary)
    if result.startswith("ERROR"):
        if "not found" in result.lower():
            raise HTTPException(status_code=404, detail=sanitize_error(result))
        raise HTTPException(status_code=400, detail=sanitize_error(result))
    return {"message": result}
