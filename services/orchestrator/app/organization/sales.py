from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable

from app.coordination.bus import MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.coordination.owner_control import ClientMessage, create_project_opportunity
from app.coordination import store as coordination_store
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_TECHNICAL_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("backend", ("backend", "api", "fastapi", "django", "node", "service")),
    ("frontend", ("frontend", "react", "vue", "web app", "browser", "ui")),
    ("mobile", ("mobile", "android", "ios", "react native", "flutter")),
    ("database", ("database", "sqlite", "postgres", "mysql", "migration")),
    ("security", ("security", "authentication", "authorization", "oauth", "compliance")),
    ("deployment", ("deploy", "hosting", "docker", "kubernetes", "production")),
    ("testing", ("test", "qa", "quality", "acceptance")),
)
_UNSUPPORTED_MARKERS = ("legal advice", "malware", "credential theft", "guaranteed investment return")
_COMMITMENT_TYPES = {"external_commitment", "financial_commitment", "legal_commitment"}


def _items(values: Iterable[object], *, limit: int = 20, max_chars: int = 500) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        clean, _ = sanitize_text(str(value or ""), max_chars=max_chars)
        clean = clean.strip()
        if clean and clean not in result:
            result.append(clean)
        if len(result) >= limit:
            break
    return tuple(result)


