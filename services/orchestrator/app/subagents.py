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
    section: str = "core"
    capabilities: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "objective": self.objective,
            "read_only": self.read_only,
            "validation_required": self.validation_required,
            "section": self.section,
            "capabilities": list(self.capabilities),
        }


SUBAGENT_ROLES: tuple[SubagentRole, ...] = (
    SubagentRole(
        key="inspector",
        title="Project Inspector",
        objective="Inspect the project and collect concrete evidence about its current structure.",
        read_only=True,
        section="core",
        capabilities=("read", "evidence"),
    ),
    SubagentRole(
        key="planner",
        title="Change Planner",
        objective="Use the inspected evidence to identify one small, high-value, low-risk improvement.",
        read_only=True,
        section="core",
        capabilities=("read", "plan"),
    ),
    SubagentRole(
        key="implementer",
        title="Safe Implementer",
        objective="Apply exactly one coherent improvement to an already-read target file.",
        read_only=False,
        validation_required=True,
        section="implementation",
        capabilities=("read", "write", "checkpoint", "validate"),
    ),
    SubagentRole(
        key="verifier",
        title="Validation Engineer",
        objective="Run the project validation command and confirm the implementation remains healthy.",
        read_only=True,
        validation_required=True,
        section="tests",
        capabilities=("read", "validate", "evidence"),
    ),
    SubagentRole(
        key="reviewer",
        title="Change Reviewer",
        objective="Review the resulting diff and recorded validation evidence for scope and safety.",
        read_only=True,
        section="quality",
        capabilities=("read", "diff", "evidence", "handoff"),
    ),
    SubagentRole(
        key="monitor",
        title="Supervisor Manager",
        objective="Coordinate bounded sub-agent progress, reconcile stale tasks, and report pipeline health without competing with the writer.",
        read_only=True,
        section="supervisor",
        capabilities=("read", "monitor", "reconcile", "schedule", "lease"),
    ),
    # Domain specialists give every product section a stable owner.  They are
    # logical sub-agents executed by the same policy-enforcing worker; this
    # keeps the local deployment lightweight while making handoffs explicit.
    SubagentRole(
        key="requirements",
        title="Requirements Analyst",
        objective="Extract acceptance criteria, constraints, and observable success signals from the goal and current evidence.",
        read_only=True,
        section="product",
        capabilities=("read", "requirements", "handoff"),
    ),
    SubagentRole(
        key="architect",
        title="Architecture Analyst",
        objective="Map dependencies and contracts, then propose the smallest safe change boundary for the selected section.",
        read_only=True,
        section="architecture",
        capabilities=("read", "impact", "plan", "handoff"),
    ),
    SubagentRole(
        key="orchestrator",
        title="Orchestrator Specialist",
        objective="Inspect the supervisor, task state, memory, and API flow for restart-safe coordination improvements.",
        read_only=True,
        section="orchestrator",
        capabilities=("read", "state", "api", "handoff"),
    ),
    SubagentRole(
        key="gateway",
        title="Model Gateway Specialist",
        objective="Inspect provider routing, fallback behavior, and model health without exposing credentials or changing providers implicitly.",
        read_only=True,
        section="model-gateway",
        capabilities=("read", "routing", "health", "handoff"),
    ),
    SubagentRole(
        key="local_agent",
        title="Local Agent Specialist",
        objective="Inspect filesystem, terminal, Git, and process policy boundaries for safe local execution.",
        read_only=True,
        section="local-agent",
        capabilities=("read", "policy", "security", "handoff"),
    ),
    SubagentRole(
        key="ui",
        title="Control Center Specialist",
        objective="Inspect the control-center API client and dashboard contracts so specialist progress is observable.",
        read_only=True,
        section="control-center",
        capabilities=("read", "ui", "api", "handoff"),
    ),
    SubagentRole(
        key="desktop",
        title="Desktop Specialist",
        objective="Inspect the desktop shell, startup, and service health integration for a reliable local app experience.",
        read_only=True,
        section="desktop",
        capabilities=("read", "desktop", "health", "handoff"),
    ),
    SubagentRole(
        key="tests",
        title="Test Specialist",
        objective="Inspect test coverage and execute the narrowest meaningful validation for the selected change.",
        read_only=True,
        validation_required=True,
        section="tests",
        capabilities=("read", "validate", "coverage", "handoff"),
    ),
    SubagentRole(
        key="security",
        title="Security Reviewer",
        objective="Review paths, secrets, commands, permissions, and diffs for policy or data-loss risks.",
        read_only=True,
        section="security",
        capabilities=("read", "security", "diff", "handoff"),
    ),
    SubagentRole(
        key="docs",
        title="Documentation Specialist",
        objective="Inspect documentation contracts and identify concise updates needed to keep operation and recovery instructions accurate.",
        read_only=True,
        section="docs",
        capabilities=("read", "docs", "handoff"),
    ),
    SubagentRole(
        key="debugger",
        title="Bounded Debugger",
        objective="Use a concrete failed validation as evidence for at most one narrowly scoped repair, then hand it back for verification.",
        read_only=False,
        validation_required=True,
        section="recovery",
        capabilities=("read", "write", "checkpoint", "validate", "retry"),
    ),
    SubagentRole(
        key="integration",
        title="Integration and Release Analyst",
        objective="Inspect build and health contracts across services; publishing, deployment, and commits remain approval-gated.",
        read_only=True,
        validation_required=True,
        section="integration",
        capabilities=("read", "validate", "health", "handoff"),
    ),
)

