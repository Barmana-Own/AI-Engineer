"""Bounded autonomous self-improvement cycles.

The supervisor deliberately creates ordinary Agent tasks. This keeps the
existing checkpoint, policy, validation, and recovery guarantees in one place
while adding a controlled way for the project to choose and complete its next
improvement without a new user prompt on every cycle.
"""

from __future__ import annotations

import asyncio
import json

from app.db import (
    create_autonomy_run,
    create_task,
    get_autonomy_run,
    get_project,
    get_task,
    list_projects,
    list_tasks,
    search_memories,
    update_autonomy_run,
)
from app.config import settings


def build_cycle_instruction(
    goal: str,
    cycle: int,
    total_cycles: int,
    memories: list[dict[str, object]],
) -> str:
    memory_text = json.dumps(memories[:6], ensure_ascii=False, indent=2)
    return f"""
You are running bounded autonomous self-improvement cycle {cycle}/{total_cycles}.

PRIMARY GOAL:
{goal.strip()}

OPERATING CONTRACT:
- Inspect the existing project before deciding what to change.
- Choose exactly one small, high-value, coherent improvement that is supported by evidence.
- Read every target file before editing it.
- Create/use the Git checkpoint before the first file mutation.
- Prefer a small apply_patch or replace_text edit; do not rewrite unrelated files.
- Do not install packages, access secrets, change the operating system, delete data,
  rollback Git, or publish/deploy anything.
- Run the project's real validation command after the repair and fix a failure once
  using the observed error. Stop if the failure is not safely repairable.
- Finish only after the change has a non-empty diff and validation passes.
- Record useful facts from this cycle so a later cycle can avoid repeating failures.

LEARNED PROJECT MEMORY FROM PREVIOUS CYCLES:
{memory_text}

This is an autonomous mode task. File mutations may be auto-approved only after
the normal checkpoint and target-read guards. Terminal/process/destructive actions
remain policy-controlled.
""".strip()


async def run_autonomous_cycles(run_id: str) -> None:
    """Run a finite sequence of self-improvement tasks and persist its progress."""
    from app.agent_service import run_agent_task

    run = get_autonomy_run(run_id)
    if not run:
        return

    project = get_project(run["project_id"])
    if not project:
        update_autonomy_run(
            run_id,
            status="failed",
            error="Project not found.",
        )
        return

    task_ids = list(run.get("task_ids") or [])
    update_autonomy_run(run_id, status="running", error=None)

    try:
        for cycle in range(1, int(run["requested_cycles"]) + 1):
            memories = search_memories(run["project_id"], limit=6)
            instruction = build_cycle_instruction(
                str(run["goal"]),
                cycle,
                int(run["requested_cycles"]),
                memories,
            )
            task = create_task(
                project_id=run["project_id"],
                instruction=instruction,
                mode="autonomous",
            )
            task_ids.append(task["id"])
            update_autonomy_run(
                run_id,
                task_ids=task_ids,
                completed_cycles=cycle - 1,
            )

            await run_agent_task(task["id"])
            finished = get_task(task["id"])
            if not finished or finished["status"] != "completed":
                update_autonomy_run(
                    run_id,
                    task_ids=task_ids,
                    completed_cycles=cycle - 1,
                    status="failed",
                    error=(finished or {}).get("error") or "Autonomous cycle did not complete.",
                )
                return

            update_autonomy_run(
                run_id,
                task_ids=task_ids,
                completed_cycles=cycle,
            )

        update_autonomy_run(
            run_id,
            task_ids=task_ids,
            completed_cycles=int(run["requested_cycles"]),
            status="completed",
            error=None,
        )
    except Exception as exc:
        update_autonomy_run(
            run_id,
            task_ids=task_ids,
            status="failed",
            error=str(exc),
        )


async def run_autonomy_scheduler(stop_event: asyncio.Event) -> None:
    """Wake periodically for the configured workspace and reconcile stale workers."""
    interval_seconds = max(int(settings.autonomous_interval_minutes), 1) * 60
    target_workspace = str(settings.autonomous_workspace or "").strip().casefold()
    active_statuses = {"queued", "planning", "running", "awaiting_approval"}

    while not stop_event.is_set():
        for project in list_projects():
            if target_workspace and project["workspace"].casefold() != target_workspace:
                continue

            project_tasks = list_tasks(project["id"])
            active_tasks = [
                task for task in project_tasks
                if task.get("mode") == "autonomous"
                and task.get("status") in active_statuses
            ]
            # A task left active by a dead worker must not block the next run.
            for task in active_tasks:
                update_task(
                    task["id"],
                    status="failed",
                    error="Reconciled after restart before a new autonomous cycle.",
                )

            # Re-read after task reconciliation so the run that owned the stale
            # task is closed before a fresh cycle is created.
            open_runs = list_autonomy_runs(project["id"], limit=100)
            active_ids = {
                task["id"]
                for task in list_tasks(project["id"])
                if task.get("mode") == "autonomous"
                and task.get("status") in active_statuses
            }
            for run in open_runs:
                if run["status"] not in {"queued", "running"}:
                    continue
                if active_ids.intersection(set(run.get("task_ids") or [])):
                    continue
                update_autonomy_run(
                    run["id"],
                    status="failed",
                    error="Reconciled after restart: no active autonomous task was found.",
                )

            open_runs = list_autonomy_runs(project["id"], limit=100)
            if any(run["status"] in {"queued", "running"} for run in open_runs):
                continue

            run = create_autonomy_run(
                project_id=project["id"],
                goal="Inspect the project and complete the highest-value safe improvement.",
                requested_cycles=max(int(settings.autonomous_cycles_per_run), 1),
            )
            await run_autonomous_cycles(run["id"])

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue