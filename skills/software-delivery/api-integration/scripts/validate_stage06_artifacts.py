#!/usr/bin/env python3
"""Validate presence and basic structure of Stage 06 delivery artifacts.

This validator is intentionally repository-agnostic. It checks orchestration/document
integrity and performs lightweight OpenAPI validation. It does not replace project tests.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_DOC_SECTIONS = [
    "baseline",
    "traceability",
    "endpoint",
    "error",
    "idempotency",
    "frontend",
    "openapi",
    "validation",
    "stage 07",
    "quality-gate",
]


def find_openapi(root: Path, explicit: str | None) -> Path | None:
    if explicit:
        p = (root / explicit).resolve() if not Path(explicit).is_absolute() else Path(explicit)
        return p if p.is_file() else None
    candidates = [
        root / "docs/openapi.yaml",
        root / "docs/openapi.yml",
        root / "docs/openapi.json",
        root / "openapi.yaml",
        root / "openapi.yml",
        root / "openapi.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def validate_openapi(path: Path) -> tuple[bool, str]:
    if path.suffix.lower() == ".json":
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"OpenAPI JSON parse failed: {exc}"
        version = str(obj.get("openapi", "")) if isinstance(obj, dict) else ""
        paths = obj.get("paths") if isinstance(obj, dict) else None
        if not version.startswith("3."):
            return False, "OpenAPI version is missing or not 3.x"
        if not isinstance(paths, dict):
            return False, "OpenAPI paths object is missing"
        return True, f"OpenAPI JSON parsed; operations path count={len(paths)}"

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not re.search(r"(?m)^openapi:\s*['\"]?3\.", text):
        return False, "OpenAPI YAML does not declare a 3.x openapi version"
    if not re.search(r"(?m)^paths:\s*$", text):
        return False, "OpenAPI YAML does not contain a top-level paths section"

    # Use PyYAML when available for stronger parse validation without making it mandatory.
    try:
        proc = subprocess.run(
            [sys.executable, "-c", "import sys,yaml; d=yaml.safe_load(open(sys.argv[1],encoding='utf-8')); assert isinstance(d,dict) and isinstance(d.get('paths'),dict)", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except Exception:
        proc = None
    if proc is not None and proc.returncode != 0:
        if "No module named" not in proc.stderr:
            return False, "OpenAPI YAML parsing failed with available YAML parser"
        return True, "OpenAPI YAML passed structural checks; PyYAML unavailable"
    if proc is not None:
        return True, "OpenAPI YAML parsed successfully"
    return True, "OpenAPI YAML passed structural checks"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--openapi")
    parser.add_argument("--allow-no-openapi", action="store_true")
    parser.add_argument("--require-stage06-pass", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures: list[str] = []

    doc = root / "docs/06-api-design.md"
    if not doc.is_file():
        failures.append("missing docs/06-api-design.md")
    else:
        text = doc.read_text(encoding="utf-8", errors="ignore").lower()
        missing = [section for section in REQUIRED_DOC_SECTIONS if section not in text]
        if missing:
            failures.append("API design document missing expected topics: " + ", ".join(missing))
        else:
            print("OK: API design document contains expected Stage 06 topics")

    state = root / "project-state.json"
    if not state.is_file():
        failures.append("missing project-state.json")
    else:
        try:
            json.loads(state.read_text(encoding="utf-8"))
            print("OK: project-state.json parses as JSON")
        except Exception as exc:
            failures.append(f"project-state.json is invalid JSON: {exc}")

    if state.is_file():
        validator = Path(__file__).with_name("validate_project_state.py")
        cmd = [sys.executable, str(validator), str(state), "--require-stage05-pass"]
        if args.require_stage06_pass:
            cmd.append("--require-stage06-pass")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(proc.stdout.rstrip())
        if proc.returncode != 0:
            failures.append("project state stage conditions failed")

    openapi = find_openapi(root, args.openapi)
    if openapi is None:
        if not args.allow_no_openapi:
            failures.append("OpenAPI file not found; use --allow-no-openapi only for a non-HTTP API")
    else:
        ok, message = validate_openapi(openapi)
        print(("OK: " if ok else "ERROR: ") + message + f" ({openapi.relative_to(root) if openapi.is_relative_to(root) else openapi})")
        if not ok:
            failures.append(message)

    if failures:
        print("\nStage 06 artifact validation FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nOK: Stage 06 artifact integrity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
