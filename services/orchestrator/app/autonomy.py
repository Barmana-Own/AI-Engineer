"""Bounded autonomous self-improvement cycles.

The supervisor deliberately creates ordinary Agent tasks. This keeps the
existing checkpoint, policy, validation, and recovery guarantees in one place
while adding a controlled way for the project to choose and complete its next
improvement without a new user prompt on every cycle.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.db import (
    create_autonomy_run,
    create_project,
    create_task,
    create_subagent_handoff,
    get_autonomy_run,
    get_project,
    get_subagent_handoff,
    get_task,
    list_autonomy_runs,
    list_projects,
    list_tasks,
    update_subagent_handoff,
    search_memories,
    update_task,
    update_autonomy_run,
)
from app.config import settings
from app.memory import MemoryStore
from app.subagents import SUBAGENT_ROLES, build_execution_phases, build_role_instruction, configured_subagent_roles
from app.self_improvement import SelfImprovementEngine
from app.recovery import (
    WAITING_TASK_STATUSES,
    pause_task_for_dependency,
    recover_incomplete_runs,
    record_run_heartbeat,
    requeue_waiting_task,
)

MAX_MEMORY_CONTEXT_CHARS = 4_000
RECONCILIATION_GRACE_SECONDS = 300
logger = logging.getLogger(__name__)

EXPECTED_GITHUB_REMOTE = "https://github.com/Barmana-Own/AI-Engineer.git"


def _normalise_git_remote(value: str) -> str:
    """Compare HTTPS and SSH spellings without ever logging credentials."""
    remote = value.strip().rstrip("/")
    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.split(":", 1)[1]
    if remote.endswith(".git"):
        remote = remote[:-4]
    return remote.casefold()


def _task_changed_paths(task_ids: list[str]) -> set[str]:
    """Collect mutation paths produced by this run, excluding model prose."""
    paths: set[str] = set()
    mutation_tools = {"write_file", "replace_text", "apply_patch"}
    for task_id in task_ids:
        task = get_task(task_id)
        if not task:
            continue
        for record in task.get("results") or []:
            step = record.get("step") or {}
            outcome = record.get("outcome") or {}
            tool = str(outcome.get("tool") or step.get("tool") or "").casefold()
            if not outcome.get("ok") or tool not in mutation_tools:
                continue
            result = outcome.get("result") or {}
            raw_path = str(result.get("path") or "").replace("\\", "/").strip("/")
            if raw_path and not raw_path.startswith(("/", "./")) and ":" not in raw_path:
                paths.add(raw_path.casefold())
    return paths


def _run_has_successful_validation(task_ids: list[str]) -> bool:
    """Require a successful validation after a mutation before publishing."""
    mutation_tools = {"write_file", "replace_text", "apply_patch"}
    mutation_seen = False
    for task_id in task_ids:
        task = get_task(task_id)
        if not task:
            continue
        for record in task.get("results") or []:
            step = record.get("step") or {}
            outcome = record.get("outcome") or {}
            tool = str(outcome.get("tool") or step.get("tool") or "").casefold()
            if not outcome.get("ok"):
                continue
            if tool in mutation_tools:
                mutation_seen = True
            elif mutation_seen and tool == "run_terminal":
                return True
    return False

def _working_tree_paths(status_text: str) -> set[str]:
    """Extract paths from porcelain output without exposing file contents."""
    paths: set[str] = set()
    for line in status_text.splitlines():
        value = line[3:] if len(line) >= 4 else line
        if " -> " in value:
            value = value.rsplit(" -> ", 1)[-1]
        value = value.strip().replace("\\", "/").strip("/")
        if value:
            paths.add(value.casefold())
    return paths


def _push_verified_checkpoint(
    allowed_paths: set[str] | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    """Report the local-only policy for autonomous cycles.

    Autonomous cycles may create local checkpoints, but remote commits and pushes
    are intentionally unavailable from the scheduler. Explicit human-reviewed
    release workflows remain responsible for publication.
    """
    if not allowed_paths:
        return {"pushed": False, "reason": "no verified changes"}
    return {"pushed": False, "reason": "automatic remote push disabled by safety policy"}


@dataclass(frozen=True)
class AutonomousBacklogItem:
    """One concrete, project-relative improvement the supervisor can pursue."""

    key: str
    target: str
    goal: str
    validation: str
    section: str = "orchestrator"


# The supervisor must have an actionable queue instead of asking a small local
# model to rediscover the same generic README edit on every wake-up.  Targets
# are deliberately limited to the orchestrator's own source and its tests.
AUTONOMOUS_BACKLOG: tuple[AutonomousBacklogItem, ...] = (
    AutonomousBacklogItem(
        key="supervisor-resume",
        target="services/orchestrator/app/autonomy.py",
        goal="Improve restart-safe supervisor resume and stale-run reconciliation without changing the public API.",
        validation="python -m compileall -q services/orchestrator/app",
        section="orchestrator",
    ),
    AutonomousBacklogItem(
        key="task-observability",
        target="services/orchestrator/app/routers/agent.py",
        goal="Improve autonomous task and run observability while preserving existing response contracts.",
        validation="python -m compileall -q services/orchestrator/app",
        section="orchestrator",
    ),
    AutonomousBacklogItem(
        key="memory-safety",
        target="services/orchestrator/app/db.py",
        goal="Improve bounded autonomous memory persistence or compaction without changing stored secrets.",
        validation="python -m compileall -q services/orchestrator/app",
        section="orchestrator",
    ),
    AutonomousBacklogItem(
        key="role-contracts",
        target="services/orchestrator/app/subagents.py",
        goal="Improve specialist role contracts or status reporting so later agents can act on concrete evidence.",
        validation="python -m compileall -q services/orchestrator/app",
        section="architecture",
    ),
    AutonomousBacklogItem(
        key="gateway-routing",
        target="services/model-gateway/app/router.py",
        goal="Inspect provider routing and runtime model health, then make one safe contract-preserving improvement.",
        validation="python -m pytest -q services/model-gateway/tests",
        section="model-gateway",
    ),
    AutonomousBacklogItem(
        key="local-agent-policy",
        target="services/local-agent/app/main.py",
        goal="Inspect local execution boundaries and improve one safe filesystem, terminal, or process policy contract.",
        validation="python -m compileall -q services/local-agent/app",
        section="local-agent",
    ),
    AutonomousBacklogItem(
        key="control-center-observability",
        target="apps/control-center/src/api.ts",
        goal="Improve typed polling or specialist observability in the control center without changing the backend contract unexpectedly.",
        validation="npm run build",
        section="control-center",
    ),
    AutonomousBacklogItem(
        key="desktop-health",
        target="apps/desktop/src/App.tsx",
        goal="Improve desktop service health visibility while preserving the local app startup contract.",
        validation="npm run build",
        section="desktop",
    ),
    AutonomousBacklogItem(
        key="test-coverage",
        target="services/orchestrator/tests/test_autonomous_backlog.py",
        goal="Add a focused regression test for the specialist handoff or autonomous scheduler contract.",
        validation="python -m unittest discover -s services/orchestrator/tests -q",
        section="tests",
    ),
    AutonomousBacklogItem(
        key="requirements-contract",
        target="services/orchestrator/app/schemas.py",
        goal="Keep the typed task, handoff, and acceptance contracts explicit so requirement changes remain observable and bounded.",
        validation="python -m compileall -q services/orchestrator/app",
        section="product",
    ),
    AutonomousBacklogItem(
        key="security-boundary",
        target="services/orchestrator/app/agent_service.py",
        goal="Review path, command, checkpoint, and validation guards for one narrowly scoped security hardening that preserves safe execution.",
        validation="python -m compileall -q services/orchestrator/app",
        section="security",
    ),
    AutonomousBacklogItem(
        key="recovery-coverage",
        target="services/orchestrator/tests/test_subagents.py",
        goal="Add one deterministic regression test for bounded recovery, validation, or specialist handoff behavior.",
        validation="python -m unittest discover -s services/orchestrator/tests -q",
        section="recovery",
    ),
    AutonomousBacklogItem(
        key="operations-docs",
        target="README.md",
        goal="Keep local operation, offline Ollama behavior, and autonomous supervisor recovery instructions accurate and concise.",
        validation="python -c \"from pathlib import Path; assert Path('README.md').read_text(encoding='utf-8').strip()\"",
        section="docs",
    ),
    AutonomousBacklogItem(
        key="integration-health",
        target="services/orchestrator/app/main.py",
        goal="Improve the cross-service health and startup contract without changing service ports or opening the UI during supervisor runs.",
        validation="python -m compileall -q services/orchestrator/app",
        section="integration",
    ),
)


def select_autonomous_backlog_item(project_id: str) -> AutonomousBacklogItem:
    """Select the oldest uncompleted target instead of repeating no-op work.

    Task memories contain one record per specialist, so using their bounded
    window as a cursor can count the same target several times and pin the
    selector on a small subset of the backlog.  The persisted autonomy-run
    goals are one record per target attempt and provide a stable fairness
    signal across restarts.  Memories remain the fallback for isolated unit
    tests and older databases that predate autonomy-run persistence.
    """
    memories = search_memories(project_id, limit=50)
    changed_files: set[str] = set()
    memory_attempted_targets: list[str] = []
    failed_targets: set[str] = set()
    for memory in memories:
        detail = memory.get("detail")
        if not isinstance(detail, dict):
            continue
        for path in detail.get("changed_files") or []:
            changed_files.add(str(path).replace("\\", "/").casefold())
        instruction = str(detail.get("instruction") or "")
        for line in instruction.splitlines():
            if line.strip().casefold().startswith("target file:"):
                target = line.split(":", 1)[1].strip().replace("\\", "/")
                if target:
                    memory_attempted_targets.append(target.casefold())
                    status = str(detail.get("status") or memory.get("kind") or "").casefold()
                    if status == "failed":
                        failed_targets.add(target.casefold())
                break

    run_attempted_targets: list[str] = []
    run_limit = max(len(AUTONOMOUS_BACKLOG) * 4, 50)
    for run in list_autonomy_runs(project_id, limit=run_limit):
        target = ""
        for line in str(run.get("goal") or "").splitlines():
            if line.strip().casefold().startswith("target file:"):
                target = line.split(":", 1)[1].strip().replace("\\", "/").casefold()
                break
        if not target:
            continue
        run_attempted_targets.append(target)
        if str(run.get("status") or "").casefold() == "failed":
            failed_targets.add(target)

    untouched = [
        item for item in AUTONOMOUS_BACKLOG
        if item.target.casefold() not in changed_files
    ]
    retryable = [
        item for item in untouched
        if item.target.casefold() not in failed_targets
    ]
    # Keep failed targets out of the first retry pass, but allow them back into
    # the fairness pool once the other candidates have been attempted. A
    # permanent failure blacklist can starve the backlog after transient model
    # or validation failures.
    fairness_pool = list(AUTONOMOUS_BACKLOG)
    candidates = retryable or fairness_pool

    # One autonomy run represents one target attempt, unlike the many
    # specialist memories generated inside it.  Prefer targets absent from
    # the recent run window; this makes a no-op immediately advance to the
    # next untouched backlog item and survives process restarts.
    attempted_targets = run_attempted_targets or memory_attempted_targets
    recent_targets = set(attempted_targets[: len(AUTONOMOUS_BACKLOG)])
    fresh = [item for item in candidates if item.target.casefold() not in recent_targets]
    if fresh:
        return fresh[0]

    # If the only untouched target has just produced a successful no-op, widen
    # the pool so a previously changed target can receive a new improvement.
    # This prevents a valid but unproductive target from starving the backlog.
    non_recent = [
        item
        for item in fairness_pool
        if item.target.casefold() not in recent_targets
    ]
    if non_recent:
        candidates = non_recent

    # Once every candidate has appeared in the window, choose the least
    # recently attempted item.  Never-used targets sort before old attempts.
    last_seen = {
        target: index
        for index, target in reversed(list(enumerate(attempted_targets)))
    }
    return min(
        candidates,
        key=lambda item: last_seen.get(item.target.casefold(), len(attempted_targets) + 1),
    )

def build_backlog_goal(item: AutonomousBacklogItem) -> str:
    """Render an explicit target/validation contract for all sub-agents."""
    return (
        f"BACKLOG_KEY: {item.key}\n"
        f"SECTION: {item.section}\n"
        f"TARGET FILE: {item.target}\n"
        f"VALIDATION COMMAND: {item.validation}\n"
        f"Implement one small, evidence-based code change. {item.goal}"
    )


def _handoff_payload(task: dict[str, object]) -> dict[str, object]:
    """Extract bounded, tool-backed evidence for the next specialist."""
    changed_files: list[str] = []
    validations: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    failures: list[str] = []
    results = task.get("results") or []
    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        if not isinstance(step, dict) or not isinstance(outcome, dict):
            continue
        tool = str(outcome.get("tool") or step.get("tool") or "")
        arguments = step.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}
        path = str(arguments.get("path") or "").replace("\\", "/").strip()
        if outcome.get("ok") and tool in {"write_file", "replace_text", "apply_patch"} and path:
            if path not in changed_files:
                changed_files.append(path)
        if outcome.get("ok") and tool == "run_terminal":
            command = str(arguments.get("command") or "").strip()
            if command:
                validations.append({
                    "command": command[:1_000],
                    "ok": True,
                    "step_index": item.get("step_index"),
                })
        if outcome.get("ok"):
            observation = str(outcome.get("result") or outcome.get("action") or tool).strip()
            if observation:
                evidence.append({
                    "tool": tool,
                    "step_index": item.get("step_index"),
                    "observation": observation[:1_000],
                })
        elif not outcome.get("approval_required"):
            error = str(outcome.get("error") or "Tool failed.").strip()
            if error and error not in failures:
                failures.append(error[:1_000])
    if task.get("error"):
        failures.append(str(task["error"])[:1_000])
    return {
        "changed_files": changed_files[:50],
        "validations": validations[-20:],
        "evidence": evidence[-20:],
        "blockers": failures[-20:],
    }


def _bounded_handoff_text(handoff_ids: list[str]) -> str:
    """Render the immediate blackboard context for the next specialist."""
    records: list[dict[str, object]] = []
    for handoff_id in handoff_ids[-6:]:
        record = get_subagent_handoff(handoff_id)
        if not record:
            continue
        records.append({
            "role": record["role"],
            "section": record["section"],
            "status": record["status"],
            "summary": str(record.get("summary") or "")[:600],
            "changed_files": list(record.get("changed_files") or [])[:20],
            "validations": list(record.get("validations") or [])[:10],
            "blockers": list(record.get("blockers") or [])[:10],
        })
    if not records:
        return ""
    return json.dumps(records, ensure_ascii=False, indent=2)[:MAX_MEMORY_CONTEXT_CHARS]


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


def _reconciliation_grace_seconds() -> int:
    """Keep the manager from reclaiming a healthy task before its timeout."""
    configured = max(
        int(getattr(settings, "autonomous_reconciliation_grace_seconds", 900)),
        RECONCILIATION_GRACE_SECONDS,
    )
    task_timeout = max(
        int(getattr(settings, "autonomous_task_timeout_seconds", 360)),
        60,
    )
    interval = max(int(getattr(settings, "autonomous_interval_minutes", 3)), 1) * 60
    return max(configured, task_timeout + interval)

def _record_age_seconds(value: object) -> float:
    """Return the age of a persisted record without trusting local timezone."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return float(_reconciliation_grace_seconds() + 1)
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


