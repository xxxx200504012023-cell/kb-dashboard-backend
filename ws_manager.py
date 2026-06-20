"""WebSocket connection pool, publish/subscribe, and heartbeat."""
import asyncio
from datetime import datetime, timezone

from starlette.websockets import WebSocket, WebSocketDisconnect

_connections: dict[str, set[WebSocket]] = {}


def _schedule(coro) -> None:
    """Schedule an async coroutine from sync context (fire-and-forget)."""
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def websocket_endpoint(websocket: WebSocket, project: str) -> None:
    """Accept a WebSocket, register it into the project pool, and run the heartbeat loop."""
    await websocket.accept()
    _connections.setdefault(project, set()).add(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except (WebSocketDisconnect, asyncio.CancelledError, RuntimeError):
        pass
    finally:
        _connections.get(project, set()).discard(websocket)
        if project in _connections and not _connections[project]:
            del _connections[project]


async def publish(project: str, event_type: str, data: dict) -> None:
    """Push an event to every subscriber of a project. Fire-and-forget per connection."""
    payload = {"type": event_type, "data": {**data, "timestamp": _now_iso()}}
    for ws in list(_connections.get(project, set())):
        try:
            await ws.send_json(payload)
        except (WebSocketDisconnect, RuntimeError):
            _connections.get(project, set()).discard(ws)


async def broadcast(event_type: str, data: dict) -> None:
    """Push an event to every connected client across all projects."""
    payload = {"type": event_type, "data": {**data, "timestamp": _now_iso()}}
    for project_key in list(_connections):
        for ws in list(_connections[project_key]):
            try:
                await ws.send_json(payload)
            except (WebSocketDisconnect, RuntimeError):
                _connections[project_key].discard(ws)
        if project_key in _connections and not _connections[project_key]:
            del _connections[project_key]
