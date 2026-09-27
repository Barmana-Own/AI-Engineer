#!/usr/bin/env python3
"""Validate the Stage 11 evidence ledger and PASS eligibility."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_GATES = [
    "G00_PRECONDITIONS",
    "G01_RELEASE_BASELINE",
    "G02_DETERMINISTIC_BUILD",
    "G03_RUNTIME_PACKAGING",
    "G04_CONFIG_AND_SECRETS",
    "G05_DATABASE_AND_DATA",
    "G06_EDGE_AND_NETWORK",
    "G07_CI_CD_AND_PROMOTION",
    "G08_SUPPLY_CHAIN_SECURITY",
    "G09_OBSERVABILITY",
    "G10_BACKUP_RESTORE",
    "G11_RELEASE_STRATEGY",
    "G12_PRODUCTION_LIKE_VALIDATION",
    "G13_DEPLOYMENT_TRUTH",
    "G14_EVIDENCE_AND_HANDOFF",
]
ALLOWED = {"PASS", "FAIL", "N_A", "BLOCKED"}
SEVERITIES = {"P0", "P1", "P2", "P3"}
RESOLVED_FINDING_STATES = {"RESOLVED", "CLOSED", "FIXED", "ACCEPTED"}


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(data: Any, require_pass: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root must be a JSON object"]

    if data.get("stage") != "11-deployment-production":
        errors.append("stage must equal '11-deployment-production'")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")

    deployment = data.get("deployment")
    if not isinstance(deployment, dict):
        errors.append("deployment must be an object")
    else:
        dep_status = deployment.get("status")
        if dep_status not in {"PERFORMED", "NOT_PERFORMED"}:
            errors.append("deployment.status must be PERFORMED or NOT_PERFORMED")
        if dep_status == "PERFORMED" and not nonempty_string(deployment.get("target")):
            errors.append("deployment.target is required when deployment.status is PERFORMED")

    gates = data.get("gates")
    if not isinstance(gates, list):
        return errors + ["gates must be a list"]

    by_id: dict[str, dict[str, Any]] = {}
    for idx, gate in enumerate(gates):
        if not isinstance(gate, dict):
            errors.append(f"gates[{idx}] must be an object")
            continue
        gate_id = gate.get("id")
        if not nonempty_string(gate_id):
            errors.append(f"gates[{idx}].id must be a non-empty string")
            continue
        if gate_id in by_id:
            errors.append(f"duplicate gate id: {gate_id}")
            continue
        by_id[gate_id] = gate

        status = gate.get("status")
        if status not in ALLOWED:
            errors.append(f"{gate_id}: invalid status {status!r}")
        if not nonempty_string(gate.get("summary")):
            errors.append(f"{gate_id}: summary is required")
        evidence = gate.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append(f"{gate_id}: evidence must be a list")
        if status == "PASS" and (not isinstance(evidence, list) or len(evidence) == 0):
            errors.append(f"{gate_id}: PASS requires at least one evidence item")
        if status == "N_A" and not nonempty_string(gate.get("rationale")):
            errors.append(f"{gate_id}: N_A requires non-empty rationale")

        findings = gate.get("findings", [])
        if findings is not None and not isinstance(findings, list):
            errors.append(f"{gate_id}: findings must be a list when present")
        elif isinstance(findings, list):
            for fidx, finding in enumerate(findings):
                if not isinstance(finding, dict):
                    errors.append(f"{gate_id}.findings[{fidx}] must be an object")
                    continue
                sev = finding.get("severity")
                if sev is not None and sev not in SEVERITIES:
                    errors.append(f"{gate_id}.findings[{fidx}]: invalid severity {sev!r}")
                if require_pass and sev in {"P0", "P1"}:
                    fstatus = str(finding.get("status", "")).upper()
                    if fstatus not in RESOLVED_FINDING_STATES:
                        errors.append(f"{gate_id}.findings[{fidx}]: unresolved {sev} finding prevents PASS")

    missing = [g for g in REQUIRED_GATES if g not in by_id]
    extra = [g for g in by_id if g not in REQUIRED_GATES]
    if missing:
        errors.append("missing required gates: " + ", ".join(missing))
    if extra:
        errors.append("unknown gate ids: " + ", ".join(extra))

    if require_pass:
        for gate_id in REQUIRED_GATES:
            gate = by_id.get(gate_id)
            if not gate:
                continue
            if gate.get("status") not in {"PASS", "N_A"}:
                errors.append(f"{gate_id}: status {gate.get('status')!r} is incompatible with Stage 11 PASS")
        g13 = by_id.get("G13_DEPLOYMENT_TRUTH")
        if g13 and g13.get("status") != "PASS":
            errors.append("G13_DEPLOYMENT_TRUTH must be PASS; deployment may be NOT_PERFORMED, but truthfulness cannot be N_A")
        blockers = data.get("blockers", [])
        if blockers not in (None, []) and isinstance(blockers, list) and blockers:
            errors.append("top-level blockers must be empty for Stage 11 PASS")

    return errors


def main() -> int:
    p = argparse.ArgumentParser(description="Validate Stage 11 evidence ledger")
    p.add_argument("evidence", help="Path to evidence.json")
    p.add_argument("--require-pass", action="store_true", help="Enforce Stage 11 PASS eligibility")
    args = p.parse_args()

    try:
        data = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"INVALID: cannot read evidence JSON: {exc}", file=sys.stderr)
        return 2

    errors = validate(data, args.require_pass)
    if errors:
        print("INVALID")
        for err in errors:
            print(f"- {err}")
        return 1
    print("VALID")
    if args.require_pass:
        print("Stage 11 evidence is structurally eligible for PASS; engineering truth still depends on the referenced evidence being real and correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
