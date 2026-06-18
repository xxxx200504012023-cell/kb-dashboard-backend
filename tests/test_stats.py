"""Tests for /api/stats routes."""


class TestGlobalStats:
    async def test_empty_kb_returns_zeros(self, client):
        response = await client.get("/api/stats/global")
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 0
        assert data["total_tasks"] == 0
        assert data["total_files"] >= 0
        assert "recent_activity" in data

    async def test_with_projects(self, client, kb_root):
        (kb_root / "projects" / "alpha").mkdir()
        (kb_root / "projects" / "alpha" / "readme.md").write_text(
            "# Alpha\n\nContent here.\n", encoding="utf-8"
        )
        (kb_root / "projects" / "beta").mkdir()

        response = await client.get("/api/stats/global")
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 2
        assert data["total_files"] >= 1


class TestProjectStats:
    async def test_existing_project(self, client, kb_root):
        proj = kb_root / "projects" / "demo"
        proj.mkdir()
        (proj / "readme.md").write_text("# Demo\n\nA demo project.\n", encoding="utf-8")

        response = await client.get("/api/stats/projects/demo")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "demo"
        assert data["file_count"] >= 1
        assert data["total_lines"] >= 3

    async def test_nonexistent_project(self, client):
        response = await client.get("/api/stats/projects/ghost")
        assert response.status_code == 404

    async def test_invalid_project_name(self, client):
        # Name with special characters triggers 422 validation
        response = await client.get("/api/stats/projects/bad@name")
        assert response.status_code == 422
