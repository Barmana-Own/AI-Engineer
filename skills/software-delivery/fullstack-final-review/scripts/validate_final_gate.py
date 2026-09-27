#!/usr/bin/env python3
"""Compute a deterministic Stage 12 verdict from review state and audit artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALL_GATES = [f"G{i:02d}" for i in range(20)]
NONBLOCKING_NOT_RUN_DEFAULT = {"G03", "G04", "G05", "G10", "G15"}
BAD_CORE_STATUSES = {"IMPLEMENTED_UNVERIFIED", "PARTIAL", "MISSING", "BROKEN", "UNKNOWN"}
CLOSED_FINDING_STATUSES = {"CLOSED", "FALSE_POSITIVE"}


def load_json(path: Path, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(str(path))
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--phase", choices=["prepackage", "final"], default="final")
    ap.add_argument("--output")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    audit = root / ".final-review"
    state_path = audit / "review-state.json"
    trace_path = audit / "traceability.json"
    hygiene_path = audit / "hygiene-report.json"
    output = Path(args.output).resolve() if args.output else audit / "final-verdict.json"

    blockers: list[str] = []
    warnings: list[str] = []

    try:
        state = load_json(state_path)
    except Exception as exc:
        state = {}
        blockers.append(f"Review state unavailable/invalid: {exc}")
    try:
        trace = load_json(trace_path)
    except Exception as exc:
        trace = {}
        blockers.append(f"Traceability unavailable/invalid: {exc}")
    try:
        hygiene = load_json(hygiene_path)
    except Exception as exc:
        hygiene = {}
        blockers.append(f"Hygiene report unavailable/invalid: {exc}")

    required_gates = ALL_GATES[:-1] if args.phase == "prepackage" else ALL_GATES
    gates = state.get("gates", {}) if isinstance(state, dict) else {}
    for gid in required_gates:
        gate = gates.get(gid)
        if not isinstance(gate, dict):
            blockers.append(f"{gid}: missing gate record")
            continue
        status = gate.get("status")
        evidence = gate.get("evidence") or []
        reason = gate.get("reason")
        if status == "PASS":
            if not evidence:
                blockers.append(f"{gid}: PASS without evidence")
        elif status == "NOT_RUN":
            if not str(reason or "").strip():
                blockers.append(f"{gid}: NOT_RUN without a precise reason")
            elif gid not in NONBLOCKING_NOT_RUN_DEFAULT:
                blockers.append(f"{gid}: essential gate is NOT_RUN ({reason})")
            else:
                warnings.append(f"{gid}: NOT_RUN allowed only as documented non-blocking limitation ({reason})")
        elif status in {"PENDING", "STALE", "FAIL", None}:
            blockers.append(f"{gid}: status={status or 'MISSING'} ({reason or 'no reason'})")
        else:
            blockers.append(f"{gid}: invalid status {status}")

    findings = state.get("findings", []) if isinstance(state, dict) else []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        status = finding.get("status")
        blocking = bool(finding.get("blocking"))
        severity = finding.get("severity")
        priority = finding.get("priority")
        if status == "ACCEPTED_NONBLOCKING" and blocking:
            blockers.append(f"{finding.get('id')}: inconsistent accepted status for blocking finding")
        if blocking and status not in CLOSED_FINDING_STATUSES:
            blockers.append(f"{finding.get('id')}: open blocking finding ({severity}/{priority}, status={status})")
        category = str(finding.get("category", "")).lower()
        if severity in {"Critical", "High"} and any(tag in category for tag in ("security", "auth", "authorization", "authentication")) and status not in CLOSED_FINDING_STATUSES:
            blockers.append(f"{finding.get('id')}: open {severity} security/auth finding")
        if priority in {"P0", "P1"} and status not in CLOSED_FINDING_STATUSES and status != "ACCEPTED_NONBLOCKING":
            blockers.append(f"{finding.get('id')}: open {priority} finding")

    requirements = trace.get("requirements", []) if isinstance(trace, dict) else []
    if not isinstance(requirements, list) or not requirements:
        blockers.append("Traceability contains no requirements")
    else:
        for req in requirements:
            if not isinstance(req, dict) or not req.get("core"):
                continue
            rid = req.get("id", "<unknown>")
            status = req.get("status", "UNKNOWN")
            if status in BAD_CORE_STATUSES:
                blockers.append(f"{rid}: core requirement status={status}")
            elif status == "VERIFIED":
                implementations = req.get("implementation") or []
                if not implementations:
                    blockers.append(f"{rid}: VERIFIED without implementation mapping")
                else:
                    existing = []
                    for item in implementations:
                        if not isinstance(item, str):
                            continue
                        candidate = item.split("#", 1)[0].split("::", 1)[0].strip()
                        if candidate and not candidate.startswith(("http://", "https://", "/")) and (root / candidate).exists():
                            existing.append(candidate)
                    if not existing:
                        blockers.append(f"{rid}: no mapped repository-relative implementation path exists")
                if not (req.get("evidence") or req.get("tests")):
                    blockers.append(f"{rid}: VERIFIED without test/evidence mapping")
            elif status in {"EXCLUDED_APPROVED", "NOT_APPLICABLE"}:
                if not str(req.get("notes", "")).strip():
                    blockers.append(f"{rid}: {status} without rationale/approved evidence note")
            else:
                blockers.append(f"{rid}: unsupported core requirement status={status}")

    summary = hygiene.get("summary", {}) if isinstance(hygiene, dict) else {}
    if summary.get("blocking_active", 0):
        blockers.append(f"Release hygiene has {summary.get('blocking_active')} active blocking finding(s)")
    if summary.get("review_required_active", 0):
        blockers.append(f"Release hygiene has {summary.get('review_required_active')} unresolved review-required candidate(s)")

    external = state.get("external_blockers", []) if isinstance(state, dict) else []
    if external:
        blockers.append(f"Unresolved external blockers: {len(external)}")

    verdict = "PASS" if not blockers else "FAIL"
    result = {
        "schema_version": 1,
        "phase": args.phase,
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blockers": blockers,
        "warnings": warnings,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Stage 12 {args.phase} verdict: {verdict}")
    if blockers:
        for item in blockers:
            print(f"BLOCKER: {item}")
    for item in warnings:
        print(f"WARNING: {item}")
    print(f"Verdict file: {output}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
