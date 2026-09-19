"""Evidence-backed SEO management on top of the existing AI company core.

The SEO Manager is deliberately a managerial/read-only role.  It records
site facts, audit evidence, keyword decisions, delegated work, and quality
gates through the existing coordination, memory, handoff, and decision
stores.  It never writes production source code itself and never invents
analytics that were not supplied by an inspection or an approved data source.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4

from app.coordination import collaboration_store, store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, CoordinationTask, MessageType, TaskState, TechnicalDecision
from app.coordination.project_management import enqueue_work
from app.memory.models import MemoryLifecycle, MemoryType
from app.memory.sanitizer import sanitize_text
from app.memory.store import MemoryStore

from .models import Department, EmployeeStatus
from .store import ensure_employee


SEO_STATUSES = frozenset({"SEO_PENDING", "SEO_IN_PROGRESS", "SEO_REVIEW", "SEO_VERIFIED", "SEO_FAILED"})
SEO_PRIORITIES = frozenset({"CRITICAL", "HIGH", "MEDIUM", "LOW"})
SEO_INTENTS = frozenset({"INFORMATIONAL", "COMMERCIAL", "TRANSACTIONAL", "NAVIGATIONAL", "LOCAL"})

SEO_AUDIT_CATEGORIES = (
    "robots_txt", "xml_sitemap", "indexability", "canonical_tags", "http_status_codes",
    "redirects", "duplicate_pages", "url_structure", "page_titles", "meta_descriptions",
    "heading_hierarchy", "internal_links", "orphan_pages", "broken_links", "image_seo",
    "structured_data", "mobile_behavior", "performance_signals", "crawlability",
    "rendering", "pagination", "hreflang", "multilingual_structure", "thin_pages",
    "duplicate_content", "javascript_seo", "site_architecture",
)

_ROLE_BY_CATEGORY = {
    "robots_txt": "devops", "xml_sitemap": "devops", "indexability": "backend",
    "canonical_tags": "frontend", "http_status_codes": "devops", "redirects": "devops",
    "duplicate_pages": "seo_manager", "url_structure": "architect", "page_titles": "frontend",
    "meta_descriptions": "frontend", "heading_hierarchy": "frontend", "internal_links": "frontend",
    "orphan_pages": "researcher", "broken_links": "integration", "image_seo": "frontend",
    "structured_data": "backend", "mobile_behavior": "frontend", "performance_signals": "devops",
    "crawlability": "devops", "rendering": "frontend", "pagination": "frontend",
    "hreflang": "frontend", "multilingual_structure": "architect", "thin_pages": "researcher",
    "duplicate_content": "researcher", "javascript_seo": "frontend", "site_architecture": "architect",
}

_ROLE_ALIASES = {
    "seo": "seo_manager", "seo-manager": "seo_manager", "search-optimization": "seo_manager",
    "search_optimization": "seo_manager", "seo-manager-agent": "seo_manager", "seo-specialist": "seo_specialist", "seo_expert": "seo_specialist",
    "frontend-engineer": "frontend", "backend-engineer": "backend", "deployment": "devops",
    "qa": "tester", "test": "tester", "documentation": "docs",
}
_IMPLEMENTING_ROLES = frozenset({"backend", "frontend", "implementer", "integration", "devops", "docs", "architect", "researcher", "tester", "reviewer", "security"})
_DELEGATABLE_ROLES = _IMPLEMENTING_ROLES | frozenset({"seo_specialist"})
_PRIORITY_SCORE = {"CRITICAL": 95, "HIGH": 75, "MEDIUM": 50, "LOW": 25}


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


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _serialise(value: object) -> object:
    if hasattr(value, "as_dict"):
        return value.as_dict()  # type: ignore[no-any-return]
    if isinstance(value, Mapping):
        return {str(key): _serialise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_serialise(item) for item in value]
    return value


def _payload(value: object, *, max_chars: int = 30000) -> str:
    raw = json.dumps(_serialise(value), ensure_ascii=False, default=str)
    return _clean(raw, max_chars=max_chars)


def _normalise_role(value: object, default: str = "researcher") -> str:
    role = _clean(value, max_chars=128).casefold().replace(" ", "_")
    return _ROLE_ALIASES.get(role, role) if role else default


def _priority_number(value: object) -> int:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0, min(100, int(value)))
    label = _clean(value, max_chars=32).upper()
    return _PRIORITY_SCORE.get(label, 50)


def _priority_label(value: object) -> str:
    if isinstance(value, str) and value.strip().upper() in SEO_PRIORITIES:
        return value.strip().upper()
    score = _priority_number(value)
    if score >= 90:
        return "CRITICAL"
    if score >= 65:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def _numeric(value: object, *, default: float = 0.0, maximum: float = 100.0) -> float:
    if isinstance(value, bool):
        return maximum if value else 0.0
    if isinstance(value, (int, float)):
        return max(0.0, min(maximum, float(value)))
    text = _clean(value, max_chars=32).casefold()
    named = {"critical": maximum, "high": maximum * 0.8, "medium": maximum * 0.5, "low": maximum * 0.2, "none": 0.0}
    if text in named:
        return named[text]
    try:
        return max(0.0, min(maximum, float(text)))
    except (TypeError, ValueError):
        return default


def _evidence_items(values: Iterable[object]) -> tuple[dict[str, str], ...]:
    if isinstance(values, str):
        values = (values,)
    result: list[dict[str, str]] = []
    for value in values:
        if isinstance(value, Mapping):
            description = _clean(value.get("description") or value.get("evidence") or value.get("summary"), max_chars=4000)
            source = _clean(value.get("source") or value.get("file") or value.get("url"), max_chars=1000)
            if description:
                item = {"description": description}
                if source:
                    item["source"] = source
                result.append(item)
        else:
            description = _clean(value, max_chars=4000)
            if description:
                result.append({"description": description})
        if len(result) >= 100:
            break
    return tuple(result)


@dataclass(frozen=True)
class SEOProjectProfile:
    profile_id: str
    project_id: str
    site_domain: str
    business_type: str
    products_services: tuple[str, ...]
    target_audience: tuple[str, ...]
    target_countries: tuple[str, ...]
    target_languages: tuple[str, ...]
    conversion_objectives: tuple[str, ...]
    cms_framework: str
    site_structure: tuple[str, ...]
    existing_seo_state: tuple[str, ...]
    competitors: tuple[str, ...]
    target_keywords: tuple[str, ...]
    technical_limitations: tuple[str, ...]
    seo_risks: tuple[str, ...]
    unknown_fields: tuple[str, ...] = ()
    status: str = "profiled"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOAuditFinding:
    finding_id: str
    project_id: str
    category: str
    title: str
    problem: str
    evidence: tuple[str, ...]
    seo_impact: str
    affected_urls_or_files: tuple[str, ...]
    recommended_action: str
    responsible_role: str
    priority: str
    confidence: float
    verification_method: str
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOKeywordCluster:
    cluster_id: str
    project_id: str
    name: str
    keywords: tuple[str, ...]
    intent: str
    language: str
    region: str
    funnel_stage: str
    commercial_value: str
    target_page: str
    current_page: str
    recommended_page: str
    priority: str
    status: str = "mapped"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOBacklogTask:
    task_id: str
    project_id: str
    title: str
    problem: str
    evidence: tuple[str, ...]
    seo_impact: str
    affected_scope: tuple[str, ...]
    recommended_action: str
    responsible_role: str
    priority: str
    acceptance_criteria: tuple[str, ...]
    verification_method: str
    status: str = "SEO_PENDING"
    handoff_id: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOQualityGate:
    task_id: str
    project_id: str
    status: str
    evidence: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()
    responsible_role: str = "seo_manager"
    verification_method: str = ""
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SEOReport:
    project_id: str
    summary: str
    priorities: tuple[SEOAuditFinding, ...]
    keyword_map: tuple[SEOKeywordCluster, ...]
    content_gap_summary: tuple[str, ...]
    technical_issues: tuple[SEOAuditFinding, ...]
    implementation_status: tuple[SEOQualityGate, ...]
    blockers: tuple[str, ...]
    verification_results: tuple[str, ...]
    next_actions: tuple[str, ...]
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["priorities"] = [item.as_dict() for item in self.priorities]
        result["keyword_map"] = [item.as_dict() for item in self.keyword_map]
        result["technical_issues"] = [item.as_dict() for item in self.technical_issues]
        result["implementation_status"] = [item.as_dict() for item in self.implementation_status]
        return result


class SEOManagerAgent:
    """SEO strategy and verification manager using existing company stores."""

    ROLE = "seo_manager"
    DISPLAY_NAME = "SEO Manager"
    AGENT_ID = "employee-seo-manager"

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
            department=Department.PRODUCT,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"SEO task not found: {task_id}")
        if _normalise_role(task.get("role")) != self.ROLE:
            raise ValueError("SEO Manager can only operate seo_manager tasks")
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
            project_id=project_id,
            task_id=task_id,
            run_id=run_id,
            recipient_role=recipient_role,
            references=_items(references, max_chars=512),
            topic=topic,
        )

    def create_site_profile(
        self,
        project_id: str,
        *,
        site_domain: str | None,
        business_type: str | None,
        products_services: Iterable[object] = (),
        target_audience: Iterable[object] = (),
        target_countries: Iterable[object] = (),
        target_languages: Iterable[object] = (),
        conversion_objectives: Iterable[object] = (),
        cms_framework: str | None = None,
        site_structure: Iterable[object] = (),
        existing_seo_state: Iterable[object] = (),
        competitors: Iterable[object] = (),
        target_keywords: Iterable[object] = (),
        technical_limitations: Iterable[object] = (),
        seo_risks: Iterable[object] = (),
        unknown_fields: Iterable[object] = (),
        run_id: str | None = None,
    ) -> SEOProjectProfile:
        project = _clean(project_id, max_chars=128)
        if not project:
            raise ValueError("project_id is required")
        unknown = list(_items(unknown_fields))
        values = {
            "site_domain": _clean(site_domain, max_chars=512),
            "business_type": _clean(business_type, max_chars=512),
            "cms_framework": _clean(cms_framework, max_chars=512),
        }
        for key, value in values.items():
            if not value:
                values[key] = "DATA NOT AVAILABLE"
                if key not in unknown:
                    unknown.append(key)
        profile = SEOProjectProfile(
            profile_id=str(uuid4()), project_id=project, site_domain=values["site_domain"],
            business_type=values["business_type"], products_services=_items(products_services),
            target_audience=_items(target_audience), target_countries=_items(target_countries),
            target_languages=_items(target_languages), conversion_objectives=_items(conversion_objectives),
            cms_framework=values["cms_framework"], site_structure=_items(site_structure),
            existing_seo_state=_items(existing_seo_state), competitors=_items(competitors),
            target_keywords=_items(target_keywords), technical_limitations=_items(technical_limitations),
            seo_risks=_items(seo_risks), unknown_fields=tuple(unknown),
        )
        message = self._publish(
            message_type=MessageType.STATUS,
            subject="SEO site profile created",
            body=profile,
            project_id=project,
            run_id=run_id,
            topic="seo_site_profile",
        )
        return SEOProjectProfile(**{**profile.as_dict(), "message_id": str(message["message_id"])})

    def calculate_priority(
        self,
        *,
        seo_impact: object,
        business_impact: object,
        severity: object,
        affected_page_count: object,
        implementation_effort: object,
        dependency: object,
        confidence: object,
    ) -> str:
        severity_label = _clean(severity, max_chars=32).upper()
        impact = _numeric(seo_impact) / 100.0 * 30.0
        business = _numeric(business_impact) / 100.0 * 25.0
        pages = min(15.0, math.log2(max(1.0, _numeric(affected_page_count, maximum=100000.0) + 1.0)) * 3.0)
        effort = _numeric(implementation_effort) / 100.0 * 15.0
        dependency_bonus = _numeric(dependency) / 100.0 * 10.0
        confidence_score = _numeric(confidence) / 100.0 * 10.0
        score = impact + business + pages + dependency_bonus + confidence_score - effort
        if severity_label == "CRITICAL" or score >= 85:
            return "CRITICAL"
        if score >= 60 or (severity_label == "HIGH" and score >= 42):
            return "HIGH"
        if score >= 30 or severity_label == "MEDIUM":
            return "MEDIUM"
        return "LOW"

    prioritize_finding = calculate_priority

    def audit_site(
        self,
        task_id: str,
        *,
        audit: Mapping[str, object] | Iterable[Mapping[str, object]],
        available_data: Iterable[object] = (),
        required_categories: Iterable[str] | None = None,
        run_id: str | None = None,
    ) -> tuple[SEOAuditFinding, ...]:
        task = self._task(task_id)
        project_id = str(task["project_id"])
        if isinstance(audit, Mapping):
            raw_map = {str(key): value for key, value in audit.items() if str(key) != "__required_categories"}
            requested = tuple(required_categories or audit.get("__required_categories") or SEO_AUDIT_CATEGORIES)
        else:
            raw_map = {}
            for item in audit:
                if isinstance(item, Mapping):
                    key = _clean(item.get("category"), max_chars=128)
                    if key:
                        raw_map[key] = item
            requested = tuple(required_categories or SEO_AUDIT_CATEGORIES)
        if not requested:
            requested = SEO_AUDIT_CATEGORIES
        available = {_clean(item, max_chars=128) for item in available_data}
        findings: list[SEOAuditFinding] = []
        for category in requested:
            category_name = _clean(category, max_chars=128).casefold()
            raw = raw_map.get(category_name, raw_map.get(str(category), {}))
            item = _as_mapping(raw)
            evidence = _items(item.get("evidence") or item.get("proof") or item.get("observed") or ())
            if item.get("data_available") is False or not evidence or _clean(raw, max_chars=64).upper() == "DATA NOT AVAILABLE":
                evidence = ("DATA NOT AVAILABLE",)
                data_status = "data_not_available"
                title = _clean(item.get("title") or f"SEO data unavailable: {category_name}", max_chars=500)
                problem = _clean(item.get("problem") or f"No observable evidence was supplied for {category_name}.", max_chars=4000)
                confidence = 0.0
            else:
                data_status = "open"
                title = _clean(item.get("title") or item.get("name") or category_name.replace("_", " ").title(), max_chars=500)
                problem = _clean(item.get("problem") or item.get("issue") or item.get("summary") or "Observed SEO issue requires review.", max_chars=4000)
                confidence = _numeric(item.get("confidence"), default=50.0) / 100.0
            severity = item.get("severity") or item.get("impact") or "MEDIUM"
            priority = _priority_label(item.get("priority") or self.calculate_priority(
                seo_impact=item.get("seo_impact") or item.get("impact") or severity,
                business_impact=item.get("business_impact") or severity,
                severity=severity,
                affected_page_count=item.get("affected_page_count") or len(_items(item.get("affected_urls_or_files") or item.get("affected") or ())),
                implementation_effort=item.get("implementation_effort") or "MEDIUM",
                dependency=item.get("dependency") or "MEDIUM",
                confidence=item.get("confidence") or (0 if data_status == "data_not_available" else 50),
            ))
            responsible = _normalise_role(item.get("responsible_role") or _ROLE_BY_CATEGORY.get(category_name), _ROLE_BY_CATEGORY.get(category_name, "researcher"))
            if responsible == self.ROLE:
                responsible = "researcher"
            finding = SEOAuditFinding(
                finding_id=str(uuid4()), project_id=project_id, category=category_name,
                title=title, problem=problem, evidence=evidence,
                seo_impact=_clean(item.get("seo_impact") or severity, max_chars=256),
                affected_urls_or_files=_items(item.get("affected_urls_or_files") or item.get("affected") or ()),
                recommended_action=_clean(item.get("recommended_action") or item.get("action") or "Collect evidence and define an implementation action.", max_chars=4000),
                responsible_role=responsible, priority=priority, confidence=confidence,
                verification_method=_clean(item.get("verification_method") or "Repeat the relevant inspection and attach evidence.", max_chars=2000),
                status=data_status,
            )
            message_type = MessageType.BLOCKER if data_status == "data_not_available" else MessageType.EVIDENCE
            message = self._publish(
                message_type=message_type, subject=f"SEO audit: {finding.title}", body=finding,
                project_id=project_id, task_id=task_id, run_id=run_id or task.get("run_id"),
                topic="seo_audit", recipient_role=responsible, references=finding.evidence,
            )
            findings.append(SEOAuditFinding(**{**finding.as_dict(), "message_id": str(message["message_id"]) }))
        return tuple(findings)

    audit = audit_site

    def build_keyword_map(
        self,
        project_id: str,
        clusters: Iterable[Mapping[str, object]],
        *,
        run_id: str | None = None,
    ) -> tuple[SEOKeywordCluster, ...]:
        project = _clean(project_id, max_chars=128)
        if not project:
            raise ValueError("project_id is required")
        result: list[SEOKeywordCluster] = []
        seen_pages: dict[str, str] = {}
        for raw in clusters:
            name = _clean(raw.get("name") or raw.get("cluster") or raw.get("title"), max_chars=500) or "Unnamed keyword cluster"
            keywords = _items(raw.get("keywords") or raw.get("terms") or ())
            if not keywords:
                raise ValueError("keyword cluster requires at least one keyword")
            raw_intent = _clean(raw.get("intent"), max_chars=64).upper()
            intent = raw_intent if raw_intent in SEO_INTENTS else "DATA NOT AVAILABLE"
            target_page = _clean(raw.get("target_page"), max_chars=1000)
            current_page = _clean(raw.get("current_page"), max_chars=1000)
            recommended_page = _clean(raw.get("recommended_page"), max_chars=1000)
            page_key = (target_page or current_page or recommended_page).casefold()
            status = "mapped" if page_key else "missing_target_page"
            if page_key and page_key in seen_pages:
                status = "cannibalization"
            elif page_key:
                seen_pages[page_key] = name
            if status == "cannibalization":
                recommended_page = recommended_page or target_page or current_page
            cluster = SEOKeywordCluster(
                cluster_id=_clean(raw.get("cluster_id") or raw.get("id"), max_chars=128) or str(uuid4()),
                project_id=project, name=name, keywords=keywords, intent=intent,
                language=_clean(raw.get("language") or "DATA NOT AVAILABLE", max_chars=64),
                region=_clean(raw.get("region") or "DATA NOT AVAILABLE", max_chars=128),
                funnel_stage=_clean(raw.get("funnel_stage") or "DATA NOT AVAILABLE", max_chars=128),
                commercial_value=_clean(raw.get("commercial_value") or "DATA NOT AVAILABLE", max_chars=128),
                target_page=target_page, current_page=current_page, recommended_page=recommended_page,
                priority=_priority_label(raw.get("priority") or "MEDIUM"), status=status,
            )
            message_type = MessageType.BLOCKER if status in {"cannibalization", "missing_target_page"} else MessageType.RESULT
            message = self._publish(
                message_type=message_type, subject=f"SEO keyword map: {cluster.name}", body=cluster,
                project_id=project, run_id=run_id, topic="seo_keyword_map",
                references=(f"keyword_cluster:{cluster.cluster_id}",),
            )
            result.append(SEOKeywordCluster(**{**cluster.as_dict(), "message_id": str(message["message_id"]) }))
        return tuple(result)

    map_keywords = build_keyword_map

    def generate_backlog_tasks(
        self,
        task_id: str,
        findings: Iterable[SEOAuditFinding | Mapping[str, object]],
        *,
        run_id: str | None = None,
    ) -> tuple[SEOBacklogTask, ...]:
        parent = self._task(task_id)
        project_id = str(parent["project_id"])
        result: list[SEOBacklogTask] = []
        for raw in findings:
            finding = raw.as_dict() if isinstance(raw, SEOAuditFinding) else dict(raw)
            role = _normalise_role(finding.get("responsible_role"), "researcher")
            if role == self.ROLE:
                role = "researcher"
            if role not in _DELEGATABLE_ROLES:
                role = "researcher"
            priority = _priority_label(finding.get("priority") or "MEDIUM")
            title = _clean(finding.get("title") or finding.get("problem") or "SEO action", max_chars=500)
            evidence = _items(finding.get("evidence") or ())
            scope = _items(finding.get("affected_urls_or_files") or finding.get("affected_scope") or ())
            acceptance = _items(finding.get("acceptance_criteria") or (f"The SEO issue '{title}' is corrected and the verification evidence is attached.",))
            verification = _clean(finding.get("verification_method") or "Repeat the SEO inspection and record observable evidence.", max_chars=2000)
            task = CoordinationTask(
                project_id=project_id, title=title,
                description=f"{_clean(finding.get('problem') or title)}\nEvidence: {'; '.join(evidence) or 'DATA NOT AVAILABLE'}\nRecommended action: {_clean(finding.get('recommended_action') or 'Define an evidence-backed fix.')}",
                role=role, run_id=run_id or parent.get("run_id"), parent_task_id=task_id,
                assigned_agent=f"employee-{role.replace('_', '-')}", state=TaskState.PENDING,
                priority=_priority_number(priority), inputs={"seo_impact": _clean(finding.get("seo_impact") or "DATA NOT AVAILABLE"), "evidence": list(evidence), "affected_scope": list(scope), "verification_method": verification},
                expected_outputs=("SEOQualityGate", "verification_result"), acceptance_criteria=acceptance,
                scope=scope, writer=role in _IMPLEMENTING_ROLES,
            )
            stored = coordination_store.create_task(task, database_path=self.database_path)
            enqueue_work(task.assigned_agent or f"employee-{role}", project_id, "task", task.id, task_id=task.id, priority=_priority_number(priority), database_path=self.database_path)
            handoff = self.handoffs.submit(AgentHandoff(
                sender_role=self.ROLE, recipient_role=role, summary=f"SEO work delegated: {title}",
                completed=("SEO finding was converted into an actionable task.",), artifacts=("seo_finding", "seo_backlog_task"),
                risks=(_clean(finding.get("problem") or title),), remaining_work=acceptance,
                verification=(verification,), run_id=task.run_id, project_id=project_id, task_id=task.id,
            ))
            message = self._publish(
                message_type=MessageType.HANDOFF, subject=f"SEO task delegated: {title}",
                body={"task": stored, "handoff": handoff, "finding": finding}, project_id=project_id,
                task_id=task.id, run_id=task.run_id, topic="seo_task_delegation", recipient_role=role,
                references=(f"task:{task.id}", f"handoff:{handoff['handoff_id']}"),
            )
            result.append(SEOBacklogTask(
                task_id=task.id, project_id=project_id, title=title,
                problem=_clean(finding.get("problem") or title), evidence=evidence,
                seo_impact=_clean(finding.get("seo_impact") or "DATA NOT AVAILABLE"), affected_scope=scope,
                recommended_action=_clean(finding.get("recommended_action") or "Define an evidence-backed fix."),
                responsible_role=role, priority=priority, acceptance_criteria=acceptance,
                verification_method=verification, handoff_id=str(handoff["handoff_id"]), message_id=str(message["message_id"]),
            ))
        return tuple(result)

    create_tasks = generate_backlog_tasks

    def delegate_task(
        self,
        task_id: str,
        *,
        title: str,
        problem: str,
        responsible_role: str,
        evidence: Iterable[object] = (),
        acceptance_criteria: Iterable[object] = (),
        verification_method: str,
        priority: object = "MEDIUM",
        seo_impact: str = "DATA NOT AVAILABLE",
        affected_scope: Iterable[object] = (),
        run_id: str | None = None,
    ) -> SEOBacklogTask:
        rows = self.generate_backlog_tasks(task_id, ({
            "title": title, "problem": problem, "responsible_role": responsible_role,
            "evidence": tuple(evidence), "acceptance_criteria": tuple(acceptance_criteria),
            "verification_method": verification_method, "priority": priority,
            "seo_impact": seo_impact, "affected_urls_or_files": tuple(affected_scope),
        },), run_id=run_id)
        return rows[0]

    def record_decision(
        self,
        project_id: str,
        *,
        title: str,
        context: str,
        decision: str,
        options: Iterable[object] = (),
        arguments: Iterable[object] = (),
        evidence: Iterable[object] = (),
        affected_tasks: Iterable[object] = (),
        decision_maker: str = ROLE,
        run_id: str | None = None,
    ) -> dict[str, object]:
        supporting = _items(evidence)
        if not supporting:
            raise ValueError("SEO decisions require supporting evidence")
        row = collaboration_store.create_decision(
            TechnicalDecision(
                project_id=_clean(project_id, max_chars=128), title=_clean(title, max_chars=500),
                context=_clean(context, max_chars=4000), decision=_clean(decision, max_chars=4000),
                decision_maker=_normalise_role(decision_maker, self.ROLE), options=_items(options),
                arguments=_items(arguments), supporting_evidence=supporting, affected_tasks=_items(affected_tasks),
                run_id=run_id,
            ), database_path=self.database_path,
        )
        self._publish(
            message_type=MessageType.DECISION, subject=f"SEO decision: {_clean(title, max_chars=500)}",
            body=row, project_id=_clean(project_id, max_chars=128), run_id=run_id,
            topic="seo_decision", references=(f"decision:{row['decision_id']}",),
        )
        return row

    create_decision = record_decision

    def quality_gate(
        self,
        task_id: str,
        *,
        status: str,
        evidence: Iterable[object] = (),
        blocking_reasons: Iterable[object] = (),
        responsible_role: str | None = None,
        verification_method: str = "",
        run_id: str | None = None,
    ) -> SEOQualityGate:
        task = self._task(task_id)
        project_id = str(task["project_id"])
        requested = _clean(status, max_chars=64).upper()
        if requested not in SEO_STATUSES:
            raise ValueError(f"Unsupported SEO quality status: {requested}")
        proof = _items(evidence)
        blockers = list(_items(blocking_reasons))
        final_status = requested
        if requested == "SEO_VERIFIED" and (not proof or blockers):
            final_status = "SEO_FAILED"
            if not proof:
                blockers.append("Verification requires observable evidence.")
            if not blockers:
                blockers.append("Verification has unresolved blocking reasons.")
        if final_status == "SEO_FAILED" and not blockers:
            blockers.append("SEO verification failed; responsible agent must provide a repair and rerun verification.")
        role = _normalise_role(responsible_role, self.ROLE)
        gate = SEOQualityGate(task_id=task_id, project_id=project_id, status=final_status, evidence=proof, blocking_reasons=tuple(blockers), responsible_role=role, verification_method=_clean(verification_method, max_chars=2000))
        message = self._publish(
            message_type=MessageType.BLOCKER if final_status == "SEO_FAILED" else MessageType.RESULT,
            subject=f"SEO quality gate: {final_status}", body=gate, project_id=project_id,
            task_id=task_id, run_id=run_id or task.get("run_id"), topic="seo_quality_gate",
            recipient_role=role if final_status == "SEO_FAILED" else None, references=proof,
        )
        return SEOQualityGate(**{**gate.as_dict(), "message_id": str(message["message_id"]) })

    def verify_seo_task(
        self,
        task_id: str,
        *,
        observed: object,
        expected: object,
        evidence: Iterable[object],
        verification_method: str,
        responsible_role: str | None = None,
        run_id: str | None = None,
    ) -> SEOQualityGate:
        proof = _items(evidence)
        observed_value = json.dumps(_serialise(observed), sort_keys=True, ensure_ascii=False, default=str)
        expected_value = json.dumps(_serialise(expected), sort_keys=True, ensure_ascii=False, default=str)
        if observed_value != expected_value:
            return self.quality_gate(task_id, status="SEO_FAILED", evidence=proof, blocking_reasons=("Observed SEO result does not satisfy the expected acceptance criteria.",), responsible_role=responsible_role, verification_method=verification_method, run_id=run_id)
        return self.quality_gate(task_id, status="SEO_VERIFIED", evidence=proof, responsible_role=responsible_role, verification_method=verification_method, run_id=run_id)

    verify = verify_seo_task

    def remember_validated_knowledge(
        self,
        project_id: str,
        *,
        summary: str,
        content: Mapping[str, object],
        evidence: Iterable[object],
        lifecycle: str | MemoryLifecycle = MemoryLifecycle.CANDIDATE,
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        raw_evidence = _evidence_items(evidence)
        state = lifecycle.value if isinstance(lifecycle, MemoryLifecycle) else _clean(lifecycle, max_chars=32).casefold()
        if state in {MemoryLifecycle.VALIDATED.value, MemoryLifecycle.TRUSTED.value} and not raw_evidence:
            raise ValueError("Validated SEO knowledge requires evidence")
        return self.memory.create(
            project_id=_clean(project_id, max_chars=128), memory_type=MemoryType.PROJECT,
            summary=_clean(summary, max_chars=1000), content=dict(content), evidence=raw_evidence,
            lifecycle=state, role=self.ROLE, task_type="seo", run_id=run_id, task_id=task_id,
            source="seo_manager",
        )

    def retrieve_knowledge(self, project_id: str, *, query: str = "", limit: int = 8) -> list[dict[str, object]]:
        return self.memory.retrieve(project_id=_clean(project_id, max_chars=128), query=_clean(query, max_chars=1000), role=self.ROLE, task_type="seo", limit=limit)

    def report(
        self,
        project_id: str,
        *,
        summary: str,
        priorities: Iterable[SEOAuditFinding] = (),
        keyword_map: Iterable[SEOKeywordCluster] = (),
        content_gap_summary: Iterable[object] = (),
        technical_issues: Iterable[SEOAuditFinding] = (),
        implementation_status: Iterable[SEOQualityGate] = (),
        blockers: Iterable[object] = (),
        verification_results: Iterable[object] = (),
        next_actions: Iterable[object] = (),
        run_id: str | None = None,
    ) -> SEOReport:
        report = SEOReport(
            project_id=_clean(project_id, max_chars=128), summary=_clean(summary, max_chars=4000),
            priorities=tuple(priorities), keyword_map=tuple(keyword_map), content_gap_summary=_items(content_gap_summary),
            technical_issues=tuple(technical_issues), implementation_status=tuple(implementation_status),
            blockers=_items(blockers), verification_results=_items(verification_results), next_actions=_items(next_actions),
        )
        message = self._publish(message_type=MessageType.RESULT, subject="SEO report", body=report, project_id=report.project_id, run_id=run_id, topic="seo_report")
        return SEOReport(**{**report.as_dict(), "message_id": str(message["message_id"]), "priorities": report.priorities, "keyword_map": report.keyword_map, "technical_issues": report.technical_issues, "implementation_status": report.implementation_status})


SEOManager = SEOManagerAgent

__all__ = [
    "SEO_AUDIT_CATEGORIES", "SEO_INTENTS", "SEO_PRIORITIES", "SEO_STATUSES",
    "SEOAuditFinding", "SEOBacklogTask", "SEOKeywordCluster", "SEOManager", "SEOManagerAgent",
    "SEOProjectProfile", "SEOQualityGate", "SEOReport",
]
