"""Tests for /api/projects/{name}/tasks routes."""
from datetime import datetime, timezone
from pathlib import Path


def _create_task(root: Path, task_id: str, project: str, task_type: str = "backend"):
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


class TestGetTasks:
    async def test_empty(self, client):
        response = await client.get("/api/projects/nonexistent/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["backlog"] == []
        assert data["in_progress"] == []
        assert data["done"] == []

    async def test_with_tasks(self, client, kb_root):
        _create_task(kb_root, "task-01", "demo")
        response = await client.get("/api/projects/demo/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["backlog"]) == 1
        assert data["backlog"][0]["id"] == "task-01"


class TestClaimTask:
    async def test_claim_success(self, client, kb_root):
        _create_task(kb_root, "task-10", "demo")
        response = await client.post("/api/projects/demo/tasks/task-10/claim", json={"assigned_to": "tester"})
        assert response.status_code == 200
        assert "OK" in response.json()["message"]

    async def test_claim_not_found(self, client):
        response = await client.post("/api/projects/demo/tasks/no-task/claim", json={"assigned_to": "tester"})
        assert response.status_code == 404


class TestCompleteTask:
    async def test_complete_success(self, client, kb_root):
        _create_task(kb_root, "task-20", "demo")
        await client.post("/api/projects/demo/tasks/task-20/claim", json={"assigned_to": "tester"})
        response = await client.post("/api/projects/demo/tasks/task-20/complete", json={"summary": "done"})
        assert response.status_code == 200
        assert "OK" in response.json()["message"]

    async def test_complete_not_in_progress(self, client):
        response = await client.post("/api/projects/demo/tasks/no-task/complete", json={"summary": "x"})
        assert response.status_code == 404
