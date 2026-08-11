import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.autonomy import run_autonomy_scheduler
from app.db import initialize_database
from app.routers.agent import router as agent_router
from app.routers.developer import router as developer_router
from app.routers.health import router as health_router
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router

initialize_database()


def _start_scheduler_thread(stop_holder: dict[str, object]) -> threading.Thread:
    """Run autonomous work off the HTTP event loop so SQLite/model work cannot starve APIs."""
    def worker() -> None:
        async def run() -> None:
            loop = asyncio.get_running_loop()
            stop_event = asyncio.Event()
            stop_holder["stop"] = lambda: loop.call_soon_threadsafe(stop_event.set)
            await asyncio.sleep(0.5)
            await run_autonomy_scheduler(stop_event)

        asyncio.run(run())

    thread = threading.Thread(
        target=worker,
        name="autonomy-scheduler",
        daemon=True,
    )
    thread.start()
    return thread


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop_holder: dict[str, object] = {}
    scheduler_thread: threading.Thread | None = None
    if settings.autonomous_mode_enabled:
        scheduler_thread = _start_scheduler_thread(stop_holder)
    try:
        yield
    finally:
        stop_callback = stop_holder.get("stop")
        if callable(stop_callback):
            stop_callback()
        if scheduler_thread:
            scheduler_thread.join(timeout=5)

app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    lifespan=lifespan,
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
        "version": "0.6.0",
    }
