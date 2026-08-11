from fastapi import APIRouter

from app.models import (
    ManagedProcessResponse,
    ProcessStartRequest,
    ProcessStopRequest,
)
from app.services.processes import (
    list_processes,
    start_process,
    stop_process,
)

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("", response_model=list[ManagedProcessResponse])
def processes_list() -> list[ManagedProcessResponse]:
    return [
        ManagedProcessResponse(**item)
        for item in list_processes()
    ]


@router.post("/start", response_model=ManagedProcessResponse)
def process_start(
    request: ProcessStartRequest,
) -> ManagedProcessResponse:
    return ManagedProcessResponse(
        **start_process(
            name=request.name,
            executable=request.executable,
            args=request.args,
            cwd=request.cwd,
            approved=request.approved,
        )
    )


@router.post("/stop", response_model=ManagedProcessResponse)
def process_stop(
    request: ProcessStopRequest,
) -> ManagedProcessResponse:
    return ManagedProcessResponse(
        **stop_process(
            process_id=request.process_id,
            approved=request.approved,
        )
    )