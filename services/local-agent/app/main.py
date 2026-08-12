from fastapi import FastAPI

from app.config import settings
from app.routers.files import router as files_router
from app.routers.git import router as git_router
from app.routers.health import router as health_router
from app.routers.processes import router as processes_router
from app.routers.terminal import router as terminal_router

app = FastAPI(
    title=settings.app_name,
    version="0.5.0",
)

app.include_router(health_router)
app.include_router(files_router)
app.include_router(terminal_router)
app.include_router(git_router)
app.include_router(processes_router)


@app.get("/")
def root() -> dict:
    return {
        "message": "AI Engineer Local Agent is running",
        "service": settings.app_name,
        "version": "0.5.0",
    }


@app.get("/capabilities")
def capabilities() -> dict:
    return {
        "service": settings.app_name,
        "workspace_guarded": True,
        "mutation_requires_checkpoint": True,
        "read_only_tools": ["files", "terminal_preview", "health"],
    }