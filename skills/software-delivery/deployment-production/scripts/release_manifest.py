#!/usr/bin/env python3
"""Generate a deterministic Stage 11 release manifest with artifact hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKIP_NAMES = {".git", "node_modules", ".venv", "venv", ".DS_Store"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
            check=False,
        )
        value = proc.stdout.strip()
        return value if proc.returncode == 0 and value else None
    except (OSError, subprocess.SubprocessError):
        return None


def sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def iter_dir_files(path: Path):
    for current, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_NAMES)
        for name in sorted(files):
            if name in SKIP_NAMES:
                continue
            yield Path(current) / name


def sha256_directory(path: Path) -> tuple[str, int]:
    """Hash sorted relative paths + bytes; ignore filesystem metadata."""
    h = hashlib.sha256()
    total = 0
    for file_path in iter_dir_files(path):
        rel = file_path.relative_to(path).as_posix().encode("utf-8")
        file_hash, size = sha256_file(file_path)
        h.update(len(rel).to_bytes(8, "big"))
        h.update(rel)
        h.update(bytes.fromhex(file_hash))
        total += size
    return h.hexdigest(), total


def artifact_entry(root: Path, raw: str) -> dict[str, Any]:
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"artifact does not exist: {raw}")
    try:
        display = path.relative_to(root).as_posix()
    except ValueError:
        display = str(path)
    if path.is_file():
        digest, size = sha256_file(path)
        kind = "file"
    elif path.is_dir():
        digest, size = sha256_directory(path)
        kind = "directory"
    else:
        raise ValueError(f"unsupported artifact type: {raw}")
    return {"path": display, "type": kind, "sha256": digest, "size_bytes": size}


def parse_image(spec: str) -> dict[str, str | None]:
    if "@" in spec:
        name, digest = spec.rsplit("@", 1)
        return {"name": name, "digest": digest}
    return {"name": spec, "digest": None}


def main() -> int:
    p = argparse.ArgumentParser(description="Generate Stage 11 release manifest")
    p.add_argument("--root", default=".")
    p.add_argument("--output", default="artifacts/stage-11/release-manifest.json")
    p.add_argument("--version")
    p.add_argument("--environment", default="production-like")
    p.add_argument("--deployment-status", choices=["PERFORMED", "NOT_PERFORMED"], default="NOT_PERFORMED")
    p.add_argument("--target")
    p.add_argument("--artifact", action="append", default=[])
    p.add_argument("--image", action="append", default=[], help="Image as name@digest or name")
    p.add_argument("--migration-tool")
    p.add_argument("--migration-target")
    p.add_argument("--migration-status", choices=["PASS", "N_A", "NOT_RUN", "BLOCKED"], default="NOT_RUN")
    p.add_argument("--sbom")
    p.add_argument("--scan-report", action="append", default=[])
    p.add_argument("--smoke-report")
    p.add_argument("--evidence-ledger", default="artifacts/stage-11/evidence.json")
    args = p.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: invalid root: {root}", file=sys.stderr)
        return 2

    entries = []
    try:
        for item in args.artifact:
            entries.append(artifact_entry(root, item))
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    commit = git(root, "rev-parse", "HEAD")
    ref = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    status = git(root, "status", "--porcelain") if commit else None

    manifest = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "source": {
            "commit": commit,
            "ref": ref,
            "dirty": bool(status) if commit else None,
        },
        "release": {
            "version": args.version,
            "environment": args.environment,
            "deployment_status": args.deployment_status,
            "target": args.target,
        },
        "artifacts": entries,
        "images": [parse_image(x) for x in args.image],
        "migrations": {
            "tool": args.migration_tool,
            "target_version": args.migration_target,
            "status": args.migration_status,
        },
        "security": {
            "sbom": args.sbom,
            "scan_reports": args.scan_report,
        },
        "validation": {
            "evidence_ledger": args.evidence_ledger,
            "smoke_report": args.smoke_report,
        },
    }

    out = Path(args.output)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
