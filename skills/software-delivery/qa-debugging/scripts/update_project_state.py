#!/usr/bin/env python3
"""Conservatively merge a Stage 10 payload into project-state.json."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGE_ID = 10
STAGE_NAME = "qa-debugging"
NEXT_STAGE = "11-deployment-production"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Stage payload must be a JSON object")
    if payload.get("stage_id") != STAGE_ID:
        raise ValueError("stage_id must be 10")
    if payload.get("stage_name") != STAGE_NAME:
        raise ValueError("stage_name must be 'qa-debugging'")
    status = payload.get("status")
    if status not in {"PASS", "BLOCKED"}:
        raise ValueError("status must be PASS or BLOCKED")
    if status == "PASS":
        if payload.get("next_stage") != NEXT_STAGE:
            raise ValueError(f"PASS payload next_stage must be '{NEXT_STAGE}'")
    else:
        if payload.get("next_stage") not in {None, "", "NONE"}:
            raise ValueError("BLOCKED payload next_stage must be null, empty, or NONE")
        blockers = payload.get("blockers")
        if not isinstance(blockers, list) or not blockers:
            raise ValueError("BLOCKED payload must contain at least one blocker")


def stage_matches(value: Any) -> bool:
    if isinstance(value, dict):
        sid = value.get("stage_id", value.get("id"))
        name = value.get("stage_name", value.get("name"))
        return sid in {10, "10"} or name in {STAGE_NAME, "10-qa-debugging"}
    if isinstance(value, int):
        return value == 10
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"10", STAGE_NAME, "10-qa-debugging", "stage-10", "stage_10"}
    return False


def completed_entry_for(existing: list[Any], payload: dict[str, Any]) -> Any:
    sample = next((item for item in existing if item is not None), None)
    if isinstance(sample, dict):
        return deepcopy(payload)
    if isinstance(sample, int):
        return 10
    return "10-qa-debugging"


def merge_completed_stages(state: dict[str, Any], payload: dict[str, Any]) -> None:
    existing = state.get("completed_stages")
    if existing is None:
        if payload["status"] == "PASS":
            state["completed_stages"] = ["10-qa-debugging"]
        return
    if not isinstance(existing, list):
        return

    kept = [item for item in existing if not stage_matches(item)]
    if payload["status"] == "PASS":
        kept.append(completed_entry_for(existing, payload))
    state["completed_stages"] = kept


def merge_stages_container(state: dict[str, Any], payload: dict[str, Any]) -> bool:
    stages = state.get("stages")
    if isinstance(stages, dict):
        key = next((k for k, v in stages.items() if stage_matches(v) or k in {"10", "stage_10", "10-qa-debugging"}), None)
        stages[key or "10"] = deepcopy(payload)
        return True
    if isinstance(stages, list):
        replaced = False
        result = []
        for item in stages:
            if stage_matches(item):
                if not replaced:
                    result.append(deepcopy(payload))
                    replaced = True
            else:
                result.append(item)
        if not replaced:
            result.append(deepcopy(payload))
        state["stages"] = result
        return True
    return False


def update_navigation(state: dict[str, Any], payload: dict[str, Any]) -> None:
    status = payload["status"]
    desired_next = NEXT_STAGE if status == "PASS" else None

    if "current_stage" in state:
        state["current_stage"] = 11 if status == "PASS" and isinstance(state["current_stage"], int) else (NEXT_STAGE if status == "PASS" else STAGE_NAME)
    if "next_stage" in state:
        state["next_stage"] = desired_next


def merge_state(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    payload = deepcopy(payload)
    payload.setdefault("completed_at", datetime.now(timezone.utc).isoformat())

    merge_completed_stages(result, payload)
    used_existing_container = merge_stages_container(result, payload)

    if not used_existing_container:
        result["stage_10"] = payload

    update_navigation(result, payload)
    return result


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default="project-state.json", help="Path to project-state.json")
    parser.add_argument("--stage-payload", required=True, help="Path to Stage 10 payload JSON")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a backup of an existing state file")
    args = parser.parse_args()

    state_path = Path(args.state)
    payload_path = Path(args.stage_payload)

    try:
        state = load_json(state_path, default={})
        if not isinstance(state, dict):
            raise ValueError("project-state.json must contain a JSON object")
        payload = load_json(payload_path)
        validate_payload(payload)

        if state_path.exists() and not args.no_backup:
            backup = state_path.with_name(state_path.name + ".stage10.bak")
            shutil.copy2(state_path, backup)
            print(f"Backup: {backup}")

        merged = merge_state(state, payload)
        atomic_write_json(state_path, merged)
        print(f"Updated: {state_path}")
        print(f"Stage 10 status: {payload['status']}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
