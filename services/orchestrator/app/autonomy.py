"""Bounded autonomous self-improvement cycles.

The supervisor deliberately creates ordinary Agent tasks. This keeps the
existing checkpoint, policy, validation, and recovery guarantees in one place
while adding a controlled way for the project to choose and complete its next
improvement without a new user prompt on every cycle.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.db import (
    create_autonomy_run,
    create_project,
    create_task,
    get_autonomy_run,
    get_project,
    get_task,
    list_autonomy_runs,
    list_projects,
    list_tasks,
    search_memories,
    update_task,
    update_autonomy_run,
)
from app.config import settings
from app.subagents import build_role_instruction, configured_subagent_roles

MAX_MEMORY_CONTEXT_CHARS = 4_000
RECONCILIATION_GRACE_SECONDS = 300


@dataclass(frozen=True)
class AutonomousBacklogItem:
    """One concrete, project-relative improvement the supervisor can pursue."""

    key: str
    target: str
    goal: str
    validation: str


# The supervisor must have an actionable queue instead of asking a small local
# model to rediscover the same generic README edit on every wake-up.  Targets
# are deliberately limited to the orchestrator's own source and its tests.
AUTONOMOUS_BACKLOG: tuple[AutonomousBacklogItem, ...] = (
    AutonomousBacklogItem(
        key="supervisor-resume",
        target="services/orchestrator/app/autonomy.py",
        goal="Improve restart-safe supervisor resume and stale-run reconciliation without changing the public API.",
        validation="python -m compileall -q services/orchestrator/app",
    ),
    AutonomousBacklogItem(
        key="task-observability",
        target="services/orchestrator/app/routers/agent.py",
        goal="Improve autonomous task and run observability while preserving existing response contracts.",
        validation="python -m compileall -q services/orchestrator/app",
    ),
    AutonomousBacklogItem(
        key="memory-safety",
        target="services/orchestrator/app/db.py",
        goal="Improve bounded autonomous memory persistence or compaction without changing stored secrets.",
        validation="python -m compileall -q services/orchestrator/app",
    ),
    AutonomousBacklogItem(
        key="role-contracts",
        target="services/orchestrator/app/subagents.py",
        goal="Improve specialist role contracts or status reporting so later agents can act on concrete evidence.",
        validation="python -m compileall -q services/orchestrator/app",
    ),
)


def select_autonomous_backlog_item(project_id: str) -> AutonomousBacklogItem:
    """Select a rotating concrete item, preferring work not recently changed."""
    memories = search_memories(project_id, limit=80)
    changed_files: set[str] = set()
    for memory in memories:
        detail = memory.get("detail")
        if not isinstance(detail, dict):
            continue
        for path in detail.get("changed_files") or []:
            changed_files.add(str(path).replace("\\", "/").casefold())

    untouched = [
        item for item in AUTONOMOUS_BACKLOG
        if item.target.casefold() not in changed_files
    ]
    candidates = untouched or list(AUTONOMOUS_BACKLOG)
    # A persisted memory count gives the queue a deterministic cursor across
    # process restarts without adding another database migration.
    cursor = len(memories) % len(candidates)
    return candidates[cursor]


def build_backlog_goal(item: AutonomousBacklogItem) -> str:
    """Render an explicit target/validation contract for all sub-agents."""
    return (
        f"BACKLOG_KEY: {item.key}\n"
        f"TARGET FILE: {item.target}\n"
        f"VALIDATION COMMAND: {item.validation}\n"
        f"Implement one small, evidence-based code change. {item.goal}"
    )


def _bounded_memory_text(memories: list[dict[str, object]]) -> str:
    """Keep episodic memory useful without allowing prompt-size amplification."""
    compact: list[dict[str, object]] = []
    for memory in memories[:6]:
        detail = memory.get("detail")
        compact_detail: dict[str, object] = {}
        if isinstance(detail, dict):
            for key in ("status", "mode", "step_count", "changed_files", "validations", "failures"):
                if key in detail:
                    value = detail[key]
                    if isinstance(value, list):
                        compact_detail[key] = [str(item)[:500] for item in value[:20]]
                    else:
                        compact_detail[key] = str(value)[:1_200]
        raw_summary = str(memory.get("summary") or "").strip()
        if "model failed" in raw_summary.casefold():
            raw_summary = "Previous autonomous attempt failed; use current observations and choose a different action."
        compact.append({
            "kind": str(memory.get("kind") or "memory"),
            "summary": raw_summary[:320],
            "detail": compact_detail,
        })

    text = json.dumps(compact, ensure_ascii=False, indent=2)
    if len(text) <= MAX_MEMORY_CONTEXT_CHARS:
        return text
    return text[:MAX_MEMORY_CONTEXT_CHARS] + "\n[older memory truncated]"


def build_cycle_instruction(
    goal: str,
    cycle: int,
    total_cycles: int,
    memories: list[dict[str, object]],
) -> str:
    memory_text = _bounded_memory_text(memories)
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


def _record_age_seconds(value: object) -> float:
    """Return the age of a persisted record without trusting local timezone."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return float(RECONCILIATION_GRACE_SECONDS + 1)
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


