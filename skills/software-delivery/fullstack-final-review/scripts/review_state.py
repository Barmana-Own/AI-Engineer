#!/usr/bin/env python3
"""Maintain deterministic Stage 12 gate/finding/repair state."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GATES = {
    "G00": "Stage 11 precondition", "G01": "Repository integrity", "G02": "Requirement traceability",
    "G03": "Architecture/topology coherence", "G04": "Frontend critical journeys",
    "G05": "Backend/business rules", "G06": "API contract/integration", "G07": "Data model/migrations",
    "G08": "Authentication/authorization", "G09": "Security review", "G10": "Dependencies/supply chain",
    "G11": "Static quality", "G12": "Automated tests", "G13": "Clean setup/migrations",
    "G14": "Production build", "G15": "Runtime/health/smoke", "G16": "Operations/observability",
    "G17": "Documentation", "G18": "Release hygiene", "G19": "Manifest/package integrity"
}
STATUSES = {"PENDING", "PASS", "FAIL", "NOT_RUN", "STALE"}
FINDING_STATUSES = {"OPEN", "REPAIRED_PENDING_VERIFY", "CLOSED", "ACCEPTED_NONBLOCKING", "FALSE_POSITIVE"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def initial_state(root: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_root": str(root),
        "environment": {"classification": "unknown"},
        "gates": {gid: {"name": name, "status": "PENDING", "reason": None, "evidence": [], "updated_at": now()}
                  for gid, name in GATES.items()},
        "findings": [], "repairs": [], "assumptions": [], "external_blockers": [], "history": []
    }


def load_or_init(path: Path, root: Path) -> dict[str, Any]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        for gid, name in GATES.items():
            data.setdefault("gates", {}).setdefault(gid, {"name": name, "status": "PENDING", "reason": None, "evidence": [], "updated_at": now()})
        return data
    return initial_state(root)


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def append_history(state: dict[str, Any], action: str, detail: dict[str, Any]) -> None:
    state.setdefault("history", []).append({"at": now(), "action": action, "detail": detail})


def find_by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    return next((x for x in items if x.get("id") == item_id), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--state")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p = sub.add_parser("set-env")
    p.add_argument("--classification", required=True, choices=["local", "test", "ephemeral", "staging", "production-adjacent", "production", "unknown"])

    p = sub.add_parser("set-gate")
    p.add_argument("--id", required=True, choices=sorted(GATES))
    p.add_argument("--status", required=True, choices=sorted(STATUSES))
    p.add_argument("--reason", default="")
    p.add_argument("--evidence", action="append", default=[])

    p = sub.add_parser("invalidate")
    p.add_argument("--ids", required=True, help="Comma-separated gate IDs")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("finding-add")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--severity", required=True, choices=["Critical", "High", "Medium", "Low", "Info"])
    p.add_argument("--priority", required=True, choices=["P0", "P1", "P2", "P3"])
    p.add_argument("--confidence", default="CONFIRMED", choices=["CONFIRMED", "HIGH", "MEDIUM", "LOW"])
    p.add_argument("--blocking", required=True, choices=["true", "false"])
    p.add_argument("--owner-stage", default="")
    p.add_argument("--requirement", default="")
    p.add_argument("--summary", required=True)
    p.add_argument("--evidence", action="append", default=[])

    p = sub.add_parser("finding-status")
    p.add_argument("--id", required=True)
    p.add_argument("--status", required=True, choices=sorted(FINDING_STATUSES))
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--note", default="")

    p = sub.add_parser("repair-add")
    p.add_argument("--id", required=True)
    p.add_argument("--finding", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--files", default="")
    p.add_argument("--invalidates", default="")
    p.add_argument("--evidence", action="append", default=[])

    p = sub.add_parser("assume")
    p.add_argument("--text", required=True)

    p = sub.add_parser("blocker-add")
    p.add_argument("--text", required=True)
    p.add_argument("--owner-stage", default="")

    sub.add_parser("summary")

    args = ap.parse_args()
    root = Path(args.root).resolve()
    state_path = Path(args.state).resolve() if args.state else root / ".final-review" / "review-state.json"
    state = load_or_init(state_path, root)

    if args.cmd == "init":
        append_history(state, "init", {})
    elif args.cmd == "set-env":
        state["environment"] = {"classification": args.classification, "updated_at": now()}
        append_history(state, "set-env", {"classification": args.classification})
    elif args.cmd == "set-gate":
        if args.status == "PASS" and not args.evidence:
            raise SystemExit("PASS requires at least one --evidence entry")
        if args.status in {"FAIL", "NOT_RUN", "STALE"} and not args.reason.strip():
            raise SystemExit(f"{args.status} requires --reason")
        gate = state["gates"][args.id]
        gate.update({"status": args.status, "reason": args.reason or None, "evidence": list(args.evidence), "updated_at": now()})
        append_history(state, "set-gate", {"id": args.id, "status": args.status, "reason": args.reason})
    elif args.cmd == "invalidate":
        ids = split_csv(args.ids)
        bad = [gid for gid in ids if gid not in GATES]
        if bad:
            raise SystemExit(f"Unknown gate IDs: {', '.join(bad)}")
        for gid in ids:
            state["gates"][gid].update({"status": "STALE", "reason": args.reason, "evidence": [], "updated_at": now()})
        append_history(state, "invalidate", {"ids": ids, "reason": args.reason})
    elif args.cmd == "finding-add":
        if find_by_id(state["findings"], args.id):
            raise SystemExit(f"Finding already exists: {args.id}")
        finding = {
            "id": args.id, "title": args.title, "category": args.category, "severity": args.severity,
            "priority": args.priority, "confidence": args.confidence, "blocking": args.blocking == "true",
            "owner_stage": args.owner_stage or None, "requirement": args.requirement or None,
            "summary": args.summary, "evidence": list(args.evidence), "status": "OPEN",
            "created_at": now(), "updated_at": now()
        }
        state["findings"].append(finding)
        append_history(state, "finding-add", {"id": args.id})
    elif args.cmd == "finding-status":
        finding = find_by_id(state["findings"], args.id)
        if not finding:
            raise SystemExit(f"Finding not found: {args.id}")
        if args.status == "CLOSED" and not args.evidence:
            raise SystemExit("CLOSED requires verification --evidence")
        if args.status == "FALSE_POSITIVE" and not (args.note.strip() and args.evidence):
            raise SystemExit("FALSE_POSITIVE requires --note and verification --evidence")
        if args.status == "ACCEPTED_NONBLOCKING":
            if finding.get("blocking"):
                raise SystemExit("Cannot accept a finding as non-blocking while blocking=true; reclassify based on evidence first")
            if not args.note.strip():
                raise SystemExit("ACCEPTED_NONBLOCKING requires --note")
        finding["status"] = args.status
        finding.setdefault("verification_evidence", []).extend(args.evidence)
        if args.note:
            finding["status_note"] = args.note
        finding["updated_at"] = now()
        append_history(state, "finding-status", {"id": args.id, "status": args.status})
    elif args.cmd == "repair-add":
        if find_by_id(state["repairs"], args.id):
            raise SystemExit(f"Repair already exists: {args.id}")
        if not find_by_id(state["findings"], args.finding):
            raise SystemExit(f"Finding not found: {args.finding}")
        invalidates = split_csv(args.invalidates)
        if not invalidates:
            raise SystemExit("A recorded repair must invalidate at least one affected gate")
        bad = [gid for gid in invalidates if gid not in GATES]
        if bad:
            raise SystemExit(f"Unknown gate IDs: {', '.join(bad)}")
        repair = {"id": args.id, "finding": args.finding, "summary": args.summary,
                  "files": split_csv(args.files), "invalidates": invalidates,
                  "evidence": list(args.evidence), "created_at": now()}
        state["repairs"].append(repair)
        for gid in invalidates:
            state["gates"][gid].update({"status": "STALE", "reason": f"Invalidated by repair {args.id}", "evidence": [], "updated_at": now()})
        finding = find_by_id(state["findings"], args.finding)
        finding["status"] = "REPAIRED_PENDING_VERIFY"
        finding["updated_at"] = now()
        append_history(state, "repair-add", {"id": args.id, "finding": args.finding, "invalidates": invalidates})
    elif args.cmd == "assume":
        state.setdefault("assumptions", []).append({"text": args.text, "at": now()})
        append_history(state, "assume", {"text": args.text})
    elif args.cmd == "blocker-add":
        state.setdefault("external_blockers", []).append({"text": args.text, "owner_stage": args.owner_stage or None, "at": now()})
        append_history(state, "blocker-add", {"text": args.text, "owner_stage": args.owner_stage})
    elif args.cmd == "summary":
        gate_counts: dict[str, int] = {}
        for gate in state["gates"].values():
            gate_counts[gate["status"]] = gate_counts.get(gate["status"], 0) + 1
        open_blocking = [f for f in state["findings"] if f.get("blocking") and f.get("status") not in {"CLOSED", "FALSE_POSITIVE"}]
        print(json.dumps({"gates": gate_counts, "findings": len(state["findings"]),
                          "open_blocking_findings": [f["id"] for f in open_blocking],
                          "repairs": len(state["repairs"]), "external_blockers": len(state.get("external_blockers", []))},
                         ensure_ascii=False, indent=2))
        return 0

    atomic_write(state_path, state)
    print(f"Review state updated: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
