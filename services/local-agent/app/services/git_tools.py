from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO

from fastapi import HTTPException, status

from app.services.files import (
    assert_no_symlink_escape,
    resolve_workspace_path,
    to_relative_path,
)


# The Local Agent can receive overlapping Git requests while the autonomous
# supervisor is moving from a checkpoint to diff/validation.  Serialize those
# requests in-process and retry a short-lived index lock instead of turning a
# healthy cycle into a false failure.
_GIT_MUTEX = threading.RLock()
_LOCK_RETRY_SECONDS = 15.0
_GIT_DIFF_MAX_BYTES = 1_048_576
_GIT_DIFF_TRUNCATION_MARKER = "\n...[diff truncated at 1048576 bytes]..."
_GIT_OUTPUT_MAX_BYTES = 1_048_576
_GIT_OUTPUT_TRUNCATION_MARKER = "\n...[git output truncated at 1048576 bytes]..."


def _drain_stream(stream: BinaryIO, buffer: bytearray) -> None:
    limit = _GIT_OUTPUT_MAX_BYTES + 1
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            return
        if len(buffer) < limit:
            buffer.extend(chunk[: limit - len(buffer)])


def _decode_git_output(buffer: bytearray) -> str:
    raw = bytes(buffer)
    if len(raw) <= _GIT_OUTPUT_MAX_BYTES:
        return raw.decode("utf-8", errors="replace")

    marker = _GIT_OUTPUT_TRUNCATION_MARKER.encode("utf-8")
    budget = max(_GIT_OUTPUT_MAX_BYTES - len(marker), 0)
    return raw[:budget].decode("utf-8", errors="ignore") + _GIT_OUTPUT_TRUNCATION_MARKER

def _git_executable() -> str:
    executable = shutil.which("git.exe") or shutil.which("git")

    if not executable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Git is not installed or not available in PATH.",
        )

    return executable


def _project_root(project_path: str) -> Path:
    root = resolve_workspace_path(project_path, must_exist=True)
    assert_no_symlink_escape(root)

    if not root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project path must be a directory.",
        )

    return root


def _git_environment(root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
            "GIT_ASKPASS": "echo",
            "SSH_ASKPASS": "echo",
            "GIT_PAGER": "cat",
            "GIT_EDITOR": "true",
            "GIT_EXTERNAL_DIFF": "",
            "NO_COLOR": "1",
            # Never inherit F:/AI-Engineer/.git or another parent repository.
            "GIT_CEILING_DIRECTORIES": str(root.parent),
        }
    )
    return environment


def _run_git(
    root: Path,
    args: list[str],
    *,
    check: bool = True,
    timeout: int = 90,
) -> subprocess.CompletedProcess[str]:
    with _GIT_MUTEX:
        retry_deadline = time.monotonic() + _LOCK_RETRY_SECONDS
        while True:
            command = [_git_executable(), *args]
            process = subprocess.Popen(
                command,
                cwd=str(root),
                env=_git_environment(root),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout_buffer = bytearray()
            stderr_buffer = bytearray()
            stdout_thread = threading.Thread(
                target=_drain_stream,
                args=(process.stdout, stdout_buffer),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_drain_stream,
                args=(process.stderr, stderr_buffer),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                process.kill()
                process.wait()
                stdout_thread.join()
                stderr_thread.join()
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail={
                        "message": "Git command timed out.",
                        "args": args,
                        "timeout_seconds": timeout,
                    },
                ) from exc
            stdout_thread.join()
            stderr_thread.join()
            completed = subprocess.CompletedProcess(
                command,
                process.returncode,
                _decode_git_output(stdout_buffer),
                _decode_git_output(stderr_buffer),
            )

            lock_busy = (
                completed.returncode != 0
                and "index.lock" in (completed.stderr or "")
                and time.monotonic() < retry_deadline
            )
            if not lock_busy:
                break
            time.sleep(0.5)

    if check and completed.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Git command failed.",
                "args": args,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )

    return completed


def _ensure_repository(root: Path) -> None:
    # A project must own its repository. A parent repository is never accepted.
    project_git = root / ".git"

    if not project_git.exists():
        _run_git(root, ["init"], timeout=30)

    top_level = _run_git(
        root,
        ["rev-parse", "--show-toplevel"],
        timeout=15,
    )

    discovered = Path(top_level.stdout.strip()).resolve()

    if discovered != root:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Project Git isolation failed.",
                "expected": str(root),
                "discovered": str(discovered),
            },
        )

    hooks_dir = project_git / "ai-engineer-hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    local_settings = (
        ("user.name", "AI Engineer"),
        ("user.email", "ai-engineer@local"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
        ("core.hooksPath", str(hooks_dir)),
        ("credential.interactive", "never"),
        ("core.fsmonitor", "false"),
        ("diff.external", ""),
    )

    for key, value in local_settings:
        _run_git(
            root,
            ["config", "--local", key, value],
            timeout=15,
        )

    # Never delete Git lock files here.  A lock can belong to a concurrent
    # checkpoint; _run_git waits briefly for that operation to finish.  An
    # operator can still recover a genuinely stale lock explicitly after
    # checking that no Git process is active.