_ROLE_BY_KEY = {role.key: role for role in SUBAGENT_ROLES}
_ROLE_ALIASES = {"manager": "monitor", "scout": "inspector", "local-agent": "local_agent", "test-verifier": "tests"}
ROLE_KEYS: tuple[str, ...] = tuple(role.key for role in SUBAGENT_ROLES)
_DOMAIN_ROLE_KEYS = {
    "requirements", "architect", "orchestrator", "gateway", "local_agent",
    "ui", "desktop", "tests", "security", "docs", "debugger", "integration",
}
SECTION_ROLE_KEYS: dict[str, str] = {
    role.section: role.key
    for role in SUBAGENT_ROLES
    if role.key in _DOMAIN_ROLE_KEYS
}
HANDOFF_SCHEMA_VERSION = "1.0"


def get_subagent_role(key: str) -> SubagentRole:
    normalized = (key or "").strip().casefold()
    normalized = _ROLE_ALIASES.get(normalized, normalized)
    # Unknown markers are observational by default. A malformed model output
    # must never silently acquire the writer role.
    return _ROLE_BY_KEY.get(normalized, _ROLE_BY_KEY["inspector"])


def configured_subagent_roles(value: str | None) -> list[SubagentRole]:
    """Resolve a comma-separated role list while preserving registry order."""
    requested = [part.strip().casefold() for part in (value or "").split(",")]
    requested = [part for part in requested if part]
    if not requested:
        requested = ["inspector", "planner", "implementer", "verifier", "reviewer"]

    roles: list[SubagentRole] = []
    for key in requested:
        canonical = _ROLE_ALIASES.get(key, key)
        if canonical not in _ROLE_BY_KEY:
            continue
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


@dataclass(frozen=True)
class SubagentHandoff:
    """Versioned blackboard record passed from one specialist to the next."""

    run_id: str
    project_id: str
    role: str
    section: str
    status: str
    summary: str = ""
    task_id: str | None = None
    evidence: tuple[dict[str, object], ...] = ()
    changed_files: tuple[str, ...] = ()
    validations: tuple[dict[str, object], ...] = ()
    blockers: tuple[str, ...] = ()
    next_action: str | None = None
    confidence: float = 0.0
    previous_handoff_ids: tuple[str, ...] = ()
    created_at: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": HANDOFF_SCHEMA_VERSION,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "role": self.role,
            "section": self.section,
            "status": self.status,
            "summary": self.summary,
            "evidence": [dict(item) for item in self.evidence],
            "changed_files": list(self.changed_files),
            "validations": [dict(item) for item in self.validations],
            "blockers": list(self.blockers),
            "next_action": self.next_action,
            "confidence": max(0.0, min(float(self.confidence), 1.0)),
            "previous_handoff_ids": list(self.previous_handoff_ids),
            "created_at": self.created_at or datetime.now(timezone.utc).isoformat(),
        }


def build_handoff(
    *,
    run_id: str,
    project_id: str,
    role: SubagentRole | str,
    status: str,
    summary: str = "",
    task_id: str | None = None,
    evidence: list[dict[str, object]] | tuple[dict[str, object], ...] = (),
    changed_files: list[str] | tuple[str, ...] = (),
    validations: list[dict[str, object]] | tuple[dict[str, object], ...] = (),
    blockers: list[str] | tuple[str, ...] = (),
    next_action: str | None = None,
    confidence: float = 0.0,
    previous_handoff_ids: list[str] | tuple[str, ...] = (),
    created_at: str | None = None,
) -> dict[str, object]:
    """Normalize a specialist result before it is persisted to the blackboard."""
    resolved = role if isinstance(role, SubagentRole) else get_subagent_role(role)
    return SubagentHandoff(
        run_id=str(run_id),
        project_id=str(project_id),
        role=resolved.key,
        section=resolved.section,
        status=(status or "unknown").strip().casefold(),
        summary=str(summary or "").strip()[:4_000],
        task_id=task_id,
        evidence=tuple(dict(item) for item in evidence[:20]),
        changed_files=tuple(str(item).replace("\\", "/") for item in changed_files[:50]),
        validations=tuple(dict(item) for item in validations[:20]),
        blockers=tuple(str(item).strip() for item in blockers if str(item).strip())[:20],
        next_action=str(next_action).strip()[:1_000] if next_action else None,
        confidence=confidence,
        previous_handoff_ids=tuple(str(item) for item in previous_handoff_ids[:20]),
        created_at=created_at,
    ).as_dict()


def list_subagent_roles() -> list[dict[str, object]]:
    return [role.as_dict() for role in SUBAGENT_ROLES]


def list_section_subagents() -> list[dict[str, object]]:
    """Return one stable specialist owner for each product section."""
    return [
        role.as_dict()
        for role in SUBAGENT_ROLES
        if role.key in _DOMAIN_ROLE_KEYS
    ]


__all__ = [
    "ROLE_KEYS",
    "SECTION_ROLE_KEYS",
    "SUBAGENT_ROLES",
    "HANDOFF_SCHEMA_VERSION",
    "SubagentHandoff",
    "SubagentRole",
    "build_handoff",
    "build_role_instruction",
    "build_role_prompt",
    "build_status_report",
    "configured_subagent_roles",
    "get_subagent_role",
    "list_subagent_roles",
    "list_section_subagents",
    "role_from_instruction",
    "role_marker",
]
