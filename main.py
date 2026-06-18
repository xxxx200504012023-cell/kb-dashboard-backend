"""KB Dashboard Backend — FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import files, projects, stats, tasks

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
