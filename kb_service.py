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
from config import PROJECTS_DIR, KB_ROOT                            # noqa: E402
from schemas import GlobalStats, ProjectStats, RecentActivity        # noqa: E402
from ws_manager import _schedule, broadcast, publish                   # noqa: E402

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
    _schedule(broadcast("project_created", {"name": name}))
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
    result = _task_claim(task_id, assigned_to)
    if not result.startswith("ERROR:") and project:
        _schedule(publish(project, "task_claimed", {"task_id": task_id, "assigned_to": assigned_to}))
    return result


def complete_task(task_id: str, summary: str = "", project: str | None = None) -> str:
    """Mark a task as done. Optionally validate project ownership."""
    if project:
        task_project = _get_task_project(task_id)
        if task_project and task_project != project:
            return f"ERROR: Task '{task_id}' does not belong to project '{project}'"
    result = _task_complete(task_id, summary)
    if not result.startswith("ERROR:") and project:
        _schedule(publish(project, "task_completed", {"task_id": task_id, "summary": summary}))
        _schedule(publish(project, "project_stats_updated", {}))
    return result


# -- Stats Aggregation --

_MAX_STATS_FILES = 1000
_MAX_STATS_FILE_SIZE = 1024 * 1024

_SKIP_STATS_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", "logs", ".venv"}


def _count_lines(path: Path) -> int:
    """Count lines in a text file. Returns 0 for non-text or unreadable files."""
    try:
        if path.stat().st_size > _MAX_STATS_FILE_SIZE:
            return 0
        return len(path.read_text(encoding="utf-8").split("\n"))
    except (UnicodeDecodeError, OSError):
        return 0


def _get_file_count_and_lines(dir_path: Path) -> tuple[int, int]:
    """Count .md, .yaml, .json files and total lines in a directory tree."""
    file_count = 0
    total_lines = 0
    if not dir_path.is_dir():
        return 0, 0
    for dirpath, dirnames, filenames in os.walk(dir_path):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_STATS_DIRS]
        for fname in filenames:
            if file_count >= _MAX_STATS_FILES:
                break
            entry = Path(dirpath) / fname
            if entry.is_file() and entry.suffix in (".md", ".yaml", ".json"):
                file_count += 1
                total_lines += _count_lines(entry)
        if file_count >= _MAX_STATS_FILES:
            break
    return file_count, total_lines


def _recent_activity(limit: int = 10) -> list[RecentActivity]:
    """Get recently modified .md files. Limit to 10 most recent."""
    entries: list[tuple[str, float]] = []
    files_scanned = 0
    for dirpath, dirnames, filenames in os.walk(KB_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_STATS_DIRS]
        for fname in filenames:
            if files_scanned >= _MAX_STATS_FILES:
                break
            if not fname.endswith((".md", ".yaml", ".json")):
                continue
            fp = Path(dirpath) / fname
            try:
                mtime = fp.stat().st_mtime
                rel = fp.relative_to(KB_ROOT)
                entries.append((str(rel).replace("\\", "/"), mtime))
                files_scanned += 1
            except OSError:
                continue
        if files_scanned >= _MAX_STATS_FILES:
            break
    entries.sort(key=lambda x: x[1], reverse=True)
    from datetime import datetime, timezone
    result = []
    for rel, mtime in entries[:limit]:
        iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        result.append(RecentActivity(path=rel, modified_at=iso))
    return result


def get_global_stats() -> GlobalStats:
    """Compute global statistics across all projects."""
    project_names = list_projects()

    total_tasks = 0
    backlog, in_progress, done = 0, 0, 0
    project_stats_list: list[ProjectStats] = []

    for name in project_names:
        proj_dir = PROJECTS_DIR / name
        fc, tl = _get_file_count_and_lines(proj_dir)
        task_data = get_tasks(name)
        b_count = len(task_data.get("backlog", []))
        ip_count = len(task_data.get("in_progress", []))
        d_count = len(task_data.get("done", []))

        total_tasks += b_count + ip_count + d_count
        backlog += b_count
        in_progress += ip_count
        done += d_count

        project_stats_list.append(ProjectStats(
            name=name,
            task_counts={"backlog": b_count, "in_progress": ip_count, "done": d_count},
            file_count=fc,
            total_lines=tl,
        ))

    total_files, _ = _get_file_count_and_lines(KB_ROOT)
    recent = _recent_activity(limit=10)

    return GlobalStats(
        total_projects=len(project_names),
        total_tasks=total_tasks,
        total_files=total_files,
        tasks_by_status={"backlog": backlog, "in_progress": in_progress, "done": done},
        projects=project_stats_list,
        recent_activity=recent,
    )


def get_project_stats(name: str) -> ProjectStats | None:
    """Compute statistics for a single project. Returns None if project not found."""
    proj_dir = PROJECTS_DIR / name
    if not proj_dir.is_dir():
        return None

    fc, tl = _get_file_count_and_lines(proj_dir)
    task_data = get_tasks(name)

    # Determine last modified
    last_modified = None
    try:
        latest = None
        count = 0
        for dirpath, dirnames, filenames in os.walk(proj_dir):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_STATS_DIRS]
            for fname in filenames:
                if count >= _MAX_STATS_FILES:
                    break
                try:
                    mtime = (Path(dirpath) / fname).stat().st_mtime
                    if latest is None or mtime > latest:
                        latest = mtime
                    count += 1
                except OSError:
                    continue
            if count >= _MAX_STATS_FILES:
                break
        if latest:
            from datetime import datetime, timezone
            last_modified = datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()
    except OSError:
        pass

    return ProjectStats(
        name=name,
        task_counts={
            "backlog": len(task_data.get("backlog", [])),
            "in_progress": len(task_data.get("in_progress", [])),
            "done": len(task_data.get("done", [])),
        },
        file_count=fc,
        total_lines=tl,
        last_modified=last_modified,
    )
