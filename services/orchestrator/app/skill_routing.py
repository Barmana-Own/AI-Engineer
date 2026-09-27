"""Role-aware routing and bounded context loading for imported engineering skills.

The skill registry owns the installed playbooks.  This module owns the one
canonical role-to-skill routing policy and translates a task into a small,
auditable selection.  It deliberately does not execute skills or create a
second workflow engine: workers can persist the returned selection on the
existing agent task and later load only the selected material.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from app.skill_registry import SkillRegistry


ROLE_SKILL_MAP_FILE = "role-skill-map.json"
MAX_CONTEXT_DOCUMENT_BYTES = 160_000
MAX_REFERENCE_BYTES = 80_000
MAX_SELECTIONS = 32
MAX_EVIDENCE_ITEMS = 40


class SkillRoutingError(ValueError):
    """Raised when a routing request cannot be safely resolved."""


class UnknownRoleError(SkillRoutingError):
    """Raised for a role that has no canonical routing contract."""


ROLE_ALIASES: dict[str, str] = {
    "project-manager": "project_manager",
    "project manager": "project_manager",
    "engineering-manager": "engineering_manager",
    "engineering manager": "engineering_manager",
    "release-verifier": "release_verifier",
    "release verifier": "release_verifier",
    "ux/ui": "ux_designer",
    "ux-designer": "ux_designer",
    "ux designer": "ux_designer",
    "qa": "tester",
    "qa/test": "tester",
    "security-engineer": "security",
    "devops/deployment": "devops",
    "documentation": "docs",
    "seo-manager": "seo_manager",
    "seo-specialist": "seo_specialist",
}


CONDITION_TERMS: dict[str, tuple[str, ...]] = {
    "frontend_or_ui": (
        "frontend", "front-end", "ui", "ux", "react", "vue", "svelte", "client", "browser",
        "responsive", "accessibility", "component", "layout", "screen", "page",
    ),
    "backend_or_service": (
        "backend", "back-end", "server", "service", "fastapi", "django", "flask", "endpoint",
        "api", "worker", "webhook", "business logic",
    ),
    "database_or_data": (
        "database", "db", "sqlite", "postgres", "postgresql", "mysql", "migration", "schema",
        "transaction", "query", "persistence", "table", "index", "data model",
    ),
    "interface_or_api": (
        "api", "endpoint", "contract", "integration", "frontend/backend", "service-to-service",
        "http", "rest", "graphql", "webhook",
    ),
    "security_or_auth": (
        "auth", "authentication", "authorization", "permission", "credential", "token", "session",
        "password", "security", "secret", "oauth", "oidc", "payment",
    ),
    "deployment": (
        "deploy", "deployment", "production", "release", "container", "docker", "iis", "reverse proxy",
        "server startup", "infrastructure", "rollback", "ci/cd", "health check",
    ),
    "testing": (
        "test", "testing", "pytest", "vitest", "jest", "regression", "coverage", "assertion",
    ),
}


FULL_STACK_TERMS = (
    "full-stack", "full stack", "fullstack", "web application", "frontend and backend", "frontend/backend",
)
DOC_ONLY_TERMS = ("documentation-only", "docs-only", "readme", "documentation", "docs", "release notes")
IMPLEMENTATION_TERMS = ("implement", "build", "develop", "fix", "refactor", "source code", "bug", "feature", "migration", "schema", "deploy", "test suite")


def _bounded_text(value: object, limit: int = 12_000) -> str:
    text = str(value or "").strip().casefold()
    return text[:limit]


def _flatten_text(values: object) -> str:
    if values is None:
        return ""
    if isinstance(values, str):
        return _bounded_text(values)
    if isinstance(values, Mapping):
        return _bounded_text(" ".join(f"{key} {value}" for key, value in list(values.items())[:80]))
    if isinstance(values, Iterable):
        return _bounded_text(" ".join(str(item) for item in list(values)[:80]))
    return _bounded_text(values)


def normalize_role(role: str) -> str:
    normalized = _bounded_text(role).replace("_", "-")
    normalized = ROLE_ALIASES.get(normalized, normalized)
    return normalized.replace("-", "_")


def _has_signal(text: str, condition: str) -> bool:
    if condition == "always":
        return True
    return any(term in text for term in CONDITION_TERMS.get(condition, ()))


def _is_docs_only(text: str, role: str) -> bool:
    if role == "docs":
        return True
    if any(term in text for term in ("documentation-only", "docs-only", "documentation only")):
        return True
    # A full-stack objective may include documentation as one deliverable;
    # it must not be reduced to a documentation-only route.
    if any(term in text for term in FULL_STACK_TERMS):
        return False
    return any(term in text for term in DOC_ONLY_TERMS) and not any(term in text for term in IMPLEMENTATION_TERMS)


@dataclass(frozen=True)
class SkillSelection:
    skill_id: str
    reason: str
    priority: int
    required: bool
    condition: str = "always"

    @property
    def mode(self) -> str:
        return "required" if self.required else "optional"

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "reason": self.reason,
            "priority": self.priority,
            "required": self.required,
            "mode": self.mode,
            "condition": self.condition,
        }


@dataclass(frozen=True)
class SkillRouteRequest:
    task_objective: str
    assigned_role: str
    project_type: str = ""
    requirements: Sequence[str] | Mapping[str, Any] | str = ()
    risk: str = ""
    technologies: Sequence[str] | Mapping[str, Any] | str = ()
    project_phase: str = ""
    project_skill_ids: Sequence[str] = ()
    task_id: str | None = None
    project_id: str | None = None

    @property
    def context_text(self) -> str:
        return _bounded_text(
            " ".join(
                (
                    self.task_objective,
                    self.project_type,
                    _flatten_text(self.requirements),
                    self.risk,
                    _flatten_text(self.technologies),
                    self.project_phase,
                )
            )
        )


@dataclass(frozen=True)
class StageDependency:
    skill_id: str
    depends_on: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"skill_id": self.skill_id, "depends_on": list(self.depends_on)}


@dataclass(frozen=True)
class SkillRouteResult:
    role: str
    selections: tuple[SkillSelection, ...]
    stage_dependencies: tuple[StageDependency, ...] = ()
    project_skill_ids: tuple[str, ...] = ()

    @property
    def skill_ids(self) -> tuple[str, ...]:
        return tuple(selection.skill_id for selection in self.selections)

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "skills": [selection.as_dict() for selection in self.selections],
            "skill_ids": list(self.skill_ids),
            "stage_dependencies": [item.as_dict() for item in self.stage_dependencies],
            "project_skill_ids": list(self.project_skill_ids),
        }


@dataclass(frozen=True)
class LoadedSkillContext:
    skill_id: str
    skill_document: str
    references: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_document": self.skill_document,
            "references": dict(self.references),
        }


@dataclass(frozen=True)
class SkillExecutionEvidence:
    skill_id: str
    task_id: str
    agent_id: str
    artifacts_created: tuple[str, ...] = ()
    checks_run: tuple[str, ...] = ()
    findings: tuple[Mapping[str, Any], ...] = ()
    gate_status: str = "pending"
    handoff: Mapping[str, Any] | None = None
    evidence: tuple[Mapping[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "artifacts_created": list(self.artifacts_created)[:MAX_EVIDENCE_ITEMS],
            "checks_run": list(self.checks_run)[:MAX_EVIDENCE_ITEMS],
            "findings": [dict(item) for item in self.findings[:MAX_EVIDENCE_ITEMS]],
            "gate_status": self.gate_status,
            "handoff": dict(self.handoff) if self.handoff else None,
            "evidence": [dict(item) for item in self.evidence[:MAX_EVIDENCE_ITEMS]],
        }


@dataclass(frozen=True)
class SkillGateResult:
    skill_id: str
    status: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"skill_id": self.skill_id, "status": self.status, "reason": self.reason}


class SkillRouter:
    """Resolve task and project skills from one registry-backed policy."""

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or SkillRegistry()
        self.role_rules = self._load_role_rules()

    def _load_role_rules(self) -> dict[str, tuple[dict[str, str], ...]]:
        path = self.registry.root / ROLE_SKILL_MAP_FILE
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SkillRoutingError(f"Unable to load role-skill policy: {path}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("roles"), dict):
            raise SkillRoutingError("Role-skill policy must contain a roles object")
        result: dict[str, tuple[dict[str, str], ...]] = {}
        for raw_role, raw_rules in payload["roles"].items():
            role = normalize_role(str(raw_role))
            if not isinstance(raw_rules, list):
                raise SkillRoutingError(f"Role policy must be a list: {raw_role}")
            normalized: list[dict[str, str]] = []
            for raw_rule in raw_rules:
                if not isinstance(raw_rule, dict):
                    raise SkillRoutingError(f"Invalid skill rule for role: {raw_role}")
                skill_id = str(raw_rule.get("skill_id") or "")
                self.registry.get(skill_id)
                mode = str(raw_rule.get("mode") or "optional")
                if mode not in {"required", "optional"}:
                    raise SkillRoutingError(f"Invalid skill rule mode for {role}: {mode}")
                normalized.append(
                    {
                        "skill_id": skill_id,
                        "mode": mode,
                        "condition": str(raw_rule.get("condition") or "always"),
                        "reason": str(raw_rule.get("reason") or "Selected by role policy."),
                    }
                )
            result[role] = tuple(normalized)
        return result

    def supported_roles(self) -> tuple[str, ...]:
        return tuple(sorted(self.role_rules))

    def route(self, request: SkillRouteRequest) -> SkillRouteResult:
        role = normalize_role(request.assigned_role)
        if role not in self.role_rules:
            raise UnknownRoleError(f"No skill routing contract for role: {request.assigned_role}")
        context = request.context_text
        if _is_docs_only(context, role):
            selections: tuple[SkillSelection, ...] = ()
        elif role == "engineering_manager":
            selections = self._overview_selections(request)
        else:
            selections = self._select_rules(role, context)
        dependencies = self.adapt_stage_dependencies(selections, request=request)
        return SkillRouteResult(
            role=role,
            selections=selections,
            stage_dependencies=dependencies,
            project_skill_ids=tuple(request.project_skill_ids),
        )

    def route_project(self, request: SkillRouteRequest) -> SkillRouteResult:
        """Select a project-level set without imposing a twelve-stage pipeline."""

        context = request.context_text
        if _is_docs_only(context, ""):
            selections: tuple[SkillSelection, ...] = ()
        else:
            selected: dict[str, SkillSelection] = {}

            def add(skill_id: str, *, required: bool, reason: str, priority: int = 1) -> None:
                self.registry.get(skill_id)
                current = selected.get(skill_id)
                candidate = SkillSelection(skill_id, reason, priority, required)
                if current is None or (candidate.required and not current.required):
                    selected[skill_id] = candidate

            add("project-analysis-prompt-engineering", required=True, reason="Project scope and acceptance criteria.")
            is_full_stack = any(term in context for term in FULL_STACK_TERMS) or _has_signal(context, "frontend_or_ui") and _has_signal(context, "backend_or_service")
            has_frontend = _has_signal(context, "frontend_or_ui") or is_full_stack
            has_backend = _has_signal(context, "backend_or_service") or is_full_stack
            has_database = _has_signal(context, "database_or_data") or is_full_stack
            has_api = _has_signal(context, "interface_or_api") or is_full_stack
            has_auth = _has_signal(context, "security_or_auth")
            has_deployment = _has_signal(context, "deployment")
            if has_frontend:
                add("design-system-ui-architecture", required=True, reason="User-facing scope requires UI architecture.")
                add("frontend-architecture", required=True, reason="User-facing scope requires frontend boundaries.")
            if has_backend:
                add("backend-architecture", required=True, reason="Service scope requires backend boundaries.")
            if has_database:
                add("database-architecture", required=True, reason="Persistent data scope requires database architecture.")
            if has_api:
                add("api-integration", required=True, reason="Multiple or externally visible interfaces require integration contracts.")
            if has_auth:
                add("authentication-authorization", required=True, reason="Identity or access-control scope requires the auth playbook.")
                add("application-security", required=True, reason="Security-sensitive scope requires defensive review.")
            if any(term in context for term in CONDITION_TERMS["testing"]) or has_frontend or has_backend:
                add("software-testing", required=True, reason="Implementation scope requires executable tests.")
                add("qa-debugging", required=True, reason="Implementation scope requires regression and defect handling.")
            if has_deployment:
                add("deployment-production", required=True, reason="Operational scope requires deployment and health evidence.")
            add("fullstack-final-review", required=True, reason="Completion requires an independent final review.")
            selections = tuple(selected.values())
        dependencies = self.adapt_stage_dependencies(selections, request=request)
        return SkillRouteResult(
            role="project",
            selections=selections,
            stage_dependencies=dependencies,
            project_skill_ids=tuple(selection.skill_id for selection in selections),
        )

    def _select_rules(self, role: str, context: str) -> tuple[SkillSelection, ...]:
        selections: list[SkillSelection] = []
        for rule in self.role_rules.get(role, ()):
            if not _has_signal(context, rule["condition"]):
                continue
            selections.append(
                SkillSelection(
                    skill_id=rule["skill_id"],
                    reason=rule["reason"],
                    priority=1 if rule["mode"] == "required" else 2,
                    required=rule["mode"] == "required",
                    condition=rule["condition"],
                )
            )
        return tuple(selections[:MAX_SELECTIONS])

    def _overview_selections(self, request: SkillRouteRequest) -> tuple[SkillSelection, ...]:
        allowed = set(request.project_skill_ids)
        if not allowed:
            return ()
        selections: list[SkillSelection] = []
        for skill_id in request.project_skill_ids:
            descriptor = self.registry.get(skill_id)
            selections.append(
                SkillSelection(
                    skill_id=descriptor.skill_id,
                    reason="Read-only overview of the project-selected skill.",
                    priority=2,
                    required=False,
                    condition="project_selected",
                )
            )
        return tuple(selections[:MAX_SELECTIONS])

    def adapt_stage_dependencies(
        self,
        selections: Sequence[SkillSelection],
        *,
        request: SkillRouteRequest | None = None,
    ) -> tuple[StageDependency, ...]:
        """Build only the dependencies represented by this task's selection."""

        selected = {selection.skill_id for selection in selections}
        if not selected:
            return ()
        order = (
            "project-analysis-prompt-engineering",
            "design-system-ui-architecture",
            "frontend-architecture",
            "backend-architecture",
            "database-architecture",
            "api-integration",
            "authentication-authorization",
            "application-security",
            "software-testing",
            "qa-debugging",
            "deployment-production",
            "fullstack-final-review",
        )
        dependencies: dict[str, tuple[str, ...]] = {}

        def add(skill_id: str, values: Sequence[str] = ()) -> None:
            if skill_id in selected:
                dependencies[skill_id] = tuple(item for item in values if item in selected and item != skill_id)

        add("project-analysis-prompt-engineering")
        add("design-system-ui-architecture", ("project-analysis-prompt-engineering",))
        add("frontend-architecture", ("design-system-ui-architecture", "project-analysis-prompt-engineering"))
        add("backend-architecture", ("project-analysis-prompt-engineering",))
        add("database-architecture", ("backend-architecture", "project-analysis-prompt-engineering"))
        add("api-integration", ("frontend-architecture", "backend-architecture", "database-architecture"))
        add("authentication-authorization", ("backend-architecture", "api-integration"))
        add("application-security", ("authentication-authorization", "backend-architecture", "api-integration"))
        implementation = tuple(
            skill_id
            for skill_id in (
                "frontend-architecture", "backend-architecture", "database-architecture", "api-integration",
            )
            if skill_id in selected
        )
        add("software-testing", implementation or ("project-analysis-prompt-engineering",))
        add("qa-debugging", ("software-testing",))
        add("deployment-production", ("qa-debugging", "software-testing"))
        final_dependencies = tuple(skill_id for skill_id in order if skill_id in selected and skill_id != "fullstack-final-review")
        add("fullstack-final-review", final_dependencies)
        return tuple(StageDependency(skill_id, dependencies.get(skill_id, ())) for skill_id in order if skill_id in selected)


