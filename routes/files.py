"""Routes for /api/projects/{name}/files."""
from fastapi import APIRouter, HTTPException, Request, Query, Response

import kb_service
from routes.helpers import sanitize_error

router = APIRouter(prefix="/api/projects", tags=["files"])

MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10 MB


def _validate_file_path(path: str) -> str | None:
    """Validate and normalize file path. Returns error or None."""
    if not path or path.startswith("/"):
        return "Invalid file path"
    if ".." in path.split("/"):
        return "Path traversal blocked"
    if "\x00" in path:
        return "Path contains null byte"
    if len(path) > 500:
        return "Path too long"
    return None


@router.get("/{name}/files/{path:path}")
def read_file(name: str, path: str):
    err = _validate_file_path(path)
    if err:
        raise HTTPException(status_code=400, detail=err)
    result = kb_service.read_file(path, name)
    if result.startswith("ERROR:"):
        if "not found" in result.lower():
            raise HTTPException(status_code=404, detail=sanitize_error(result))
        raise HTTPException(status_code=400, detail=sanitize_error(result))
    return Response(content=result, media_type="text/plain; charset=utf-8")


@router.put("/{name}/files/{path:path}")
async def write_file(name: str, path: str, request: Request):
    err = _validate_file_path(path)
    if err:
        raise HTTPException(status_code=400, detail=err)
    # Check Content-Length before reading body to avoid memory exhaustion
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_CONTENT_SIZE:
        raise HTTPException(status_code=413, detail="Content too large")
    content = await request.body()
    text = content.decode("utf-8")
    if len(text.encode("utf-8")) > MAX_CONTENT_SIZE:
        raise HTTPException(status_code=413, detail="Content too large")
    result = kb_service.write_file(path, text, name)
    if result.startswith("ERROR:"):
        raise HTTPException(status_code=400, detail=sanitize_error(result))
    return {"message": result}


@router.get("/{name}/search")
def search_files(name: str, q: str = Query(..., min_length=1)):
    results = kb_service.search_files(q, name)
    return {"query": q, "results": results}
