#!/usr/bin/env python3
"""Run an explicit command without a shell and append evidence to the Stage 12 ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BLOCKED_EXECUTABLES = {"rm", "mkfs", "mkfs.ext4", "dd", "shutdown", "reboot", "poweroff", "halt", "fdisk", "parted"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_ledger(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "checks": []}


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return cleaned or "check"


def parse_env(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid --env value (expected KEY=VALUE): {item}")
        key, value = item.split("=", 1)
        result[key] = value
    return result


def tail_text(path: Path, lines: int = 30) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(content[-lines:])
    except OSError:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--id", required=True)
    ap.add_argument("--category", required=True)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("A command is required after --")

    exe = Path(command[0]).name.lower()
    if exe in BLOCKED_EXECUTABLES:
        raise SystemExit(f"Refusing direct destructive executable: {exe}")

    root = Path(args.root).resolve()
    cwd = (root / args.cwd).resolve() if not Path(args.cwd).is_absolute() else Path(args.cwd).resolve()
    try:
        cwd.relative_to(root)
    except ValueError:
        raise SystemExit(f"Working directory escapes project root: {cwd}")
    if not cwd.is_dir():
        raise SystemExit(f"Working directory does not exist: {cwd}")

    audit_dir = root / ".final-review"
    log_dir = audit_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{safe_id(args.id)}.log"
    ledger_path = audit_dir / "evidence.json"

    env = os.environ.copy()
    env.update(parse_env(args.env))

    started = time.monotonic()
    started_at = now()
    status = "FAIL"
    exit_code = None
    reason = None

    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"check_id: {args.id}\ncategory: {args.category}\ncwd: {cwd}\n")
        log.write("command: " + shlex.join(command) + "\n--- output ---\n")
        log.flush()
        try:
            p = subprocess.run(command, cwd=str(cwd), env=env, stdout=log, stderr=subprocess.STDOUT,
                               text=True, timeout=args.timeout, check=False)
            exit_code = p.returncode
            status = "PASS" if p.returncode == 0 else "FAIL"
            if p.returncode != 0:
                reason = f"Command exited with code {p.returncode}"
        except FileNotFoundError:
            status = "NOT_RUN"
            reason = f"Executable not found: {command[0]}"
            log.write(f"\nNOT_RUN: {reason}\n")
        except subprocess.TimeoutExpired:
            status = "FAIL"
            reason = f"Command timed out after {args.timeout} seconds"
            log.write(f"\nFAIL: {reason}\n")
        except OSError as exc:
            status = "NOT_RUN"
            reason = f"OS error starting command: {exc}"
            log.write(f"\nNOT_RUN: {reason}\n")

    duration = round(time.monotonic() - started, 3)
    digest = hashlib.sha256(log_path.read_bytes()).hexdigest()
    entry = {
        "id": args.id,
        "category": args.category,
        "status": status,
        "command": command,
        "cwd": str(cwd),
        "started_at": started_at,
        "duration_seconds": duration,
        "exit_code": exit_code,
        "log_path": str(log_path.relative_to(root)),
        "log_sha256": digest,
        "reason": reason,
    }

    ledger = load_ledger(ledger_path)
    ledger.setdefault("checks", []).append(entry)
    atomic_write(ledger_path, ledger)

    print(f"{args.id}: {status} ({duration}s)")
    if reason:
        print(reason)
    if status != "PASS":
        tail = tail_text(log_path)
        if tail:
            print("--- log tail ---")
            print(tail)
    print(f"Evidence: {ledger_path} | Log: {log_path}")

    if status == "PASS":
        return 0
    if status == "NOT_RUN":
        return 3
    return exit_code if isinstance(exit_code, int) and exit_code != 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