class SkillContextLoader:
    """Load only selected skill files and explicitly requested references."""

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or SkillRegistry()

    def load(
        self,
        route: SkillRouteResult,
        *,
        task_id: str,
        role: str,
        project_id: str,
        reference_names: Mapping[str, Sequence[str]] | None = None,
    ) -> tuple[LoadedSkillContext, ...]:
        if not isinstance(route, SkillRouteResult):
            raise SkillRoutingError("Skill context must come from a SkillRouter result")
        if not task_id or not role or not project_id:
            raise SkillRoutingError("Skill context requires task_id, role, and project_id")
        normalized_role = normalize_role(role)
        if route.role not in {normalized_role, "project"}:
            raise SkillRoutingError("Skill route role does not match the executing role")
        selections = route.selections
        requested = reference_names or {}
        loaded: list[LoadedSkillContext] = []
        for selection in selections[:MAX_SELECTIONS]:
            descriptor = self.registry.get(selection.skill_id)
            if not self.registry.activation_allowed(
                selection.skill_id,
                router_approved=True,
                task_id=task_id,
                role=role,
                project_id=project_id,
            ):
                raise SkillRoutingError(f"Skill activation denied: {selection.skill_id}")
            document = descriptor.skill_file.read_text(encoding="utf-8")
            document = document[:MAX_CONTEXT_DOCUMENT_BYTES]
            references: dict[str, str] = {}
            for name in tuple(requested.get(selection.skill_id, ()))[:8]:
                if name not in descriptor.references:
                    raise SkillRoutingError(f"Reference is not declared by {selection.skill_id}: {name}")
                content = (descriptor.root / "references" / name).read_text(encoding="utf-8")
                references[name] = content[:MAX_REFERENCE_BYTES]
            loaded.append(LoadedSkillContext(selection.skill_id, document, references))
        return tuple(loaded)


