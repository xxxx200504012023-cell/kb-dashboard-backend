"""Service layer wrapping KB MCP Server modules for the dashboard backend."""

import os
import re
import sys
from pathlib import Path

_MCP_SERVER = Path(os.environ.get("MCP_SERVER_PATH", "E:/knowledge-base/mcp-server"))
if str(_MCP_SERVER) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER))

os.environ.setdefault("KNOWLEDGE_BASE_ROOT", "E:/knowledge-base")

from file_tools import _read_file, _write_file, _search_kb        # noqa: E402
from task_tools import _task_status, _task_next, _task_claim, _task_complete  # noqa: E402
from project_tools import _list_projects, _init_project             # noqa: E402
from security import SecurityError                                    # noqa: E402
from config import PROJECTS_DIR                                      # noqa: E402

_TASKS_DIR = PROJECTS_DIR.parent / "tasks"


def list_projects() -> list[str]:
    """Return sorted list of project names."""
    raw = _list_projects()
    if raw.startswith("No projects"):
        return []
    lines = raw.strip().split("\n")
    return [line.lstrip("- ") for line in lines if line.startswith("- ")]


def init_project(name: str, project_type: str = "backend") -> dict:
    """Create a new project. Returns dict with name and created paths, or error."""
    raw = _init_project(name, project_type)
    if raw.startswith("ERROR:"):
        return {"error": raw}
    lines = raw.strip().split("\n")
    created = [line.lstrip("  + ") for line in lines if line.startswith("  +")]
    return {"name": name, "created": created}


def _get_task_project(task_id: str) -> str | None:
    """Extract the project field from a task file's frontmatter. Returns None if not found."""
    for stage in ["backlog", "in-progress", "done"]:
        task_file = _TASKS_DIR / stage / f"{task_id}.md"
        if task_file.exists():
            content = task_file.read_text(encoding="utf-8")
            match = re.search(r"^project:\s*(.+)$", content, re.MULTILINE)
            return match.group(1).strip() if match else None
    return None


def get_project_type(name: str) -> str:
    """Detect project type from directory contents. Returns 'frontend' or 'backend'."""
    proj_dir = PROJECTS_DIR / name
    if (proj_dir / "CODEX.md").exists():
        return "frontend"
    return "backend"


def get_project(name: str) -> dict | None:
    """Get project details including file listing. Returns None if not found."""
    proj_dir = PROJECTS_DIR / name
    if not proj_dir.exists() or not proj_dir.is_dir():
        return None
    files = []
    for entry in sorted(proj_dir.rglob("*")):
        rel = str(entry.relative_to(proj_dir))
        if entry.is_dir():
            files.append(rel + "/")
        else:
            files.append(rel)
    return {"name": name, "files": files}


def read_file(path: str, project: str | None) -> str:
    """Read a file from a KB project."""
    return _read_file(path, project)


def write_file(path: str, content: str, project: str | None) -> str:
    """Write content to a file in a KB project."""
    return _write_file(path, content, project)


def search_files(query: str, project: str | None) -> list[dict]:
    """Search files in a project. Returns list of {file, excerpts}."""
    raw = _search_kb(query, project)
    if raw.startswith("No matches") or raw.startswith("ERROR:"):
        return []
    results = []
    current = None
    for line in raw.strip().split("\n"):
        if line.startswith("## "):
            if current:
                results.append(current)
            current = {"file": line[3:].strip(), "excerpts": []}
        elif line.startswith("  L") and current:
            current["excerpts"].append(line.strip())
    if current:
        results.append(current)
    return results


def get_tasks(project: str) -> dict:
    """Get task kanban for a project: {backlog, in_progress, done}."""
    try:
        raw = _task_status(project)
    except SecurityError:
        return {"backlog": [], "in_progress": [], "done": []}

    result = {"backlog": [], "in_progress": [], "done": []}
    section_map = {"Pending": "backlog", "In Progress": "in_progress", "Done": "done"}
    current_section = None

    for line in raw.strip().split("\n"):
        for label, key in section_map.items():
            if line.startswith(f"## {label}"):
                current_section = key
                break
        if line.startswith("- [") and current_section:
            bracket_end = line.find("]")
            if bracket_end == -1:
                continue
            task_id = line[3:bracket_end]
            title = line[bracket_end + 2:].strip()
            result[current_section].append({"id": task_id, "title": title})

    return result


def get_next_task(project: str, task_type: str | None = None) -> dict | None:
    """Get the next pending task from backlog."""
    raw = _task_next(project, task_type)
    if raw.startswith("No pending") or raw.startswith("ERROR:"):
        return None
    lines = raw.strip().split("\n")
    task_id = None
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("**File:**"):
            task_id = line.split("**File:**")[1].strip().replace(".md", "")
            body_start = i + 1
            break
    if not task_id:
        return None
    body = "\n".join(lines[body_start:]).strip()
    return {"id": task_id, "body": body}


def claim_task(task_id: str, assigned_to: str = "claude-code", project: str | None = None) -> str:
    """Claim a task: move from backlog to in-progress. Optionally validate project ownership."""
    if project:
        task_project = _get_task_project(task_id)
        if task_project and task_project != project:
            return f"ERROR: Task '{task_id}' does not belong to project '{project}'"
    return _task_claim(task_id, assigned_to)


def complete_task(task_id: str, summary: str = "", project: str | None = None) -> str:
    """Mark a task as done. Optionally validate project ownership."""
    if project:
        task_project = _get_task_project(task_id)
        if task_project and task_project != project:
            return f"ERROR: Task '{task_id}' does not belong to project '{project}'"
    return _task_complete(task_id, summary)
