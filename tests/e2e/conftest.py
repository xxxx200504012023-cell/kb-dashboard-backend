"""E2E test fixtures — test full API workflows via ASGI transport."""
import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MCP_SERVER = Path(os.environ.get("MCP_SERVER_PATH", "E:/knowledge-base/mcp-server"))
if str(MCP_SERVER) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER))


@pytest.fixture
def kb_root(tmp_path):
    """Create an isolated KB root with required directory structure."""
    root = tmp_path / "kb"
    for subdir in ["projects", "tasks", "templates", "logs", "codex"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    (root / "codex" / "CODEX.md").write_text("# CODEX.md placeholder\n", encoding="utf-8")
    for stage in ["backlog", "in-progress", "done"]:
        (root / "tasks" / stage).mkdir(parents=True, exist_ok=True)
    os.environ["KNOWLEDGE_BASE_ROOT"] = str(root)
    for mod in list(sys.modules):
        if mod.startswith(("config", "security", "utils", "file_tools", "task_tools",
                           "project_tools", "search_tools", "graph_tools", "schemas",
                           "kb_service", "routes", "main", "ws_events")):
            if mod in sys.modules:
                del sys.modules[mod]
    yield root
    for mod in list(sys.modules):
        if mod.startswith(("config", "security", "utils", "file_tools", "task_tools",
                           "project_tools", "search_tools", "graph_tools", "schemas",
                           "kb_service", "routes", "main", "ws_events")):
            if mod in sys.modules:
                del sys.modules[mod]


@pytest.fixture
async def api(kb_root):
    """Async HTTP client for E2E workflow tests."""
    import importlib
    import main
    importlib.reload(main)
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
