#!/usr/bin/env python3
"""Update Stage 01 workflow status while preserving unknown project-state keys."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

STAGE = "01-project-analysis-prompt-engineering"
NEXT_STAGE = "02-design-system-ui-architecture"
REQUIRED_ARTIFACTS = [
    "docs/01-source-map.md",
    "docs/01-project-brief.md",
    "docs/01-requirements.md",
    "docs/01-domain-integration-map.md",
    "docs/01-risk-register.md",
    "docs/01-traceability-matrix.md",
    "docs/01-readiness-review.md",
    "docs/01-stage-02-handoff.md",
]
OPTIONAL_ARTIFACTS = [
    "docs/01-research-evidence.md",
    "docs/01-stage01-validation.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validation_report_is_fresh(root: Path, hashes: object) -> bool:
    if not isinstance(hashes, dict) or not hashes:
        return False
    expected_paths = list(REQUIRED_ARTIFACTS) + ["project-state.json"]
    if (root / "docs/01-research-evidence.md").exists():
        expected_paths.append("docs/01-research-evidence.md")
    if set(hashes.keys()) != set(expected_paths):
        return False
    for rel in expected_paths:
        path = root / rel
        if not path.exists() or not path.is_file():
            return False
        if hashes.get(rel) != sha256_file(path):
            return False
    return True


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("project-state.json must contain a JSON object")
    return value


def dedupe_completed(items: list, include_stage: bool) -> list:
    result = []
    for item in items:
        item_stage = item.get("stage") if isinstance(item, dict) else item
        if item_stage == STAGE:
            continue
        result.append(item)
    if include_stage:
        result.append({"stage": STAGE, "status": "PASS", "completed_at": now_iso()})
    return result


def extract_int(text: str, label: str) -> int | None:
    match = re.search(rf"^-\s*{re.escape(label)}:\s*(\d+)(?:/100)?\s*$", text, re.MULTILINE | re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_readiness(root: Path) -> dict:
    path = root / "docs/01-readiness-review.md"
    if not path.exists():
        return {
            "score": None,
            "recommended_status": None,
            "open_critical_findings": None,
            "open_high_findings": None,
            "blocking_questions": None,
        }
    text = path.read_text(encoding="utf-8")
    rec = re.search(r"^-\s*Recommended status:\s*(PASS|REPAIR_REQUIRED|BLOCKED)\s*$", text, re.MULTILINE | re.IGNORECASE)
    score = extract_int(text, "Quality score")
    if score is None:
        total_row = re.search(r"\|\s*\*\*TOTAL\*\*\s*\|\s*\*\*100\*\*\s*\|\s*\*\*(\d+)\*\*", text)
        if total_row:
            score = int(total_row.group(1))
    return {
        "score": score,
        "recommended_status": rec.group(1).upper() if rec else None,
        "open_critical_findings": extract_int(text, "Open CRITICAL findings"),
        "open_high_findings": extract_int(text, "Open HIGH findings"),
        "blocking_questions": extract_int(text, "Blocking questions"),
    }


def parse_validator(root: Path) -> dict:
    path = root / "docs/01-stage01-validation.json"
    if not path.exists():
        return {"passed": False, "score": None, "strict_pass": False, "fresh": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"passed": False, "score": None, "strict_pass": False, "fresh": False}
    return {
        "passed": data.get("passed") is True,
        "score": data.get("score"),
        "strict_pass": data.get("strict_pass") is True,
        "fresh": validation_report_is_fresh(root, data.get("input_hashes")),
    }


def verify_pass_preconditions(root: Path) -> tuple[dict, dict]:
    missing = [p for p in REQUIRED_ARTIFACTS if not (root / p).exists()]
    if missing:
        raise ValueError("Cannot set PASS; missing required artifacts: " + ", ".join(missing))

    readiness = parse_readiness(root)
    validator = parse_validator(root)
    failures = []
    if readiness["recommended_status"] != "PASS":
        failures.append("readiness recommendation must be PASS")
    if readiness["score"] is None or readiness["score"] < 95:
        failures.append("readiness quality score must be >= 95")
    if readiness["open_critical_findings"] != 0:
        failures.append("open CRITICAL findings must be 0")
    if readiness["open_high_findings"] != 0:
        failures.append("open HIGH findings must be 0")
    if readiness["blocking_questions"] != 0:
        failures.append("blocking questions must be 0")
    if not validator["passed"]:
        failures.append("latest machine validation report must have passed=true")
    if not validator.get("fresh"):
        failures.append("machine validation report is stale or does not match current Stage 01 inputs")
    if failures:
        raise ValueError("Cannot set PASS; " + "; ".join(failures))
    return readiness, validator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    parser.add_argument("--status", required=True, choices=["IN_PROGRESS", "PASS", "BLOCKED"])
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    path = root / "project-state.json"
    state = load(path)
    state.setdefault("schema_version", "1.0")
    state.setdefault("project", {"name": root.name, "summary": "Stage 01 project analysis"})
    for key in ["sources", "decisions", "assumptions", "risks", "open_questions", "conflicts", "evidence", "review_findings"]:
        state.setdefault(key, [])

    workflow = state.setdefault("workflow", {})
    records = workflow.setdefault("stage_records", {})
    completed = workflow.setdefault("completed_stages", [])
    if not isinstance(completed, list):
        raise ValueError("workflow.completed_stages must be an array")

    readiness = parse_readiness(root)
    validator = parse_validator(root)
    if args.status == "PASS":
        readiness, validator = verify_pass_preconditions(root)

    artifacts = [p for p in REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS if (root / p).exists()]
    existing_record = records.get(STAGE, {}) if isinstance(records.get(STAGE), dict) else {}
    quality = existing_record.get("quality", {}) if isinstance(existing_record.get("quality"), dict) else {}
    quality.update({
        "score": readiness.get("score"),
        "hard_gates_passed": readiness.get("recommended_status") == "PASS",
        "open_critical_findings": readiness.get("open_critical_findings"),
        "open_high_findings": readiness.get("open_high_findings"),
        "blocking_questions": readiness.get("blocking_questions"),
        "validator_passed": validator.get("passed") is True and validator.get("fresh") is True,
        "review_artifact": "docs/01-readiness-review.md" if (root / "docs/01-readiness-review.md").exists() else None,
        "validation_artifact": "docs/01-stage01-validation.json" if (root / "docs/01-stage01-validation.json").exists() else None,
    })

    records[STAGE] = {
        **existing_record,
        "status": args.status,
        "artifacts": artifacts,
        "quality": quality,
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

    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": args.status, "state": str(path), "quality": quality}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
