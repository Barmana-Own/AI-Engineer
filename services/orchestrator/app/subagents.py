"""Bounded sub-agent roles used by autonomous project cycles.

Roles are deliberately small and sequential.  The registry is the single
source of truth for which specialist may inspect, edit, or validate a project.
"""

from __future__ import annotations

from dataclasses import dataclass


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
        key="scout",
        title="Project Scout",
        objective="Inspect the project and collect concrete evidence about its current structure.",
        read_only=True,
    ),
    SubagentRole(
        key="planner",
        title="Improvement Planner",
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
        title="Diff Reviewer",
        objective="Review the resulting diff and recorded validation evidence for scope and safety.",
        read_only=True,
    ),
    SubagentRole(
        key="monitor",
        title="Autonomy Monitor",
        objective="Reconcile stale tasks and report the health of the autonomous pipeline.",
        read_only=True,
    ),
)

_ROLE_BY_KEY = {role.key: role for role in SUBAGENT_ROLES}


def get_subagent_role(key: str) -> SubagentRole:
    normalized = (key or "").strip().casefold()
    return _ROLE_BY_KEY.get(normalized, _ROLE_BY_KEY["implementer"])


def configured_subagent_roles(value: str | None) -> list[SubagentRole]:
    """Resolve a comma-separated role list while preserving registry order."""
    requested = [part.strip().casefold() for part in (value or "").split(",")]
    requested = [part for part in requested if part]
    if not requested:
        requested = ["scout", "planner", "implementer", "verifier", "reviewer"]

    roles: list[SubagentRole] = []
    for key in requested:
        role = _ROLE_BY_KEY.get(key)
        if role and role not in roles:
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


def list_subagent_roles() -> list[dict[str, object]]:
    return [role.as_dict() for role in SUBAGENT_ROLES]
