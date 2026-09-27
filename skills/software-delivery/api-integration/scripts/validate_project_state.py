#!/usr/bin/env python3
"""Validate project-state.json for Barmana Stage 06 orchestration.

This script intentionally supports several compatible historical layouts instead of
rewriting them. It never prints secret values and never modifies the state file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

PASS = "PASS"
BLOCKED = "BLOCKED"


def norm_id(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    aliases = {
        "5": "05",
        "05": "05",
        "stage05": "05",
        "stage-05": "05",
        "stage_05": "05",
        "database": "05",
        "persistence": "05",
        "6": "06",
        "06": "06",
        "stage06": "06",
        "stage-06": "06",
        "stage_06": "06",
        "api-integration": "06",
    }
    return aliases.get(s, s)


def norm_status(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().upper()
    if s in {"PASS", "PASSED", "COMPLETE", "COMPLETED", "DONE"}:
        return PASS
    if s in {"BLOCKED", "FAIL", "FAILED", "ERROR"}:
        return BLOCKED
    return s


def iter_stage_records(data: dict[str, Any]) -> Iterable[tuple[str, str | None, str]]:
    stages = data.get("stages")
    if isinstance(stages, dict):
        for key, value in stages.items():
            sid = norm_id(key)
            if isinstance(value, dict):
                sid = norm_id(value.get("id") or value.get("stage") or value.get("stage_id") or sid)
                status = norm_status(value.get("status") or value.get("result"))
            else:
                status = norm_status(value)
            if sid:
                yield sid, status, f"stages.{key}"
    elif isinstance(stages, list):
        for idx, value in enumerate(stages):
            if not isinstance(value, dict):
                continue
            sid = norm_id(value.get("id") or value.get("stage") or value.get("stage_id") or value.get("name"))
            status = norm_status(value.get("status") or value.get("result"))
            if sid:
                yield sid, status, f"stages[{idx}]"

    completed = data.get("completed_stages")
    if isinstance(completed, list):
        for idx, value in enumerate(completed):
            if isinstance(value, dict):
                sid = norm_id(value.get("id") or value.get("stage") or value.get("stage_id") or value.get("name"))
                status = norm_status(value.get("status") or value.get("result") or PASS)
            else:
                sid = norm_id(value)
                status = PASS
            if sid:
                yield sid, status, f"completed_stages[{idx}]"


def resolve_stage(data: dict[str, Any], stage_id: str) -> tuple[str | None, list[str], bool]:
    statuses: list[str] = []
    sources: list[str] = []
    for sid, status, source in iter_stage_records(data):
        if sid == stage_id:
            sources.append(source)
            if status:
                statuses.append(status)
    unique = sorted(set(statuses))
    conflict = len(unique) > 1
    return (unique[0] if len(unique) == 1 else None), sources, conflict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="project-state.json")
    parser.add_argument("--require-stage05-pass", action="store_true")
    parser.add_argument("--require-stage06-pass", action="store_true")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: state file not found: {path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print("ERROR: root JSON value must be an object", file=sys.stderr)
        return 2

    failed = False
    for stage_id in ("05", "06"):
        status, sources, conflict = resolve_stage(data, stage_id)
        source_text = ", ".join(sources) if sources else "not found"
        if conflict:
            print(f"ERROR: Stage {stage_id} has conflicting status records ({source_text})")
            failed = True
        else:
            print(f"Stage {stage_id}: {status or 'UNKNOWN'} ({source_text})")

    stage05, _, stage05_conflict = resolve_stage(data, "05")
    stage06, _, stage06_conflict = resolve_stage(data, "06")

    if args.require_stage05_pass and (stage05_conflict or stage05 != PASS):
        print("ERROR: Stage 05 PASS is required")
        failed = True
    if args.require_stage06_pass and (stage06_conflict or stage06 != PASS):
        print("ERROR: Stage 06 PASS is required")
        failed = True

    if failed:
        return 1

    print("OK: project state is parseable and requested stage conditions are satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