async def run_autonomous_cycles(run_id: str) -> None:
    """Run bounded specialist phases with one explicit writer barrier.

    Read-only specialists share an immutable snapshot in small concurrent
    batches. Mutation-capable roles always receive their own phase, and no
    later phase starts until every reader in the previous phase has produced a
    persisted handoff. This keeps speedups bounded without allowing concurrent
    workspace writers.
    """
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
    experience_store = MemoryStore()

    configured_roles = configured_subagent_roles(settings.autonomous_subagents)
    section_value = ""
    for line in str(run.get("goal") or "").splitlines():
        if line.strip().casefold().startswith("section:"):
            section_value = line.split(":", 1)[1].strip().casefold()
            break
    generic_role_keys = {"inspector", "planner", "implementer", "verifier", "reviewer", "monitor"}
    section_role = next(
        (
            role
            for role in SUBAGENT_ROLES
            if role.key not in generic_role_keys
            and role.section.casefold() == section_value
        ),
        None,
    )
    # Keep the writer and at least one validation-capable reader inside the
    # bounded role budget. Optional specialists fill remaining slots instead of
    # displacing the safety-critical handoff.
    configured_roles = [role for role in configured_roles if role.key != "monitor"]
    max_roles = max(int(settings.autonomous_max_subagents), 1)
    writers = [role for role in configured_roles if not role.read_only]
    validators = [
        role for role in configured_roles if role.read_only and role.validation_required
    ]
    observers = [
        role
        for role in configured_roles
        if role.read_only and not role.validation_required
    ]
    selected_roles: list[object] = []
    for role in [*writers, *validators]:
        if role.key not in {item.key for item in selected_roles}:
            selected_roles.append(role)
    include_section_specialist = bool(
        getattr(settings, "autonomous_include_section_specialist", False)
    )
    if (
        include_section_specialist
        and section_role
        and len(selected_roles) < max_roles
    ):
        # Keep the safety-critical writer/validator path first. Domain readers
        # are optional evidence and must never displace that path.
        selected_roles.append(section_role)
    for role in observers:
        if len(selected_roles) >= max_roles:
            break
        if role.key not in {item.key for item in selected_roles}:
            selected_roles.append(role)
    roles = selected_roles[:max_roles]
    if not roles:
        roles = configured_subagent_roles("implementer")
    previous_handoff_ids: list[str] = []
    task_timeout = max(
        int(getattr(settings, "autonomous_task_timeout_seconds", 360)),
        60,
    )
    read_parallelism = max(
        int(getattr(settings, "autonomous_read_parallelism", 2)),
        1,
    )

    async def execute_item(item: tuple[object, dict[str, object], dict[str, object]]) -> tuple[
        tuple[object, dict[str, object], dict[str, object]],
        dict[str, object] | None,
        str | None,
    ]:
        role, task, _handoff = item
        task_id = str(task["id"])
    
        try:
            await asyncio.wait_for(
                run_agent_task(task_id),
                timeout=task_timeout,
            )
        except asyncio.TimeoutError:
            pause_task_for_dependency(
                task_id,
                "worker",
                f"Sub-agent exceeded the autonomous timeout of {task_timeout} seconds.",
                run_id=run_id,
                retry_after_seconds=60,
            )
            return (
                item,
                get_task(task_id),
                f"Sub-agent exceeded the autonomous timeout of {task_timeout} seconds.",
            )
        except Exception as exc:
            dependency = getattr(exc, "dependency", None)
            if dependency:
                pause_task_for_dependency(
                    task_id, str(dependency), exc, run_id=run_id
                )
            return item, get_task(task_id), str(exc)
        finished = get_task(task_id)
        if not finished or finished.get("status") != "completed":
            return (
                item,
                finished,
                str((finished or {}).get("error") or f"{role.key} sub-agent did not complete."),
            )
        return item, finished, None

    completed_cycles = 0
    try:
        record_run_heartbeat(
            run_id,
            stage="running",
            ttl_seconds=max(int(getattr(settings, "autonomous_lease_seconds", 600)), 30),
        )
        for cycle in range(1, int(run["requested_cycles"]) + 1):
            record_run_heartbeat(
                run_id,
                stage=f"cycle:{cycle}",
                ttl_seconds=max(int(getattr(settings, "autonomous_lease_seconds", 600)), 30),
            )
            cycle_memories = search_memories(
                run["project_id"],
                query=str(run["goal"]),
                limit=8,
            )
            experience_records = experience_store.retrieve(project_id=run["project_id"], query=str(run["goal"]), role="supervisor", task_type="autonomous", run_id=run_id, limit=8, include_candidate=True)
            if experience_records:
                cycle_memories = [*cycle_memories, *[
                    {"kind": "engineering_experience", "summary": str(item.get("summary") or "")[:500], "detail": {"lifecycle": item.get("lifecycle"), "confidence": item.get("confidence"), "usefulness": item.get("usefulness"), "memory_type": item.get("memory_type"), "content": item.get("content")}}
                    for item in experience_records
                ]]
            cycle_task_ids: list[str] = []
            phases = build_execution_phases(
                roles,
                max_parallel_readers=read_parallelism,
            )
            writer_phase_completed = False
            for phase_index, phase in enumerate(phases, start=1):
                if (
                    writer_phase_completed
                    and not _task_changed_paths(cycle_task_ids)
                    and all(role.read_only for role in phase)
                ):
                    logger.info(
                        "Supervisor skipped post-writer read-only phase %s/%s because no verified mutation occurred.",
                        phase_index,
                        len(phases),
                    )
                    break
                phase_previous_handoffs = list(previous_handoff_ids)
                phase_items: list[tuple[object, dict[str, object], dict[str, object]]] = []
                for role in phase:
                    memories = cycle_memories
                    memory_text = _bounded_memory_text(memories)
                    handoff_text = _bounded_handoff_text(phase_previous_handoffs)
                    if handoff_text:
                        memory_text = f"{memory_text}\n\nIMMEDIATE SPECIALIST HANDOFFS:\n{handoff_text}"
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
                    update_task(
                        task["id"],
                        run_id=run_id,
                        recovery_state="queued",
                    )
                    task_ids.append(task["id"])
                    cycle_task_ids.append(task["id"])
                    handoff = create_subagent_handoff(
                        run_id=run_id,
                        project_id=run["project_id"],
                        task_id=task["id"],
                        role=role.key,
                        section=role.section,
                        status="running",
                        summary=f"{role.title} started for cycle {cycle}, phase {phase_index}.",
                        previous_handoff_ids=phase_previous_handoffs,
                    )
                    phase_items.append((role, task, handoff))

                update_autonomy_run(
                    run_id,
                    task_ids=task_ids,
                    completed_cycles=cycle - 1,
                )
                logger.info(
                    "Supervisor phase %s/%s started for cycle %s with %s role(s); read_parallelism=%s",
                    phase_index,
                    len(phases),
                    cycle,
                    len(phase),
                    read_parallelism,
                )
                if any(not role.read_only for role in phase):
                    writer_phase_completed = True
                outcomes = await asyncio.gather(
                    *(execute_item(item) for item in phase_items)
                )
                phase_failed = False
                writer_failed = False
                validation_failed = False
                for item, finished, problem in outcomes:
                    role, task, handoff = item
                    handoff_id = handoff["id"]
                    previous_handoff_ids.append(handoff_id)
                    if problem:
                        if finished and finished.get("status") in WAITING_TASK_STATUSES:
                            update_subagent_handoff(
                                handoff_id,
                                status="waiting",
                                summary=problem[:4_000],
                                blockers=[problem],
                                next_action="Retry after the dependency lease becomes available.",
                                confidence=0.0,
                            )
                            update_autonomy_run(
                                run_id,
                                task_ids=task_ids,
                                completed_cycles=cycle - 1,
                                status="waiting_dependency",
                                error=problem[:2_000],
                                current_stage="waiting_dependency",
                                recovery_state="waiting_for_dependency",
                            )
                            return
                        phase_failed = True
                        if not role.read_only:
                            writer_failed = True
                        if role.validation_required and role.read_only:
                            validation_failed = True
                        if finished and finished.get("status") not in {"failed", "completed"}:
                            update_task(
                                task["id"],
                                status="failed",
                                error=problem,
                            )
                        elif not finished:
                            update_task(
                                task["id"],
                                status="failed",
                                error=problem,
                            )
                        payload = _handoff_payload(finished or {"error": problem})
                        update_subagent_handoff(
                            handoff_id,
                            status="failed",
                            summary=problem[:4_000],
                            evidence=payload["evidence"],
                            changed_files=payload["changed_files"],
                            validations=payload["validations"],
                            blockers=payload["blockers"] or [problem],
                            next_action="Reconcile the failed phase before starting a writer or later reader phase.",
                            confidence=0.0,
                        )
                        try:
                            experience_store.extract_task_experience(project_id=run["project_id"], run_id=run_id, task_id=str(task["id"]), role=role.key, task_type=role.section, summary=problem, evidence=payload["evidence"], changed_files=payload["changed_files"], validations=[str(item.get("command") or "") for item in payload["validations"]], success=False, failure_reason=problem, retry_count=int((finished or {}).get("retry_count") or 0), model_profile=getattr(role, "model_profile", "balanced"))
                        except Exception:
                            logger.exception("Failed to record autonomous failure experience", extra={"task_id": task.get("id")})
                        continue

                    payload = _handoff_payload(finished)
                    update_subagent_handoff(
                        handoff_id,
                        status="completed",
                        summary=str(finished.get("final_output") or f"{role.title} completed.")[:4_000],
                        evidence=payload["evidence"],
                        changed_files=payload["changed_files"],
                        validations=payload["validations"],
                        blockers=payload["blockers"],
                        next_action="Use this evidence as the input contract for the next specialist phase.",
                        confidence=0.85 if payload["blockers"] == [] else 0.55,
                    )
                    try:
                        experience_store.extract_task_experience(project_id=run["project_id"], run_id=run_id, task_id=str(task["id"]), role=role.key, task_type=role.section, summary=str(finished.get("final_output") or f"{role.title} completed."), evidence=payload["evidence"], changed_files=payload["changed_files"], validations=[str(item.get("command") or "") for item in payload["validations"]], success=True, retry_count=int(finished.get("retry_count") or 0), model_profile=getattr(role, "model_profile", "balanced"), tests_passed=True if role.validation_required else None, review_accepted=True if role.key == "reviewer" else None)
                    except Exception:
                        logger.exception("Failed to record autonomous success experience", extra={"task_id": task.get("id")})

                if phase_failed and writer_failed:
                    error = "The writer specialist failed; later phases were held behind the writer barrier."
                    update_autonomy_run(
                        run_id,
                        task_ids=task_ids,
                        completed_cycles=cycle - 1,
                        status="failed",
                        error=error,
                    )
                    return
                if validation_failed:
                    update_autonomy_run(
                        run_id,
                        task_ids=task_ids,
                        completed_cycles=cycle - 1,
                        status="failed",
                        error="Validation specialist failed; no checkpoint was published.",
                    )
                    return
                if phase_failed:
                    logger.warning(
                        "One or more read-only specialists failed in phase %s/%s; "
                        "continuing with the writer and validation evidence.",
                        phase_index,
                        len(phases),
                    )

            completed_cycles = cycle
            update_autonomy_run(
                run_id,
                task_ids=task_ids,
                completed_cycles=completed_cycles,
            )
            if cycle < int(run["requested_cycles"]) and not _task_changed_paths(cycle_task_ids):
                logger.info(
                    "Supervisor stopped after cycle %s because no verified mutation occurred; "
                    "the next backlog target will be selected on the next wake.",
                    cycle,
                )
                break
        changed_paths = _task_changed_paths(task_ids)
        if changed_paths and not _run_has_successful_validation(task_ids):
            update_autonomy_run(
                run_id,
                task_ids=task_ids,
                completed_cycles=completed_cycles,
                status="failed",
                error="Mutation completed without a successful post-change validation; no checkpoint was published.",
            )
            return
        update_autonomy_run(
            run_id,
            task_ids=task_ids,
            completed_cycles=completed_cycles,
            status="completed",
            error=None,
        )
        push_result = await asyncio.to_thread(
            _push_verified_checkpoint,
            changed_paths,
            run_id,
        )
        if push_result.get("pushed"):
            logger.info(
                "Autonomous checkpoint pushed to GitHub: %s",
                push_result.get("commit", "unknown"),
            )
        elif push_result.get("reason") not in {"disabled", "working tree is not clean"}:
            logger.warning(
                "Autonomous checkpoint was not pushed: %s",
                push_result.get("reason", "unknown reason"),
            )
    except Exception as exc:
        update_autonomy_run(
            run_id,
            task_ids=task_ids,
            status="failed",
            error=str(exc),
        )