def effective_tool_permissions(
    *,
    role_tools: Iterable[str],
    task_tools: Iterable[str],
    global_tools: Iterable[str],
    selected_skill_ids: Iterable[str],
    registry: SkillRegistry | None = None,
) -> frozenset[str]:
    """Return the least-privilege intersection; skills never grant tools."""

    skill_registry = registry or SkillRegistry()
    role_set = {str(item) for item in role_tools}
    task_set = {str(item) for item in task_tools}
    global_set = {str(item) for item in global_tools}
    skill_set: set[str] = set()
    for skill_id in selected_skill_ids:
        skill_set.update(skill_registry.get(str(skill_id)).allowed_tools)
    return frozenset(role_set & task_set & global_set & skill_set)


QUALITY_GATE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "software-testing": ("tests_passed", "checks_run"),
    "qa-debugging": ("regressions_absent", "checks_run"),
    "fullstack-final-review": ("review_accepted", "critical_findings_absent", "checks_run"),
    "application-security": ("security_findings_resolved", "checks_run"),
    "authentication-authorization": ("security_findings_resolved", "checks_run"),
    "deployment-production": ("health_checks_passed", "checks_run"),
}


def evaluate_skill_gate(skill_id: str, evidence: Mapping[str, Any]) -> SkillGateResult:
    """Evaluate evidence, never a free-form self-reported PASS string."""

    requirements = QUALITY_GATE_REQUIREMENTS.get(skill_id, ("checks_run",))
    missing = [key for key in requirements if not evidence.get(key)]
    if missing:
        return SkillGateResult(skill_id, "blocked", f"Missing objective evidence: {', '.join(missing)}")
    if skill_id == "fullstack-final-review" and evidence.get("critical_findings"):
        return SkillGateResult(skill_id, "blocked", "Critical final-review findings remain.")
    return SkillGateResult(skill_id, "passed", "Required objective evidence is present.")


