#!/usr/bin/env python3
"""Validate Stage 04/05 status signals in project-state.json without mutating it."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

STAGE04_KEYS = {"04-backend-architecture", "04-backend-domain", "04", "stage-04"}
STAGE05_KEYS = {"05-database-architecture", "05", "stage-05"}


def walk(obj: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield path, obj
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(value, path + (str(key),))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, path + (str(idx),))


def find_stage_status(data: Any, keys: set[str]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path, value in walk(data):
        if not path:
            continue
        key = path[-1].lower()
        if key in keys and isinstance(value, dict):
            status = value.get("status")
            if isinstance(status, str):
                found.append((".".join(path), status.upper()))
        if isinstance(value, dict):
            stage_id = value.get("stage_id") or value.get("id") or value.get("stage")
            if isinstance(stage_id, str) and stage_id.lower() in keys:
                status = value.get("status")
                if isinstance(status, str):
                    found.append((".".join(path), status.upper()))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root containing project-state.json")
    parser.add_argument("--mode", choices=("preflight", "final"), default="preflight")
    args = parser.parse_args()

    path = Path(args.root).resolve() / "project-state.json"
    if not path.exists():
        print(f"WARN: {path} does not exist; authoritative Stage 04 evidence must be verified elsewhere.")
        return 2

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot parse {path}: {exc}")
        return 1

    stage04 = find_stage_status(data, STAGE04_KEYS)
    if not stage04:
        print("ERROR: no recognizable Stage 04 status found.")
        return 1
    if not any(status == "PASS" for _, status in stage04):
        print("ERROR: Stage 04 is not PASS:", stage04)
        return 1
    print("PASS: Stage 04 PASS signal found:", stage04)

    if args.mode == "final":
        stage05 = find_stage_status(data, STAGE05_KEYS)
        if not stage05:
            print("ERROR: no recognizable Stage 05 status found.")
            return 1
        if not any(status == "PASS" for _, status in stage05):
            print("ERROR: Stage 05 is not PASS:", stage05)
            return 1
        print("PASS: Stage 05 PASS signal found:", stage05)

    return 0


if __name__ == "__main__":
    sys.exit(main())
