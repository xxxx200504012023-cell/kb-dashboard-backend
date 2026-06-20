"""KB Dashboard Backend — FastAPI application."""
from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from routes import files, projects, stats, tasks
from ws_manager import websocket_endpoint

app = FastAPI(title="KB Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(files.router)
app.include_router(stats.router)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, project: str = Query(...)):
    await websocket_endpoint(websocket, project)
