"""Shared helpers for route handlers."""
import re

_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:[/\\][^\s]*knowledge-base[/\\][^\s]*"),
    re.compile(r"C:\\Users\\[^\s]*"),
    re.compile(r"/home/[^\s]*"),
]


def sanitize_error(msg: str) -> str:
    """Strip internal filesystem paths from error messages."""
    for pattern in _PATH_PATTERNS:
        msg = pattern.sub("[internal-path]", msg)
    return msg


def validate_project_name(name: str) -> str | None:
    """Validate project name. Returns error message or None if valid."""
    if not name or not name.strip():
        return "Project name must not be empty"
    name = name.strip()
    if len(name) > 100:
        return "Project name too long (max 100 chars)"
    if ".." in name or "/" in name or "\\" in name:
        return "Project name contains invalid characters"
    if "\x00" in name:
        return "Project name contains null byte"
    if not re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9_]*$", name):
        return "Project name must start with alphanumeric and contain only alphanumeric, hyphens, and underscores"
    return None
