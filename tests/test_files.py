"""Tests for /api/projects/{name}/files routes."""


class TestReadFile:
    async def test_read_existing(self, client, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        (proj / "readme.md").write_text("# Hello World", encoding="utf-8")
        response = await client.get("/api/projects/app/files/readme.md")
        assert response.status_code == 200
        assert response.text == "# Hello World"

    async def test_read_nonexistent(self, client):
        response = await client.get("/api/projects/app/files/no-file.md")
        assert response.status_code == 404

    async def test_read_path_traversal(self, client):
        response = await client.get("/api/projects/app/files/../secret.md")
        assert response.status_code in (400, 404)


class TestWriteFile:
    async def test_write_success(self, client, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        response = await client.put("/api/projects/app/files/notes.md", content="# Notes")
        assert response.status_code == 200
        assert (proj / "notes.md").read_text(encoding="utf-8") == "# Notes"

    async def test_write_content_too_large(self, client, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        response = await client.put("/api/projects/app/files/big.md", content="x" * 11_000_000)
        assert response.status_code == 413


class TestSearchFiles:
    async def test_search_finds_match(self, client, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        (proj / "doc.md").write_text("# Searchable content", encoding="utf-8")
        response = await client.get("/api/projects/app/search?q=Searchable")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

    async def test_search_no_match(self, client, kb_root):
        proj = kb_root / "projects" / "app"
        proj.mkdir()
        (proj / "doc.md").write_text("# Nothing here", encoding="utf-8")
        response = await client.get("/api/projects/app/search?q=xyzzy")
        assert response.status_code == 200
        assert response.json()["results"] == []
