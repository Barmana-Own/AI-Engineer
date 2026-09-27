from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

from app.coordination import store as coordination_store
from app.coordination.bus import MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .sales import OpenQuestions, OpportunityBrief, Risks
from .store import ensure_employee


_CLASSIFICATIONS = frozenset({"FACT", "CLIENT_REQUEST", "ASSUMPTION", "RECOMMENDATION"})
_PRIORITIES = frozenset({"must", "should", "could", "must_not"})
_ALLOWED_HANDOFFS = frozenset({"project_manager", "architect", "engineering_manager"})


def _clean(value: object, *, max_chars: int = 4000) -> str:
    cleaned, _ = sanitize_text(str(value or ""), max_chars=max_chars)
    return cleaned.strip()


def _items(values: Iterable[object] | None, *, limit: int = 100, max_chars: int = 1000) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for value in values or ():
        cleaned = _clean(value, max_chars=max_chars)
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if len(result) >= limit:
            break
    return tuple(result)


def _classified(value: object, default: str) -> tuple[str, str]:
    cleaned = _clean(value)
    for label in _CLASSIFICATIONS:
        prefix = f"{label}:"
        if cleaned.upper().startswith(prefix):
            return label, cleaned[len(prefix):].strip()
    return default, cleaned


def _entry(
    requirement_id: str,
    value: object,
    *,
    default_classification: str,
    priority: str = "must",
    source: str = "requirements_analysis",
) -> "RequirementEntry | None":
    classification, text = _classified(value, default_classification)
    if not text:
        return None
    return RequirementEntry(
        requirement_id=requirement_id,
        text=text,
        classification=classification,
        priority=priority,
        source=source,
    )


