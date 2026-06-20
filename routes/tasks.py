"""Routes for /api/projects/{name}/tasks."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import kb_service
from routes.helpers import sanitize_error, validate_project_name

router = APIRouter(prefix="/api/projects", tags=["tasks"])


class ClaimTaskRequest(BaseModel):
    assigned_to: str = Field(default="claude-code", max_length=100)


class CompleteTaskRequest(BaseModel):
    summary: str = Field(default="", max_length=2000)


@router.get("/{name}/tasks")
def get_tasks(name: str):
    err = validate_project_name(name)
    if err:
        raise HTTPException(status_code=422, detail=err)
    return kb_service.get_tasks(name)


@router.post("/{name}/tasks/{task_id}/claim")
def claim_task(name: str, task_id: str, body: ClaimTaskRequest | None = None):
    err = validate_project_name(name)
    if err:
        raise HTTPException(status_code=422, detail=err)
    assigned_to = body.assigned_to if body else "claude-code"
    result = kb_service.claim_task(task_id, assigned_to, project=name)
    if result.startswith("ERROR"):
        if "not found" in result.lower():
            raise HTTPException(status_code=404, detail=sanitize_error(result))
        raise HTTPException(status_code=400, detail=sanitize_error(result))
    return {"message": result}


@router.post("/{name}/tasks/{task_id}/complete")
def complete_task(name: str, task_id: str, body: CompleteTaskRequest | None = None):
    err = validate_project_name(name)
    if err:
        raise HTTPException(status_code=422, detail=err)
    summary = body.summary if body else ""
    result = kb_service.complete_task(task_id, summary, project=name)
    if result.startswith("ERROR"):
        if "not found" in result.lower():
            raise HTTPException(status_code=404, detail=sanitize_error(result))
        raise HTTPException(status_code=400, detail=sanitize_error(result))
    return {"message": result}
