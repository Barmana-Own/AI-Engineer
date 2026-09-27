#!/usr/bin/env python3
"""Static Stage 05 artifact completeness checks.

The script is intentionally framework-agnostic and does not replace migration or integration tests.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_HEADINGS = [
    "# Stage 05 - Database Architecture",
    "## Inputs and Stage 04 traceability",
    "## Invariant and constraint matrix",
    "## Index and query-path matrix",
    "## Transaction boundaries",
    "## Concurrency and idempotency controls",
    "## Migration plan and recovery strategy",
    "## Persistence adapter coverage",
    "## Validation evidence",
    "## Stage 06 handoff",
    "## Quality-gate result",
]

MIGRATION_HINTS = ("migration", "migrations", "alembic", "prisma", "drizzle", "typeorm", "sequelize", "knex", "flyway", "liquibase")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    failures: list[str] = []
    warnings: list[str] = []

    doc = root / "docs" / "05-database-architecture.md"
    if not doc.exists():
        failures.append(f"missing {doc}")
    else:
        text = doc.read_text(encoding="utf-8", errors="replace")
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                failures.append(f"documentation missing heading: {heading}")

    state = root / "project-state.json"
    if not state.exists():
        warnings.append("project-state.json missing; verify repository uses another authoritative state mechanism")
    else:
        try:
            json.loads(state.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"project-state.json is invalid JSON: {exc}")

    migration_files = []
    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue
        lowered_parts = [p.lower() for p in candidate.parts]
        if any(any(hint in part for hint in MIGRATION_HINTS) for part in lowered_parts):
            if candidate.suffix.lower() in {".sql", ".py", ".js", ".ts", ".rb", ".php", ".json"}:
                migration_files.append(candidate)
    if not migration_files:
        warnings.append("no migration-like files detected; confirm project convention or database-first exception")

    for warning in warnings:
        print("WARN:", warning)
    for failure in failures:
        print("FAIL:", failure)
    if failures:
        print(f"SUMMARY: {len(failures)} failure(s), {len(warnings)} warning(s).")
        return 1
    print(f"PASS: static artifact checks complete with {len(warnings)} warning(s); runtime validation is still required by the skill.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
