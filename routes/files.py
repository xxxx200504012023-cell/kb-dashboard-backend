"""Routes for /api/projects/{name}/files."""
import re
from fastapi import APIRouter, HTTPException, Request, Query, Response

import kb_service
from routes.helpers import sanitize_error, validate_project_name

router = APIRouter(prefix="/api/projects", tags=["files"])

MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10 MB
_VERSION_RE = re.compile(r"^\d{8}T\d{6}Z\.md$")


def _validate_file_path(path: str) -> str | None:
    """Validate and normalize file path. Returns error or None."""
    if not path or path.startswith("/"):
        return "Invalid file path"
    if ".." in path.replace("\\", "/").split("/"):
        return "Path traversal blocked"
    if "\x00" in path:
        return "Path contains null byte"
    if len(path) > 500:
        return "Path too long"
    return None


def _validate_project(name: str) -> None:
    """Validate project name and raise HTTPException on failure."""
    err = validate_project_name(name)
    if err:
        raise HTTPException(status_code=422, detail=err)


async def _read_body_bounded(request: Request, max_size: int = MAX_CONTENT_SIZE) -> bytes:
    """Read request body with a hard size cap using stream() to prevent DoS."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_size:
                raise HTTPException(status_code=413, detail="Content too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_size:
            raise HTTPException(status_code=413, detail="Content too large")
    return bytes(body)


@router.get("/{name}/files/{path:path}/diff")
def file_diff(name: str, path: str, version: str | None = Query(default=None)):
    _validate_project(name)
    err = _validate_file_path(path)
    if err:
        raise HTTPException(status_code=400, detail=err)
    if version is not None and not _VERSION_RE.match(version):
        raise HTTPException(status_code=400, detail="Invalid version format")
    result = kb_service.get_file_diff(name, path, version)
    if result is None:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return result


@router.get("/{name}/files/{path:path}")
def read_file(name: str, path: str):
    _validate_project(name)
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
    _validate_project(name)
    err = _validate_file_path(path)
    if err:
        raise HTTPException(status_code=400, detail=err)
    raw = await _read_body_bounded(request)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File content must be valid UTF-8")
    result = kb_service.write_file(path, text, name)
    if result.startswith("ERROR:"):
        raise HTTPException(status_code=400, detail=sanitize_error(result))
    return {"message": result}


@router.get("/{name}/search")
def search_files(name: str, q: str = Query(..., min_length=1, max_length=500)):
    _validate_project(name)
    results = kb_service.search_files(q, name)
    return {"query": q, "results": results}
