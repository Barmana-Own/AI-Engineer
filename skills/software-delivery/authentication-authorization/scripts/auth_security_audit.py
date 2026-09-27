#!/usr/bin/env python3
"""Heuristic Stage 07 authentication/authorization static audit.

This script intentionally uses only the Python standard library. It finds
high-signal auth anti-patterns and emits redacted evidence. Findings are leads
for manual review; they are not a replacement for tests or code review.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build", "out",
    ".next", ".nuxt", "coverage", "target", ".venv", "venv", "__pycache__",
    ".idea", ".vscode", ".cache", "tmp", "temp",
}

TEXT_EXTENSIONS = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".rb", ".php",
    ".java", ".kt", ".kts", ".go", ".cs", ".fs", ".rs", ".scala",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".properties",
    ".env", ".graphql", ".gql", ".sql", ".vue", ".svelte",
}

SEVERITY_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: str
    title: str
    rationale: str
    pattern: re.Pattern[str]
    secret_bearing: bool = False


@dataclass
class Finding:
    rule_id: str
    severity: str
    title: str
    rationale: str
    file: str
    line: int
    excerpt: str


RULES = [
    Rule(
        "AUTH-STATIC-001", "HIGH", "Likely hard-coded authentication secret",
        "Reusable auth secrets should come from managed runtime configuration, not source code.",
        re.compile(r"(?i)\b(jwt[_-]?secret|session[_-]?secret|client[_-]?secret|api[_-]?secret|auth[_-]?secret)\b\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
        True,
    ),
    Rule(
        "AUTH-STATIC-002", "HIGH", "Likely default or trivial credential",
        "Default/trivial reusable credentials can create immediate authentication bypass.",
        re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|client[_-]?secret)\b\s*[:=]\s*['\"](?:admin|password|passwd|changeme|change_me|secret|123456|12345678|test123|default)['\"]"),
        True,
    ),
    Rule(
        "AUTH-STATIC-003", "HIGH", "Refresh or long-lived token stored in browser persistent storage",
        "Persistent JavaScript-readable storage increases bearer-token exposure to XSS and requires explicit risk approval.",
        re.compile(r"(?i)\b(?:localStorage|sessionStorage)\.setItem\s*\([^\n]*(?:refresh[_-]?token|refreshToken|long[_-]?lived[_-]?token)"),
        True,
    ),
    Rule(
        "AUTH-STATIC-004", "MEDIUM", "Access/auth token stored in browser persistent storage",
        "Review whether the architecture intentionally accepts JavaScript-readable bearer-token exposure.",
        re.compile(r"(?i)\b(?:localStorage|sessionStorage)\.setItem\s*\([^\n]*(?:access[_-]?token|accessToken|auth[_-]?token|authToken|bearer|jwt)"),
        True,
    ),
    Rule(
        "AUTH-STATIC-005", "HIGH", "Sensitive auth material may be written to logs",
        "Passwords, tokens, authorization headers, cookies, and recovery secrets must not be logged.",
        re.compile(r"(?i)\b(?:console\.(?:log|debug|info|warn|error)|logger\.(?:log|debug|info|warn|error)|print\s*\()([^\n]{0,180})(?:password|passwd|authorization|access[_-]?token|refresh[_-]?token|reset[_-]?token|verification[_-]?token|cookie|client[_-]?secret|api[_-]?key)"),
        True,
    ),
    Rule(
        "AUTH-STATIC-006", "HIGH", "JWT appears to be decoded without verification",
        "Decoded JWT claims are attacker-controlled until signature and required claims are verified.",
        re.compile(r"(?i)\b(?:jwt|jsonwebtoken)\.decode\s*\("),
    ),
    Rule(
        "AUTH-STATIC-007", "HIGH", "Weak fast hash appears to be used for a password",
        "General-purpose MD5/SHA-1 hashing is not appropriate password verification.",
        re.compile(r"(?i)(?:password|passwd)[^\n]{0,100}(?:md5|sha1)|(?:md5|sha1)[^\n]{0,100}(?:password|passwd)"),
    ),
    Rule(
        "AUTH-STATIC-008", "MEDIUM", "Auth/session cookie explicitly disables HttpOnly",
        "JavaScript-readable session cookies increase credential theft risk.",
        re.compile(r"(?i)(?:session|auth|token|sid|jwt)[^\n]{0,160}httpOnly\s*:\s*false|httpOnly\s*:\s*false[^\n]{0,160}(?:session|auth|token|sid|jwt)"),
    ),
    Rule(
        "AUTH-STATIC-009", "MEDIUM", "Auth/session cookie explicitly disables Secure",
        "Production auth cookies should normally be restricted to TLS transport.",
        re.compile(r"(?i)(?:session|auth|token|sid|jwt)[^\n]{0,160}secure\s*:\s*false|secure\s*:\s*false[^\n]{0,160}(?:session|auth|token|sid|jwt)"),
    ),
    Rule(
        "AUTH-STATIC-010", "HIGH", "Token or auth secret appears in URL query construction",
        "Credentials in URLs can leak through logs, history, referrers, and monitoring.",
        re.compile(r"(?i)[?&](?:access_token|refresh_token|auth_token|token|jwt|api_key|apikey)=|[?&](?:access_token|refresh_token|auth_token|token|jwt|api_key|apikey)\$\{"),
        True,
    ),
    Rule(
        "AUTH-STATIC-011", "HIGH", "Secret-like value exposed through public frontend environment variable",
        "Public frontend build variables are delivered to untrusted clients and cannot contain secrets.",
        re.compile(r"(?i)\b(?:NEXT_PUBLIC_|VITE_|REACT_APP_)[A-Z0-9_]*(?:SECRET|PRIVATE_KEY|CLIENT_SECRET|API_SECRET|JWT_SECRET)\b"),
        True,
    ),
    Rule(
        "AUTH-STATIC-012", "MEDIUM", "Privileged field appears to be assigned directly from request input",
        "Direct assignment of role/tenant/owner/security fields can create mass-assignment or privilege-escalation bugs.",
        re.compile(r"(?i)\b(?:role|roles|permission|permissions|isAdmin|is_admin|tenantId|tenant_id|ownerId|owner_id|verified|isVerified|is_verified)\b\s*[:=]\s*(?:req\.(?:body|query|params)|request\.(?:json|form|args)|params\[|data\[|body\.)"),
    ),
    Rule(
        "AUTH-STATIC-013", "HIGH", "Wildcard CORS origin combined with credentialed requests",
        "Credentialed cross-origin access must not trust every origin.",
        re.compile(r"(?is)(?:origin\s*:\s*['\"]\*['\"][^\n]{0,300}credentials\s*:\s*true|credentials\s*:\s*true[^\n]{0,300}origin\s*:\s*['\"]\*['\"])"),
    ),
    Rule(
        "AUTH-STATIC-014", "MEDIUM", "Authorization/CSRF control appears explicitly disabled",
        "Disabling an auth boundary requires architecture-specific justification and compensating controls.",
        re.compile(r"(?i)\b(?:csrf|authorization|authorize|authentication|auth)\b[^\n]{0,100}\b(?:disable|disabled|false|skip|bypass)\b"),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heuristic static audit for Stage 07 auth controls")
    parser.add_argument("project_root", help="Project root to scan")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="Write report to this path; stdout if omitted")
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    parser.add_argument("--fail-on", choices=("none", "medium", "high"), default="none")
    return parser.parse_args()


def iter_files(root: Path, max_file_bytes: int) -> Iterable[Path]:
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".cache")]
        base = Path(current_root)
        for name in files:
            path = base / name
            suffix = path.suffix.lower()
            if suffix not in TEXT_EXTENSIONS and not name.startswith(".env"):
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            yield path


def redact_excerpt(line: str, secret_bearing: bool) -> str:
    text = line.strip().replace("\t", " ")
    text = re.sub(r"(?i)(authorization\s*[:=]\s*['\"]?bearer\s+)[^'\"\s]+", r"\1<REDACTED>", text)
    text = re.sub(r"(?i)((?:password|passwd|secret|token|api[_-]?key|client[_-]?secret)\s*[:=]\s*['\"])[^'\"]+(['\"])", r"\1<REDACTED>\2", text)
    text = re.sub(r"(?i)([?&](?:access_token|refresh_token|auth_token|token|jwt|api_key|apikey)=)[^&\s'\"]+", r"\1<REDACTED>", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b", "<JWT_REDACTED>", text)
    if secret_bearing:
        text = re.sub(r"(['\"])[A-Za-z0-9_./+=:@$!%*?#-]{6,}\1", r"\1<REDACTED>\1", text)
    if len(text) > 240:
        text = text[:237] + "..."
    return text


def scan_file(root: Path, path: Path) -> list[Finding]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rel = path.relative_to(root).as_posix()
    findings: list[Finding] = []
    lines = raw.splitlines()
    for idx, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith(("#", "//", "/*", "*")):
            continue
        for rule in RULES:
            if rule.pattern.search(line):
                findings.append(Finding(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    title=rule.title,
                    rationale=rule.rationale,
                    file=rel,
                    line=idx,
                    excerpt=redact_excerpt(line, rule.secret_bearing),
                ))
    return findings


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, int]] = set()
    result: list[Finding] = []
    for finding in findings:
        key = (finding.rule_id, finding.file, finding.line)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    result.sort(key=lambda f: (-SEVERITY_RANK[f.severity], f.file, f.line, f.rule_id))
    return result


def render_json(root: Path, scanned_files: int, findings: list[Finding]) -> str:
    counts = {severity: 0 for severity in SEVERITY_RANK}
    for finding in findings:
        counts[finding.severity] += 1
    payload = {
        "tool": "auth_security_audit.py",
        "scope": str(root),
        "scanned_files": scanned_files,
        "summary": counts,
        "finding_count": len(findings),
        "findings": [asdict(f) for f in findings],
        "interpretation": "Heuristic findings require manual review. This report does not replace executable auth tests or code review.",
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_markdown(root: Path, scanned_files: int, findings: list[Finding]) -> str:
    counts = {severity: 0 for severity in SEVERITY_RANK}
    for finding in findings:
        counts[finding.severity] += 1
    out = [
        "# Stage 07 Static Auth Audit",
        "",
        f"Scanned root: `{root}`",
        f"Scanned files: {scanned_files}",
        "",
        "## Summary",
        "",
        f"- HIGH: {counts['HIGH']}",
        f"- MEDIUM: {counts['MEDIUM']}",
        f"- LOW: {counts['LOW']}",
        f"- INFO: {counts['INFO']}",
        "",
        "Heuristic findings require manual review. This report does not replace executable auth tests or code review.",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        out.append("No matching heuristic findings.")
    for f in findings:
        out.extend([
            f"### {f.severity} - {f.rule_id} - {f.title}",
            "",
            f"- Location: `{f.file}:{f.line}`",
            f"- Excerpt: `{f.excerpt.replace(chr(96), chr(39))}`",
            f"- Review: {f.rationale}",
            "",
        ])
    return "\n".join(out).rstrip() + "\n"


def should_fail(findings: list[Finding], fail_on: str) -> bool:
    if fail_on == "none":
        return False
    threshold = SEVERITY_RANK[fail_on.upper()]
    return any(SEVERITY_RANK[f.severity] >= threshold for f in findings)


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: project root is not a directory: {root}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    scanned_files = 0
    for path in iter_files(root, args.max_file_bytes):
        scanned_files += 1
        findings.extend(scan_file(root, path))
    findings = dedupe(findings)

    report = render_json(root, scanned_files, findings) if args.format == "json" else render_markdown(root, scanned_files, findings)
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    return 3 if should_fail(findings, args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
