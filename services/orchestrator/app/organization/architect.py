from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.collaboration_store import create_decision
from app.coordination.models import AgentHandoff, MessageType, TechnicalDecision
from app.coordination.roles import ROLE_ALIASES, ROLE_REGISTRY, resolve_role
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_CHALLENGE_ROLES = frozenset({"security", "backend", "frontend", "integration", "tester", "engineering_manager"})
_HANDOFF_TARGETS = frozenset({
    "backend", "frontend", "integration", "tester", "security", "engineering_manager",
    "reviewer", "docs", "release_verifier",
})


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
        if isinstance(value, Mapping):
            item: dict[str, object] = {}
            for key, raw in value.items():
                clean_key = _clean(key, max_chars=128)
                if not clean_key:
                    continue
                if isinstance(raw, Mapping):
                    item[clean_key] = {str(k): _clean(v, max_chars=2000) for k, v in raw.items()}
                elif isinstance(raw, (list, tuple, set)):
                    item[clean_key] = list(_items(raw, max_chars=2000))
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
        raise ValueError(f"role is not allowed for this architecture action: {value}")
    return resolved


@dataclass(frozen=True)
class ComponentMap:
    components: tuple[dict[str, object], ...] = ()
    boundaries: tuple[dict[str, object], ...] = ()
    interfaces: tuple[dict[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"components": list(self.components), "boundaries": list(self.boundaries), "interfaces": list(self.interfaces)}


@dataclass(frozen=True)
class APIContract:
    name: str
    method: str = ""
    path: str = ""
    request: str = ""
    response: str = ""
    errors: tuple[str, ...] = ()
    owner_role: str = "backend"

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["errors"] = list(self.errors)
        return result


@dataclass(frozen=True)
class DataFlow:
    source: str
    destination: str
    data: str
    protocol: str = ""
    trust_boundary: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TechnologyDecision:
    area: str
    choice: str
    rationale: str
    alternatives: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("alternatives", "tradeoffs", "evidence"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class ArchitectureRisk:
    title: str
    impact: str
    likelihood: str = "medium"
    mitigation: str = ""
    owner_role: str = "engineering_manager"
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class ArchitectureProposal:
    proposal_id: str
    project_id: str
    title: str
    context: str = ""
    current_state: tuple[dict[str, object], ...] = ()
    component_map: ComponentMap = ComponentMap()
    api_contracts: tuple[dict[str, object], ...] = ()
    data_flow: tuple[dict[str, object], ...] = ()
    technology_decisions: tuple[dict[str, object], ...] = ()
    architecture_risks: tuple[dict[str, object], ...] = ()
    alternatives: tuple[dict[str, object], ...] = ()
    tradeoffs: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    version: int = 1
    status: str = "proposed"
    revision_of: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["component_map"] = self.component_map.as_dict()
        for key in ("current_state", "api_contracts", "data_flow", "technology_decisions", "architecture_risks", "alternatives"):
            result[key] = list(getattr(self, key))
        for key in ("tradeoffs", "evidence"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class ArchitectureChallenge:
    challenge_id: str
    proposal_id: str
    project_id: str
    challenger_role: str
    subject: str
    concerns: str
    evidence: tuple[str, ...] = ()
    requested_changes: tuple[str, ...] = ()
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        result["requested_changes"] = list(self.requested_changes)
        return result


@dataclass(frozen=True)
class ArchitectureRevision:
    revision_id: str
    previous_proposal_id: str
    proposal: ArchitectureProposal
    reason: str
    changed_areas: tuple[str, ...] = ()
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["proposal"] = self.proposal.as_dict()
        result["changed_areas"] = list(self.changed_areas)
        return result


class SoftwareArchitectAgent:
    """Read-only architect that records challengeable architecture evidence."""

    ROLE = "architect"
    DISPLAY_NAME = "Software Architect"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-architect",
            display_name=self.DISPLAY_NAME,
            department=Department.ENGINEERING,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def inspect_current_architecture(self, project_id: str, *, components: Iterable[object] = (), boundaries: Iterable[object] = (), constraints: Iterable[object] = (), evidence: Iterable[object] = ()) -> dict[str, object]:
        """Build an evidence-only snapshot; it never rewrites the project."""
        return {
            "project_id": project_id,
            "components": list(_mapping_items(components)),
            "boundaries": list(_mapping_items(boundaries)),
            "constraints": list(_items(constraints)),
            "evidence": list(_items(evidence, max_chars=500)),
        }

    def _proposal_from_message(self, row: Mapping[str, object]) -> ArchitectureProposal:
        try:
            payload = json.loads(str(row.get("body") or "{}"))
            raw_map = payload.get("component_map") or {}
            component_map = ComponentMap(
                components=tuple(raw_map.get("components") or ()),
                boundaries=tuple(raw_map.get("boundaries") or ()),
                interfaces=tuple(raw_map.get("interfaces") or ()),
            )
            return ArchitectureProposal(
                proposal_id=str(payload.get("proposal_id") or row.get("message_id")),
                project_id=str(payload.get("project_id") or row.get("project_id") or ""),
                title=str(payload.get("title") or row.get("subject") or "Architecture proposal"),
                context=str(payload.get("context") or ""),
                current_state=tuple(payload.get("current_state") or ()), component_map=component_map,
                api_contracts=tuple(payload.get("api_contracts") or ()), data_flow=tuple(payload.get("data_flow") or ()),
                technology_decisions=tuple(payload.get("technology_decisions") or ()), architecture_risks=tuple(payload.get("architecture_risks") or ()),
                alternatives=tuple(payload.get("alternatives") or ()), tradeoffs=tuple(payload.get("tradeoffs") or ()),
                evidence=tuple(payload.get("evidence") or ()), version=int(payload.get("version") or 1),
                status=str(payload.get("status") or "proposed"), revision_of=payload.get("revision_of"), message_id=str(row.get("message_id") or ""),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid persisted architecture proposal") from exc

    def list_proposals(self, *, project_id: str | None = None, limit: int = 100) -> list[ArchitectureProposal]:
        rows = coordination_store.list_messages(project_id=project_id, limit=min(max(int(limit), 1), 500), database_path=self.database_path)
        result: list[ArchitectureProposal] = []
        for row in rows:
            if row.get("topic") != "architecture_proposal" or row.get("message_type") != MessageType.PROPOSAL.value:
                continue
            try:
                result.append(self._proposal_from_message(row))
            except ValueError:
                continue
        return result

    def get_proposal(self, proposal_id: str) -> ArchitectureProposal:
        for proposal in self.list_proposals(limit=500):
            if proposal.proposal_id == str(proposal_id):
                return proposal
        raise KeyError(f"Architecture proposal not found: {proposal_id}")

    def _resolve_proposal(self, proposal: ArchitectureProposal | str) -> ArchitectureProposal:
        return proposal if isinstance(proposal, ArchitectureProposal) else self.get_proposal(str(proposal))

    def propose(self, project_id: str, title: str, *, context: str = "", current_state: Iterable[object] = (), components: Iterable[object] = (), component_map: ComponentMap | Mapping[str, object] | None = None, boundaries: Iterable[object] = (), interfaces: Iterable[object] = (), api_contracts: Iterable[object] = (), data_flow: Iterable[object] = (), technology_decisions: Iterable[object] = (), architecture_risks: Iterable[object] = (), risks: Iterable[object] = (), alternatives: Iterable[object] = (), tradeoffs: Iterable[object] = (), evidence: Iterable[object] = (), version: int = 1, revision_of: str | None = None, run_id: str | None = None) -> ArchitectureProposal:
        self.ensure_profile()
        clean_title = _clean(title, max_chars=500)
        if not clean_title:
            raise ValueError("architecture proposal title is required")
        if component_map is None:
            map_model = ComponentMap(components=_mapping_items(components), boundaries=_mapping_items(boundaries), interfaces=_mapping_items(interfaces))
        elif isinstance(component_map, ComponentMap):
            map_model = component_map
        elif isinstance(component_map, Mapping):
            map_model = ComponentMap(components=_mapping_items(component_map.get("components", ())), boundaries=_mapping_items(component_map.get("boundaries", ())), interfaces=_mapping_items(component_map.get("interfaces", ())))
        else:
            raise TypeError("component_map must be a ComponentMap or mapping")
        proposal = ArchitectureProposal(
            proposal_id=str(uuid4()), project_id=project_id, title=clean_title,
            context=_clean(context, max_chars=20_000), current_state=_mapping_items(current_state), component_map=map_model,
            api_contracts=_mapping_items(api_contracts), data_flow=_mapping_items(data_flow), technology_decisions=_mapping_items(technology_decisions),
            architecture_risks=_mapping_items(architecture_risks or risks), alternatives=_mapping_items(alternatives),
            tradeoffs=_items(tradeoffs), evidence=_items(evidence, max_chars=500), version=max(1, int(version)), status="proposed", revision_of=revision_of,
        )
        message = self.bus.publish(sender_role=self.ROLE, message_type=MessageType.PROPOSAL,
            subject=clean_title, body=json.dumps(proposal.as_dict(), ensure_ascii=False), run_id=run_id,
            project_id=project_id, references=proposal.evidence, topic="architecture_proposal")
        return replace(proposal, message_id=str(message["message_id"]))

    def challenge(self, proposal: ArchitectureProposal | str, challenger_role: str, subject: str, concerns: str, *, evidence: Iterable[object] = (), requested_changes: Iterable[object] = (), run_id: str | None = None) -> ArchitectureChallenge:
        model = self._resolve_proposal(proposal)
        challenger = _role(challenger_role, _CHALLENGE_ROLES)
        subject, concerns = _clean(subject, max_chars=500), _clean(concerns, max_chars=20_000)
        if not subject or not concerns:
            raise ValueError("architecture challenge subject and concerns are required")
        result = ArchitectureChallenge(str(uuid4()), model.proposal_id, model.project_id, challenger, subject, concerns, _items(evidence, max_chars=500), _items(requested_changes), message_id=None)
        message = self.bus.publish(sender_role=challenger, message_type=MessageType.CHALLENGE, subject=subject,
            body=json.dumps(result.as_dict(), ensure_ascii=False), run_id=run_id, project_id=model.project_id,
            references=result.evidence + (f"proposal:{model.proposal_id}",), recipient_role=self.ROLE, topic="architecture_challenge")
        return replace(result, message_id=str(message["message_id"]))

    def revise(self, proposal: ArchitectureProposal | str, *, reason: str, changed_areas: Iterable[object] = (), components: Iterable[object] | None = None, component_map: ComponentMap | Mapping[str, object] | None = None, api_contracts: Iterable[object] | None = None, data_flow: Iterable[object] | None = None, technology_decisions: Iterable[object] | None = None, architecture_risks: Iterable[object] | None = None, evidence: Iterable[object] = (), run_id: str | None = None) -> ArchitectureRevision:
        current = self._resolve_proposal(proposal)
        reason = _clean(reason, max_chars=4000)
        if not reason:
            raise ValueError("architecture revision reason is required")
        if component_map is None:
            revised_map = current.component_map if components is None else replace(current.component_map, components=_mapping_items(components))
        elif isinstance(component_map, ComponentMap):
            revised_map = component_map
        elif isinstance(component_map, Mapping):
            revised_map = ComponentMap(components=_mapping_items(component_map.get("components", ())), boundaries=_mapping_items(component_map.get("boundaries", ())), interfaces=_mapping_items(component_map.get("interfaces", ())))
        else:
            raise TypeError("component_map must be a ComponentMap or mapping")
        revised = replace(current, proposal_id=str(uuid4()), component_map=revised_map,
            api_contracts=current.api_contracts if api_contracts is None else _mapping_items(api_contracts),
            data_flow=current.data_flow if data_flow is None else _mapping_items(data_flow),
            technology_decisions=current.technology_decisions if technology_decisions is None else _mapping_items(technology_decisions),
            architecture_risks=current.architecture_risks if architecture_risks is None else _mapping_items(architecture_risks),
            version=current.version + 1, status="revised", revision_of=current.proposal_id, evidence=_items(evidence, max_chars=500), message_id=None)
        message = self.bus.publish(sender_role=self.ROLE, message_type=MessageType.PROPOSAL,
            subject=f"Architecture revision: {revised.title}", body=json.dumps(revised.as_dict(), ensure_ascii=False), run_id=run_id,
            project_id=revised.project_id, references=revised.evidence + (f"proposal:{current.proposal_id}",), topic="architecture_proposal")
        return ArchitectureRevision(str(uuid4()), current.proposal_id, replace(revised, message_id=str(message["message_id"])), reason, _items(changed_areas), str(message["message_id"]))

    def revise_proposal(self, proposal: ArchitectureProposal | str, **kwargs: object) -> ArchitectureRevision:
        return self.revise(proposal, **kwargs)

    def record_decision(self, proposal: ArchitectureProposal | str, decision: str, *, decision_maker: str = "architect", options: Iterable[object] = (), arguments: Iterable[object] = (), evidence: Iterable[object] = (), affected_task_ids: Iterable[object] = (), run_id: str | None = None) -> dict[str, object]:
        model = self._resolve_proposal(proposal)
        maker = _role(decision_maker, frozenset({"architect", "engineering_manager", "supervisor", "company_director"}))
        outcome = _clean(decision, max_chars=20_000)
        if not outcome:
            raise ValueError("architecture decision is required")
        task_ids: list[str] = []
        for raw in affected_task_ids:
            task_id = _clean(raw, max_chars=128)
            if not task_id:
                continue
            task = coordination_store.get_task(task_id, database_path=self.database_path)
            if not task or str(task.get("project_id")) != model.project_id:
                raise ValueError("architecture decision tasks must belong to the project")
            task_ids.append(task_id)
        clean_evidence = _items(evidence, max_chars=500)
        record = create_decision(TechnicalDecision(project_id=model.project_id, run_id=run_id, title=model.title, context=model.context, options=_items(options), arguments=_items(arguments), decision=outcome, decision_maker=maker, supporting_evidence=clean_evidence + (f"proposal:{model.proposal_id}",), affected_tasks=tuple(task_ids)), database_path=self.database_path)
        message = self.bus.publish(sender_role=maker, message_type=MessageType.DECISION, subject=model.title, body=outcome, run_id=run_id, project_id=model.project_id, references=clean_evidence + (f"decision:{record['decision_id']}", f"proposal:{model.proposal_id}"), recipient_role="engineering_manager", topic="architecture_decision")
        return {"decision": record, "message": message, "proposal": model.as_dict()}

    def handoff(self, proposal: ArchitectureProposal | str, *, target_role: str, decision_ids: Iterable[object] = (), risks: Iterable[object] | None = None, remaining_work: Iterable[object] = (), verification: Iterable[object] = (), run_id: str | None = None, task_id: str | None = None) -> dict[str, object]:
        model = self._resolve_proposal(proposal)
        target = _role(target_role, _HANDOFF_TARGETS)
        risk_values = tuple(_clean(item.get("title") if isinstance(item, Mapping) else item, max_chars=500) for item in (risks if risks is not None else model.architecture_risks))
        risk_values = tuple(item for item in risk_values if item)
        handoff = AgentHandoff(sender_role=self.ROLE, recipient_role=target, summary=f"Architecture proposal: {model.title}", completed=("Existing architecture inspected.", "Component boundaries and contracts documented.", "Tradeoffs and risks recorded."), artifacts=("ArchitectureProposal", "ComponentMap", "APIContracts", "DataFlow"), decisions=_items(decision_ids, max_chars=128), risks=risk_values, remaining_work=_items(remaining_work), verification=_items(verification, max_chars=500), run_id=run_id, project_id=model.project_id, task_id=task_id)
        row = self.handoffs.submit(handoff)
        message = self.bus.publish(sender_role=self.ROLE, message_type=MessageType.HANDOFF, subject=handoff.summary, body=json.dumps({"proposal": model.as_dict(), "handoff": handoff.as_dict()}, ensure_ascii=False), run_id=run_id, project_id=model.project_id, task_id=task_id, recipient_role=target, references=(f"proposal:{model.proposal_id}",), topic="architecture_handoff")
        return {"handoff": row, "message": message, "proposal": model.as_dict()}


SoftwareArchitect = SoftwareArchitectAgent
ArchitectAgent = SoftwareArchitectAgent


__all__ = ["APIContract", "ArchitectureChallenge", "ArchitectureProposal", "ArchitectureRevision", "ArchitectureRisk", "ArchitectAgent", "ComponentMap", "DataFlow", "SoftwareArchitect", "SoftwareArchitectAgent", "TechnologyDecision"]
