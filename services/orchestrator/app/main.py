import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.autonomy import run_autonomy_scheduler
from app.db import initialize_database
from app.recovery import recover_incomplete_runs
from app.security import ControlPlaneAuthMiddleware
from app.routers.agent import router as agent_router
from app.routers.developer import router as developer_router
from app.routers.coordination import router as coordination_router
from app.routers.self_improvement import router as self_improvement_router
from app.routers.health import router as health_router
from app.routers.projects import router as projects_router
from app.routers.organization import router as organization_router
from app.routers.tasks import router as tasks_router
from app.routers.recovery import router as recovery_router
from app.routers.project_management import router as project_management_router
from app.routers.collaboration import router as collaboration_router
from app.routers.incident_control import router as incident_control_router
from app.routers.company_trace import router as company_trace_router

initialize_database()
STARTUP_RECOVERY_REPORT = recover_incomplete_runs(
    stale_after_seconds=settings.autonomous_recovery_stale_seconds
)


def _start_scheduler_thread(stop_holder: dict[str, object]) -> threading.Timer:
    """Run autonomous work off the HTTP loop after the HTTP server is ready."""
    def worker() -> None:
        async def run() -> None:
            loop = asyncio.get_running_loop()
            stop_event = asyncio.Event()
            stop_holder["stop"] = lambda: loop.call_soon_threadsafe(stop_event.set)
            await asyncio.sleep(0.5)
            await run_autonomy_scheduler(stop_event)

        asyncio.run(run())

    timer = threading.Timer(3.0, worker)
    timer.name = "autonomy-scheduler"
    timer.daemon = True
    timer.start()
    return timer


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop_holder: dict[str, object] = {}
    scheduler_thread: threading.Timer | None = None
    if settings.autonomous_mode_enabled:
        scheduler_thread = _start_scheduler_thread(stop_holder)
    try:
        yield
    finally:
        stop_callback = stop_holder.get("stop")
        if callable(stop_callback):
            stop_callback()
        if scheduler_thread:
            scheduler_thread.cancel()
            scheduler_thread.join(timeout=5)

if settings.control_plane_auth_required:
    control_token = settings.control_plane_token.get_secret_value() if settings.control_plane_token else ""
    owner_token = settings.owner_control_token.get_secret_value() if settings.owner_control_token else ""
    if not control_token or not owner_token:
        raise RuntimeError(
            "CONTROL_PLANE_TOKEN and OWNER_CONTROL_TOKEN are required when "
            "CONTROL_PLANE_AUTH_REQUIRED=true."
        )
else:
    control_token = ""
    owner_token = ""

app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    ControlPlaneAuthMiddleware,
    required=settings.control_plane_auth_required,
    control_token=control_token,
    owner_token=owner_token,
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
app.include_router(organization_router)
app.include_router(agent_router)
app.include_router(developer_router)
app.include_router(coordination_router)
app.include_router(self_improvement_router)
app.include_router(recovery_router)
app.include_router(project_management_router)
app.include_router(collaboration_router)
app.include_router(incident_control_router)
app.include_router(company_trace_router)


@app.get("/")
def root() -> dict:
    return {
        "message": "AI Engineer Orchestrator is running",
        "service": settings.app_name,
        "version": "0.6.0",
    }

@app.get("/capabilities")
def capabilities() -> dict:
    return {
        "service": settings.app_name,
        "health_endpoint": "/health",
        "workspace_guarded": True,
        "mutation_requires_checkpoint": True,
        "autonomous_supervisor": {
            "enabled": bool(settings.autonomous_mode_enabled),
            "interval_minutes": settings.autonomous_interval_minutes,
            "cycles_per_run": settings.autonomous_cycles_per_run,
        },
        "recovery": {
            "enabled": bool(settings.autonomous_recovery_enabled),
            "recovered_runs": len(STARTUP_RECOVERY_REPORT),
            "status_endpoint": "/v1/recovery/status",
        },
    }


