#!/usr/bin/env python3
"""Heuristic static scanner for risky migration operations.

This does not prove migration safety; it surfaces statements/patterns requiring review.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERNS = [
    ("HIGH", r"\bDROP\s+TABLE\b", "drops a table"),
    ("HIGH", r"\bDROP\s+COLUMN\b", "drops a column"),
    ("HIGH", r"\bTRUNCATE\b", "truncates data"),
    ("HIGH", r"\.dropTable\s*\(", "ORM drops a table"),
    ("HIGH", r"\.dropColumn\s*\(", "ORM drops a column"),
    ("MEDIUM", r"\bALTER\s+TABLE\b", "table alteration may lock/rewrite data"),
    ("MEDIUM", r"\bSET\s+NOT\s+NULL\b", "tightens nullability"),
    ("MEDIUM", r"\bADD\s+(?:CONSTRAINT\s+\S+\s+)?UNIQUE\b", "adds uniqueness; existing duplicates must be checked"),
    ("MEDIUM", r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b", "index creation may be expensive/locking"),
    ("MEDIUM", r"\.renameColumn\s*\(", "column rename may break old application versions"),
    ("MEDIUM", r"\.alter\s*\(", "ORM column alteration may rewrite/lock"),
    ("LOW", r"\bDELETE\s+FROM\b", "data deletion in migration"),
    ("LOW", r"\bUPDATE\b.+\bSET\b", "data backfill/update requires restartability/volume review"),
]

EXTENSIONS = {".sql", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".rb", ".php", ".go", ".java", ".kt"}


def iter_files(paths: list[Path]):
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in EXTENSIONS:
                    yield candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Migration file(s) or directories")
    args = parser.parse_args()

    total = 0
    high = 0
    for file_path in iter_files([Path(p) for p in args.paths]):
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"WARN {file_path}: {exc}")
            continue
        for severity, pattern, message in PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                line = text.count("\n", 0, match.start()) + 1
                snippet = re.sub(r"\s+", " ", match.group(0))[:100]
                print(f"{severity}: {file_path}:{line}: {message}: {snippet}")
                total += 1
                if severity == "HIGH":
                    high += 1

    print(f"SUMMARY: {total} review finding(s), {high} HIGH.")
    return 3 if high else 0


if __name__ == "__main__":
    sys.exit(main())
