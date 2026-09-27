#!/usr/bin/env python3
"""Validate the minimum Stage 10 QA artifact contract and PASS consistency."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


REPORT = Path("docs/10-qa-report.md")
MATRIX = Path("docs/10-qa-matrix.md")
KNOWN = Path("docs/10-known-issues.md")
STATE = Path("project-state.json")

REPORT_HEADINGS = [
    "Executive status",
    "Release candidate identity",
    "Environment and constraints",
    "Risk and coverage strategy",
    "Automated baseline",
    "QA matrix summary",
    "Core journey results",
    "Functional and exploratory findings",
    "Authorization and security regression",
    "API and data integrity",
    "UI, responsive, RTL, and accessibility",
    "Defect log",
    "Final suite verification",
    "Open known issues",
    "Quality gate evaluation",
    "Stage 11 handoff",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def has_heading(text: str, phrase: str) -> bool:
    pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(phrase) + r".*$", re.IGNORECASE | re.MULTILINE)
    return bool(pattern.search(text))


def parse_decision(report: str) -> str | None:
    match = re.search(r"Stage\s*10\s*decision\s*:\s*`?(PASS|BLOCKED)`?", report, re.IGNORECASE)
    return match.group(1).upper() if match else None


def parse_open_count(report: str, severity: str) -> int | None:
    match = re.search(rf"Open\s+{re.escape(severity)}\s*:\s*`?(\d+)`?", report, re.IGNORECASE)
    return int(match.group(1)) if match else None


def find_stage10(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        sid = obj.get("stage_id", obj.get("id"))
        name = obj.get("stage_name", obj.get("name"))
        if sid in {10, "10"} or name in {"qa-debugging", "10-qa-debugging"}:
            return obj
        if isinstance(obj.get("stage_10"), dict):
            return obj["stage_10"]
        for key in ("stages", "completed_stages"):
            if key in obj:
                found = find_stage10(obj[key])
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_stage10(item)
            if found:
                return found
    return None


def contains_any(text: str, needles: Iterable[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def release_critical_nonpass_rows(matrix: str) -> list[str]:
    bad = []
    for line in matrix.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        lower = line.lower()
        if "release-critical" not in lower:
            continue
        cells = [cell.strip().upper() for cell in line.strip().strip("|").split("|")]
        if any(cell in {"FAIL", "BLOCKED", "NOT_RUN"} for cell in cells):
            bad.append(line.strip())
    return bad


def gate_results(report: str) -> dict[str, str]:
    results: dict[str, str] = {}
    for line in report.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = re.match(r"([A-I])\s*-", cells[0], re.IGNORECASE)
        if match:
            results[match.group(1).upper()] = cells[1].upper().strip("`")
    return results


def unresolved_high_known_issue_rows(known: str) -> list[str]:
    hits = []
    for line in known.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().upper() for cell in line.strip().strip("|").split("|")]
        if any(cell in {"P0", "P1"} for cell in cells):
            hits.append(line.strip())
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root containing docs/ and project-state.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    errors: list[str] = []
    warnings: list[str] = []

    paths = {"report": root / REPORT, "matrix": root / MATRIX, "known": root / KNOWN, "state": root / STATE}
    for label, path in paths.items():
        if not path.exists():
            errors.append(f"Missing required {label} artifact: {path.relative_to(root)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 2

    report = read(paths["report"])
    matrix = read(paths["matrix"])
    known = read(paths["known"])

    for heading in REPORT_HEADINGS:
        if not has_heading(report, heading):
            errors.append(f"QA report missing heading containing: {heading}")

    decision = parse_decision(report)
    if decision is None:
        errors.append("QA report must declare 'Stage 10 decision: PASS' or 'BLOCKED'")

    for field in ("Requirement", "Role", "Criticality", "Status", "Evidence"):
        if field.lower() not in matrix.lower():
            errors.append(f"QA matrix does not appear to contain required field: {field}")

    if not contains_any(known, ["Unresolved issues", "No intentionally unresolved Stage 10 issues remain"]):
        errors.append("Known-issues artifact must list unresolved issues or explicitly state none remain")

    try:
        state = json.loads(read(paths["state"]))
    except json.JSONDecodeError as exc:
        errors.append(f"project-state.json is invalid JSON: {exc}")
        state = None

    state_stage = find_stage10(state) if state is not None else None
    if state_stage is None:
        errors.append("project-state.json does not contain a recognizable Stage 10 record")
    elif decision is not None:
        state_status = str(state_stage.get("status", "")).upper()
        if state_status and state_status != decision:
            errors.append(f"Stage 10 state status ({state_status}) disagrees with report decision ({decision})")

    if decision == "PASS":
        p0 = parse_open_count(report, "P0")
        p1 = parse_open_count(report, "P1")
        if p0 is None or p1 is None:
            errors.append("PASS report must declare numeric Open P0 and Open P1 counts")
        else:
            if p0 != 0:
                errors.append(f"PASS is invalid with Open P0 = {p0}")
            if p1 != 0:
                errors.append(f"PASS is invalid with Open P1 = {p1}")

        bad_rows = release_critical_nonpass_rows(matrix)
        if bad_rows:
            errors.append(f"PASS is invalid with {len(bad_rows)} release-critical FAIL/BLOCKED/NOT_RUN matrix row(s)")

        high_known = unresolved_high_known_issue_rows(known)
        if high_known:
            errors.append(f"PASS is invalid while known-issues contains {len(high_known)} P0/P1 row(s)")

        gates = gate_results(report)
        for gate in "ABCDFGHI":
            if gates.get(gate) != "PASS":
                errors.append(f"PASS report requires Quality Gate {gate} = PASS")
        if gates.get("E") not in {"PASS", "N/A"}:
            errors.append("PASS report requires Quality Gate E = PASS or N/A")

        if state_stage is not None:
            state_status = str(state_stage.get("status", "")).upper()
            if state_status != "PASS":
                errors.append("PASS report requires Stage 10 project state status = PASS")
            next_stage = state_stage.get("next_stage")
            if next_stage not in {"11-deployment-production", 11, "11"}:
                errors.append("PASS Stage 10 state must point to 11-deployment-production")
            artifacts = state_stage.get("artifacts")
            if isinstance(artifacts, list):
                required_artifacts = {str(REPORT), str(MATRIX), str(KNOWN)}
                missing = sorted(required_artifacts - {str(item) for item in artifacts})
                if missing:
                    errors.append("Stage 10 project state missing artifact path(s): " + ", ".join(missing))
            else:
                errors.append("PASS Stage 10 state must include an artifacts list")

    if decision == "BLOCKED" and state_stage is not None:
        blockers = state_stage.get("blockers")
        if isinstance(blockers, list) and not blockers:
            warnings.append("BLOCKED Stage 10 state has an empty blockers list")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 2

    print(f"Stage 10 artifact validation passed with {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
