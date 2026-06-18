"""Shared test fixtures for kb-dashboard-backend."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MCP_SERVER = Path("E:/knowledge-base/mcp-server")
if str(MCP_SERVER) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER))


@pytest.fixture
def kb_root(tmp_path):
    """Create an isolated KB root with projects/ and tasks/ directories."""
    root = tmp_path / "kb"
    (root / "projects").mkdir(parents=True)
    for stage in ["backlog", "in-progress", "done"]:
        (root / "tasks" / stage).mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    (root / "codex").mkdir(parents=True)
    (root / "codex" / "CODEX.md").write_text("# CODEX.md placeholder\n", encoding="utf-8")
    os.environ["KNOWLEDGE_BASE_ROOT"] = str(root)
    for mod in list(sys.modules):
        if mod.startswith(("config", "security", "utils", "file_tools", "task_tools",
                           "project_tools", "search_tools", "graph_tools", "schemas",
                           "kb_service", "routes", "main")):
            if mod in sys.modules:
                del sys.modules[mod]
    yield root
    for mod in list(sys.modules):
        if mod.startswith(("config", "security", "utils", "file_tools", "task_tools",
                           "project_tools", "search_tools", "graph_tools", "schemas",
                           "kb_service", "routes", "main")):
            if mod in sys.modules:
                del sys.modules[mod]


@pytest.fixture
async def client(kb_root):
    """Create an async HTTP client for testing the FastAPI app."""
    import importlib
    import main
    importlib.reload(main)
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def create_task_file(root: Path, task_id: str, project: str, task_type: str = "backend"):
    """Helper to create a task file in the backlog directory."""
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
