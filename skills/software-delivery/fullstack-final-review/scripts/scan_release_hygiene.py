#!/usr/bin/env python3
"""Scan project source for release-hygiene hazards without exposing secret values."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = {
    ".git", ".final-review", "node_modules", "vendor", ".venv", "venv", ".next", ".nuxt",
    ".cache", "coverage", "target", "__pycache__", ".idea"
}
MAX_TEXT_BYTES = 2 * 1024 * 1024
SAFE_ENV_NAMES = {".env.example", ".env.sample", ".env.template", ".env.defaults"}

def is_safe_env_name(name: str) -> bool:
    return name in SAFE_ENV_NAMES or any(name.endswith(suffix) for suffix in (".example", ".sample", ".template"))
SENSITIVE_FILE_NAMES = {"id_rsa", "id_ed25519", "credentials.json", "service-account.json"}
SENSITIVE_SUFFIXES = {".key", ".p12", ".pfx", ".jks"}
DB_SUFFIXES = {".sql", ".dump", ".bak", ".sqlite", ".sqlite3", ".db"}
PLACEHOLDER_MARKERS = {"example", "placeholder", "changeme", "change-me", "your_", "your-", "dummy", "fake", "test", "xxxxx", "<", "${"}

CONTENT_RULES = [
    ("PRIVATE_KEY_MATERIAL", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "High", True, True),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "High", True, True),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "High", True, True),
    ("STRIPE_LIVE_SECRET", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"), "High", True, True),
    ("AUTH_BYPASS_ENABLED", re.compile(r"(?i)\b(?:DISABLE_AUTH|SKIP_AUTH|BYPASS_AUTH)\b\s*[:=]\s*(?:true|1|yes)\b"), "High", True, True),
    ("DEBUG_ENABLED", re.compile(r"(?i)\b(?:DEBUG|FLASK_DEBUG)\b\s*[:=]\s*(?:true|1|yes)\b"), "Medium", False, True),
]
GENERIC_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|client[_-]?secret|secret|password|passwd|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*['\"]([^'\"\r\n]{12,})['\"]"
)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def tracked_files(root: Path) -> set[str]:
    try:
        p = subprocess.run(["git", "ls-files", "-z"], cwd=str(root), stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10, check=False)
        if p.returncode == 0:
            return {x.decode("utf-8", errors="replace") for x in p.stdout.split(b"\0") if x}
    except (OSError, subprocess.SubprocessError):
        pass
    return set()


def load_allowlist(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("allowlist", [])
    if not isinstance(data, list):
        raise ValueError("Allowlist must be a list or {'allowlist': [...]} object")
    return [x for x in data if isinstance(x, dict)]


def is_suppressed(rule_id: str, path: str, allowlist: list[dict[str, Any]]) -> tuple[bool, str | None]:
    for entry in allowlist:
        if entry.get("rule_id") == rule_id and entry.get("path") == path and str(entry.get("reason", "")).strip():
            return True, str(entry.get("reason"))
    return False, None


def redact_preview(line: str, start: int, end: int) -> str:
    prefix = line[max(0, start - 40):start]
    suffix = line[end:end + 40]
    return (prefix + "<REDACTED_MATCH>" + suffix).strip()[:180]


def add_finding(findings: list[dict[str, Any]], allowlist: list[dict[str, Any]], *, rule_id: str,
                path: str, severity: str, blocking: bool, requires_review: bool, message: str,
                line: int | None = None, preview: str | None = None, tracked: bool | None = None) -> None:
    suppressed, reason = is_suppressed(rule_id, path, allowlist)
    findings.append({
        "rule_id": rule_id, "path": path, "line": line, "severity": severity,
        "blocking": blocking, "requires_review": requires_review, "message": message,
        "preview": preview, "tracked": tracked, "suppressed": suppressed,
        "suppression_reason": reason
    })


def scan_project(root: Path, allowlist_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    tracked = tracked_files(root)
    allowlist = load_allowlist(allowlist_path)
    findings: list[dict[str, Any]] = []
    scanned_files = 0

    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        cpath = Path(current)
        for name in files:
            path = cpath / name
            rpath = rel(path, root)
            scanned_files += 1
            is_tracked = rpath in tracked if tracked else None

            if name.startswith(".env") and not is_safe_env_name(name):
                if is_tracked:
                    add_finding(findings, allowlist, rule_id="TRACKED_ENV_FILE", path=rpath,
                                severity="High", blocking=True, requires_review=True,
                                message="Non-template environment file is tracked by version control.", tracked=is_tracked)
                else:
                    add_finding(findings, allowlist, rule_id="LOCAL_ENV_FILE", path=rpath,
                                severity="Info", blocking=False, requires_review=False,
                                message="Local environment file exists and must remain excluded from release packaging.", tracked=is_tracked)

            if name in SENSITIVE_FILE_NAMES or path.suffix.lower() in SENSITIVE_SUFFIXES:
                add_finding(findings, allowlist, rule_id="SENSITIVE_KEY_FILE", path=rpath,
                            severity="High" if is_tracked else "Medium", blocking=bool(is_tracked), requires_review=True,
                            message="Potential credential/private-key file present; verify it is not real release secret material.", tracked=is_tracked)

            if path.suffix.lower() in DB_SUFFIXES and is_tracked:
                add_finding(findings, allowlist, rule_id="TRACKED_DATA_DUMP", path=rpath,
                            severity="Medium", blocking=False, requires_review=True,
                            message="Tracked database/dump-like artifact requires review for private or production data.", tracked=is_tracked)

            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size > MAX_TEXT_BYTES:
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if b"\x00" in raw[:8192]:
                continue
            text = raw.decode("utf-8", errors="replace")
            lines = text.splitlines()
            for idx, line in enumerate(lines, 1):
                for rule_id, pattern, severity, blocking, review in CONTENT_RULES:
                    for m in pattern.finditer(line):
                        add_finding(findings, allowlist, rule_id=rule_id, path=rpath, severity=severity,
                                    blocking=blocking, requires_review=review,
                                    message=f"Potential {rule_id.lower().replace('_', ' ')} detected; inspect safely.",
                                    line=idx, preview=redact_preview(line, m.start(), m.end()), tracked=is_tracked)
                for m in GENERIC_SECRET.finditer(line):
                    value = m.group(2).lower()
                    if any(marker in value for marker in PLACEHOLDER_MARKERS):
                        continue
                    add_finding(findings, allowlist, rule_id="GENERIC_SECRET_ASSIGNMENT", path=rpath,
                                severity="Medium", blocking=False, requires_review=True,
                                message="Secret-like literal assignment requires manual verification.",
                                line=idx, preview=redact_preview(line, m.start(), m.end()), tracked=is_tracked)

    active = [f for f in findings if not f["suppressed"]]
    report = {
        "schema_version": 1,
        "project_root": str(root),
        "scanned_files": scanned_files,
        "findings": findings,
        "summary": {
            "total": len(findings),
            "active": len(active),
            "suppressed": len(findings) - len(active),
            "blocking_active": sum(1 for f in active if f["blocking"]),
            "review_required_active": sum(1 for f in active if f["requires_review"]),
            "by_severity": {sev: sum(1 for f in active if f["severity"] == sev)
                            for sev in ["Critical", "High", "Medium", "Low", "Info"]}
        }
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--output")
    ap.add_argument("--allowlist")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    allowlist_path = Path(args.allowlist).resolve() if args.allowlist else root / ".final-review" / "hygiene-allowlist.json"
    report = scan_project(root, allowlist_path if allowlist_path.exists() else None)
    out = Path(args.output).resolve() if args.output else root / ".final-review" / "hygiene-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    print(f"Hygiene report: {out}")
    print(f"Active findings: {s['active']} | blocking: {s['blocking_active']} | review-required: {s['review_required_active']}")
    if s["blocking_active"]:
        return 1
    if s["review_required_active"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
