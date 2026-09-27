#!/usr/bin/env python3
"""Build release-manifest.json from Stage 12 audit state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def file_artifact(path: Path, root: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def summarize_requirements(trace: dict[str, Any]) -> dict[str, Any]:
    reqs = trace.get("requirements", []) if isinstance(trace.get("requirements"), list) else []
    by_status: dict[str, int] = {}
    core = 0
    for req in reqs:
        if not isinstance(req, dict):
            continue
        status = str(req.get("status", "UNKNOWN"))
        by_status[status] = by_status.get(status, 0) + 1
        core += 1 if req.get("core") else 0
    return {"total": len(reqs), "core": core, "by_status": by_status}


def summarize_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    checks = evidence.get("checks", []) if isinstance(evidence.get("checks"), list) else []
    by_status: dict[str, int] = {}
    for check in checks:
        if not isinstance(check, dict):
            continue
        status = str(check.get("status", "UNKNOWN"))
        by_status[status] = by_status.get(status, 0) + 1
    return {"count": len(checks), "by_status": by_status}


def summarize_findings(state: dict[str, Any]) -> dict[str, Any]:
    findings = state.get("findings", []) if isinstance(state.get("findings"), list) else []
    open_items = [f for f in findings if isinstance(f, dict) and f.get("status") not in {"CLOSED", "FALSE_POSITIVE"}]
    by_severity = {sev: sum(1 for f in open_items if f.get("severity") == sev)
                   for sev in ["Critical", "High", "Medium", "Low", "Info"]}
    return {
        "total_findings": len(findings),
        "open_findings": len(open_items),
        "open_by_severity": by_severity,
        "open_blocking": sum(1 for f in open_items if f.get("blocking")),
    }


def command_summary(profile: dict[str, Any]) -> dict[str, Any]:
    candidates = profile.get("command_candidates", {}) if isinstance(profile.get("command_candidates"), dict) else {}
    return {key: value for key, value in candidates.items() if value}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--output")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    audit = root / ".final-review"
    profile = load(audit / "project-profile.json")
    state = load(audit / "review-state.json")
    trace = load(audit / "traceability.json")
    hygiene = load(audit / "hygiene-report.json")
    evidence = load(audit / "evidence.json")
    verdict = load(audit / "final-verdict.json")
    package_result = load(audit / "package-result.json")

    final_status = verdict.get("verdict") if verdict.get("phase") == "final" else "PENDING_FINAL_VALIDATION"
    project = profile.get("project", {}) if isinstance(profile.get("project"), dict) else {}
    git = profile.get("git", {}) if isinstance(profile.get("git"), dict) else {}

    components = []
    for pkg in profile.get("package_manifests", []) if isinstance(profile.get("package_manifests"), list) else []:
        if isinstance(pkg, dict):
            components.append({
                "path": pkg.get("path"), "name": pkg.get("name"), "version": pkg.get("version"),
                "frameworks": pkg.get("frameworks", [])
            })

    gates = {}
    for gid, gate in (state.get("gates", {}) if isinstance(state.get("gates"), dict) else {}).items():
        if isinstance(gate, dict):
            gates[gid] = {"status": gate.get("status"), "reason": gate.get("reason"), "evidence": gate.get("evidence", [])}

    known_nonblocking = []
    for f in state.get("findings", []) if isinstance(state.get("findings"), list) else []:
        if not isinstance(f, dict):
            continue
        if not f.get("blocking") and f.get("status") not in {"CLOSED", "FALSE_POSITIVE"}:
            known_nonblocking.append({"id": f.get("id"), "title": f.get("title"), "severity": f.get("severity"),
                                      "status": f.get("status"), "summary": f.get("summary")})

    artifacts = []
    for candidate in [root / "docs" / "12-final-review.md", root / "README.md", root / "project-state.json"]:
        item = file_artifact(candidate, root)
        if item:
            artifacts.append(item)

    manifest = {
        "schema_version": 1,
        "project": {
            "name": project.get("name") or root.name,
            "version": project.get("version"),
            "revision": git.get("revision"),
            "branch": git.get("branch"),
        },
        "final_stage": {"id": 12, "status": final_status, "validator_phase": verdict.get("phase")},
        "runtime": profile.get("runtimes", {}),
        "components": components,
        "source_layout": {
            "manifests": profile.get("manifests", []),
            "lockfiles": profile.get("lockfiles", []),
            "dockerfiles": profile.get("dockerfiles", []),
            "compose_files": profile.get("compose_files", []),
            "api_specs": profile.get("api_specs", []),
            "migration_dirs": profile.get("migration_dirs", []),
            "test_dirs": profile.get("test_dirs", []),
        },
        "commands": command_summary(profile),
        "validation": {
            "gates": gates,
            "evidence_summary": summarize_evidence(evidence),
            "traceability_summary": summarize_requirements(trace),
            "security_summary": summarize_findings(state),
            "hygiene_summary": hygiene.get("summary", {}),
            "validator_blockers": verdict.get("blockers", []),
            "validator_warnings": verdict.get("warnings", []),
        },
        "known_non_blocking_issues": known_nonblocking,
        "artifacts": artifacts,
        "package": {
            "path": None,
            "sha256": None,
            "size_bytes": None,
            "integrity_record": ".final-review/package-result.json",
            "note": "The archive SHA-256 is stored outside the self-containing archive in the audit integrity record to avoid a self-referential hash."
        },
    }

    out = Path(args.output).resolve() if args.output else root / "release-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Release manifest written: {out}")
    print(f"Final stage status in manifest: {final_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
