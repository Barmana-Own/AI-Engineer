from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.coordination.roles import ROLE_ALIASES, ROLE_REGISTRY, resolve_role
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_HANDOFF_TARGETS = frozenset({"frontend"})


def _clean(value: object, *, max_chars: int = 4000) -> str:
    cleaned, _ = sanitize_text(str(value or ""), max_chars=max_chars)
    return cleaned.strip()


def _items(values: Iterable[object] | None, *, limit: int = 100, max_chars: int = 2000) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for value in values or ():
        item = _clean(value, max_chars=max_chars)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return tuple(result)


def _mapping_items(values: Iterable[object] | None, *, limit: int = 100) -> tuple[dict[str, object], ...]:
    result: list[dict[str, object]] = []
    for value in values or ():
        if hasattr(value, "as_dict") and callable(value.as_dict):
            value = value.as_dict()
        if isinstance(value, Mapping):
            item: dict[str, object] = {}
            for key, raw in value.items():
                clean_key = _clean(key, max_chars=128)
                if not clean_key:
                    continue
                if isinstance(raw, Mapping):
                    item[clean_key] = {
                        str(k): (dict(v) if isinstance(v, Mapping) else _clean(v, max_chars=2000))
                        for k, v in raw.items()
                    }
                elif isinstance(raw, (list, tuple, set)):
                    item[clean_key] = [
                        dict(entry) if isinstance(entry, Mapping) else _clean(entry, max_chars=2000)
                        for entry in raw
                    ]
                else:
                    item[clean_key] = _clean(raw, max_chars=4000)
            if item and item not in result:
                result.append(item)
        else:
            text = _clean(value, max_chars=2000)
            if text:
                result.append({"description": text})
        if len(result) >= limit:
            break
    return tuple(result)


def _role(value: object, allowed: frozenset[str]) -> str:
    normalized = _clean(value, max_chars=128).casefold()
    if normalized not in ROLE_REGISTRY and normalized not in ROLE_ALIASES:
        raise ValueError(f"unknown agent role: {value}")
    resolved = resolve_role(normalized)
    if resolved not in allowed:
        raise ValueError(f"role is not allowed for this design action: {value}")
    return resolved


