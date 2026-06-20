"""Shared test helpers — safe to import from any test file."""
from datetime import datetime, timezone
from pathlib import Path


def create_task_file(root: Path, task_id: str, project: str, task_type: str = "backend"):
    """Create a task file in the backlog directory."""
    content = f"""---
id: {task_id}
project: {project}
type: {task_type}
status: pending
created_at: {datetime.now(timezone.utc).isoformat()}
---

# {task_id}
Task description.
"""
    (root / "tasks" / "backlog" / f"{task_id}.md").write_text(content, encoding="utf-8")
