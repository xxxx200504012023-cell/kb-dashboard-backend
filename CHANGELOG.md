# Changelog

## [0.1.1] — 2026-06-15

### Security Fixes (code review findings)

- **Path traversal prevention**: All route handlers now validate project name via `validate_project_name()` before processing
- **DoS protection**: File write endpoint uses `request.stream()` with bounded read instead of loading full body into memory
- **Cross-project task isolation**: `claim_task` and `complete_task` now validate task project ownership before operating
- **Input validation**: All request bodies use Pydantic models (`CreateProjectRequest`, `ClaimTaskRequest`, `CompleteTaskRequest`) instead of raw `dict`
- **Unicode error handling**: File write endpoint catches `UnicodeDecodeError` and returns HTTP 400 instead of 500
- **Crash safety**: Replaced `line.index("]")` with `line.find("]")` + guard in `get_tasks` to prevent `ValueError`

### Added

- `get_project_type(name)` in kb_service: detects frontend vs backend by checking for `CODEX.md`
- `_get_task_project(task_id)` in kb_service: extracts project field from task YAML frontmatter
- `_read_body_bounded()` in routes/files.py: streaming body reader with configurable size cap
- `_validate_project()` helper in routes/files.py

### Changed

- `routes/projects.py`: `list_projects` now returns actual project type instead of hardcoded `"backend"`
- Tests: deduplicated `_create_task` helper into `conftest.create_task_file`
- Tests: `conftest.py` now adds project root to `sys.path` for module discovery

## [0.1.0] — 2026-06-14

### Initial Release

- FastAPI server with 9 API endpoints
- KB MCP Server integration (file_tools, task_tools, project_tools)
- Project CRUD, task kanban, file read/write/search
- CORS middleware for frontend (localhost:5173)
- 39 tests, 94% code coverage