@dataclass(frozen=True)
class UserFlow:
    flow_id: str
    name: str
    goal: str
    actors: tuple[str, ...] = ()
    steps: tuple[str, ...] = ()
    entry_point: str = ""
    success_state: str = ""
    alternate_states: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("actors", "steps", "alternate_states", "requirement_ids"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class ScreenDefinition:
    screen_id: str
    name: str
    purpose: str
    audience: tuple[str, ...] = ()
    hierarchy: tuple[str, ...] = ()
    primary_actions: tuple[str, ...] = ()
    states: tuple[str, ...] = ()
    responsive_notes: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("audience", "hierarchy", "primary_actions", "states", "responsive_notes", "requirement_ids"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class InteractionSpecification:
    target: str
    behavior: str
    triggers: tuple[str, ...] = ()
    feedback: tuple[str, ...] = ()
    error_handling: tuple[str, ...] = ()
    keyboard_behavior: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("triggers", "feedback", "error_handling", "keyboard_behavior"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class ComponentRequirement:
    name: str
    purpose: str
    variants: tuple[str, ...] = ()
    states: tuple[str, ...] = ()
    data_requirements: tuple[str, ...] = ()
    accessibility: tuple[str, ...] = ()
    responsive_behavior: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("variants", "states", "data_requirements", "accessibility", "responsive_behavior"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class AccessibilityRequirement:
    requirement_id: str
    target: str
    guideline: str
    behavior: str
    verification: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ResponsiveRule:
    target: str
    mobile: str
    tablet: str = ""
    desktop: str = ""
    overflow: str = ""
    priority: str = "normal"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesignNotes:
    principles: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    requirement_traceability: tuple[dict[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("principles", "assumptions", "risks", "evidence", "requirement_traceability"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class UXDesignSpecification:
    design_id: str
    project_id: str
    title: str
    objective: str = ""
    user_flows: tuple[dict[str, object], ...] = ()
    screens: tuple[dict[str, object], ...] = ()
    interactions: tuple[dict[str, object], ...] = ()
    components: tuple[dict[str, object], ...] = ()
    accessibility_requirements: tuple[dict[str, object], ...] = ()
    responsive_rules: tuple[dict[str, object], ...] = ()
    design_notes: DesignNotes = DesignNotes()
    requirement_ids: tuple[str, ...] = ()
    version: int = 1
    status: str = "proposed"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["design_notes"] = self.design_notes.as_dict()
        for key in ("user_flows", "screens", "interactions", "components", "accessibility_requirements", "responsive_rules", "requirement_ids"):
            result[key] = list(getattr(self, key))
        return result


class UXDesignerAgent:
    """Read-only experience designer that hands structured specifications to Frontend."""

    ROLE = "ux_designer"
    DISPLAY_NAME = "UX/UI Designer"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-ux-designer",
            display_name=self.DISPLAY_NAME,
            department=Department.PRODUCT,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def inspect_user_goals(self, project_id: str, *, goals: Iterable[object] = (), actors: Iterable[object] = (), evidence: Iterable[object] = ()) -> dict[str, object]:
        """Create an evidence-only discovery snapshot; it never edits product source."""
        return {
            "project_id": project_id,
            "goals": list(_items(goals)),
            "actors": list(_items(actors)),
            "evidence": list(_items(evidence, max_chars=500)),
        }

    def _from_message(self, row: Mapping[str, object]) -> UXDesignSpecification:
        try:
            payload = json.loads(str(row.get("body") or "{}"))
            raw_notes = payload.get("design_notes") or {}
            notes = DesignNotes(
                principles=tuple(raw_notes.get("principles") or ()),
                assumptions=tuple(raw_notes.get("assumptions") or ()),
                risks=tuple(raw_notes.get("risks") or ()),
                evidence=tuple(raw_notes.get("evidence") or ()),
                requirement_traceability=tuple(raw_notes.get("requirement_traceability") or ()),
            )
            return UXDesignSpecification(
                design_id=str(payload.get("design_id") or row.get("message_id")),
                project_id=str(payload.get("project_id") or row.get("project_id") or ""),
                title=str(payload.get("title") or row.get("subject") or "UX design specification"),
                objective=str(payload.get("objective") or ""),
                user_flows=tuple(payload.get("user_flows") or ()),
                screens=tuple(payload.get("screens") or ()),
                interactions=tuple(payload.get("interactions") or ()),
                components=tuple(payload.get("components") or ()),
                accessibility_requirements=tuple(payload.get("accessibility_requirements") or ()),
                responsive_rules=tuple(payload.get("responsive_rules") or ()),
                design_notes=notes,
                requirement_ids=tuple(payload.get("requirement_ids") or ()),
                version=max(1, int(payload.get("version") or 1)),
                status=str(payload.get("status") or "proposed"),
                message_id=str(row.get("message_id") or ""),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid persisted UX design specification") from exc

    def list_designs(self, *, project_id: str | None = None, limit: int = 100) -> list[UXDesignSpecification]:
        rows = coordination_store.list_messages(project_id=project_id, limit=min(max(int(limit), 1), 500), database_path=self.database_path)
        result: list[UXDesignSpecification] = []
        for row in rows:
            if row.get("topic") != "ux_design_specification" or row.get("message_type") != MessageType.PROPOSAL.value:
                continue
            try:
                result.append(self._from_message(row))
            except ValueError:
                continue
        return result

    def get_design(self, design_id: str) -> UXDesignSpecification:
        for design in self.list_designs(limit=500):
            if design.design_id == str(design_id):
                return design
        raise KeyError(f"UX design specification not found: {design_id}")

    def _resolve_design(self, design: UXDesignSpecification | str) -> UXDesignSpecification:
        return design if isinstance(design, UXDesignSpecification) else self.get_design(str(design))

    def design(
        self,
        project_id: str,
        title: str,
        *,
        objective: str = "",
        user_flows: Iterable[object] = (),
        screens: Iterable[object] = (),
        interactions: Iterable[object] = (),
        components: Iterable[object] = (),
        accessibility_requirements: Iterable[object] = (),
        responsive_rules: Iterable[object] = (),
        design_notes: DesignNotes | Mapping[str, object] | None = None,
        requirement_ids: Iterable[object] = (),
        requirement_traceability: Iterable[object] = (),
        evidence: Iterable[object] = (),
        version: int = 1,
        run_id: str | None = None,
    ) -> UXDesignSpecification:
        self.ensure_profile()
        clean_title = _clean(title, max_chars=500)
        if not clean_title:
            raise ValueError("UX design title is required")
        clean_requirements = _items(requirement_ids, max_chars=128)
        if isinstance(design_notes, DesignNotes):
            notes = design_notes
        elif isinstance(design_notes, Mapping):
            notes = DesignNotes(
                principles=_items(design_notes.get("principles")),
                assumptions=_items(design_notes.get("assumptions")),
                risks=_items(design_notes.get("risks")),
                evidence=_items(design_notes.get("evidence"), max_chars=500),
                requirement_traceability=_mapping_items(design_notes.get("requirement_traceability")),
            )
        else:
            notes = DesignNotes()
        trace = _mapping_items(requirement_traceability or notes.requirement_traceability)
        if not trace and clean_requirements:
            trace = tuple({"requirement_id": requirement_id, "flows": [], "screens": []} for requirement_id in clean_requirements)
        notes = replace(notes, requirement_traceability=trace, evidence=_items(tuple(notes.evidence) + tuple(_items(evidence, max_chars=500)), max_chars=500))
        specification = UXDesignSpecification(
            design_id=str(uuid4()),
            project_id=str(project_id),
            title=clean_title,
            objective=_clean(objective, max_chars=20_000),
            user_flows=_mapping_items(user_flows),
            screens=_mapping_items(screens),
            interactions=_mapping_items(interactions),
            components=_mapping_items(components),
            accessibility_requirements=_mapping_items(accessibility_requirements),
            responsive_rules=_mapping_items(responsive_rules),
            design_notes=notes,
            requirement_ids=clean_requirements,
            version=max(1, int(version)),
            status="proposed",
        )
        message = self.bus.publish(
            sender_role=self.ROLE,
            message_type=MessageType.PROPOSAL,
            subject=clean_title,
            body=json.dumps(specification.as_dict(), ensure_ascii=False),
            run_id=run_id,
            project_id=str(project_id),
            references=specification.design_notes.evidence + tuple(f"requirement:{item}" for item in clean_requirements),
            topic="ux_design_specification",
        )
        return replace(specification, message_id=str(message["message_id"]))

    def create_design(self, *args: object, **kwargs: object) -> UXDesignSpecification:
        return self.design(*args, **kwargs)

    def propose(self, *args: object, **kwargs: object) -> UXDesignSpecification:
        return self.design(*args, **kwargs)

    def handoff(
        self,
        design: UXDesignSpecification | str,
        *,
        target_role: str = "frontend",
        requirement_ids: Iterable[object] = (),
        remaining_work: Iterable[object] = (),
        verification: Iterable[object] = (),
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        specification = self._resolve_design(design)
        target = _role(target_role, _HANDOFF_TARGETS)
        requirements = _items(requirement_ids, max_chars=128) or specification.requirement_ids
        handoff = AgentHandoff(
            sender_role=self.ROLE,
            recipient_role=target,
            summary=f"UX/UI design handoff: {specification.title}",
            completed=("User goals and flows documented.", "Screens and interaction behavior specified.", "Accessibility and responsive requirements recorded."),
            artifacts=("UserFlows", "ScreenDefinitions", "InteractionSpecification", "ComponentRequirements", "AccessibilityRequirements", "ResponsiveRules", "DesignNotes"),
            decisions=tuple(f"requirement:{item}" for item in requirements),
            risks=specification.design_notes.risks,
            remaining_work=_items(remaining_work),
            verification=_items(verification, max_chars=500),
            run_id=run_id,
            project_id=specification.project_id,
            task_id=task_id,
        )
        row = self.handoffs.submit(handoff)
        message = self.bus.publish(
            sender_role=self.ROLE,
            message_type=MessageType.HANDOFF,
            subject=handoff.summary,
            body=json.dumps({"design": specification.as_dict(), "handoff": handoff.as_dict()}, ensure_ascii=False),
            run_id=run_id,
            project_id=specification.project_id,
            task_id=task_id,
            recipient_role=target,
            references=(f"design:{specification.design_id}",) + tuple(f"requirement:{item}" for item in requirements),
            topic="ux_design_handoff",
        )
        return {"handoff": row, "message": message, "design": specification.as_dict()}


UXUIDesignerAgent = UXDesignerAgent
UXDesigner = UXDesignerAgent


__all__ = [
    "AccessibilityRequirement",
    "ComponentRequirement",
    "DesignNotes",
    "InteractionSpecification",
    "ResponsiveRule",
    "ScreenDefinition",
    "UXDesigner",
    "UXDesignerAgent",
    "UXDesignSpecification",
    "UXUIDesignerAgent",
    "UserFlow",
]
