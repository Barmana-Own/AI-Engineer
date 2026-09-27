#!/usr/bin/env python3
"""Heuristically identify mock/fake code that may be production reachable.

The scanner is intentionally conservative: it reports candidates and excludes common
test/dev fixture locations. A candidate is not automatically a defect. By default the
script exits 0 when candidates exist; use --fail-on-candidate for CI-style gating after
manual tuning/inspection.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", ".next", ".nuxt", ".output", "node_modules", "vendor", "dist", "build",
    "coverage", "out", "target", "tests", "test", "__tests__", "spec", "specs",
    "fixtures", "fixture", "mocks", "mock", "storybook", ".storybook", "stories",
    "docs", ".cache", ".turbo", ".venv", "venv",
}

SOURCE_SUFFIXES = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".py", ".go", ".java", ".kt",
    ".cs", ".php", ".rb", ".rs", ".vue", ".svelte",
}

PATTERNS = [
    ("mock-mode-flag", re.compile(r"\b(?:USE_MOCKS?|MOCK_API|MOCK_MODE|ENABLE_MOCKS?)\b", re.I)),
    ("mock-import", re.compile(r"(?:from|require\s*\()\s*['\"][^'\"]*(?:/mock(?:s)?/|/fixture(?:s)?/)", re.I)),
    ("fake-repository", re.compile(r"\b(?:Fake|Mock|InMemory)(?:\w*)Repository\b")),
    ("msw-production-start", re.compile(r"\b(?:worker\.start|setupWorker\s*\()", re.I)),
    ("json-server", re.compile(r"\bjson-server\b", re.I)),
    ("hardcoded-mock-service", re.compile(r"\b(?:mock|fake)(?:Api|Service|Client)\b", re.I)),
]


def should_skip(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    lowered = {part.lower() for part in rel_parts[:-1]}
    return any(part in EXCLUDED_DIRS for part in lowered)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--fail-on-candidate", action="store_true")
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2

    findings: list[tuple[str, int, str]] = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDED_DIRS]
        base = Path(dirpath)
        for name in filenames:
            path = base / name
            if path.suffix.lower() not in SOURCE_SUFFIXES or should_skip(path, root):
                continue
            try:
                if path.stat().st_size > args.max_file_bytes:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            scanned += 1
            for lineno, line in enumerate(text.splitlines(), 1):
                if "test" in path.name.lower() or "spec" in path.name.lower() or "story" in path.name.lower():
                    continue
                for label, pattern in PATTERNS:
                    if pattern.search(line):
                        findings.append((str(path.relative_to(root)), lineno, label))

    print(f"Scanned source files: {scanned}")
    if not findings:
        print("No heuristic production-mock candidates found")
        return 0

    print(f"Candidates: {len(findings)}")
    for rel, lineno, label in findings:
        print(f"{rel}:{lineno}: {label}")

    print("NOTE: candidates require manual reachability inspection; test/dev-isolated mocks are valid")
    return 1 if args.fail_on_candidate else 0


if __name__ == "__main__":
    raise SystemExit(main())
