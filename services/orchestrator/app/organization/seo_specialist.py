"""Evidence-driven SEO analysis and verification employee.

The specialist intentionally composes the existing coordination, queue, handoff,
message, and memory stores.  It does not create a second SEO workflow or write
production source code.  All observations are kept project-scoped and claims
which require an unavailable external data source are marked explicitly.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, CoordinationTask, MessageType, TaskState
from app.coordination.project_management import enqueue_work
from app.memory.models import MemoryLifecycle, MemoryType
from app.memory.sanitizer import sanitize_text
from app.memory.store import MemoryStore

from .models import Department, EmployeeStatus
from .store import ensure_employee
from .seo_manager import SEO_INTENTS, SEO_PRIORITIES, SEOKeywordCluster


ROLE = "seo_specialist"
DISPLAY_NAME = "SEO Specialist"
AGENT_ID = "employee-seo-specialist"
SEO_VERIFICATION_STATUSES = frozenset({"SEO_VERIFIED", "SEO_FAILED"})
SEO_SEVERITIES = frozenset({"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"})
_WRITABLE_IMPLEMENTATION_ROLES = frozenset(
    {"backend", "frontend", "implementer", "integration", "devops", "docs"}
)
_HANDOFF_ROLES = frozenset(
    {
        "seo_manager", "researcher", "frontend", "backend", "ux_designer", "docs",
        "tester", "reviewer", "devops", "integration", "architect",
    }
)
_SEVERITY_SCORE = {"CRITICAL": 95, "HIGH": 75, "MEDIUM": 50, "LOW": 25, "INFO": 10}
_ROLE_ALIASES = {
    "seo": "seo_manager",
    "seo-manager": "seo_manager",
    "seo-specialist": ROLE,
    "seo_specialist_agent": ROLE,
    "seo-expert": ROLE,
    "qa": "tester",
    "qa-engineer": "tester",
    "frontend-engineer": "frontend",
    "backend-engineer": "backend",
    "documentation": "docs",
    "documentation-engineer": "docs",
    "deployment": "devops",
}
_FORBIDDEN_UNSOURCED_CLAIMS = re.compile(
    r"\b(?:ranking|traffic|search\s*volume|cpc|difficulty|core\s*web\s*vitals|"
    r"search\s*console|analytics|indexed|indexation)\b",
    re.IGNORECASE,
)


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


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _serialise(value: object) -> object:
    if hasattr(value, "as_dict"):
        return value.as_dict()  # type: ignore[no-any-return]
    if isinstance(value, Mapping):
        return {str(key): _serialise(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_serialise(item) for item in value]
    return value


def _payload(value: object, *, max_chars: int = 30000) -> str:
    raw = json.dumps(_serialise(value), ensure_ascii=False, default=str)
    return _clean(raw, max_chars=max_chars)


def _normalise_role(value: object, default: str = "researcher") -> str:
    role = _clean(value, max_chars=128).casefold().replace(" ", "_")
    role = _ROLE_ALIASES.get(role, role)
    return role or default


def _priority_label(value: object) -> str:
    label = _clean(value, max_chars=32).upper()
    if label in SEO_PRIORITIES:
        return label
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        score = max(0, min(100, int(value)))
        if score >= 90:
            return "CRITICAL"
        if score >= 65:
            return "HIGH"
        if score >= 35:
            return "MEDIUM"
        return "LOW"
    return "MEDIUM"


def _priority_number(value: object) -> int:
    label = _priority_label(value)
    return {"CRITICAL": 95, "HIGH": 75, "MEDIUM": 50, "LOW": 25}[label]


def _evidence(values: Iterable[object] | None) -> tuple[dict[str, str], ...]:
    if isinstance(values, str):
        values = (values,)
    result: list[dict[str, str]] = []
    for value in values or ():
        if isinstance(value, Mapping):
            description = _clean(value.get("description") or value.get("evidence") or value.get("summary"))
            source = _clean(value.get("source") or value.get("file") or value.get("url"), max_chars=1000)
            if description:
                item = {"description": description}
                if source:
                    item["source"] = source
                for key in ("data_source", "provider", "observed_at"):
                    detail = _clean(value.get(key), max_chars=1000)
                    if detail:
                        item[key] = detail
                result.append(item)
        else:
            description = _clean(value)
            if description:
                result.append({"description": description})
        if len(result) >= 100:
            break
    return tuple(result)


def _has_external_source(evidence: Sequence[Mapping[str, str]]) -> bool:
    return any(item.get("source") or item.get("data_source") or item.get("provider") for item in evidence)


def _claim_is_unsourced(text: object, evidence: Sequence[Mapping[str, str]]) -> bool:
    return bool(_FORBIDDEN_UNSOURCED_CLAIMS.search(_clean(text))) and not _has_external_source(evidence)


def _finding_data_available(evidence: Sequence[Mapping[str, str]]) -> bool:
    return bool(evidence) and not all(
        _clean(item.get("description"), max_chars=128).upper() in {"DATA NOT AVAILABLE", "DATA SOURCE REQUIRED"}
        for item in evidence
    )


@dataclass(frozen=True)
class SEOFinding:
    finding_id: str
    project_id: str
    category: str
    severity: str
    resource: str
    description: str
    evidence: tuple[dict[str, str], ...]
    impact: str
    recommended_action: str
    responsible_role: str
    acceptance_criteria: tuple[str, ...]
    verification_method: str
    priority: str = "MEDIUM"
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOContentGap:
    gap_id: str
    project_id: str
    target_intent: str
    target_cluster: str
    recommended_page_type: str
    purpose: str
    suggested_outline: tuple[str, ...]
    internal_link_opportunities: tuple[str, ...]
    conversion_objective: str
    evidence: tuple[dict[str, str], ...]
    priority: str = "MEDIUM"
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOContentBrief:
    brief_id: str
    project_id: str
    page_objective: str
    audience: str
    search_intent: str
    primary_topic: str
    secondary_topics: tuple[str, ...]
    questions_to_answer: tuple[str, ...]
    recommended_structure: tuple[str, ...]
    internal_links: tuple[str, ...]
    metadata_recommendation: str
    schema_opportunity: str
    cta_objective: str
    evidence: tuple[dict[str, str], ...]
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOInternalLinkRecommendation:
    recommendation_id: str
    project_id: str
    source_page: str
    target_page: str
    anchor_context: str
    reason: str
    evidence: tuple[dict[str, str], ...]
    priority: str = "MEDIUM"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOImplementationRequest:
    request_id: str
    project_id: str
    title: str
    description: str
    evidence: tuple[dict[str, str], ...]
    affected_resource: str
    responsible_role: str
    acceptance_criteria: tuple[str, ...]
    verification_method: str
    priority: str = "MEDIUM"
    status: str = "pending"
    task_id: str | None = None
    handoff_id: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOVerification:
    verification_id: str
    project_id: str
    task_id: str
    status: str
    evidence: tuple[dict[str, str], ...]
    blocking_reasons: tuple[str, ...]
    responsible_role: str
    verification_method: str
    message_id: str | None = None
    handoff_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class SEOSpecialistAgent:
    """Hands-on SEO analyst that delegates all production changes."""

    ROLE = ROLE
    DISPLAY_NAME = DISPLAY_NAME
    AGENT_ID = AGENT_ID

    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = database_path
        self.bus = MessageBus(database_path)
        self.handoffs = HandoffProtocol(database_path)
        self.memory = MemoryStore(database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id=self.AGENT_ID,
            display_name=self.DISPLAY_NAME,
            department=Department.RESEARCH,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str, *, require_specialist: bool = True) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"SEO task not found: {task_id}")
        if require_specialist and _normalise_role(task.get("role")) != self.ROLE:
            raise ValueError("SEO Specialist can only analyze seo_specialist tasks")
        return task

    def _publish(
        self,
        *,
        message_type: MessageType,
        subject: str,
        body: object,
        project_id: str,
        task_id: str | None = None,
        run_id: str | None = None,
        topic: str,
        recipient_role: str | None = None,
        references: Iterable[object] = (),
    ) -> dict[str, object]:
        return self.bus.publish(
            sender_role=self.ROLE,
            message_type=message_type,
            subject=_clean(subject, max_chars=500),
            body=_payload(body),
            project_id=_clean(project_id, max_chars=128),
            task_id=task_id,
            run_id=run_id,
            recipient_role=recipient_role,
            references=_items(references, max_chars=512),
            topic=topic,
        )

    def _project(self, task: Mapping[str, object], expected: str | None = None) -> str:
        project = _clean(task.get("project_id"), max_chars=128)
        if expected is not None and project != _clean(expected, max_chars=128):
            raise ValueError("SEO Specialist cannot cross project boundaries")
        if not project:
            raise ValueError("SEO task requires a project_id")
        return project

    def create_finding(
        self,
        task_id: str,
        *,
        category: str,
        severity: str,
        resource: str,
        description: str,
        evidence: Iterable[object] = (),
        impact: str,
        recommended_action: str,
        responsible_role: str,
        acceptance_criteria: Iterable[object] = (),
        verification_method: str,
        priority: object = "MEDIUM",
        status: str = "open",
        run_id: str | None = None,
    ) -> SEOFinding:
        task = self._task(task_id)
        project_id = self._project(task)
        sev = _clean(severity, max_chars=32).upper()
        if sev not in SEO_SEVERITIES:
            raise ValueError(f"Unsupported SEO severity: {sev}")
        proof = _evidence(evidence)
        text = " ".join((_clean(description), *(_clean(item.get("description")) for item in proof)))
        unsourced = _claim_is_unsourced(text, proof)
        available = _finding_data_available(proof) and not unsourced
        finding_status = _clean(status, max_chars=64).lower() or "open"
        if not available:
            proof = proof or ({"description": "DATA SOURCE REQUIRED"},)
            if unsourced:
                proof = proof + ({"description": "DATA SOURCE REQUIRED: external analytics or search data was not supplied."},)
            finding_status = "data_not_available"
        role = _normalise_role(responsible_role, "researcher")
        if role == self.ROLE:
            role = "researcher"
        finding = SEOFinding(
            finding_id=str(uuid4()), project_id=project_id,
            category=_clean(category, max_chars=128).casefold(), severity=sev,
            resource=_clean(resource, max_chars=1000), description=_clean(description),
            evidence=proof, impact=_clean(impact), recommended_action=_clean(recommended_action),
            responsible_role=role, acceptance_criteria=_items(acceptance_criteria),
            verification_method=_clean(verification_method, max_chars=2000),
            priority=_priority_label(priority if priority != "MEDIUM" else _SEVERITY_SCORE[sev]),
            status=finding_status,
        )
        message = self._publish(
            message_type=MessageType.EVIDENCE if available else MessageType.BLOCKER,
            subject=f"SEO Specialist finding: {finding.category}", body=finding,
            project_id=project_id, task_id=task_id, run_id=run_id or task.get("run_id"),
            topic="seo_specialist_finding", recipient_role=role, references=tuple(item.get("description", "") for item in proof),
        )
        return SEOFinding(**{**finding.as_dict(), "message_id": str(message["message_id"])})

    def analyze_technical(
        self,
        task_id: str,
        observations: Mapping[str, object],
        *,
        run_id: str | None = None,
    ) -> tuple[SEOFinding, ...]:
        """Convert supplied technical observations into evidence-backed findings."""
        task = self._task(task_id)
        project_id = self._project(task)
        findings: list[SEOFinding] = []
        for category, raw in observations.items():
            item = _mapping(raw)
            evidence = item.get("evidence") or item.get("observed") or ()
            finding = self.create_finding(
                task_id, category=str(category), severity=str(item.get("severity") or item.get("impact") or "MEDIUM"),
                resource=str(item.get("resource") or item.get("url") or item.get("file") or "site-wide"),
                description=str(item.get("issue") or item.get("description") or item.get("summary") or f"Technical SEO observation: {category}"),
                evidence=evidence, impact=str(item.get("impact") or item.get("seo_impact") or "DATA NOT AVAILABLE"),
                recommended_action=str(item.get("recommended_action") or item.get("recommended_fix") or "Collect evidence and define a bounded fix."),
                responsible_role=str(item.get("responsible_role") or "researcher"),
                acceptance_criteria=item.get("acceptance_criteria") or (),
                verification_method=str(item.get("verification_method") or "Repeat the relevant technical inspection."),
                priority=item.get("priority") or "MEDIUM", run_id=run_id,
            )
            findings.append(finding)
        if not observations:
            findings.append(self.create_finding(
                task_id, category="technical_seo", severity="INFO", resource="site-wide",
                description="Technical SEO observations were not supplied.", evidence=(),
                impact="DATA NOT AVAILABLE", recommended_action="Provide an authorized site inspection result.",
                responsible_role="researcher", acceptance_criteria=("Inspection evidence is attached.",),
                verification_method="Repeat the technical SEO inspection.", run_id=run_id,
            ))
        return tuple(findings)

    def analyze_on_page(
        self,
        task_id: str,
        pages: Iterable[Mapping[str, object]],
        *,
        run_id: str | None = None,
    ) -> tuple[SEOFinding, ...]:
        findings: list[SEOFinding] = []
        for page in pages:
            resource = _clean(page.get("resource") or page.get("url") or "page", max_chars=1000)
            evidence = page.get("evidence") or ()
            issues = page.get("issues") or ()
            if isinstance(issues, str):
                issues = (issues,)
            if not issues:
                for field_name, label in (("title", "title"), ("meta_description", "meta description"), ("h1", "H1"), ("image_alt", "image alt text")):
                    if field_name in page and not _clean(page.get(field_name)):
                        issues = (*issues, f"Missing {label}.")
            if not issues:
                continue
            for issue in issues:
                findings.append(self.create_finding(
                    task_id, category="on_page", severity=str(page.get("severity") or "MEDIUM"), resource=resource,
                    description=str(issue), evidence=evidence, impact=str(page.get("impact") or "Potential on-page relevance or accessibility impact."),
                    recommended_action=str(page.get("recommended_action") or "Align the page element with its intended search intent."),
                    responsible_role=str(page.get("responsible_role") or "frontend"),
                    acceptance_criteria=page.get("acceptance_criteria") or ("The page element matches the approved SEO specification.",),
                    verification_method=str(page.get("verification_method") or "Inspect rendered HTML and repeat the on-page check."),
                    priority=page.get("priority") or "MEDIUM", run_id=run_id,
                ))
        return tuple(findings)

    def analyze_keywords(
        self,
        task_id: str,
        clusters: Iterable[Mapping[str, object]],
        *,
        run_id: str | None = None,
    ) -> tuple[SEOKeywordCluster, ...]:
        task = self._task(task_id)
        project_id = self._project(task)
        result: list[SEOKeywordCluster] = []
        seen_pages: dict[str, str] = {}
        for raw in clusters:
            keywords = _items(raw.get("keywords") or raw.get("terms") or ())
            if not keywords:
                raise ValueError("keyword cluster requires at least one keyword")
            name = _clean(raw.get("name") or raw.get("cluster") or keywords[0], max_chars=500)
            intent = _clean(raw.get("intent"), max_chars=64).upper()
            if intent not in SEO_INTENTS:
                intent = "DATA NOT AVAILABLE"
            target_page = _clean(raw.get("target_page"), max_chars=1000)
            current_page = _clean(raw.get("current_page"), max_chars=1000)
            recommended_page = _clean(raw.get("recommended_page"), max_chars=1000)
            page_key = (target_page or current_page or recommended_page).casefold()
            status = "mapped" if page_key else "missing_target_page"
            if page_key and page_key in seen_pages:
                status = "cannibalization"
            elif page_key:
                seen_pages[page_key] = name
            evidence = _evidence(raw.get("evidence") or ())
            cluster = SEOKeywordCluster(
                cluster_id=_clean(raw.get("cluster_id") or raw.get("id"), max_chars=128) or str(uuid4()),
                project_id=project_id, name=name, keywords=keywords, intent=intent,
                language=_clean(raw.get("language") or "DATA NOT AVAILABLE", max_chars=64),
                region=_clean(raw.get("region") or "DATA NOT AVAILABLE", max_chars=128),
                funnel_stage=_clean(raw.get("funnel_stage") or "DATA NOT AVAILABLE", max_chars=128),
                commercial_value=_clean(raw.get("commercial_value") or "DATA SOURCE REQUIRED", max_chars=128),
                target_page=target_page, current_page=current_page, recommended_page=recommended_page,
                priority=_priority_label(raw.get("priority") or "MEDIUM"), status=status,
            )
            message = self._publish(
                message_type=MessageType.BLOCKER if status != "mapped" else MessageType.EVIDENCE,
                subject=f"SEO Specialist keyword cluster: {name}", body={"cluster": cluster, "evidence": evidence},
                project_id=project_id, task_id=task_id, run_id=run_id or task.get("run_id"),
                topic="seo_specialist_keyword_cluster", recipient_role="seo_manager",
                references=(f"keyword_cluster:{cluster.cluster_id}",),
            )
            result.append(SEOKeywordCluster(**{**cluster.as_dict(), "message_id": str(message["message_id"]) }))
        return tuple(result)

    map_keywords = analyze_keywords

    def analyze_content_gaps(
        self,
        task_id: str,
        gaps: Iterable[Mapping[str, object]],
        *,
        run_id: str | None = None,
    ) -> tuple[SEOContentGap, ...]:
        task = self._task(task_id)
        project_id = self._project(task)
        result: list[SEOContentGap] = []
        for raw in gaps:
            proof = _evidence(raw.get("evidence") or ())
            gap = SEOContentGap(
                gap_id=str(uuid4()), project_id=project_id,
                target_intent=_clean(raw.get("target_intent") or "DATA NOT AVAILABLE", max_chars=64).upper(),
                target_cluster=_clean(raw.get("target_cluster") or "DATA NOT AVAILABLE", max_chars=500),
                recommended_page_type=_clean(raw.get("recommended_page_type") or "DATA NOT AVAILABLE", max_chars=128),
                purpose=_clean(raw.get("purpose") or "DATA NOT AVAILABLE"),
                suggested_outline=_items(raw.get("suggested_outline") or raw.get("outline") or ()),
                internal_link_opportunities=_items(raw.get("internal_link_opportunities") or raw.get("internal_links") or ()),
                conversion_objective=_clean(raw.get("conversion_objective") or "DATA NOT AVAILABLE"),
                evidence=proof or ({"description": "DATA SOURCE REQUIRED"},),
                priority=_priority_label(raw.get("priority") or "MEDIUM"),
                status="open" if _finding_data_available(proof) else "data_not_available",
            )
            message = self._publish(
                message_type=MessageType.PROPOSAL if gap.status == "open" else MessageType.BLOCKER,
                subject=f"SEO content gap: {gap.target_cluster}", body=gap, project_id=project_id,
                task_id=task_id, run_id=run_id or task.get("run_id"), topic="seo_specialist_content_gap",
                recipient_role="seo_manager", references=(f"content_gap:{gap.gap_id}",),
            )
            result.append(SEOContentGap(**{**gap.as_dict(), "message_id": str(message["message_id"]) }))
        return tuple(result)

    def create_content_brief(
        self,
        task_id: str,
        *,
        page_objective: str,
        audience: str,
        search_intent: str,
        primary_topic: str,
        secondary_topics: Iterable[object] = (),
        questions_to_answer: Iterable[object] = (),
        recommended_structure: Iterable[object] = (),
        internal_links: Iterable[object] = (),
        metadata_recommendation: str,
        schema_opportunity: str,
        cta_objective: str,
        evidence: Iterable[object] = (),
        run_id: str | None = None,
    ) -> SEOContentBrief:
        task = self._task(task_id)
        project_id = self._project(task)
        proof = _evidence(evidence)
        brief = SEOContentBrief(
            brief_id=str(uuid4()), project_id=project_id, page_objective=_clean(page_objective),
            audience=_clean(audience), search_intent=_clean(search_intent, max_chars=64).upper(),
            primary_topic=_clean(primary_topic), secondary_topics=_items(secondary_topics),
            questions_to_answer=_items(questions_to_answer), recommended_structure=_items(recommended_structure),
            internal_links=_items(internal_links), metadata_recommendation=_clean(metadata_recommendation),
            schema_opportunity=_clean(schema_opportunity), cta_objective=_clean(cta_objective),
            evidence=proof or ({"description": "DATA SOURCE REQUIRED"},),
        )
        message = self._publish(
            message_type=MessageType.PROPOSAL if proof else MessageType.BLOCKER,
            subject=f"SEO content brief: {brief.primary_topic}", body=brief, project_id=project_id,
            task_id=task_id, run_id=run_id or task.get("run_id"), topic="seo_specialist_content_brief",
            recipient_role="seo_manager", references=(f"content_brief:{brief.brief_id}",),
        )
        return SEOContentBrief(**{**brief.as_dict(), "message_id": str(message["message_id"])})

    def recommend_internal_links(
        self,
        task_id: str,
        recommendations: Iterable[Mapping[str, object]],
        *,
        run_id: str | None = None,
    ) -> tuple[SEOInternalLinkRecommendation, ...]:
        task = self._task(task_id)
        project_id = self._project(task)
        result: list[SEOInternalLinkRecommendation] = []
        for raw in recommendations:
            source = _clean(raw.get("source_page"), max_chars=1000)
            target = _clean(raw.get("target_page"), max_chars=1000)
            anchor = _clean(raw.get("anchor_context") or raw.get("anchor_text"), max_chars=1000)
            if not source or not target or not anchor:
                raise ValueError("internal link recommendation requires source_page, target_page and anchor_context")
            recommendation = SEOInternalLinkRecommendation(
                recommendation_id=str(uuid4()), project_id=project_id, source_page=source,
                target_page=target, anchor_context=anchor,
                reason=_clean(raw.get("reason") or "Improve contextual internal linking."),
                evidence=_evidence(raw.get("evidence") or ()) or ({"description": "DATA SOURCE REQUIRED"},),
                priority=_priority_label(raw.get("priority") or "MEDIUM"),
            )
            message = self._publish(
                message_type=MessageType.PROPOSAL, subject="SEO internal link recommendation", body=recommendation,
                project_id=project_id, task_id=task_id, run_id=run_id or task.get("run_id"),
                topic="seo_specialist_internal_linking", recipient_role="seo_manager",
                references=(f"link_recommendation:{recommendation.recommendation_id}",),
            )
            result.append(SEOInternalLinkRecommendation(**{**recommendation.as_dict(), "message_id": str(message["message_id"]) }))
        return tuple(result)

    def create_implementation_request(
        self,
        task_id: str,
        *,
        title: str,
        description: str,
        evidence: Iterable[object] = (),
        affected_resource: str,
        responsible_role: str,
        acceptance_criteria: Iterable[object],
        verification_method: str,
        priority: object = "MEDIUM",
        run_id: str | None = None,
    ) -> SEOImplementationRequest:
        parent = self._task(task_id)
        project_id = self._project(parent)
        role = _normalise_role(responsible_role)
        if role not in _HANDOFF_ROLES or role == self.ROLE:
            raise ValueError(f"Unsupported SEO implementation target: {role}")
        proof = _evidence(evidence)
        acceptance = _items(acceptance_criteria)
        if not acceptance:
            raise ValueError("implementation request requires acceptance criteria")
        request_id = str(uuid4())
        priority_label = _priority_label(priority)
        task = CoordinationTask(
            project_id=project_id, title=_clean(title, max_chars=500),
            description=f"{_clean(description)}\nSEO evidence: {_payload(proof) or 'DATA SOURCE REQUIRED'}",
            role=role, run_id=run_id or parent.get("run_id"), parent_task_id=task_id,
            assigned_agent=f"employee-{role.replace('_', '-')}", state=TaskState.PENDING,
            priority=_priority_number(priority_label), inputs={"seo_evidence": list(proof), "affected_resource": _clean(affected_resource, max_chars=1000), "verification_method": _clean(verification_method, max_chars=2000)},
            expected_outputs=("SEOQualityGate", "verification_result"), acceptance_criteria=acceptance,
            scope=(_clean(affected_resource, max_chars=1000),), writer=role in _WRITABLE_IMPLEMENTATION_ROLES,
        )
        stored = coordination_store.create_task(task, database_path=self.database_path)
        enqueue_work(task.assigned_agent or f"employee-{role}", project_id, "task", task.id, task_id=task.id, priority=task.priority, database_path=self.database_path)
        handoff = self.handoffs.submit(AgentHandoff(
            sender_role=self.ROLE, recipient_role=role, summary=f"SEO implementation request: {_clean(title, max_chars=500)}",
            completed=("SEO evidence and acceptance criteria were prepared.",), artifacts=("seo_finding", "seo_implementation_request"),
            risks=(_clean(description),), remaining_work=acceptance, verification=(_clean(verification_method, max_chars=2000),),
            run_id=task.run_id, project_id=project_id, task_id=task.id,
        ))
        message = self._publish(
            message_type=MessageType.HANDOFF, subject=f"SEO implementation request: {_clean(title, max_chars=500)}",
            body={"request_id": request_id, "task": stored, "handoff": handoff, "evidence": proof},
            project_id=project_id, task_id=task.id, run_id=task.run_id, topic="seo_specialist_implementation_request",
            recipient_role=role, references=(f"task:{task.id}", f"handoff:{handoff['handoff_id']}"),
        )
        return SEOImplementationRequest(
            request_id=request_id, project_id=project_id, title=_clean(title, max_chars=500),
            description=_clean(description), evidence=proof, affected_resource=_clean(affected_resource, max_chars=1000),
            responsible_role=role, acceptance_criteria=acceptance, verification_method=_clean(verification_method, max_chars=2000),
            priority=priority_label, task_id=task.id, handoff_id=str(handoff["handoff_id"]), message_id=str(message["message_id"]),
        )

    def verify_implementation(
        self,
        task_id: str,
        *,
        observed: object,
        expected: object,
        evidence: Iterable[object],
        verification_method: str,
        responsible_role: str | None = None,
        run_id: str | None = None,
    ) -> SEOVerification:
        task = self._task(task_id, require_specialist=False)
        project_id = self._project(task)
        proof = _evidence(evidence)
        same = json.dumps(_serialise(observed), sort_keys=True, ensure_ascii=False, default=str) == json.dumps(_serialise(expected), sort_keys=True, ensure_ascii=False, default=str)
        role = _normalise_role(responsible_role or task.get("role"), "seo_manager")
        blockers: list[str] = []
        if not proof:
            blockers.append("SEO verification requires observable evidence.")
        if not same:
            blockers.append("Observed SEO implementation does not satisfy the expected acceptance criteria.")
        status = "SEO_VERIFIED" if not blockers else "SEO_FAILED"
        handoff_id: str | None = None
        if status == "SEO_FAILED":
            handoff = self.handoffs.submit(AgentHandoff(
                sender_role=self.ROLE, recipient_role=role, summary="SEO verification failed; revision requested.",
                completed=("The implemented SEO change was independently inspected.",), artifacts=("seo_verification",),
                risks=tuple(blockers), remaining_work=("Repair the implementation and rerun SEO verification.",),
                verification=(_clean(verification_method, max_chars=2000),), run_id=run_id or task.get("run_id"), project_id=project_id, task_id=task_id,
            ))
            handoff_id = str(handoff["handoff_id"])
        message = self._publish(
            message_type=MessageType.BLOCKER if status == "SEO_FAILED" else MessageType.RESULT,
            subject=f"SEO implementation verification: {status}",
            body={"task_id": task_id, "status": status, "evidence": proof, "blocking_reasons": blockers},
            project_id=project_id, task_id=task_id, run_id=run_id or task.get("run_id"), topic="seo_specialist_verification",
            recipient_role=role if status == "SEO_FAILED" else "seo_manager", references=tuple(item.get("description", "") for item in proof),
        )
        return SEOVerification(
            verification_id=str(uuid4()), project_id=project_id, task_id=task_id, status=status,
            evidence=proof, blocking_reasons=tuple(blockers), responsible_role=role,
            verification_method=_clean(verification_method, max_chars=2000), message_id=str(message["message_id"]), handoff_id=handoff_id,
        )

    def promote_verified_memory(
        self,
        project_id: str,
        *,
        summary: str,
        content: Mapping[str, object],
        evidence: Iterable[object],
        verification: SEOVerification,
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        project = _clean(project_id, max_chars=128)
        if verification.project_id != project or verification.status != "SEO_VERIFIED":
            raise ValueError("SEO memory promotion requires a verified result from the same project")
        proof = _evidence(evidence)
        if not proof:
            raise ValueError("Verified SEO memory requires evidence")
        return self.memory.create(
            project_id=project, memory_type=MemoryType.PROJECT, summary=_clean(summary, max_chars=1000),
            content=dict(content), evidence=proof, lifecycle=MemoryLifecycle.VALIDATED,
            role=self.ROLE, task_type="seo", run_id=run_id, task_id=task_id or verification.task_id,
            source="seo_specialist",
        )

    def retrieve_knowledge(self, project_id: str, *, query: str = "", limit: int = 8) -> list[dict[str, object]]:
        return self.memory.retrieve(project_id=_clean(project_id, max_chars=128), query=_clean(query), role=self.ROLE, task_type="seo", limit=limit)


# Compatibility aliases keep the role ergonomic without introducing another API layer.
SEOSpecialistAgent.create_technical_finding = SEOSpecialistAgent.create_finding
SEOSpecialistAgent.analyze_technical_seo = SEOSpecialistAgent.analyze_technical
SEOSpecialistAgent.analyze_onpage = SEOSpecialistAgent.analyze_on_page
SEOSpecialistAgent.create_keyword_clusters = SEOSpecialistAgent.analyze_keywords
SEOSpecialistAgent.audit = SEOSpecialistAgent.analyze_technical
SEOSpecialistAgent.verify = SEOSpecialistAgent.verify_implementation
SEOSpecialistAgent.promote_memory = SEOSpecialistAgent.promote_verified_memory
SEOSpecialist = SEOSpecialistAgent

__all__ = [
    "AGENT_ID", "DISPLAY_NAME", "ROLE", "SEO_VERIFICATION_STATUSES", "SEOSpecialist", "SEOSpecialistAgent",
    "SEOFinding", "SEOContentGap", "SEOContentBrief", "SEOInternalLinkRecommendation", "SEOImplementationRequest", "SEOVerification",
]