def git_status(project_path: str) -> dict[str, Any]:
    root = _project_root(project_path)
    _ensure_repository(root)

    branch = _run_git(
        root,
        ["branch", "--show-current"],
        check=False,
        timeout=15,
    )
    result = _run_git(
        root,
        ["status", "--porcelain=v1", "--untracked-files=all"],
        timeout=30,
    )

    changes = [
        line
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    return {
        "project_path": to_relative_path(root),
        "repository_root": str(root),
        "branch": branch.stdout.strip() or "detached",
        "clean": not changes,
        "changes": changes,
    }


def git_checkpoint(
    project_path: str,
    message: str,
    include_untracked: bool,
) -> dict[str, Any]:
    root = _project_root(project_path)
    _ensure_repository(root)

    _run_git(
        root,
        ["add", "-A" if include_untracked else "-u"],
        timeout=120,
    )

    staged = _run_git(
        root,
        ["diff", "--cached", "--quiet"],
        check=False,
        timeout=30,
    )
    head = _run_git(
        root,
        ["rev-parse", "HEAD"],
        check=False,
        timeout=15,
    )

    if staged.returncode == 0:
        return {
            "project_path": to_relative_path(root),
            "repository_root": str(root),
            "created": False,
            "commit": head.stdout.strip() if head.returncode == 0 else None,
            "message": "No changes to checkpoint.",
        }

    _run_git(
        root,
        [
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--no-verify",
            "--no-gpg-sign",
            "-m",
            message,
        ],
        timeout=120,
    )

    commit = _run_git(
        root,
        ["rev-parse", "HEAD"],
        timeout=15,
    ).stdout.strip()

    return {
        "project_path": to_relative_path(root),
        "repository_root": str(root),
        "created": True,
        "commit": commit,
        "message": message,
    }


def _truncate_diff(value: str) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= _GIT_DIFF_MAX_BYTES:
        return value, False

    marker_bytes = _GIT_DIFF_TRUNCATION_MARKER.encode("utf-8")
    budget = max(_GIT_DIFF_MAX_BYTES - len(marker_bytes), 0)
    truncated = encoded[:budget].decode("utf-8", errors="ignore")
    return truncated + _GIT_DIFF_TRUNCATION_MARKER, True

def git_diff(
    project_path: str,
    staged: bool,
    base: str | None,
) -> dict[str, Any]:
    root = _project_root(project_path)
    _ensure_repository(root)

    args = [
        "-c",
        "diff.external=",
        "--no-pager",
        "diff",
        "--no-ext-diff",
        "--text",
        "--no-renames",
    ]

    if staged:
        args.append("--cached")

    if base:
        args.append(base)

    args.extend(["--", "."])
    result = _run_git(root, args, timeout=90)
    diff, diff_truncated = _truncate_diff(result.stdout)

    return {
        "project_path": to_relative_path(root),
        "repository_root": str(root),
        "staged": staged,
        "base": base,
        "diff": diff,
        "diff_truncated": diff_truncated,
    }


def git_rollback(
    project_path: str,
    commit: str,
    approved: bool,
) -> dict[str, Any]:
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Explicit approval is required for rollback.",
        )

    if not re.fullmatch(r"[0-9a-fA-F]{4,40}", commit):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Git commit identifier.",
        )

    root = _project_root(project_path)
    _ensure_repository(root)

    verify = _run_git(
        root,
        ["rev-parse", "--verify", f"{commit}^{{commit}}"],
        check=False,
        timeout=15,
    )

    if verify.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commit was not found.",
        )

    previous = _run_git(
        root,
        ["rev-parse", "HEAD"],
        check=False,
        timeout=15,
    )

    _run_git(
        root,
        ["reset", "--hard", commit],
        timeout=90,
    )

    current = _run_git(
        root,
        ["rev-parse", "HEAD"],
        timeout=15,
    ).stdout.strip()

    return {
        "project_path": to_relative_path(root),
        "repository_root": str(root),
        "previous_commit": (
            previous.stdout.strip()
            if previous.returncode == 0
            else None
        ),
        "current_commit": current,
        "untracked_files_preserved": True,
    }
