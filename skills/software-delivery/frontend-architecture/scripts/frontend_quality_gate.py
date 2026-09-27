#!/usr/bin/env python3
"""Run declared Node frontend quality scripts and write truthful JSON evidence.

This helper is intentionally conservative: it never installs dependencies, never edits files,
and only runs scripts already declared by the target package.json.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_CANDIDATES = {
    "format": ["format:check", "format-check", "check:format"],
    "lint": ["lint"],
    "typecheck": ["typecheck", "type-check", "check:types", "types"],
    "tests": ["test:run", "test:unit", "test"],
    "build": ["build"],
}

LOCKFILES = [
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lockb", "bun"),
    ("bun.lock", "bun"),
    ("package-lock.json", "npm"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_package_manager(root: Path, package_json: dict[str, Any]) -> str | None:
    package_manager = package_json.get("packageManager")
    if isinstance(package_manager, str) and package_manager:
        name = package_manager.split("@", 1)[0].strip()
        if name in {"npm", "pnpm", "yarn", "bun"}:
            return name

    for filename, manager in LOCKFILES:
        if (root / filename).exists():
            return manager
    return "npm" if shutil.which("npm") else None


def choose_script(scripts: dict[str, Any], names: list[str]) -> str | None:
    for name in names:
        if isinstance(scripts.get(name), str):
            return name
    return None


def command_for(manager: str, script: str, category: str) -> list[str]:
    if manager == "npm":
        return ["npm", "run", script]
    if manager == "pnpm":
        return ["pnpm", "run", script]
    if manager == "yarn":
        return ["yarn", script]
    if manager == "bun":
        return ["bun", "run", script]
    raise ValueError(f"Unsupported package manager: {manager}")


def run_command(cmd: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    started = now_iso()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env={**os.environ.copy(), "CI": os.environ.get("CI", "1")},
        )
        output = completed.stdout or ""
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "command": " ".join(cmd),
            "exit_code": completed.returncode,
            "started_at": started,
            "completed_at": now_iso(),
            "output_tail": output[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        return {
            "status": "FAIL",
            "command": " ".join(cmd),
            "exit_code": None,
            "started_at": started,
            "completed_at": now_iso(),
            "error": f"Timed out after {timeout} seconds",
            "output_tail": stdout[-12000:],
        }
    except FileNotFoundError as exc:
        return {
            "status": "NOT_RUN",
            "command": " ".join(cmd),
            "exit_code": None,
            "started_at": started,
            "completed_at": now_iso(),
            "error": str(exc),
            "output_tail": "",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Frontend package root containing package.json")
    parser.add_argument("--output", help="JSON evidence output path")
    parser.add_argument("--timeout", type=int, default=900, help="Per-command timeout in seconds")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    package_path = root / "package.json"
    if not package_path.exists():
        print(f"ERROR: package.json not found: {package_path}", file=sys.stderr)
        return 2

    try:
        package_json = json.loads(package_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot parse {package_path}: {exc}", file=sys.stderr)
        return 2

    scripts = package_json.get("scripts") or {}
    if not isinstance(scripts, dict):
        scripts = {}

    manager = detect_package_manager(root, package_json)
    evidence: dict[str, Any] = {
        "generated_at": now_iso(),
        "root": str(root),
        "package_manager": manager,
        "package_name": package_json.get("name"),
        "checks": {},
    }

    if manager is None or shutil.which(manager) is None:
        for category in SCRIPT_CANDIDATES:
            evidence["checks"][category] = {
                "status": "NOT_RUN",
                "reason": f"Package manager executable unavailable: {manager}",
            }
    else:
        for category, candidates in SCRIPT_CANDIDATES.items():
            script = choose_script(scripts, candidates)
            if script is None:
                evidence["checks"][category] = {
                    "status": "NOT_APPLICABLE",
                    "reason": "No matching script declared in package.json",
                    "candidates": candidates,
                }
                continue
            cmd = command_for(manager, script, category)
            evidence["checks"][category] = run_command(cmd, root, args.timeout)
            evidence["checks"][category]["script"] = script

    mandatory_categories = ("lint", "typecheck", "tests", "build")
    mandatory_failures = []
    mandatory_not_run = []
    executed_checks = 0
    for category, result in evidence["checks"].items():
        if result.get("status") in {"PASS", "FAIL"}:
            executed_checks += 1
        if category in mandatory_categories and result.get("status") == "FAIL":
            mandatory_failures.append(category)
        if category in mandatory_categories and result.get("status") == "NOT_RUN":
            mandatory_not_run.append(category)

    if mandatory_failures:
        summary_status = "FAIL"
    elif mandatory_not_run:
        summary_status = "INCOMPLETE"
    elif executed_checks == 0:
        summary_status = "NO_CHECKS_EXECUTED"
    else:
        summary_status = "NO_EXECUTED_FAILURES"

    evidence["summary"] = {
        "mandatory_failures": mandatory_failures,
        "mandatory_not_run": mandatory_not_run,
        "executed_checks": executed_checks,
        "status": summary_status,
        "note": "This helper reports declared script execution only. Stage 03 PASS still requires the full project-specific quality-gate review.",
    }

    serialized = json.dumps(evidence, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
        print(output)
    else:
        print(serialized, end="")

    return 1 if mandatory_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
