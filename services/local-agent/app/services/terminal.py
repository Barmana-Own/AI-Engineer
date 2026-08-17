from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, status

from app.config import settings
from app.services.files import (
    assert_no_symlink_escape,
    resolve_workspace_path,
    to_relative_path,
)

Risk = Literal["safe", "approval_required", "blocked"]


@dataclass(frozen=True)
class CommandAssessment:
    risk: Risk
    reasons: list[str]


BLOCKED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?i)(^|\s)format(?:\.com)?(\s|$)", "Disk formatting is blocked."),
    (r"(?i)(^|\s)diskpart(\s|$)", "DiskPart is blocked."),
    (r"(?i)(^|\s)(shutdown|restart-computer|stop-computer)(\s|$)", "System shutdown/restart is blocked."),
    (r"(?i)(^|\s)bcdedit(\s|$)", "Boot configuration changes are blocked."),
    (r"(?i)(^|\s)mkfs(?:\.|\s|$)", "Filesystem formatting is blocked."),
    (r"(?i)(^|\s)dd\s+if=", "Raw disk writes are blocked."),
    (r"(?i)reg(?:\.exe)?\s+delete\s+HKLM", "Deleting HKLM registry keys is blocked."),
    (r"(?i)netsh\s+advfirewall\s+set\s+allprofiles\s+state\s+off", "Disabling the firewall is blocked."),
    (r"(?i)set-executionpolicy\s+(unrestricted|bypass)\s+-(scope\s+)?(localmachine|machinepolicy)", "Machine-wide execution-policy weakening is blocked."),
    (r"(?i)remove-item\b.*(?:[A-Z]:\\(?:Windows|Program Files|Users)?\\?\s*$)", "Deleting protected drive roots is blocked."),
    (r"(?i)(?:rd|rmdir|del|erase)\b.*(?:/s|/q).*[A-Z]:\\(?:Windows|Program Files|Users)?\\?\s*$", "Deleting protected drive roots is blocked."),
    (r"(?i)rm\s+-rf\s+/(?:\s|$)", "Deleting the filesystem root is blocked."),
)

APPROVAL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?i)\b(remove-item|del|erase|rd|rmdir)\b", "Deletes files or directories."),
    (r"(?i)\brm(?:\.exe)?\b", "Deletes files or directories."),
    (r"(?i)\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f)", "Can discard Git work."),
    (r"(?i)\b(npm|pnpm|yarn|pip|python\s+-m\s+pip)\s+(install|uninstall|update|upgrade)\b", "Changes installed dependencies."),
    (r"(?i)\bwinget\s+(install|uninstall|upgrade)\b", "Changes installed applications."),
    (r"(?i)\b(choco|scoop)\s+(install|uninstall|update|upgrade)\b", "Changes installed applications."),
    (r"(?i)\b(docker|docker-compose)\b", "Controls containers or images."),
    (r"(?i)\b(start-process|stop-process|taskkill|kill|pkill)\b", "Starts or stops processes."),
    (r"(?i)\b(net|sc(?:\.exe)?)\s+(start|stop|delete|config|create)\b", "Changes Windows services."),
    (r"(?i)\b(reg(?:\.exe)?\s+(add|import)|set-itemproperty|new-itemproperty|remove-itemproperty)\b", "Changes registry or system settings."),
    (r"(?i)\b(set-content|add-content|out-file|new-item|copy-item|move-item|rename-item)\b", "Writes or changes files."),
    (r"(?i)\b(invoke-webrequest|invoke-restmethod|iwr|irm|curl(?:\.exe)?|wget)\b", "Makes an external network request."),
    (r"(?i)(?:^|[^>])>(?:>|[^>])", "Uses output redirection."),
    (r"(?i)\$\(", "Contains PowerShell subexpression or command substitution."),
    (r"[\r\n;&|]", "Contains command chaining, piping, or multiple commands."),
)


def classify_command(command: str) -> CommandAssessment:
    normalized = command.strip()

    if not normalized:
        return CommandAssessment(
            risk="blocked",
            reasons=["Command is empty."],
        )

    if len(normalized) > settings.max_command_length:
        return CommandAssessment(
            risk="blocked",
            reasons=[f"Command exceeds {settings.max_command_length} characters."],
        )

    blocked_reasons = [
        reason
        for pattern, reason in BLOCKED_PATTERNS
        if re.search(pattern, normalized)
    ]

    if blocked_reasons:
        return CommandAssessment(
            risk="blocked",
            reasons=list(dict.fromkeys(blocked_reasons)),
        )

    approval_reasons = [
        reason
        for pattern, reason in APPROVAL_PATTERNS
        if re.search(pattern, normalized)
    ]

    if approval_reasons:
        return CommandAssessment(
            risk="approval_required",
            reasons=list(dict.fromkeys(approval_reasons)),
        )

    return CommandAssessment(
        risk="safe",
        reasons=["No destructive or system-changing pattern detected."],
    )


def resolve_command_cwd(cwd: str) -> Path:
    target = resolve_workspace_path(cwd, must_exist=True)
    assert_no_symlink_escape(target)

    if not target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Terminal cwd must be a directory.",
        )

    return target


def _truncate_output(value: str) -> str:
    encoded = value.encode("utf-8", errors="replace")

    if len(encoded) <= settings.max_command_output_bytes:
        return value

    marker = "\n...[output truncated by Local Agent]..."
    allowed = settings.max_command_output_bytes - len(marker.encode("utf-8"))
    clipped = encoded[:max(0, allowed)].decode("utf-8", errors="replace")
    return clipped + marker


def run_command(
    *,
    command: str,
    cwd: str,
    shell: Literal["powershell", "cmd"],
    approved: bool,
    timeout_seconds: int | None,
) -> dict:
    assessment = classify_command(command)

    if assessment.risk == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Command is blocked.",
                "risk": assessment.risk,
                "reasons": assessment.reasons,
            },
        )

    if assessment.risk == "approval_required" and not approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Explicit approval is required.",
                "risk": assessment.risk,
                "reasons": assessment.reasons,
            },
        )

    target_cwd = resolve_command_cwd(cwd)
    timeout = timeout_seconds or settings.command_timeout_seconds
    timeout = min(timeout, settings.max_command_timeout_seconds)

    if shell == "powershell":
        executable = "powershell.exe"
        arguments = [
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]
    else:
        executable = "cmd.exe"
        arguments = ["/d", "/s", "/c", command]

    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["NO_PROXY"] = "localhost,127.0.0.1,::1"
    environment["no_proxy"] = "localhost,127.0.0.1,::1"

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            [executable, *arguments],
            cwd=str(target_cwd),
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
            creationflags=creation_flags,
        )

        duration_ms = int((time.perf_counter() - started) * 1000)

        return {
            "command": command,
            "cwd": to_relative_path(target_cwd),
            "shell": shell,
            "risk": assessment.risk,
            "exit_code": completed.returncode,
            "stdout": _truncate_output(completed.stdout),
            "stderr": _truncate_output(completed.stderr),
            "timed_out": False,
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)

        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return {
            "command": command,
            "cwd": to_relative_path(target_cwd),
            "shell": shell,
            "risk": assessment.risk,
            "exit_code": 124,
            "stdout": _truncate_output(stdout),
            "stderr": _truncate_output(stderr or f"Command timed out after {timeout} seconds."),
            "timed_out": True,
            "duration_ms": duration_ms,
        }