async def _run_autonomy_scheduler_loop(stop_event: asyncio.Event) -> None:
    """Wake periodically for the configured workspace and reconcile stale workers."""
    interval_seconds = max(int(settings.autonomous_interval_minutes), 1) * 60
    target_workspace = str(settings.autonomous_workspace or "").strip().casefold()
    active_statuses = {
        "queued", "planning", "running", "awaiting_approval", "needs_verification"
    }
    reconciliation_grace = _reconciliation_grace_seconds()

    while not stop_event.is_set():
        if bool(getattr(settings, "autonomous_recovery_enabled", True)):
            recover_incomplete_runs(
                stale_after_seconds=max(
                    int(getattr(settings, "autonomous_recovery_stale_seconds", 900)),
                    30,
                )
            )
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
            for task in project_tasks:
                if task.get("mode") == "autonomous" and task.get("status") in WAITING_TASK_STATUSES:
                    requeue_waiting_task(task["id"])

            # Resume durable queued work before considering a fresh autonomous
            # cycle. This keeps provider/local-agent recovery from losing the
            # task graph after a scheduler or machine restart.
            open_runs = list_autonomy_runs(project["id"], limit=100)
            resumed_existing_work = False
            for run in open_runs:
                if run.get("status") not in {
                    "queued", "planning", "running", "awaiting_approval",
                    "waiting_dependency",
                }:
                    continue
                run_task_ids = {
                    str(task_id) for task_id in (run.get("task_ids") or [])
                }
                queued_tasks = [
                    task for task in list_tasks(project["id"])
                    if str(task.get("id")) in run_task_ids
                    and task.get("mode") == "autonomous"
                    and task.get("status") == "queued"
                ]
                if not queued_tasks:
                    continue
                from app.agent_service import run_agent_task
                for task in queued_tasks:
                    try:
                        await run_agent_task(str(task["id"]))
                    except Exception:
                        logger.exception(
                            "Durable task resume failed",
                            extra={"task_id": task.get("id"), "run_id": run.get("id")},
                        )
                resumed_existing_work = True
                break
            if resumed_existing_work:
                continue

            remaining_active_tasks = [
                task for task in list_tasks(project["id"])
                if task.get("mode") == "autonomous"
                and task.get("status") in active_statuses
            ]
            if remaining_active_tasks:
                continue

            open_runs = list_autonomy_runs(project["id"], limit=100)
            if any(run.get("status") in {
                "queued", "planning", "running", "awaiting_approval",
                "waiting_dependency", "recovery_required",
            } for run in open_runs):
                continue

            improvement_engine = SelfImprovementEngine()
            improvement_candidates: list[dict[str, object]] = []
            try:
                improvement_candidates = improvement_engine.observe_and_propose(project["id"])
            except Exception:
                logger.exception("Self-improvement observation failed; continuing with the regular backlog.")
            backlog_item = select_autonomous_backlog_item(project["id"])
            goal = build_backlog_goal(backlog_item)
            if bool(getattr(settings, "autonomous_improvement_enabled", False)):
                ranked = improvement_engine.prioritize(project["id"], limit=1)
                if ranked:
                    goal = improvement_engine.render_goal(ranked[0])
            run = create_autonomy_run(
                project_id=project["id"],
                goal=goal,
                requested_cycles=max(int(settings.autonomous_cycles_per_run), 1),
            )
            if bool(getattr(settings, "autonomous_improvement_enabled", False)) and improvement_candidates:
                chosen = improvement_engine.prioritize(project["id"], limit=1)
                if chosen:
                    try:
                        cycle = improvement_engine.start_cycle(
                            chosen[0]["id"],
                            project_id=project["id"],
                            run_id=run["id"],
                        )
                        if cycle.get("stage") == "planned":
                            improvement_engine.checkpoint(cycle["id"])
                    except (KeyError, RuntimeError, ValueError):
                        logger.exception("Self-improvement checkpoint failed; run remains resumable.")
            await run_autonomous_cycles(run["id"])

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue


async def run_autonomy_scheduler(stop_event: asyncio.Event) -> None:
    """Keep the supervisor alive if one database/provider iteration fails."""
    while not stop_event.is_set():
        try:
            await _run_autonomy_scheduler_loop(stop_event)
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Autonomous supervisor iteration failed; retrying.")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                continue

