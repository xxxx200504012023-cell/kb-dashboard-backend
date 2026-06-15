"""Tests for kb_service.py — wraps KB MCP modules."""
from pathlib import Path

import pytest
from conftest import create_task_file


@pytest.fixture
def kb_service(kb_root):
    """Import kb_service after KB_ROOT is configured."""
    import importlib
    import kb_service
    importlib.reload(kb_service)
    return kb_service


class TestListProjects:
    def test_empty_projects(self, kb_service):
        result = kb_service.list_projects()
        assert result == []

    def test_projects_exist(self, kb_service, kb_root):
        (kb_root / "projects" / "alpha").mkdir()
        (kb_root / "projects" / "beta").mkdir()
        result = kb_service.list_projects()
        assert result == ["alpha", "beta"]


class TestInitProject:
    def test_create_backend_project(self, kb_service, kb_root):
        result = kb_service.init_project("test-proj", "backend")
        assert result["name"] == "test-proj"
        assert (kb_root / "projects" / "test-proj" / "spec.md").exists()

    def test_create_frontend_project(self, kb_service, kb_root):
        result = kb_service.init_project("frontend-app", "frontend")
        assert result["name"] == "frontend-app"
        assert (kb_root / "projects" / "frontend-app" / "CODEX.md").exists()

    def test_duplicate_project_error(self, kb_service, kb_root):
        (kb_root / "projects" / "dup").mkdir()
        result = kb_service.init_project("dup", "backend")
        assert "error" in result


class TestGetProject:
    def test_existing_project(self, kb_service, kb_root):
        proj = kb_root / "projects" / "demo"
        proj.mkdir()
        (proj / "spec.md").write_text("---\n---\n# Demo", encoding="utf-8")
        (proj / "api").mkdir()
        result = kb_service.get_project("demo")
        assert result["name"] == "demo"
        assert "spec.md" in result["files"]

    def test_nonexistent_project(self, kb_service):
        result = kb_service.get_project("no-such")
        assert result is None


class TestReadFile:
    def test_read_existing_file(self, kb_service, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        (proj / "readme.md").write_text("# Hello", encoding="utf-8")
        result = kb_service.read_file("readme.md", "app")
        assert result == "# Hello"

    def test_read_nonexistent_file(self, kb_service):
        result = kb_service.read_file("no-file.md", "app")
        assert result.startswith("ERROR:")


class TestWriteFile:
    def test_write_new_file(self, kb_service, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        result = kb_service.write_file("notes.md", "# Notes", "app")
        assert "OK" in result
        content = (proj / "notes.md").read_text(encoding="utf-8")
        assert content == "# Notes"

    def test_write_content_too_large(self, kb_service, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        result = kb_service.write_file("big.md", "x" * 11_000_000, "app")
        assert "ERROR" in result


class TestSearchFiles:
    def test_search_finds_match(self, kb_service, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        (proj / "doc.md").write_text("# Searchable doc", encoding="utf-8")
        result = kb_service.search_files("Searchable", "app")
        assert len(result) > 0

    def test_search_no_match(self, kb_service, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        (proj / "doc.md").write_text("# Nothing", encoding="utf-8")
        result = kb_service.search_files("xyzzy", "app")
        assert result == []


class TestTaskOperations:
    def test_get_tasks_empty(self, kb_service):
        result = kb_service.get_tasks("empty-proj")
        assert result["backlog"] == []
        assert result["in_progress"] == []
        assert result["done"] == []

    def test_get_tasks_with_items(self, kb_service, kb_root):
        create_task_file(kb_root, "task-01", "myproject")
        result = kb_service.get_tasks("myproject")
        assert len(result["backlog"]) == 1
        assert result["backlog"][0]["id"] == "task-01"

    def test_claim_task(self, kb_service, kb_root):
        create_task_file(kb_root, "task-02", "myproject")
        result = kb_service.claim_task("task-02", "claude-code")
        assert "OK" in result
        assert not (kb_root / "tasks" / "backlog" / "task-02.md").exists()
        assert (kb_root / "tasks" / "in-progress" / "task-02.md").exists()

    def test_complete_task(self, kb_service, kb_root):
        create_task_file(kb_root, "task-03", "myproject")
        kb_service.claim_task("task-03", "claude-code")
        result = kb_service.complete_task("task-03", "Done!")
        assert "OK" in result
        assert (kb_root / "tasks" / "done" / "task-03.md").exists()

    def test_get_next_task(self, kb_service, kb_root):
        create_task_file(kb_root, "task-04", "myproject")
        result = kb_service.get_next_task("myproject")
        assert result is not None
        assert "task-04" in result["id"]

    def test_get_next_task_filtered(self, kb_service, kb_root):
        create_task_file(kb_root, "task-05", "myproject", "frontend")
        create_task_file(kb_root, "task-06", "myproject", "backend")
        result = kb_service.get_next_task("myproject", "frontend")
        assert result is not None
        assert result["id"] == "task-05"
