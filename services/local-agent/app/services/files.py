from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import HTTPException, status

from app.config import settings


def resolve_workspace_path(relative_path: str, *, must_exist: bool = False) -> Path:
    raw = (relative_path or "").strip().replace("\\", "/")

    if raw in {"", "."}:
        candidate = settings.workspace_path
    else:
        supplied = Path(raw)

        if supplied.is_absolute():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only workspace-relative paths are allowed.",
            )

        candidate = (settings.workspace_path / supplied).resolve(strict=False)

    workspace = settings.workspace_path

    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path escapes the configured workspace.",
        ) from exc

    if must_exist and not candidate.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Path does not exist.",
        )

    return candidate


def to_relative_path(path: Path) -> str:
    relative = path.relative_to(settings.workspace_path)
    value = relative.as_posix()
    return "." if value == "." else value


def assert_no_symlink_escape(path: Path) -> None:
    workspace = settings.workspace_path
    current = workspace

    try:
        relative_parts = path.relative_to(workspace).parts
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path escapes the configured workspace.",
        ) from exc

    for part in relative_parts:
        current = current / part

        if current.exists() and current.is_symlink():
            resolved = current.resolve()

            try:
                resolved.relative_to(workspace)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Symlink points outside the configured workspace.",
                ) from exc


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert_no_symlink_escape(path)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)