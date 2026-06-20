"""E2E workflow tests — full API journeys across multiple endpoints."""


class TestProjectWorkflow:
    """End-to-end: create project → list → get details → verify file structure."""

    async def test_create_and_inspect_project(self, api):
        name = "e2e-test-project"

        resp = await api.post("/api/projects", json={"name": name, "project_type": "backend"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == name

        resp = await api.get("/api/projects")
        assert resp.status_code == 200
        projects = resp.json()["projects"]
        assert any(p["name"] == name for p in projects)

        resp = await api.get(f"/api/projects/{name}")
        assert resp.status_code == 200
        files = resp.json()["files"]
        assert "spec.md" in files

    async def test_duplicate_project_rejected(self, api):
        name = "e2e-dup"
        await api.post("/api/projects", json={"name": name, "project_type": "backend"})
        resp = await api.post("/api/projects", json={"name": name, "project_type": "backend"})
        assert resp.status_code == 409


class TestTaskWorkflow:
    """End-to-end: kanban visibility and structure validation."""

    async def test_empty_kanban_on_project_creation(self, api):
        project = "e2e-task-flow"
        await api.post("/api/projects", json={"name": project, "project_type": "backend"})

        resp = await api.get(f"/api/projects/{project}/tasks")
        assert resp.status_code == 200
        initial = resp.json()
        assert initial["backlog"] == []

    async def test_kanban_visibility(self, api):
        project = "e2e-kanban"
        await api.post("/api/projects", json={"name": project, "project_type": "backend"})
        resp = await api.get(f"/api/projects/{project}/tasks")
        assert resp.status_code == 200
        for key in ["backlog", "in_progress", "done"]:
            assert isinstance(resp.json()[key], list)


class TestFileWorkflow:
    """End-to-end: write file → read back → search → verify content."""

    async def test_write_read_search(self, api):
        project = "e2e-file-flow"
        await api.post("/api/projects", json={"name": project, "project_type": "backend"})

        content = "# E2E Document\n\nTest content for end-to-end workflow."
        resp = await api.put(
            f"/api/projects/{project}/files/doc.md",
            content=content,
            headers={"Content-Type": "text/plain"},
        )
        assert resp.status_code == 200

        resp = await api.get(f"/api/projects/{project}/files/doc.md")
        assert resp.status_code == 200
        assert resp.text == content

        resp = await api.get(f"/api/projects/{project}/search?q=E2E+Document")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) > 0

    async def test_write_and_read_multiple_files(self, api):
        project = "e2e-multi-file"
        await api.post("/api/projects", json={"name": project, "project_type": "backend"})
        for i in range(3):
            await api.put(
                f"/api/projects/{project}/files/file_{i}.md",
                content=f"# File {i}",
                headers={"Content-Type": "text/plain"},
            )
        resp = await api.get(f"/api/projects/{project}")
        files = [f for f in resp.json()["files"] if f.startswith("file_")]
        assert len(files) == 3


class TestStatsWorkflow:
    """End-to-end: multiple projects → global stats aggregate correctly."""

    async def test_global_stats_after_operations(self, api):
        await api.post("/api/projects", json={"name": "e2e-stats-1", "project_type": "backend"})
        await api.post("/api/projects", json={"name": "e2e-stats-2", "project_type": "frontend"})

        resp = await api.get("/api/stats/global")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_projects"] == 2

    async def test_project_stats_has_required_fields(self, api):
        project = "e2e-stat-fields"
        await api.post("/api/projects", json={"name": project, "project_type": "backend"})
        resp = await api.get(f"/api/stats/projects/{project}")
        assert resp.status_code == 200
        stats = resp.json()
        for key in ["file_count", "total_lines", "task_counts"]:
            assert key in stats


class TestDependenciesWorkflow:
    """End-to-end: dependencies endpoint returns valid DAG structure."""

    async def test_dependencies_returns_dag(self, api):
        project = "e2e-deps"
        await api.post("/api/projects", json={"name": project, "project_type": "backend"})
        resp = await api.get(f"/api/projects/{project}/dependencies")
        assert resp.status_code == 200
        dag = resp.json()
        for key in ["nodes", "edges"]:
            assert key in dag
        assert isinstance(dag["nodes"], list)
        assert isinstance(dag["edges"], list)


class TestDiffWorkflow:
    """End-to-end: file diff returns expected structure."""

    async def test_diff_structure_for_new_file(self, api):
        project = "e2e-diff"
        await api.post("/api/projects", json={"name": project, "project_type": "backend"})
        await api.put(
            f"/api/projects/{project}/files/versioned.md",
            content="# Version 1",
            headers={"Content-Type": "text/plain"},
        )
        resp = await api.get(f"/api/projects/{project}/files/versioned.md/diff")
        assert resp.status_code == 200
        diff = resp.json()
        assert "current" in diff
        assert "versions" in diff
        assert "diff" in diff
