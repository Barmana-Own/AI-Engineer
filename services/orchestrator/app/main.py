from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import initialize_database
from app.routers.agent import router as agent_router
from app.routers.developer import router as developer_router
from app.routers.health import router as health_router
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router

initialize_database()

app = FastAPI(
    title=settings.app_name,
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(projects_router)
app.include_router(agent_router)
app.include_router(developer_router)


@app.get("/")
def root() -> dict:
    return {
        "message": "AI Engineer Orchestrator is running",
        "service": settings.app_name,
        "version": "0.5.0",
    }