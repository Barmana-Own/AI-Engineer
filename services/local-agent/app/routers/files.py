from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.models import (
    FileEntry,
    FileListResponse,
    FileReadResponse,
    FileWriteRequest,
    FileWriteResponse,
)
from app.services.files import (
    assert_no_symlink_escape,
    atomic_write_text,
    resolve_workspace_path,
    to_relative_path,
)

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/list", response_model=FileListResponse)
def list_files(path: str = Query(default=".", max_length=500)) -> FileListResponse:
    target = resolve_workspace_path(path, must_exist=True)
    assert_no_symlink_escape(target)

    if not target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a directory.",
        )

    entries: list[FileEntry] = []

    for child in sorted(
        target.iterdir(),
        key=lambda item: (not item.is_dir(), item.name.casefold()),
    ):
        if len(entries) >= settings.max_list_entries:
            break

        assert_no_symlink_escape(child)

        entry_type = "directory" if child.is_dir() else "file"
        size = child.stat().st_size if child.is_file() else None

        entries.append(
            FileEntry(
                name=child.name,
                path=to_relative_path(child),
                type=entry_type,
                size=size,
            )
        )

    return FileListResponse(
        path=to_relative_path(target),
        entries=entries,
    )


@router.get("/read", response_model=FileReadResponse)
def read_file(path: str = Query(min_length=1, max_length=500)) -> FileReadResponse:
    target = resolve_workspace_path(path, must_exist=True)
    assert_no_symlink_escape(target)

    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a file.",
        )

    size = target.stat().st_size

    if size > settings.max_file_read_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_file_read_bytes} bytes.",
        )

    try:
        with target.open("rb") as handle:
            raw_content = handle.read(settings.max_file_read_bytes + 1)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read file.",
        ) from exc

    if len(raw_content) > settings.max_file_read_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_file_read_bytes} bytes.",
        )

    try:
        content = raw_content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only UTF-8 text files are supported.",
        ) from exc

    size = len(raw_content)

    return FileReadResponse(
        path=to_relative_path(target),
        content=content,
        size=size,
    )


@router.post("/write", response_model=FileWriteResponse)
def write_file(request: FileWriteRequest) -> FileWriteResponse:
    target = resolve_workspace_path(request.path)
    assert_no_symlink_escape(target)

    encoded = request.content.encode("utf-8")

    if len(encoded) > settings.max_file_write_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Content exceeds {settings.max_file_write_bytes} bytes.",
        )

    if target.exists() and target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target path is a directory.",
        )

    existed = target.exists()

    if existed and not request.overwrite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File already exists. Set overwrite=true to replace it.",
        )

    atomic_write_text(target, request.content)

    return FileWriteResponse(
        path=to_relative_path(target),
        size=len(encoded),
        created=not existed,
    )