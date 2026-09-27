"""Read-only compatibility view for skills that expect ``project-state.json``.

The view is generated from the existing SQLite persistence layer.  It is not a
second workflow store and it never accepts state transitions from a skill.
Writing the rendered JSON, when a caller needs a file for a validator, remains
an explicit caller operation behind the normal Local Agent policy boundary.
"""

from __future__ import annotations

import json
from typing import Any

from app import db


COMPATIBILITY_SCHEMA_VERSION = "1.0"


def build_project_state_view(project_id: str) -> dict[str, Any]:
    """Build a bounded Stage State view from authoritative database records."""

    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id is required")
    project = db.get_project(project_id)
    if project is None:
        raise ValueError(f"Unknown project: {project_id}")
    tasks = db.list_tasks(project_id)
    runs = db.list_autonomy_runs(project_id, limit=100)
    return {
        "schema_version": COMPATIBILITY_SCHEMA_VERSION,
        "state_view": "compatibility",
        "authoritative_store": "orchestrator_database",
        "project": project,
        "tasks": tasks,
        "autonomy_runs": runs,
        "read_only": True,
    }


def render_project_state_view(project_id: str) -> str:
    """Serialize a compatibility view without mutating the database."""

    return json.dumps(
        build_project_state_view(project_id),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

