#!/usr/bin/env python3
"""Stage 11 repository preflight inventory and basic release-readiness checks.

This script is intentionally ecosystem-neutral and uses only the Python standard
library. It reports facts and obvious precondition issues; it does not replace
project-specific engineering review.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SKIP_DIRS = {
    ".git", "node_modules", "vendor", ".venv", "venv", "dist", "build",
    ".next", ".nuxt", "coverage", ".cache", "target", "bin", "obj",
}

MANIFESTS = [
    "package.json", "pyproject.toml", "requirements.txt", "Pipfile",
    "poetry.lock", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    "build.gradle.kts", "composer.json", "Gemfile", "mix.exs",
]
LOCKFILES = [
    "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
    "bun.lockb", "bun.lock", "poetry.lock", "Pipfile.lock", "uv.lock",
    "go.sum", "Cargo.lock", "composer.lock", "Gemfile.lock",
]
ENV_EXAMPLES = [
    ".env.example", ".env.sample", ".env.template", "env.example",
]
SENSITIVE_LOCAL_NAMES = {
    ".env", ".env.production", ".env.prod", "credentials.json",
    "service-account.json", "id_rsa", "id_ed25519",
}
PRIVATE_KEY_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_git(root: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        return proc.returncode, proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def iter_files(root: Path, max_depth: int = 5) -> Iterable[Path]:
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".pytest_cache")]
        if depth >= max_depth:
            dirs[:] = []
        for name in files:
            yield current_path / name


def find_named(root: Path, names: set[str], max_depth: int = 4) -> list[str]:
    found: list[str] = []
    for path in iter_files(root, max_depth=max_depth):
        if path.name in names:
            found.append(relative(root, path))
    return sorted(set(found))


def find_patterns(root: Path, max_depth: int = 4) -> dict[str, list[str]]:
    out = {
        "docker": [],
        "compose": [],
        "ci": [],
        "migrations": [],
        "infrastructure": [],
        "env_examples": [],
        "sensitive_local_files": [],
    }
    for path in iter_files(root, max_depth=max_depth):
        rel = relative(root, path)
        low = rel.lower()
        name = path.name.lower()

        if name == "dockerfile" or name.startswith("dockerfile."):
            out["docker"].append(rel)
        if name in {"compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}:
            out["compose"].append(rel)
        if low.startswith(".github/workflows/") or low in {
            ".gitlab-ci.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml", "jenkinsfile"
        }:
            out["ci"].append(rel)
        if any(seg in {"migrations", "migration", "alembic", "prisma"} for seg in path.parts):
            if path.is_file():
                out["migrations"].append(rel)
        if name.endswith(('.tf', '.tfvars')) or any(
            seg.lower() in {"k8s", "kubernetes", "helm", "terraform", "infra", "infrastructure"}
            for seg in path.parts
        ):
            out["infrastructure"].append(rel)
        if path.name in ENV_EXAMPLES:
            out["env_examples"].append(rel)
        if path.name in SENSITIVE_LOCAL_NAMES or path.suffix.lower() in PRIVATE_KEY_SUFFIXES:
            out["sensitive_local_files"].append(rel)

    for key in out:
        out[key] = sorted(set(out[key]))
    return out


def contains_stage10_pass(data: Any) -> bool:
    """Conservatively search structured state for a stage-10 object with PASS status."""
    if isinstance(data, dict):
        status = str(data.get("status", data.get("state", ""))).upper()
        identifiers = []
        for key in ("id", "stage", "stage_id", "name", "key", "title"):
            if key in data:
                identifiers.append(str(data[key]).lower())
        joined = " ".join(identifiers)
        if status == "PASS" and (
            "stage 10" in joined or "stage-10" in joined or "stage_10" in joined
            or joined.startswith("10") or "10-" in joined
        ):
            return True
        for key, value in data.items():
            key_l = str(key).lower()
            if ("stage10" in key_l or "stage_10" in key_l or "stage-10" in key_l or key_l == "10"):
                if isinstance(value, str) and value.upper() == "PASS":
                    return True
                if isinstance(value, dict):
                    vstatus = str(value.get("status", value.get("state", ""))).upper()
                    if vstatus == "PASS":
                        return True
            if contains_stage10_pass(value):
                return True
    elif isinstance(data, list):
        return any(contains_stage10_pass(item) for item in data)
    return False


def load_project_state(root: Path) -> tuple[str | None, Any | None, str | None]:
    candidates = [root / "project-state.json"]
    for path in candidates:
        if path.exists():
            try:
                return relative(root, path), json.loads(path.read_text(encoding="utf-8")), None
            except Exception as exc:  # noqa: BLE001 - report malformed state safely
                return relative(root, path), None, f"invalid JSON: {exc}"
    return None, None, None


def check_record(check_id: str, status: str, summary: str, evidence: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "summary": summary,
        "evidence": evidence or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory Stage 11 release-readiness facts.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--json-out", help="Write JSON report to this path")
    parser.add_argument("--max-depth", type=int, default=5, help="Filesystem inventory depth")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: project root does not exist or is not a directory: {root}", file=sys.stderr)
        return 2

    manifests = find_named(root, set(MANIFESTS), max_depth=min(args.max_depth, 4))
    lockfiles = find_named(root, set(LOCKFILES), max_depth=min(args.max_depth, 4))
    patterns = find_patterns(root, max_depth=args.max_depth)

    rc, commit = run_git(root, "rev-parse", "HEAD")
    git_available = rc == 0 and bool(commit)
    _, ref = run_git(root, "rev-parse", "--abbrev-ref", "HEAD") if git_available else (1, "")
    dirty = None
    if git_available:
        _, status = run_git(root, "status", "--porcelain")
        dirty = bool(status)

    state_path, state_data, state_error = load_project_state(root)
    stage10_pass = contains_stage10_pass(state_data) if state_data is not None else None

    checks: list[dict[str, Any]] = []
    if state_error:
        checks.append(check_record("stage10_state", "FAIL", f"{state_path} is not valid JSON: {state_error}", [state_path]))
    elif state_path is None:
        checks.append(check_record("stage10_state", "WARN", "project-state.json not found; Stage 10 PASS must be verified from another authoritative artifact."))
    elif stage10_pass:
        checks.append(check_record("stage10_state", "PASS", "Structured project state contains Stage 10 PASS evidence.", [state_path]))
    else:
        checks.append(check_record("stage10_state", "WARN", "project-state.json was found but Stage 10 PASS was not recognized; verify schema/evidence manually.", [state_path]))

    if manifests:
        checks.append(check_record("dependency_manifests", "PASS", "Dependency/build manifests detected.", manifests))
    else:
        checks.append(check_record("dependency_manifests", "WARN", "No known dependency/build manifest detected in scanned depth."))

    if lockfiles:
        checks.append(check_record("dependency_locks", "PASS", "Dependency lock/resolution files detected.", lockfiles))
    else:
        checks.append(check_record("dependency_locks", "WARN", "No known lockfile detected; determine whether the ecosystem supports/needs one."))

    if patterns["env_examples"]:
        checks.append(check_record("env_contract", "PASS", "Environment example/template detected.", patterns["env_examples"]))
    else:
        checks.append(check_record("env_contract", "WARN", "No .env example/template detected; verify target-native config contract or add one."))

    if patterns["sensitive_local_files"]:
        checks.append(check_record(
            "sensitive_local_files",
            "WARN",
            "Potentially sensitive local files detected. Verify they are placeholders/untracked and are not included in release artifacts.",
            patterns["sensitive_local_files"],
        ))
    else:
        checks.append(check_record("sensitive_local_files", "PASS", "No obvious sensitive local filenames detected in scanned depth."))

    if git_available:
        checks.append(check_record("source_identity", "PASS", f"Git source identity captured at {commit}.", [f"ref:{ref or 'detached'}", f"dirty:{dirty}"]))
    else:
        checks.append(check_record("source_identity", "WARN", "Git source identity unavailable; establish an equivalent release source identifier."))

    rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
    overall = max((c["status"] for c in checks), key=lambda s: rank[s], default="WARN")

    report = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "root": str(root),
        "overall": overall,
        "source": {
            "git": git_available,
            "commit": commit or None,
            "ref": ref or None,
            "dirty": dirty,
        },
        "inventory": {
            "manifests": manifests,
            "lockfiles": lockfiles,
            **patterns,
        },
        "checks": checks,
        "notes": [
            "This preflight is heuristic and does not replace project-specific Stage 11 quality gates.",
            "Potentially sensitive files are reported by filename only; values are never read or emitted by this script.",
        ],
    }

    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.json_out:
        out = Path(args.json_out)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 2 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
