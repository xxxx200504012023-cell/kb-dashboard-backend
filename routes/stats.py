"""Routes for /api/stats — global and per-project statistics."""

from fastapi import APIRouter, HTTPException

import kb_service
from routes.helpers import sanitize_error, validate_project_name

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/global")
def global_stats():
    """Return global statistics across all projects."""
    try:
        return kb_service.get_global_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error(str(e)))


@router.get("/projects/{name}")
def project_stats(name: str):
    """Return statistics for a single project."""
    err = validate_project_name(name)
    if err:
        raise HTTPException(status_code=422, detail=err)
    result = kb_service.get_project_stats(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")
    return result