@dataclass(frozen=True)
class RequirementEntry:
    requirement_id: str
    text: str
    classification: str
    priority: str = "must"
    source: str = ""

    def __post_init__(self) -> None:
        if self.classification not in _CLASSIFICATIONS:
            raise ValueError(f"Unsupported requirement classification: {self.classification}")
        if self.priority not in _PRIORITIES:
            raise ValueError(f"Unsupported requirement priority: {self.priority}")
        if not self.requirement_id.strip() or not self.text.strip():
            raise ValueError("Requirement entries need an id and text.")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AcceptanceCriterion:
    criterion_id: str
    statement: str
    evidence: tuple[str, ...] = ()
    source_classification: str = "RECOMMENDATION"

    def __post_init__(self) -> None:
        if self.source_classification not in _CLASSIFICATIONS:
            raise ValueError(f"Unsupported criterion classification: {self.source_classification}")
        if not self.criterion_id.strip() or not self.statement.strip():
            raise ValueError("Acceptance criteria need an id and statement.")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectSummary:
    title: str
    summary: str
    project_type: str = "software_project"
    classification: str = "CLIENT_REQUEST"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FunctionalRequirements:
    items: tuple[RequirementEntry, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class NonFunctionalRequirements:
    items: tuple[RequirementEntry, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class AcceptanceCriteria:
    items: tuple[AcceptanceCriterion, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class Constraints:
    items: tuple[RequirementEntry, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class Assumptions:
    items: tuple[RequirementEntry, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class OutOfScopeItems:
    items: tuple[RequirementEntry, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class RequirementsSpecification:
    opportunity_id: str | None
    project_summary: ProjectSummary
    functional_requirements: FunctionalRequirements
    non_functional_requirements: NonFunctionalRequirements
    acceptance_criteria: AcceptanceCriteria
    constraints: Constraints
    assumptions: Assumptions
    open_questions: OpenQuestions
    out_of_scope_items: OutOfScopeItems
    risks: Risks
    dependencies: tuple[RequirementEntry, ...] = ()
    status: str = "needs_clarification"
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "opportunity_id": self.opportunity_id,
            "project_summary": self.project_summary.as_dict(),
            "functional_requirements": self.functional_requirements.as_dict(),
            "non_functional_requirements": self.non_functional_requirements.as_dict(),
            "acceptance_criteria": self.acceptance_criteria.as_dict(),
            "constraints": self.constraints.as_dict(),
            "assumptions": self.assumptions.as_dict(),
            "open_questions": self.open_questions.as_dict(),
            "out_of_scope_items": self.out_of_scope_items.as_dict(),
            "risks": self.risks.as_dict(),
            "dependencies": [item.as_dict() for item in self.dependencies],
            "status": self.status,
            "evidence": list(self.evidence),
        }


def _derive_project_type(text: str, technical_areas: tuple[str, ...]) -> str:
    lowered = text.casefold()
    areas = set(technical_areas)
    if "mobile" in areas or any(marker in lowered for marker in ("android", "ios", "flutter", "react native")):
        return "mobile_application"
    if "frontend" in areas or any(marker in lowered for marker in ("web app", "browser", "website", "react", "vue")):
        return "web_application"
    if "backend" in areas or any(marker in lowered for marker in ("api", "fastapi", "service", "backend")):
        return "software_service"
    return "software_project"


def _derive_functional_items(text: str, deliverables: tuple[str, ...]) -> tuple[str, ...]:
    if deliverables:
        return deliverables
    markers = (
        "build",
        "create",
        "develop",
        "add",
        "provide",
        "support",
        "allow",
        "integrate",
        "implement",
        "expose",
        "deliver",
    )
    segments = re.split(r"[.!?;\n]+", text)
    return tuple(
        segment.strip()
        for segment in segments
        if segment.strip() and any(marker in segment.casefold() for marker in markers)
    )[:100]


def _detect_conflicts(text: str) -> tuple[str, ...]:
    lowered = text.casefold()
    conflicts: list[str] = []
    if "sqlite" in lowered and any(marker in lowered for marker in ("postgres", "postgresql", "mysql")):
        conflicts.append("More than one primary database technology is requested; choose one or define a justified split.")
    if any(marker in lowered for marker in ("mobile only", "mobile-only")) and any(marker in lowered for marker in ("web", "browser", "website")):
        conflicts.append("The request contains both a mobile-only constraint and a web/browser target.")
    if any(marker in lowered for marker in ("without authentication", "no authentication", "unauthenticated")) and any(marker in lowered for marker in ("login", "oauth", "authenticated")):
        conflicts.append("The request contains incompatible authentication expectations.")
    if "offline" in lowered and any(marker in lowered for marker in ("real-time", "realtime", "live updates")):
        conflicts.append("Offline-only and real-time requirements need an explicit synchronization decision.")
    return tuple(conflicts)


def _mapping_value(source: Mapping[str, object], *keys: str, default: object = "") -> object:
    for key in keys:
        if key in source and source[key] not in (None, ""):
            return source[key]
    return default


class RequirementsAgent:
    """Read-only requirements analysis over the existing company workflow."""

    ROLE = "requirements"
    DISPLAY_NAME = "Requirements Analyst"

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = database_path
        self.bus = MessageBus(str(database_path) if database_path is not None else None)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-requirements",
            display_name=self.DISPLAY_NAME,
            department=Department.PRODUCT,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def analyze(
        self,
        brief: OpportunityBrief | Mapping[str, object] | None = None,
        *,
        title: str = "",
        client_request: str = "",
        deliverables: Iterable[object] | None = None,
        technical_areas: Iterable[object] | None = None,
        constraints: Iterable[object] | None = None,
        assumptions: Iterable[object] | None = None,
        dependencies: Iterable[object] | None = None,
        out_of_scope: Iterable[object] | None = None,
        source: str = "client",
    ) -> RequirementsSpecification:
        self.ensure_profile()
        opportunity_id: str | None = None
        incoming_questions: tuple[str, ...] = ()
        incoming_risks: tuple[str, ...] = ()
        if isinstance(brief, OpportunityBrief):
            opportunity_id = brief.opportunity_id
            title = title or brief.title
            client_request = client_request or brief.client_needs.summary
            deliverables = tuple(deliverables or brief.client_needs.deliverables)
            technical_areas = tuple(technical_areas or brief.client_needs.technical_areas)
            incoming_questions = brief.open_questions.questions
            incoming_risks = brief.risks.items
            source = source if source != "client" else brief.source
        elif isinstance(brief, Mapping):
            opportunity_id = str(_mapping_value(brief, "opportunity_id", default="") or "") or None
            title = title or str(_mapping_value(brief, "title", default=""))
            client_request = client_request or str(_mapping_value(brief, "client_request", "summary", default=""))
            nested = _mapping_value(brief, "client_needs_summary", "client_needs", default={})
            if isinstance(nested, Mapping):
                deliverables = tuple(deliverables or nested.get("deliverables", ()))
                technical_areas = tuple(technical_areas or nested.get("technical_areas", ()))
            incoming_questions = tuple(_mapping_value(brief, "open_questions", default=()) or ())
            incoming_risks = tuple(_mapping_value(brief, "risks", default=()) or ())

        clean_title = _clean(title, max_chars=500)
        clean_request = _clean(client_request, max_chars=10000)
        clean_deliverables = _items(deliverables)
        clean_areas = _items(technical_areas, max_chars=200)
        clean_constraints = _items(constraints)
        clean_assumptions = _items(assumptions)
        clean_dependencies = _items(dependencies)
        clean_out_of_scope = _items(out_of_scope)
        functional_values = _derive_functional_items(clean_request, clean_deliverables)
        functional_items = tuple(
            item
            for index, value in enumerate(functional_values, 1)
            if (item := _entry(f"FR-{index:03d}", value, default_classification="CLIENT_REQUEST", source=source))
        )

        lowered = clean_request.casefold()
        nfr_patterns = (
            ("security", ("security", "authentication", "authorization", "oauth", "compliance"), "Security and access-control behavior must meet the agreed policy."),
            ("performance", ("fast", "performance", "latency", "response time"), "Response-time and performance targets must be measurable."),
            ("reliability", ("reliable", "availability", "uptime", "fault tolerant"), "Availability and failure-recovery expectations must be measurable."),
            ("scalability", ("scale", "scalable", "concurrent", "throughput"), "Expected load and scaling limits must be measurable."),
            ("accessibility", ("accessible", "wcag", "keyboard navigation"), "Accessibility expectations must be verified against the agreed standard."),
            ("observability", ("monitor", "logging", "observability", "metrics"), "Operational logging and monitoring expectations must be explicit."),
            ("recovery", ("backup", "restore", "disaster recovery"), "Backup and recovery expectations must be verified."),
        )
        nfr_items: list[RequirementEntry] = []
        for index, (_area, markers, statement) in enumerate(nfr_patterns, 1):
            if any(marker in lowered for marker in markers):
                item = _entry(f"NFR-{index:03d}", statement, default_classification="CLIENT_REQUEST", priority="should", source=source)
                if item is not None:
                    nfr_items.append(item)

        conflicts = _detect_conflicts(clean_request)
        generic_functional = frozenset({
            "build an application",
            "build an app",
            "create an application",
            "create an app",
            "develop an application",
            "develop an app",
        })
        questions = list(_items(incoming_questions))
        if not clean_title:
            questions.append("What is the client-facing project name and intended outcome?")
        if not clean_request and not functional_items:
            questions.append("What user or business problem must the system solve?")
        if not functional_items or all(item.text.casefold().strip(" .") in generic_functional for item in functional_items):
            questions.append("Which concrete behaviors or deliverables are required in the first release?")
        if not any(marker in lowered for marker in ("user", "admin", "customer", "client", "operator", "team")):
            questions.append("Who are the target users and what permissions do they need?")
        if not any(marker in lowered for marker in ("deploy", "hosting", "production", "docker", "cloud")):
            questions.append("Which deployment environment and supported clients are required?")
        if not nfr_items:
            questions.append("What security, performance, availability, accessibility, and recovery targets are required?")
        questions.extend(conflicts)
        open_questions = OpenQuestions(_items(questions))

        risks = list(_items(incoming_risks))
        risks.extend(f"Conflict: {conflict}" for conflict in conflicts)
        if not functional_items:
            risks.append("No concrete functional deliverables were identified.")
        if not nfr_items:
            risks.append("Non-functional targets are unspecified and may cause implementation rework.")
        if clean_assumptions:
            risks.append("Assumptions require client or owner confirmation before implementation.")
        risk_model = Risks(_items(risks))

        constraint_items = tuple(
            item
            for index, value in enumerate(clean_constraints, 1)
            if (item := _entry(f"CON-{index:03d}", value, default_classification="CLIENT_REQUEST", priority="must", source=source))
        )
        assumption_items = tuple(
            item
            for index, value in enumerate(clean_assumptions, 1)
            if (item := _entry(f"ASM-{index:03d}", value, default_classification="ASSUMPTION", priority="should", source="requirements_analysis"))
        )
        dependency_items = tuple(
            item
            for index, value in enumerate(clean_dependencies, 1)
            if (item := _entry(f"DEP-{index:03d}", value, default_classification="CLIENT_REQUEST", priority="must", source=source))
        )
        out_items = [
            item
            for index, value in enumerate(clean_out_of_scope, 1)
            if (item := _entry(f"OUT-{index:03d}", value, default_classification="CLIENT_REQUEST", priority="must_not", source=source))
        ]
        out_items.append(RequirementEntry("OUT-ROLE-001", "Production source-code implementation by the Requirements Analyst.", "FACT", "must_not", "role_contract"))
        out_items.append(RequirementEntry("OUT-COMMERCIAL-001", "Pricing, legal terms, and deadline commitments without owner authorization.", "FACT", "must_not", "company_policy"))
        unique_out: list[RequirementEntry] = []
        for item in out_items:
            if item.text not in {entry.text for entry in unique_out}:
                unique_out.append(item)

        criteria: list[AcceptanceCriterion] = []
        all_requirements = list(functional_items) + nfr_items
        for index, requirement in enumerate(all_requirements, 1):
            evidence = ("deterministic test",) if requirement.requirement_id.startswith("FR-") else ("test or operational evidence",)
            criteria.append(
                AcceptanceCriterion(
                    criterion_id=f"AC-{index:03d}",
                    statement=f"Given the agreed project scope, the system must satisfy: {requirement.text}",
                    evidence=evidence,
                    source_classification=requirement.classification,
                )
            )

        project_type = _derive_project_type(clean_request, clean_areas)
        summary = clean_request or "Requirements are not yet sufficiently defined."
        project_summary = ProjectSummary(
            title=clean_title or "Untitled project",
            summary=summary,
            project_type=project_type,
            classification="CLIENT_REQUEST" if clean_request else "ASSUMPTION",
        )
        status = "ready" if functional_items and not open_questions.questions and not conflicts else "needs_clarification"
        evidence = (
            "Client statements were separated from assumptions and recommendations.",
            "No source files were modified by the Requirements Analyst.",
        )
        return RequirementsSpecification(
            opportunity_id=opportunity_id,
            project_summary=project_summary,
            functional_requirements=FunctionalRequirements(functional_items),
            non_functional_requirements=NonFunctionalRequirements(tuple(nfr_items)),
            acceptance_criteria=AcceptanceCriteria(tuple(criteria)),
            constraints=Constraints(constraint_items),
            assumptions=Assumptions(assumption_items),
            open_questions=open_questions,
            out_of_scope_items=OutOfScopeItems(tuple(unique_out)),
            risks=risk_model,
            dependencies=dependency_items,
            status=status,
            evidence=evidence,
        )

    def handoff(
        self,
        specification: RequirementsSpecification,
        *,
        target_role: str = "project_manager",
        run_id: str | None = None,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        self.ensure_profile()
        from app.coordination.roles import resolve_role

        resolved_target = resolve_role(target_role)
        if resolved_target not in _ALLOWED_HANDOFFS:
            raise ValueError("Requirements handoff target must be project_manager, architect, or engineering_manager.")
        summary = f"Requirements specification for {specification.project_summary.title} ({specification.status})."
        handoff = AgentHandoff(
            sender_role=self.ROLE,
            recipient_role=resolved_target,
            summary=summary,
            completed=(
                "Client statements classified.",
                "Functional and non-functional requirements identified.",
                "Acceptance criteria generated.",
                "Scope boundaries and risks recorded.",
            ),
            artifacts=("RequirementsSpecification",),
            changed_files=(),
            decisions=(),
            risks=specification.risks.items,
            remaining_work=specification.open_questions.questions,
            verification=(
                "No source files were modified by the Requirements Analyst.",
                "Every requirement entry includes FACT, CLIENT_REQUEST, ASSUMPTION, or RECOMMENDATION classification.",
            ),
            run_id=run_id,
            project_id=project_id,
            task_id=task_id,
        )
        handoff_row = coordination_store.create_handoff(handoff, database_path=self.database_path)
        body = json.dumps(
            {
                "specification": specification.as_dict(),
                "handoff": handoff.as_dict(),
                "classification_legend": sorted(_CLASSIFICATIONS),
                "authorization": "Handoff does not authorize implementation.",
            },
            ensure_ascii=False,
        )
        message_row = self.bus.publish(
            sender_role=self.ROLE,
            message_type=MessageType.HANDOFF,
            subject=summary,
            body=body,
            run_id=run_id,
            project_id=project_id,
            task_id=task_id,
            recipient_role=resolved_target,
            references=((specification.opportunity_id,) if specification.opportunity_id else ()),
            topic="requirements",
        )
        return {"handoff": handoff_row, "message": message_row, "specification": specification.as_dict()}


__all__ = [
    "AcceptanceCriterion",
    "AcceptanceCriteria",
    "Assumptions",
    "Constraints",
    "FunctionalRequirements",
    "NonFunctionalRequirements",
    "OpenQuestions",
    "OutOfScopeItems",
    "ProjectSummary",
    "RequirementEntry",
    "RequirementsAgent",
    "RequirementsSpecification",
    "Risks",
]