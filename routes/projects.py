"""Routes for /api/projects."""
from fastapi import APIRouter, HTTPException

import kb_service
from routes.helpers import sanitize_error, validate_project_name

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects():
    projects = kb_service.list_projects()
    return {"projects": [{"name": p, "type": "backend"} for p in projects]}


@router.post("", status_code=201)
def create_project(body: dict):
    name = body.get("name", "")
    err = validate_project_name(name)
    if err:
        raise HTTPException(status_code=422, detail=err)
    project_type = body.get("project_type", "backend")
    result = kb_service.init_project(name, project_type)
    if "error" in result:
        if "already exists" in result["error"]:
            raise HTTPException(status_code=409, detail=sanitize_error(result["error"]))
        raise HTTPException(status_code=422, detail=sanitize_error(result["error"]))
    return result


@router.get("/{name}")
def get_project(name: str):
    result = kb_service.get_project(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")
    return result