def evaluate_quality_gates(
    selections: Sequence[SkillSelection],
    evidence_by_skill: Mapping[str, Mapping[str, Any]],
) -> tuple[SkillGateResult, ...]:
    return tuple(
        evaluate_skill_gate(selection.skill_id, evidence_by_skill.get(selection.skill_id, {}))
        for selection in selections
        if selection.required
    )


def build_skill_evidence(
    *,
    skill_id: str,
    task_id: str,
    agent_id: str,
    artifacts_created: Iterable[str] = (),
    checks_run: Iterable[str] = (),
    findings: Iterable[Mapping[str, Any]] = (),
    gate_status: str = "pending",
    handoff: Mapping[str, Any] | None = None,
    evidence: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return SkillExecutionEvidence(
        skill_id=skill_id,
        task_id=task_id,
        agent_id=agent_id,
        artifacts_created=tuple(str(item) for item in list(artifacts_created)[:MAX_EVIDENCE_ITEMS]),
        checks_run=tuple(str(item) for item in list(checks_run)[:MAX_EVIDENCE_ITEMS]),
        findings=tuple(dict(item) for item in list(findings)[:MAX_EVIDENCE_ITEMS]),
        gate_status=str(gate_status),
        handoff=dict(handoff) if handoff else None,
        evidence=tuple(dict(item) for item in list(evidence)[:MAX_EVIDENCE_ITEMS]),
    ).as_dict()