@dataclass(frozen=True)
class ClientNeedsSummary:
    summary: str
    deliverables: tuple[str, ...] = ()
    technical_areas: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OpenQuestions:
    questions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Risks:
    items: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RecommendedNextAction:
    action: str
    reason: str
    target_role: str | None = None
    requires_authorization: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProposalDraft:
    opportunity_id: str | None
    scope: str
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]
    exclusions: tuple[str, ...]
    status: str = "draft"
    requires_human_owner_approval: bool = True
    financial_commitment_allowed: bool = False
    deadline_commitment_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OpportunityBrief:
    opportunity_id: str | None
    source: str
    title: str
    project_type: str
    qualification: str
    client_needs: ClientNeedsSummary
    open_questions: OpenQuestions
    risks: Risks
    recommended_next_action: RecommendedNextAction
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "opportunity_id": self.opportunity_id,
            "source": self.source,
            "title": self.title,
            "project_type": self.project_type,
            "qualification": self.qualification,
            "client_needs_summary": self.client_needs.as_dict(),
            "open_questions": self.open_questions.as_dict(),
            "risks": self.risks.as_dict(),
            "recommended_next_action": self.recommended_next_action.as_dict(),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class CommercialEscalation:
    commitment_type: str
    reason: str
    message_id: str
    recipient_role: str = "company_director"
    escalation_target: str = "human_owner"
    status: str = "pending_human_owner"
    requires_human_owner: bool = True
    commitment_made: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class SalesAgent:
    """Business-facing facade over existing opportunities, messages and handoffs.

    Sales never writes source files, makes commitments, or starts implementation.
    It only creates a sanitized opportunity record and structured coordination
    artifacts for the existing company workflow.
    """

    ROLE = "sales"
    DISPLAY_NAME = "Sales / Business Development"

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = database_path
        self.bus = MessageBus(str(database_path) if database_path is not None else None)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-sales",
            display_name=self.DISPLAY_NAME,
            department=Department.PRODUCT,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    @staticmethod
    def _project_type(text: str) -> str:
        lowered = text.casefold()
        if any(marker in lowered for marker in ("mobile", "android", "ios", "flutter")):
            return "mobile_application"
        if any(marker in lowered for marker in ("api", "backend", "service", "fastapi", "django")):
            return "software_service"
        if any(marker in lowered for marker in ("website", "web app", "frontend", "browser")):
            return "web_application"
        return "software_project"

    @staticmethod
    def _technical_areas(text: str) -> tuple[str, ...]:
        lowered = text.casefold()
        return tuple(
            area for area, keywords in _TECHNICAL_KEYWORDS if any(keyword in lowered for keyword in keywords)
        )

    def qualify(
        self,
        message: ClientMessage | None = None,
        *,
        source: str = "",
        title: str = "",
        body: str = "",
        requirements: Iterable[str] = (),
        company_capabilities: Iterable[str] = (),
    ) -> OpportunityBrief:
        if message is not None:
            source = message.source
            title = title or message.external_ref or "Incoming project opportunity"
            body = message.body
        clean_source, _ = sanitize_text(str(source or ""), max_chars=128)
        clean_title, _ = sanitize_text(str(title or ""), max_chars=500)
        clean_body, _ = sanitize_text(str(body or ""), max_chars=10_000)
        clean_requirements = _items(requirements)
        combined = " ".join((clean_title, clean_body, *clean_requirements)).strip()
        areas = self._technical_areas(combined)
        deliverables = clean_requirements or _items(
            part.strip() for part in clean_body.replace(";", "\n").splitlines() if part.strip()
        )
        summary = (clean_body or clean_title).strip()[:2_000]
        questions: list[str] = []
        if not deliverables:
            questions.append("Which user-visible deliverables are required?")
        if not any("acceptance" in item.casefold() or "test" in item.casefold() for item in deliverables):
            questions.append("What acceptance criteria and verification evidence define success?")
        if not areas:
            questions.append("Which platforms, integrations, and technical constraints must be supported?")
        questions.append("Are there security, compliance, hosting, or data-retention constraints?")
        risks: list[str] = []
        lowered = combined.casefold()
        if not areas:
            risks.append("Technical scope is not yet specific enough for an engineering estimate.")
        if len(deliverables) > 8:
            risks.append("The requested deliverables may require phased planning and explicit priorities.")
        if any(marker in lowered for marker in ("urgent", "asap", "tomorrow", "guaranteed")):
            risks.append("Urgency language must not become an unsupported deadline commitment.")
        if any(marker in lowered for marker in _UNSUPPORTED_MARKERS):
            qualification = "not_fit"
            risks.append("The request includes a capability or commitment outside the engineering intake policy.")
        elif not clean_title or not summary or not deliverables or not areas:
            qualification = "needs_clarification"
        else:
            capability_text = " ".join(_items(company_capabilities)).casefold()
            unsupported_areas = [area for area in areas if capability_text and area not in capability_text]
            if unsupported_areas:
                qualification = "needs_fit_review"
                risks.append("Some technical areas require a capability review before proposal drafting.")
            else:
                qualification = "qualified"
        if qualification == "qualified":
            next_action = RecommendedNextAction(
                action="handoff_to_requirements",
                target_role="requirements",
                reason="Requirements analysis should turn the qualified brief into acceptance criteria.",
            )
        elif qualification == "not_fit":
            next_action = RecommendedNextAction(
                action="escalate_fit_review",
                target_role="company_director",
                reason="Company Director review is required before any client commitment.",
                requires_authorization=True,
            )
        else:
            next_action = RecommendedNextAction(
                action="request_clarification",
                reason="Resolve the open questions before delegating technical work.",
            )
        return OpportunityBrief(
            opportunity_id=None,
            source=clean_source,
            title=clean_title,
            project_type=self._project_type(combined),
            qualification=qualification,
            client_needs=ClientNeedsSummary(summary, deliverables, areas),
            open_questions=OpenQuestions(_items(questions)),
            risks=Risks(_items(risks)),
            recommended_next_action=next_action,
            evidence=_items(("sanitized client request", f"technical areas detected: {', '.join(areas) or 'none'}")),
        )

    def receive(
        self,
        *,
        source: str,
        title: str,
        body: str = "",
        requirements: Iterable[str] = (),
        external_ref: str | None = None,
        company_capabilities: Iterable[str] = (),
    ) -> OpportunityBrief:
        self.ensure_profile()
        brief = self.qualify(
            source=source,
            title=title,
            body=body,
            requirements=requirements,
            company_capabilities=company_capabilities,
        )
        opportunity = create_project_opportunity(
            brief.source,
            brief.title,
            summary=brief.client_needs.summary,
            requirements=brief.client_needs.deliverables,
            external_ref=external_ref,
            status=brief.qualification,
            database_path=self.database_path,
        )
        return replace(brief, opportunity_id=str(opportunity["opportunity_id"]))

    def draft_proposal(self, brief: OpportunityBrief) -> ProposalDraft:
        scope = brief.client_needs.summary or "Scope requires clarification."
        status = "draft" if brief.qualification == "qualified" else "blocked_needs_clarification"
        return ProposalDraft(
            opportunity_id=brief.opportunity_id,
            scope=scope,
            assumptions=(
                "Final scope follows validated requirements and architecture review.",
                "Any estimate requires explicit Human Owner policy and evidence.",
            ),
            risks=brief.risks.items,
            exclusions=(
                "No fixed price commitment is made by Sales.",
                "No deadline, legal term, or production commitment is made by Sales.",
            ),
            status=status,
        )

    def handoff(
        self,
        brief: OpportunityBrief,
        *,
        target_role: str = "requirements",
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        if not brief.opportunity_id:
            raise ValueError("handoff requires a persisted opportunity")
        if target_role not in {"requirements", "project_manager"}:
            raise ValueError("Sales handoff target must be requirements or project_manager")
        summary = f"Opportunity {brief.opportunity_id}: {brief.title} ({brief.qualification})"
        handoff = coordination_store.create_handoff(
            AgentHandoff(
                sender_role=self.ROLE,
                recipient_role=target_role,
                run_id=run_id,
                project_id=None,
                task_id=task_id,
                summary=summary,
                completed=("incoming request analyzed", "client needs summarized", "fit risks identified"),
                artifacts=("OpportunityBrief", "ProposalDraft"),
                risks=brief.risks.items,
                remaining_work=brief.open_questions.questions,
                verification=("No source files changed.", "No commercial commitment made."),
                status="submitted",
            ),
            database_path=self.database_path,
        )
        message = self.bus.publish(
            sender_role=self.ROLE,
            recipient_role=target_role,
            message_type=MessageType.HANDOFF,
            subject=f"Qualified opportunity handoff: {brief.title}",
            body=json.dumps(brief.as_dict(), ensure_ascii=False),
            run_id=run_id,
            task_id=task_id,
            references=(str(handoff["handoff_id"]), str(brief.opportunity_id)),
        )
        return {"handoff": handoff, "message": message}

    def escalate_commercial(
        self,
        brief: OpportunityBrief,
        *,
        commitment_type: str,
        reason: str,
    ) -> CommercialEscalation:
        normalized = str(commitment_type or "").strip().lower()
        if normalized not in _COMMITMENT_TYPES:
            raise ValueError("unsupported commercial commitment type")
        clean_reason, _ = sanitize_text(str(reason or "Commercial approval is required."), max_chars=2_000)
        message = self.bus.publish(
            sender_role=self.ROLE,
            recipient_role="company_director",
            message_type=MessageType.BLOCKER,
            subject=f"Human Owner approval required: {normalized}",
            body=json.dumps(
                {
                    "opportunity_id": brief.opportunity_id,
                    "commitment_type": normalized,
                    "escalation_target": "human_owner",
                    "reason": clean_reason,
                    "commitment_made": False,
                },
                ensure_ascii=False,
            ),
            references=((brief.opportunity_id,) if brief.opportunity_id else ()),
        )
        return CommercialEscalation(normalized, clean_reason, str(message["message_id"]))

    @staticmethod
    def make_commitment(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("Sales cannot make commercial commitments; use Human Owner approval.")
