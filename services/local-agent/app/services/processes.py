from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.config import settings
from app.services.files import (
    assert_no_symlink_escape,
    resolve_workspace_path,
    to_relative_path,
)

REGISTRY_PATH = Path(settings.managed_process_registry_path).expanduser()
LOG_ROOT = Path(settings.managed_process_log_root).expanduser()
MAX_MANAGED_PROCESSES = 256
MAX_REGISTRY_BYTES = 4 * 1024 * 1024
LOCK = threading.Lock()

ALLOWED_EXECUTABLE_NAMES = {
    "node.exe",
    "node",
    "npm.cmd",
    "npm",
    "npx.cmd",
    "npx",
    "python.exe",
    "python",
    "php.exe",
    "php",
    "composer.bat",
    "composer",
    "docker.exe",
    "docker",
    "docker-compose.exe",
    "docker-compose",
    "xampp_start.exe",
    "xampp_stop.exe",
    "apache_start.bat",
    "apache_stop.bat",
    "mysql_start.bat",
    "mysql_stop.bat",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_registry() -> dict[str, dict[str, Any]]:
    with LOCK:
        if not REGISTRY_PATH.exists():
            return {}

        try:
            payload = REGISTRY_PATH.read_bytes()
            if len(payload) > MAX_REGISTRY_BYTES:
                return {}
            value = json.loads(payload.decode("utf-8"))
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}


def _save_registry(registry: dict[str, dict[str, Any]]) -> None:
    with LOCK:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(registry, ensure_ascii=False, indent=2).encode("utf-8")
        if len(payload) > MAX_REGISTRY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Managed process registry exceeds {MAX_REGISTRY_BYTES} bytes.",
            )
        temporary = REGISTRY_PATH.with_suffix(".tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, REGISTRY_PATH)


def _is_running(pid: int) -> bool:
    completed = subprocess.run(
        ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    output = completed.stdout.strip().lower()
    return bool(output and "no tasks are running" not in output)


def _resolve_executable(value: str) -> str:
    supplied = Path(value)
    candidate: str | None = None

    if supplied.is_absolute():
        if supplied.exists() and supplied.is_file():
            candidate = str(supplied.resolve())
    else:
        candidate = shutil.which(value)

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Executable not found: {value}",
        )

    name = Path(candidate).name.lower()

    if name not in ALLOWED_EXECUTABLE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Executable is not allowed: {name}",
        )

    return candidate


def _compact_registry(registry: dict[str, dict[str, Any]], *, reserve: int = 0) -> bool:
    """Refresh process state and evict oldest stopped records within the cap."""
    changed = False
    for item in registry.values():
        try:
            running = _is_running(int(item["pid"]))
        except (KeyError, TypeError, ValueError):
            running = False
        if item.get("running") != running:
            item["running"] = running
            changed = True

    target = max(MAX_MANAGED_PROCESSES - max(int(reserve), 0), 0)
    stopped = sorted(
        (
            (process_id, item)
            for process_id, item in registry.items()
            if not item.get("running")
        ),
        key=lambda pair: (str(pair[1].get("started_at", "")), pair[0]),
    )
    while len(registry) > target and stopped:
        process_id, _item = stopped.pop(0)
        registry.pop(process_id, None)
        changed = True
    return changed

def list_processes() -> list[dict[str, Any]]:
    registry = _load_registry()
    changed = _compact_registry(registry)
    results = [
        {
            "id": process_id,
            **item,
        }
        for process_id, item in registry.items()
    ]

    if changed:
        _save_registry(registry)

    return sorted(
        results,
        key=lambda item: item["started_at"],
        reverse=True,
    )[:MAX_MANAGED_PROCESSES]
def start_process(
    *,
    name: str,
    executable: str,
    args: list[str],
    cwd: str,
    approved: bool,
) -> dict[str, Any]:
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Explicit approval is required to start a managed process.",
        )

    target_cwd = resolve_workspace_path(cwd, must_exist=True)
    assert_no_symlink_escape(target_cwd)

    if not target_cwd.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process cwd must be a directory.",
        )

    resolved_executable = _resolve_executable(executable)
    registry = _load_registry()
    changed = _compact_registry(registry, reserve=1)
    if len(registry) >= MAX_MANAGED_PROCESSES:
        if changed:
            _save_registry(registry)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Managed process limit reached ({MAX_MANAGED_PROCESSES}). Stop a process before starting another.",
        )
    if changed:
        _save_registry(registry)

    process_id = str(uuid4())
    LOG_ROOT.mkdir(parents=True, exist_ok=True)

    stdout_log = LOG_ROOT / f"{process_id}.out.log"
    stderr_log = LOG_ROOT / f"{process_id}.err.log"

    stdout_handle = stdout_log.open("ab")
    stderr_handle = stderr_log.open("ab")

    creation_flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )

    try:
        if Path(resolved_executable).suffix.lower() in {".cmd", ".bat"}:
            command_line = subprocess.list2cmdline(
                [resolved_executable, *args]
            )
            command = [
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                command_line,
            ]
        else:
            command = [resolved_executable, *args]

        process = subprocess.Popen(
            command,
            cwd=str(target_cwd),
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            shell=False,
            close_fds=False,
            creationflags=creation_flags,
        )
    finally:
        stdout_handle.close()
        stderr_handle.close()

    item = {
        "name": name,
        "executable": resolved_executable,
        "args": args,
        "cwd": to_relative_path(target_cwd),
        "pid": process.pid,
        "running": True,
        "started_at": _utc_now(),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }

    registry = _load_registry()
    registry[process_id] = item
    _save_registry(registry)

    return {"id": process_id, **item}


def stop_process(process_id: str, approved: bool) -> dict[str, Any]:
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Explicit approval is required to stop a managed process.",
        )

    registry = _load_registry()
    item = registry.get(process_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed process was not found.",
        )

    pid = int(item["pid"])

    if _is_running(pid):
        subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    item["running"] = False
    registry[process_id] = item
    _save_registry(registry)

    return {"id": process_id, **item}