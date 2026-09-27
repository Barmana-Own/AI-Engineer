#!/usr/bin/env python3
"""Validate Stage 07 evidence and authorization-matrix structure.

The validator checks report completeness, not the truth of claimed test results.
Actual command/test execution remains mandatory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_IDS = [
    "AUTHN-01", "AUTHN-02", "SESS-01", "CSRF-01", "AUTHZ-01", "AUTHZ-02",
    "AUTHZ-03", "TENANT-01", "PRIV-01", "RECOV-01", "MFA-01", "FED-01",
    "ABUSE-01", "AUDIT-01", "FRONT-01", "STATIC-01", "REG-01",
]

MUST_NOT_BE_NA = {"AUTHN-01", "AUTHN-02", "SESS-01", "AUTHZ-01", "STATIC-01", "REG-01"}
VALID_STATUS = {"PASS", "FAIL", "BLOCKED", "N/A"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate Stage 07 evidence report structure")
    p.add_argument("evidence", help="Path to docs/security/07-auth-test-evidence.md")
    p.add_argument("--authorization-matrix", help="Optional path to docs/security/07-authorization-matrix.md")
    p.add_argument("--format", choices=("json", "text"), default="text")
    return p.parse_args()


def parse_markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = text.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    i = 0
    while i < len(lines) - 1:
        if "|" not in lines[i] or "|" not in lines[i + 1]:
            i += 1
            continue
        header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        sep = [c.strip() for c in lines[i + 1].strip().strip("|").split("|")]
        if len(header) < 2 or len(sep) != len(header) or not all(re.fullmatch(r":?-{3,}:?", c) for c in sep):
            i += 1
            continue
        rows: list[list[str]] = []
        j = i + 2
        while j < len(lines) and "|" in lines[j] and lines[j].strip():
            row = [c.strip() for c in lines[j].strip().strip("|").split("|")]
            if len(row) == len(header):
                rows.append(row)
            j += 1
        tables.append((header, rows))
        i = j
    return tables


def norm(value: str) -> str:
    return re.sub(r"[`*_]", "", value).strip()


def validate_evidence(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    tables = parse_markdown_tables(text)
    target = None
    for header, rows in tables:
        lowered = [norm(h).lower() for h in header]
        if "evidence id" in lowered and "status" in lowered:
            target = (header, rows)
            break
    if target is None:
        return ["Evidence table with 'Evidence ID' and 'Status' columns was not found."], {}

    header, rows = target
    index = {norm(name).lower(): i for i, name in enumerate(header)}
    id_col = index["evidence id"]
    status_col = index["status"]
    notes_col = index.get("notes")
    requirement_col = index.get("requirement")
    result_col = index.get("result")
    command_col = index.get("test/command")

    records: dict[str, dict[str, str]] = {}
    for row in rows:
        evidence_id = norm(row[id_col]).upper()
        status = norm(row[status_col]).upper()
        if evidence_id in REQUIRED_IDS:
            records[evidence_id] = {
                "status": status,
                "notes": row[notes_col].strip() if notes_col is not None else "",
                "requirement": row[requirement_col].strip() if requirement_col is not None else "",
                "result": row[result_col].strip() if result_col is not None else "",
                "command": row[command_col].strip() if command_col is not None else "",
            }

    for evidence_id in REQUIRED_IDS:
        if evidence_id not in records:
            errors.append(f"Missing required evidence class: {evidence_id}")
            continue
        record = records[evidence_id]
        status = record["status"]
        if status not in VALID_STATUS:
            errors.append(f"{evidence_id}: invalid status '{status}'")
            continue
        if status in {"FAIL", "BLOCKED"}:
            errors.append(f"{evidence_id}: status is {status}")
        if status == "N/A":
            if evidence_id in MUST_NOT_BE_NA:
                errors.append(f"{evidence_id}: N/A is not permitted for this core evidence class")
            if len(norm(record["notes"])) < 12 and len(norm(record["requirement"])) < 12:
                errors.append(f"{evidence_id}: N/A requires a concrete architectural reason")
        if status == "PASS":
            if not norm(record["result"]):
                errors.append(f"{evidence_id}: PASS row has no result summary")
            if evidence_id in {"AUTHN-01", "SESS-01", "AUTHZ-01", "AUTHZ-02", "AUTHZ-03", "PRIV-01", "STATIC-01", "REG-01"} and not norm(record["command"]):
                errors.append(f"{evidence_id}: PASS row should reference an executed test/command")

    return errors, records


def validate_matrix(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    tables = parse_markdown_tables(text)
    target = None
    for header, rows in tables:
        lowered = [norm(h).lower() for h in header]
        if any(v in lowered for v in ("action id", "route/service action")) and "positive test" in lowered and "negative test" in lowered:
            target = (header, rows)
            break
    if target is None:
        return ["Authorization matrix table with Positive test and Negative test columns was not found."]

    header, rows = target
    index = {norm(name).lower(): i for i, name in enumerate(header)}
    pos = index["positive test"]
    neg = index["negative test"]
    action = index.get("action id", index.get("route/service action", 0))
    enforcement = index.get("enforcement point")

    if not rows:
        errors.append("Authorization matrix contains no action rows.")
        return errors

    for n, row in enumerate(rows, start=1):
        label = norm(row[action]) or f"row {n}"
        if not norm(row[pos]):
            errors.append(f"Matrix {label}: missing positive test reference")
        if not norm(row[neg]):
            errors.append(f"Matrix {label}: missing negative test reference")
        if enforcement is not None and not norm(row[enforcement]):
            errors.append(f"Matrix {label}: missing enforcement point")
    return errors


def main() -> int:
    args = parse_args()
    evidence = Path(args.evidence)
    if not evidence.is_file():
        print(f"error: evidence file not found: {evidence}", file=sys.stderr)
        return 2

    errors, records = validate_evidence(evidence)
    if args.authorization_matrix:
        matrix = Path(args.authorization_matrix)
        if not matrix.is_file():
            errors.append(f"Authorization matrix file not found: {matrix}")
        else:
            errors.extend(validate_matrix(matrix))

    result = {
        "status": "PASS" if not errors else "FAIL",
        "evidence_classes": {key: value.get("status", "") for key, value in records.items()},
        "errors": errors,
        "note": "This validates report structure only. Claimed test results must still come from real executed verification.",
    }

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Stage 07 evidence structure: {result['status']}")
        if errors:
            for error in errors:
                print(f"- {error}")
        else:
            print("- All required evidence classes are structurally complete.")
        print("- This validator does not prove that claimed tests actually ran.")

    return 0 if not errors else 3


if __name__ == "__main__":
    raise SystemExit(main())
