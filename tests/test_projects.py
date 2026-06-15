"""Tests for /api/projects routes."""
import pytest


class TestListProjects:
    async def test_empty(self, client):
        response = await client.get("/api/projects")
        assert response.status_code == 200
        assert response.json()["projects"] == []

    async def test_with_projects(self, client, kb_root):
        (kb_root / "projects" / "alpha").mkdir()
        (kb_root / "projects" / "beta").mkdir()
        response = await client.get("/api/projects")
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["projects"]]
        assert names == ["alpha", "beta"]


class TestCreateProject:
    async def test_create_backend(self, client, kb_root):
        response = await client.post("/api/projects", json={"name": "new-proj", "project_type": "backend"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new-proj"
        assert (kb_root / "projects" / "new-proj").exists()

    async def test_create_duplicate(self, client, kb_root):
        (kb_root / "projects" / "exist").mkdir()
        response = await client.post("/api/projects", json={"name": "exist", "project_type": "backend"})
        assert response.status_code == 409

    async def test_create_invalid_name(self, client):
        response = await client.post("/api/projects", json={"name": "../escape", "project_type": "backend"})
        assert response.status_code == 422


class TestGetProject:
    async def test_existing(self, client, kb_root):
        proj = kb_root / "projects" / "demo"
        proj.mkdir()
        (proj / "spec.md").write_text("# Demo", encoding="utf-8")
        (proj / "api").mkdir()
        response = await client.get("/api/projects/demo")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "demo"
        assert "spec.md" in data["files"]

    async def test_nonexistent(self, client):
        response = await client.get("/api/projects/no-such")
        assert response.status_code == 404
