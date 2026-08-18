from __future__ import annotations

import os
import tempfile
from pathlib import Path
from pathlib import PurePosixPath

from fastapi import HTTPException, status

from app.config import settings


def _allowed_roots() -> tuple[Path, ...]:
    roots: list[Path] = [settings.workspace_path]
    self_root = settings.self_workspace_path
    if self_root not in roots:
        roots.append(self_root)
    return tuple(roots)


def _relative_to_allowed_root(path: Path) -> tuple[Path, Path] | None:
    resolved = path.resolve(strict=False)
    for root in _allowed_roots():
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        return root, resolved
    return None


def resolve_workspace_path(relative_path: str, *, must_exist: bool = False) -> Path:
    raw = (relative_path or "").strip().replace("\\", "/")

    if any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path contains control characters.",
        )

    if raw in {"", "."}:
        candidate = settings.workspace_path
    else:
        supplied = PurePosixPath(raw)

        if supplied.is_absolute() or ":" in supplied.parts[0]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only workspace-relative paths are allowed.",
            )

        alias = settings.self_workspace_name.strip().strip("/").casefold()
        first = supplied.parts[0].casefold() if supplied.parts else ""
        if alias and first == alias:
            candidate = settings.self_workspace_path.joinpath(*supplied.parts[1:])
        else:
            candidate = settings.workspace_path.joinpath(*supplied.parts)

    candidate = candidate.resolve(strict=False)
    if _relative_to_allowed_root(candidate) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path escapes the configured workspace roots.",
        )

    if must_exist and not candidate.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Path does not exist.",
        )

    return candidate


def to_relative_path(path: Path) -> str:
    allowed = _relative_to_allowed_root(path)
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path is outside the configured workspace roots.",
        )

    root, resolved = allowed
    relative = resolved.relative_to(root)
    value = relative.as_posix()
    if root == settings.self_workspace_path:
        alias = settings.self_workspace_name.strip().strip("/")
        return alias if value == "." else f"{alias}/{value}"
    return "." if value == "." else value


def assert_no_symlink_escape(path: Path) -> None:
    allowed = _relative_to_allowed_root(path)
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path escapes the configured workspace roots.",
        )

    root, resolved_path = allowed
    current = root
    relative_parts = resolved_path.relative_to(root).parts
    allowed_roots = _allowed_roots()

    for part in relative_parts:
        current = current / part

        if current.exists() and current.is_symlink():
            resolved = current.resolve()

            if not any(
                resolved == allowed_root or resolved.is_relative_to(allowed_root)
                for allowed_root in allowed_roots
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Symlink points outside the configured workspace roots.",
                )


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
