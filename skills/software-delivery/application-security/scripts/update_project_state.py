#!/usr/bin/env python3
"""Safely insert/replace the Stage 08 entry in project-state.json."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STAGE_ID = "08-application-security"
VALID_STATUS = {"PASS", "FAIL", "BLOCKED"}


def parse_args():
    p = argparse.ArgumentParser(description="Update Stage 08 state without deleting unknown keys")
    p.add_argument("state_file", nargs="?", default="project-state.json")
    p.add_argument("--status", required=True, choices=sorted(VALID_STATUS))
    p.add_argument("--artifact", action="append", default=[])
    p.add_argument("--decision", action="append", default=[])
    p.add_argument("--assumption", action="append", default=[])
    p.add_argument("--risk", action="append", default=[])
    p.add_argument("--completed-at", help="ISO-8601 timestamp; defaults to now UTC")
    p.add_argument("--next-stage", help="Override next stage")
    return p.parse_args()


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("project-state root must be a JSON object")
    return data


def upsert_completed_stages(state: dict, entry: dict) -> None:
    current = state.get("completed_stages")
    if current is None:
        state["completed_stages"] = [entry]
        return
    if isinstance(current, list):
        replaced = False
        new_items = []
        for item in current:
            if isinstance(item, dict) and item.get("id") == STAGE_ID:
                new_items.append(entry)
                replaced = True
            else:
                new_items.append(item)
        if not replaced:
            new_items.append(entry)
        state["completed_stages"] = new_items
        return
    if isinstance(current, dict):
        current[STAGE_ID] = entry
        return
    raise ValueError("completed_stages has unsupported shape; refusing to overwrite it")


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def main() -> int:
    args = parse_args()
    path = Path(args.state_file).expanduser().resolve()
    try:
        state = load_state(path)
        completed_at = args.completed_at or datetime.now(timezone.utc).isoformat()
        next_stage = args.next_stage or ("09-software-testing" if args.status == "PASS" else "NONE")
        entry = {
            "id": STAGE_ID,
            "status": args.status,
            "completed_at": completed_at,
            "artifacts": args.artifact or [
                "docs/08-security-review.md",
                "docs/security/08-security-findings.json",
            ],
            "material_decisions": args.decision,
            "assumptions": args.assumption,
            "risks": args.risk,
            "next_stage": next_stage,
        }
        upsert_completed_stages(state, entry)
        atomic_write(path, state)
        # Re-parse to verify final JSON.
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"updated {path} with {STAGE_ID} status={args.status} next_stage={next_stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
