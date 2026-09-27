#!/usr/bin/env python3
"""Lightweight local candidate scanner for Stage 08 AppSec triage.

Findings from this script are *candidates only*. It intentionally does not print
matched source text to avoid leaking secrets. A human/model must verify data flow,
reachability and controls before creating a security finding.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "vendor", ".next", "dist", "build", "coverage",
    ".cache", ".turbo", ".venv", "venv", "__pycache__", "target", "out",
}
MAX_FILE_SIZE = 2_000_000
TEXT_EXTS = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".php", ".rb", ".go",
    ".java", ".kt", ".cs", ".json", ".yaml", ".yml", ".toml", ".xml", ".conf",
    ".env", ".sh", ".sql", ".html", ".vue", ".svelte",
}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity_hint: str
    regex: re.Pattern[str]
    description: str
    extensions: frozenset[str] | None = None


RULES = [
    Rule("DYNAMIC_EVAL", "High", re.compile(r"\beval\s*\("), "Dynamic eval requires untrusted-data reachability review."),
    Rule("FUNCTION_CONSTRUCTOR", "High", re.compile(r"\bnew\s+Function\s*\("), "Dynamic Function construction requires code-injection review."),
    Rule("NODE_EXEC", "High", re.compile(r"\b(?:exec|execSync)\s*\("), "Shell-style process execution requires argument/source review.", frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"})),
    Rule("PY_SHELL_TRUE", "High", re.compile(r"subprocess\.(?:run|Popen|call|check_output|check_call)\s*\([^\n]*shell\s*=\s*True"), "Python subprocess shell=True requires command-injection review.", frozenset({".py"})),
    Rule("DANGEROUS_HTML", "Medium", re.compile(r"dangerouslySetInnerHTML"), "React raw HTML escape hatch requires XSS data-flow review.", frozenset({".js", ".jsx", ".ts", ".tsx"})),
    Rule("DOM_INNERHTML", "Medium", re.compile(r"\.innerHTML\s*="), "DOM innerHTML assignment requires XSS data-flow review.", frozenset({".js", ".jsx", ".ts", ".tsx", ".html"})),
    Rule("TLS_VERIFY_DISABLED", "High", re.compile(r"(?:rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0)"), "TLS verification appears disabled; verify environment and reachability."),
    Rule("CORS_WILDCARD", "Medium", re.compile(r"(?:Access-Control-Allow-Origin[^\n]{0,40}\*|origin\s*:\s*['\"]\*['\"])"), "Wildcard CORS candidate; review credential mode and origin policy."),
    Rule("PY_PICKLE_LOAD", "High", re.compile(r"\bpickle\.(?:load|loads)\s*\("), "Pickle deserialization requires trust-boundary review.", frozenset({".py"})),
    Rule("PY_YAML_LOAD", "Medium", re.compile(r"\byaml\.load\s*\("), "YAML load requires loader/safe-mode review.", frozenset({".py"})),
    Rule("WEAK_HASH", "Low", re.compile(r"\b(?:md5|sha1)\s*\("), "Weak hash candidate; determine whether used for security-sensitive integrity/passwords."),
    Rule("DEBUG_TRUE", "Medium", re.compile(r"\bdebug\s*[:=]\s*(?:true|True|1)\b"), "Debug mode candidate; verify production applicability."),
    Rule("HARDCODED_SECRET_ASSIGNMENT", "High", re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|private[_-]?key)\b\s*[:=]\s*['\"][^'\"\n]{8,}['\"]"), "Possible hardcoded secret. Do not copy the value; verify whether placeholder/test/live."),
    Rule("PRIVATE_KEY_BLOCK", "Critical", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Private-key material appears present; verify whether test fixture or live secret."),
]


def should_scan(path: Path) -> bool:
    if path.name.startswith(".env"):
        return True
    return path.suffix.lower() in TEXT_EXTS


def walk_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        cpath = Path(current)
        for name in files:
            path = cpath / name
            if should_scan(path):
                yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 08 candidate pattern scanner")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--output", help="Optional output file")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: project root is not a directory: {root}", file=sys.stderr)
        return 2

    candidates = []
    scanned = 0
    skipped_large = 0
    errors = []

    for path in walk_files(root):
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                skipped_large += 1
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append({"path": str(path), "error": type(exc).__name__})
            continue
        scanned += 1
        ext = path.suffix.lower() or (".env" if path.name.startswith(".env") else "")
        rel = str(path.relative_to(root))
        for rule in RULES:
            if rule.extensions is not None and ext not in rule.extensions:
                continue
            for match in rule.regex.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                candidates.append({
                    "rule_id": rule.rule_id,
                    "severity_hint": rule.severity_hint,
                    "path": rel,
                    "line": line,
                    "description": rule.description,
                    "disposition": "REVIEW_REQUIRED",
                })

    result = {
        "note": "Candidate scanner only. No candidate is a confirmed vulnerability without contextual verification.",
        "root": str(root),
        "files_scanned": scanned,
        "large_files_skipped": skipped_large,
        "errors": errors,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }

    if args.format == "json":
        output = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        lines = [result["note"], f"Files scanned: {scanned}", f"Candidates: {len(candidates)}"]
        for c in candidates:
            lines.append(f"{c['severity_hint']:<8} {c['rule_id']} {c['path']}:{c['line']} - {c['description']}")
        output = "\n".join(lines)

    if args.output:
        out = Path(args.output).expanduser()
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
