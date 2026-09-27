#!/usr/bin/env python3
"""Update Stage 02 workflow status while preserving unknown project-state keys."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STAGE = "02-design-system-ui-architecture"
PREVIOUS_STAGE = "01-project-analysis-prompt-engineering"
NEXT_STAGE = "03-frontend-architecture"
REQUIRED_ARTIFACTS = [
    "docs/02-ui-architecture.md",
    "docs/02-design-system.md",
    "docs/02-stage-03-handoff.md",
    "design/tokens.json",
]
OPTIONAL_ARTIFACTS = [
    "docs/02-stage02-validation.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError("project-state.json is required for Stage 02 state transition")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("project-state.json must contain a JSON object")
    return value


def item_stage(item: object) -> object:
    return item.get("stage") if isinstance(item, dict) else item


def dedupe_completed(items: list, include_stage: bool) -> list:
    result = [item for item in items if item_stage(item) != STAGE]
    if include_stage:
        result.append({"stage": STAGE, "status": "PASS", "completed_at": now_iso()})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    parser.add_argument("--status", required=True, choices=["IN_PROGRESS", "PASS", "BLOCKED"])
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    state_path = root / "project-state.json"
    state = load(state_path)

    if state.get("schema_version") not in (None, "1.0"):
        raise ValueError("Unsupported project-state schema_version for this Stage 02 updater")
    state.setdefault("schema_version", "1.0")

    workflow = state.setdefault("workflow", {})
    if not isinstance(workflow, dict):
        raise ValueError("workflow must be an object")
    records = workflow.setdefault("stage_records", {})
    if not isinstance(records, dict):
        raise ValueError("workflow.stage_records must be an object")
    completed = workflow.setdefault("completed_stages", [])
    if not isinstance(completed, list):
        raise ValueError("workflow.completed_stages must be an array")

    previous = records.get(PREVIOUS_STAGE)
    if isinstance(previous, dict) and previous.get("status") != "PASS":
        raise ValueError("Stage 01 is recorded but has not passed")

    if args.status == "PASS":
        missing = [p for p in REQUIRED_ARTIFACTS if not (root / p).exists()]
        if missing:
            raise FileNotFoundError("Cannot mark Stage 02 PASS; missing artifacts: " + ", ".join(missing))

    artifacts = [p for p in REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS if (root / p).exists()]
    previous_record = records.get(STAGE) if isinstance(records.get(STAGE), dict) else {}
    records[STAGE] = {
        **previous_record,
        "status": args.status,
        "artifacts": artifacts,
        "updated_at": now_iso(),
    }

    if args.status == "PASS":
        workflow["current_stage"] = NEXT_STAGE
        workflow["next_stage"] = NEXT_STAGE
        workflow["completed_stages"] = dedupe_completed(completed, True)
    elif args.status == "BLOCKED":
        workflow["current_stage"] = STAGE
        workflow["next_stage"] = None
        workflow["completed_stages"] = dedupe_completed(completed, False)
    else:
        workflow["current_stage"] = STAGE
        workflow["next_stage"] = NEXT_STAGE
        workflow["completed_stages"] = dedupe_completed(completed, False)

    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": args.status, "state": str(state_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
