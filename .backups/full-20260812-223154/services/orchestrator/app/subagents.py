"""Bounded sub-agent roles used by autonomous project cycles.

Roles are deliberately small and sequential. The registry is the single
source of truth for which specialist may inspect, edit, or validate a project.
Prompt and status helpers are pure functions; they do not start workers or
mutate a workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SubagentRole:
    key: str
    title: str
    objective: str
    read_only: bool
    validation_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "objective": self.objective,
            "read_only": self.read_only,
            "validation_required": self.validation_required,
        }


SUBAGENT_ROLES: tuple[SubagentRole, ...] = (
    SubagentRole(
        key="inspector",
        title="Project Inspector",
        objective="Inspect the project and collect concrete evidence about its current structure.",
        read_only=True,
    ),
    SubagentRole(
        key="planner",
        title="Change Planner",
        objective="Use the inspected evidence to identify one small, high-value, low-risk improvement.",
        read_only=True,
    ),
    SubagentRole(
        key="implementer",
        title="Safe Implementer",
        objective="Apply exactly one coherent improvement to an already-read target file.",
        read_only=False,
        validation_required=True,
    ),
    SubagentRole(
        key="verifier",
        title="Validation Engineer",
        objective="Run the project validation command and confirm the implementation remains healthy.",
        read_only=True,
        validation_required=True,
    ),
    SubagentRole(
        key="reviewer",
        title="Change Reviewer",
        objective="Review the resulting diff and recorded validation evidence for scope and safety.",
        read_only=True,
    ),
    SubagentRole(
        key="monitor",
        title="Autonomy Monitor",
        objective="Track bounded sub-agent progress, reconcile stale tasks, and report pipeline health.",
        read_only=True,
    ),
)

_ROLE_BY_KEY = {role.key: role for role in SUBAGENT_ROLES}
_ROLE_ALIASES = {"scout": "inspector"}
ROLE_KEYS: tuple[str, ...] = tuple(role.key for role in SUBAGENT_ROLES)


def get_subagent_role(key: str) -> SubagentRole:
    normalized = (key or "").strip().casefold()
    normalized = _ROLE_ALIASES.get(normalized, normalized)
    return _ROLE_BY_KEY.get(normalized, _ROLE_BY_KEY["implementer"])


def configured_subagent_roles(value: str | None) -> list[SubagentRole]:
    """Resolve a comma-separated role list while preserving registry order."""
    requested = [part.strip().casefold() for part in (value or "").split(",")]
    requested = [part for part in requested if part]
    if not requested:
        requested = ["inspector", "planner", "implementer", "verifier", "reviewer"]

    roles: list[SubagentRole] = []
    for key in requested:
        role = get_subagent_role(key)
        if role.key not in {item.key for item in roles}:
            roles.append(role)
    return roles or [get_subagent_role("implementer")]


def role_marker(role: SubagentRole) -> str:
    return f"SUBAGENT_ROLE: {role.key}"


def role_from_instruction(instruction: str) -> SubagentRole:
    for line in (instruction or "").splitlines():
        if line.strip().casefold().startswith("subagent_role:"):
            return get_subagent_role(line.split(":", 1)[1])
    return get_subagent_role("implementer")


def build_role_instruction(
    *,
    role: SubagentRole,
    goal: str,
    cycle: int,
    total_cycles: int,
    memory_text: str,
) -> str:
    mutation_rule = (
        "Implement exactly one small file change after the normal read and Git checkpoint guards."
        if not role.read_only
        else "This role is strictly observational: inspect files and report evidence without performing filesystem or repository operations."
    )
    validation_rule = (
        "Run the real project validation command before finishing."
        if role.validation_required
        else "Do not run process-changing or destructive commands."
    )
    return f"""{role_marker(role)}
You are the {role.title} sub-agent in bounded autonomous cycle {cycle}/{total_cycles}.

PRIMARY GOAL:
{goal.strip()}

ROLE OBJECTIVE:
{role.objective}

OPERATING CONTRACT:
- Inspect the existing project before deciding what to do.
- Keep the work narrow, evidence-based, and project-relative.
- {mutation_rule}
- {validation_rule}
- Never install packages, access secrets, touch the operating system, or destroy data,
  rollback Git, or publish/deploy anything.
- Finish only with real tool evidence and leave a concise result for the next role.

LEARNED MEMORY:
{memory_text}
""".strip()


def build_role_prompt(
    *,
    role: SubagentRole | str,
    goal: str,
    project: str,
    cycle: int = 1,
    total_cycles: int = 1,
    memory_text: str = "",
) -> str:
    """Build the public prompt API for a bounded role."""
    resolved = role if isinstance(role, SubagentRole) else get_subagent_role(role)
    instruction = build_role_instruction(
        role=resolved,
        goal=goal,
        cycle=cycle,
        total_cycles=total_cycles,
        memory_text=memory_text,
    )
    return instruction.replace(
        f"PRIMARY GOAL:\n{goal.strip()}",
        f"PROJECT:\n{project.strip()}\n\nPRIMARY GOAL:\n{goal.strip()}",
        1,
    )


def build_status_report(
    *,
    run_id: str,
    project_id: str,
    role: SubagentRole | str,
    status: str,
    cycle: int = 0,
    total_cycles: int = 0,
    task_id: str | None = None,
    detail: str | None = None,
    blockers: list[str] | tuple[str, ...] = (),
    updated_at: str | None = None,
) -> dict[str, object]:
    """Return a timestamped, serializable snapshot for monitor/UI consumers."""
    resolved = role if isinstance(role, SubagentRole) else get_subagent_role(role)
    return {
        "run_id": str(run_id),
        "project_id": str(project_id),
        "role": resolved.key,
        "status": (status or "unknown").strip().casefold(),
        "cycle": max(int(cycle), 0),
        "total_cycles": max(int(total_cycles), 0),
        "task_id": task_id,
        "detail": (detail or "").strip() or None,
        "blockers": [
            str(item).strip() for item in blockers if str(item).strip()
        ],
        "updated_at": updated_at or datetime.now(timezone.utc).isoformat(),
    }


def list_subagent_roles() -> list[dict[str, object]]:
    return [role.as_dict() for role in SUBAGENT_ROLES]


__all__ = [
    "ROLE_KEYS",
    "SUBAGENT_ROLES",
    "SubagentRole",
    "build_role_instruction",
    "build_role_prompt",
    "build_status_report",
    "configured_subagent_roles",
    "get_subagent_role",
    "list_subagent_roles",
    "role_from_instruction",
    "role_marker",
]
