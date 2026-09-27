#!/usr/bin/env python3
"""Validate Stage 08 report, findings ledger, and project-state consistency."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VALID_GATE = {"PASS", "FAIL", "BLOCKED"}
HIGH_SEVERITY = {"Critical", "High"}
MATERIAL_SEVERITY = {"Critical", "High", "Medium"}
CLOSED = {"FIXED", "FALSE_POSITIVE"}
REQUIRED_FINDING_KEYS = {
    "id", "title", "severity", "confidence", "status", "component", "location",
    "actors", "exposure", "security_invariant", "evidence", "impact", "root_cause",
    "remediation", "regression_test", "retest", "standards", "notes",
}
REQUIRED_REPORT_HEADINGS = [
    "## 1. Executive summary",
    "## 2. Authorization and scope",
    "## 3. Repository baseline",
    "## 4. Architecture and attack surface",
    "## 5. Threat model and priority abuse cases",
    "## 6. Coverage matrix",
    "## 7. Findings summary",
    "## 17. Verification results",
    "## 18. Residual risks and limitations",
    "## 19. Stage 09 handoff",
    "## 21. Final decision",
]


def stage_status_from_state(data: dict) -> str | None:
    current = data.get("completed_stages")
    if isinstance(current, list):
        for item in current:
            if isinstance(item, dict) and item.get("id") == "08-application-security":
                value = item.get("status")
                return value if isinstance(value, str) else None
    elif isinstance(current, dict):
        item = current.get("08-application-security")
        if isinstance(item, dict):
            value = item.get("status")
            return value if isinstance(value, str) else None
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Validate Stage 08 security artifacts")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--report", default="docs/08-security-review.md")
    p.add_argument("--ledger", default="docs/security/08-security-findings.json")
    p.add_argument("--state", default="project-state.json")
    p.add_argument("--expected-status", choices=sorted(VALID_GATE))
    args = p.parse_args()

    root = Path(args.root).expanduser().resolve()
    report_path = root / args.report
    ledger_path = root / args.ledger
    state_path = root / args.state
    errors: list[str] = []
    warnings: list[str] = []

    if not report_path.is_file():
        errors.append(f"missing report: {args.report}")
        report_text = ""
    else:
        report_text = report_path.read_text(encoding="utf-8", errors="replace")
        for heading in REQUIRED_REPORT_HEADINGS:
            if heading not in report_text:
                errors.append(f"report missing heading: {heading}")

    ledger = None
    if not ledger_path.is_file():
        errors.append(f"missing findings ledger: {args.ledger}")
    else:
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid findings JSON: {exc}")

    gate = None
    findings = []
    if isinstance(ledger, dict):
        if ledger.get("stage") != "08-application-security":
            errors.append("ledger.stage must be '08-application-security'")
        gate = ledger.get("gate_status")
        if gate not in VALID_GATE:
            errors.append("ledger.gate_status must be PASS, FAIL, or BLOCKED")
        findings = ledger.get("findings")
        if not isinstance(findings, list):
            errors.append("ledger.findings must be a list")
            findings = []
        ids = set()
        for idx, finding in enumerate(findings):
            label = f"finding[{idx}]"
            if not isinstance(finding, dict):
                errors.append(f"{label} must be an object")
                continue
            missing = sorted(REQUIRED_FINDING_KEYS - set(finding))
            if missing:
                errors.append(f"{label} missing keys: {', '.join(missing)}")
            fid = finding.get("id")
            if not isinstance(fid, str) or not re.fullmatch(r"SEC-\d{3,}", fid):
                errors.append(f"{label} has invalid id: {fid!r}")
            elif fid in ids:
                errors.append(f"duplicate finding id: {fid}")
            else:
                ids.add(fid)
            if finding.get("severity") not in {"Critical", "High", "Medium", "Low", "Info"}:
                errors.append(f"{fid or label} has invalid severity")
            if finding.get("confidence") not in {"CONFIRMED", "STRONG", "SUSPECTED", "FALSE_POSITIVE"}:
                errors.append(f"{fid or label} has invalid confidence")
            if finding.get("status") not in {"OPEN", "IN_REMEDIATION", "FIXED", "RESIDUAL_RISK", "BLOCKED", "FALSE_POSITIVE"}:
                errors.append(f"{fid or label} has invalid status")

    effective = args.expected_status or gate
    if args.expected_status and gate and args.expected_status != gate:
        errors.append(f"expected status {args.expected_status} but ledger says {gate}")

    if effective == "PASS":
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            sev = finding.get("severity")
            status = finding.get("status")
            confidence = finding.get("confidence")
            fid = finding.get("id", "unknown")
            if sev in HIGH_SEVERITY and status not in CLOSED:
                errors.append(f"PASS invalid: {fid} is {sev} with status={status}")
            if sev in HIGH_SEVERITY and status == "FIXED" and confidence in {"CONFIRMED", "STRONG"}:
                retest = str(finding.get("retest", "")).strip().upper()
                if not retest.startswith("PASS"):
                    errors.append(f"PASS invalid: {fid} lacks successful retest evidence")
            if sev == "Medium" and status == "FIXED" and confidence in {"CONFIRMED", "STRONG"}:
                retest = str(finding.get("retest", "")).strip().upper()
                if not retest.startswith("PASS"):
                    errors.append(f"PASS invalid: fixed Medium {fid} lacks successful retest evidence")
            if sev in HIGH_SEVERITY and confidence == "SUSPECTED" and status not in {"FALSE_POSITIVE", "FIXED"}:
                errors.append(f"PASS invalid: high-severity candidate {fid} remains unresolved")

    marker_match = re.search(r"STAGE_08_STATUS:\s*(PASS|FAIL|BLOCKED)", report_text)
    if marker_match:
        report_status = marker_match.group(1)
        if effective and report_status != effective:
            errors.append(f"report marker {report_status} disagrees with expected/ledger status {effective}")
    elif report_text:
        errors.append("report missing STAGE_08_STATUS marker")

    if not state_path.is_file():
        errors.append(f"missing project state: {args.state}")
    else:
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                errors.append("project-state root must be an object")
            else:
                state_status = stage_status_from_state(state)
                if state_status is None:
                    errors.append("project-state missing 08-application-security entry")
                elif effective and state_status != effective:
                    errors.append(f"project-state status {state_status} disagrees with {effective}")
        except Exception as exc:
            errors.append(f"invalid project-state JSON: {exc}")

    print(f"Stage 08 artifact validation for: {root}")
    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"RESULT: FAIL ({len(errors)} error(s))")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
