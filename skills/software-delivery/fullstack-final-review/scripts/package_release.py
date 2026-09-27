#!/usr/bin/env python3
"""Create a filtered release ZIP after hygiene preflight."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from scan_release_hygiene import scan_project  # noqa: E402

EXCLUDED_DIRS = {
    ".git", ".final-review", "node_modules", "vendor", ".venv", "venv", ".cache", "coverage",
    "__pycache__", ".idea", ".vscode", ".pytest_cache", ".mypy_cache", ".ruff_cache"
}
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db", "npm-debug.log", "yarn-error.log"}
EXCLUDED_SUFFIXES = {".pyc", ".log", ".pid", ".sock", ".key", ".p12", ".pfx", ".jks"}


def is_safe_env(name: str) -> bool:
    return name in {".env.example", ".env.sample", ".env.template", ".env.defaults"} or any(
        name.endswith(suffix) for suffix in (".example", ".sample", ".template")
    )


def should_exclude(path: Path, root: Path, output: Path) -> tuple[bool, str | None]:
    try:
        r = path.relative_to(root)
    except ValueError:
        return True, "outside-root"
    if path.resolve() == output.resolve():
        return True, "output-archive"
    if any(part in EXCLUDED_DIRS for part in r.parts[:-1]):
        return True, "excluded-directory"
    name = path.name
    if name in EXCLUDED_NAMES:
        return True, "excluded-name"
    if name.startswith(".env") and not is_safe_env(name):
        return True, "secret-env"
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True, "sensitive-or-local-suffix"
    return False, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--output")
    ap.add_argument("--allowlist")
    ap.add_argument("--include-audit", action="store_true")
    ap.add_argument("--require-final-manifest", action="store_true", help="Require release-manifest.json with final_stage.status=PASS and docs/12-final-review.md before packaging")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")
    output = Path(args.output).resolve() if args.output else root.parent / f"{root.name}-release.zip"
    allowlist = Path(args.allowlist).resolve() if args.allowlist else root / ".final-review" / "hygiene-allowlist.json"

    if args.require_final_manifest:
        manifest_path = root / "release-manifest.json"
        report_path = root / "docs" / "12-final-review.md"
        if not manifest_path.exists() or not report_path.exists():
            print("Refusing final package: final release manifest/report is missing.")
            return 4
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Refusing final package: invalid release manifest: {exc}")
            return 4
        if manifest.get("final_stage", {}).get("status") != "PASS":
            print("Refusing final package: release-manifest final_stage.status is not PASS.")
            return 4
        report_text = report_path.read_text(encoding="utf-8", errors="replace")
        required_markers = ["STAGE_12_STATUS: PASS", "WORKFLOW_STATUS: COMPLETE", "NEXT_STAGE: NONE"]
        missing_markers = [m for m in required_markers if m not in report_text]
        if missing_markers:
            print("Refusing final package: final review report is missing completion markers: " + ", ".join(missing_markers))
            return 4

    report = scan_project(root, allowlist if allowlist.exists() else None)
    summary = report["summary"]
    if summary.get("blocking_active", 0) or summary.get("review_required_active", 0):
        print("Refusing to package: unresolved hygiene findings remain.")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    included: list[str] = []
    excluded: list[dict[str, str]] = []
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for current, dirs, files in os.walk(root):
            if not args.include_audit:
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            else:
                dirs[:] = [d for d in dirs if d not in (EXCLUDED_DIRS - {".final-review"})]
            cpath = Path(current)
            for name in sorted(files):
                path = cpath / name
                if path.is_symlink():
                    excluded.append({"path": path.relative_to(root).as_posix(), "reason": "symlink-skipped"})
                    continue
                exclude, reason = should_exclude(path, root, output)
                if args.include_audit and ".final-review" in path.relative_to(root).parts:
                    exclude = path.suffix.lower() in EXCLUDED_SUFFIXES or (path.name.startswith(".env") and not is_safe_env(path.name))
                    reason = "sensitive-audit-file" if exclude else None
                if exclude:
                    excluded.append({"path": path.relative_to(root).as_posix(), "reason": reason or "excluded"})
                    continue
                arc = path.relative_to(root).as_posix()
                zf.write(path, arc)
                included.append(arc)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    result: dict[str, Any] = {
        "schema_version": 1,
        "path": str(output),
        "sha256": digest,
        "size_bytes": output.stat().st_size,
        "included_files": len(included),
        "excluded_files": len(excluded),
        "contains_release_manifest": "release-manifest.json" in included,
        "contains_readme": any(x.lower() == "readme.md" for x in included),
        "excluded_sample": excluded[:100],
    }
    result_path = root / ".final-review" / "package-result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not included:
        print("Refusing empty release archive.")
        output.unlink(missing_ok=True)
        return 3

    print(f"Release archive: {output}")
    print(f"Files: {len(included)} | size: {result['size_bytes']} | sha256: {digest}")
    print(f"Package result: {result_path}")
    if not result["contains_release_manifest"]:
        print("WARNING: release-manifest.json is not inside the archive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