async def run_autonomous_cycles(run_id: str) -> None:
    """Run a finite, sequential specialist pipeline and persist its progress."""
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

    roles = configured_subagent_roles(settings.autonomous_subagents)
    roles = roles[: max(int(settings.autonomous_max_subagents), 1)]

    try:
        for cycle in range(1, int(run["requested_cycles"]) + 1):
            for role in roles:
                memories = search_memories(
                    run["project_id"],
                    query=f"{run['goal']} {role.key}",
                    limit=6,
                )
                memory_text = _bounded_memory_text(memories)
                instruction = build_role_instruction(
                    role=role,
                    goal=str(run["goal"]),
                    cycle=cycle,
                    total_cycles=int(run["requested_cycles"]),
                    memory_text=memory_text,
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
                        error=(finished or {}).get("error")
                        or f"{role.key} sub-agent did not complete.",
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
        projects = list_projects()
        if target_workspace and not any(
            project["workspace"].casefold() == target_workspace
            for project in projects
        ):
            create_project(
                name="AI Engineer",
                workspace=str(settings.autonomous_workspace).strip(),
            )
            projects = list_projects()

        for project in projects:
            if target_workspace and project["workspace"].casefold() != target_workspace:
                continue

            project_tasks = list_tasks(project["id"])
            active_tasks = [
                task for task in project_tasks
                if task.get("mode") == "autonomous"
                and task.get("status") in active_statuses
            ]
            # A task left active by a dead worker must not block the next run,
            # but a recently updated task may still belong to a worker that is
            # finishing during a restart.  Use a grace period to avoid killing
            # healthy work or creating duplicate runs.
            for task in active_tasks:
                if _record_age_seconds(task.get("updated_at")) < RECONCILIATION_GRACE_SECONDS:
                    continue
                update_task(
                    task["id"],
                    status="failed",
                    error="Reconciled after restart before a new autonomous cycle.",
                )

            remaining_active_tasks = [
                task for task in list_tasks(project["id"])
                if task.get("mode") == "autonomous"
                and task.get("status") in active_statuses
            ]
            if remaining_active_tasks:
                continue

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
                if _record_age_seconds(run.get("updated_at")) < RECONCILIATION_GRACE_SECONDS:
                    continue
                update_autonomy_run(
                    run["id"],
                    status="failed",
                    error="Reconciled after restart: no active autonomous task was found.",
                )

            open_runs = list_autonomy_runs(project["id"], limit=100)
            if any(run["status"] in {"queued", "running"} for run in open_runs):
                continue

            backlog_item = select_autonomous_backlog_item(project["id"])
            run = create_autonomy_run(
                project_id=project["id"],
                goal=build_backlog_goal(backlog_item),
                requested_cycles=max(int(settings.autonomous_cycles_per_run), 1),
            )
            await run_autonomous_cycles(run["id"])

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
