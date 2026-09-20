from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from app import db
from app.coordination import owner_control
from app.coordination.supervisor import Supervisor
from app.organization.director import CompanyDirector
from app.organization.requirements import RequirementsAgent
from app.organization.sales import (
    ClientNeedsSummary, OpportunityBrief, OpenQuestions,
    RecommendedNextAction, Risks, SalesAgent,
)

OPPORTUNITY_STATES = frozenset({
    "NEW", "ANALYZING", "NEEDS_CLARIFICATION", "QUALIFIED", "REJECTED",
    "WAITING_OWNER", "CONVERTED_TO_PROJECT",
})


def _state_for(qualification: str) -> str:
    return {
        "qualified": "QUALIFIED",
        "needs_clarification": "NEEDS_CLARIFICATION",
        "needs_fit_review": "WAITING_OWNER",
        "not_fit": "REJECTED",
    }.get(str(qualification).casefold(), "ANALYZING")


def _as_dict(value: object) -> dict[str, object]:
    result = value.as_dict() if hasattr(value, "as_dict") else value
    return dict(result) if isinstance(result, Mapping) else {"value": result}


def _brief_from_dict(value: Mapping[str, object]) -> OpportunityBrief:
    needs = value.get("client_needs_summary") or value.get("client_needs") or {}
    questions = value.get("open_questions") or {}
    risks = value.get("risks") or {}
    action = value.get("recommended_next_action") or {}
    needs = needs if isinstance(needs, Mapping) else {}
    questions = questions if isinstance(questions, Mapping) else {}
    risks = risks if isinstance(risks, Mapping) else {}
    action = action if isinstance(action, Mapping) else {}
    return OpportunityBrief(
        opportunity_id=str(value.get("opportunity_id") or "") or None,
        source=str(value.get("source") or ""), title=str(value.get("title") or ""),
        project_type=str(value.get("project_type") or "software_project"),
        qualification=str(value.get("qualification") or "needs_clarification"),
        client_needs=ClientNeedsSummary(
            str(needs.get("summary") or ""),
            tuple(str(item) for item in (needs.get("deliverables") or ())),
            tuple(str(item) for item in (needs.get("technical_areas") or ())),
        ),
        open_questions=OpenQuestions(tuple(str(item) for item in (questions.get("questions") or ()))),
        risks=Risks(tuple(str(item) for item in (risks.get("items") or ()))),
        recommended_next_action=RecommendedNextAction(
            str(action.get("action") or "request_clarification"),
            str(action.get("reason") or "Requirements analysis is required."),
            str(action.get("target_role")) if action.get("target_role") else None,
            bool(action.get("requires_authorization", False)),
        ),
        evidence=tuple(str(item) for item in (value.get("evidence") or ())),
    )


class OpportunityIntakeService:
    """Durable Sales-to-project intake over the existing company workflow."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path
        self.sales = SalesAgent(database_path)
        self.requirements = RequirementsAgent(database_path)
        self.director = CompanyDirector()
        self.supervisor = Supervisor(str(database_path) if database_path is not None else None)

    def _record_brief(self, opportunity: Mapping[str, object]) -> OpportunityBrief:
        raw = opportunity.get("brief")
        if isinstance(raw, Mapping) and raw.get("title"):
            return _brief_from_dict(raw)
        return self.sales.qualify(
            source=str(opportunity.get("source") or ""),
            title=str(opportunity.get("title") or ""),
            body=str(opportunity.get("summary") or ""),
            requirements=tuple(str(item) for item in (opportunity.get("requirements") or ())),
        )

    def receive(
        self, *, source: str, title: str, body: str = "",
        requirements: Iterable[str] = (), external_ref: str | None = None,
        company_capabilities: Iterable[str] = (),
    ) -> dict[str, object]:
        brief = self.sales.receive(
            source=source, title=title, body=body, requirements=requirements,
            external_ref=external_ref, company_capabilities=company_capabilities,
        )
        status = _state_for(brief.qualification)
        gate = "pending_owner" if status == "WAITING_OWNER" else ("rejected" if status == "REJECTED" else "not_required")
        qualification = {"qualification": brief.qualification, "project_type": brief.project_type, "risks": list(brief.risks.items)}
        opportunity = owner_control.update_project_opportunity(
            str(brief.opportunity_id), status=status, brief=brief.as_dict(), qualification=qualification,
            owner_gate_status=gate, last_action="sales_qualified", database_path=self.database_path,
        )
        handoff = self.sales.handoff(brief, target_role="requirements") if status == "QUALIFIED" else None
        return {"opportunity": opportunity, "brief": brief.as_dict(), "proposal": self.sales.draft_proposal(brief).as_dict(), "handoff": handoff}

    def analyze(self, opportunity_id: str, *, company_capabilities: Iterable[str] = ()) -> dict[str, object]:
        opportunity = owner_control.get_project_opportunity(opportunity_id, database_path=self.database_path)
        if not opportunity:
            raise KeyError(opportunity_id)
        brief = self._record_brief(opportunity)
        if not brief.opportunity_id:
            brief = OpportunityBrief(opportunity_id=opportunity_id, source=brief.source, title=brief.title, project_type=brief.project_type, qualification=brief.qualification, client_needs=brief.client_needs, open_questions=brief.open_questions, risks=brief.risks, recommended_next_action=brief.recommended_next_action, evidence=brief.evidence)
        if company_capabilities:
            qualified = self.sales.qualify(source=brief.source, title=brief.title, body=brief.client_needs.summary, requirements=brief.client_needs.deliverables, company_capabilities=company_capabilities)
            brief = OpportunityBrief(opportunity_id=opportunity_id, source=qualified.source, title=qualified.title, project_type=qualified.project_type, qualification=qualified.qualification, client_needs=qualified.client_needs, open_questions=qualified.open_questions, risks=qualified.risks, recommended_next_action=qualified.recommended_next_action, evidence=qualified.evidence)
        status = _state_for(brief.qualification)
        gate = "pending_owner" if status == "WAITING_OWNER" else ("rejected" if status == "REJECTED" else "not_required")
        updated = owner_control.update_project_opportunity(opportunity_id, status=status, brief=brief.as_dict(), qualification={"qualification": brief.qualification}, owner_gate_status=gate, last_action="sales_analysis", database_path=self.database_path)
        return {"opportunity": updated, "brief": brief.as_dict()}

    def qualify(self, opportunity_id: str, *, owner_approved: bool = False) -> dict[str, object]:
        item = self.analyze(opportunity_id)
        brief = _brief_from_dict(item["brief"])
        target = _state_for(brief.qualification)
        if target == "WAITING_OWNER" and owner_approved:
            target = "QUALIFIED"
        if target == "WAITING_OWNER" and not owner_approved:
            return {"opportunity": owner_control.update_project_opportunity(opportunity_id, status=target, owner_gate_status="pending_owner", last_action="owner_gate_required", database_path=self.database_path), "brief": brief.as_dict()}
        updated = owner_control.transition_project_opportunity(opportunity_id, target, owner_gate_status="approved" if owner_approved else "not_required", last_action="opportunity_qualified", database_path=self.database_path)
        return {"opportunity": updated, "brief": brief.as_dict()}

    def convert(self, opportunity_id: str, *, project_name: str | None = None, workspace: str, objective: str | None = None, owner_approved: bool = False) -> dict[str, object]:
        item = owner_control.get_project_opportunity(opportunity_id, database_path=self.database_path)
        if not item:
            raise KeyError(opportunity_id)
        if item.get("converted_project_id"):
            # Read the converted project through the same database configured for
                        # intake. Calling the default-db helper here breaks idempotent
            # conversion for isolated/test databases.
            with db.connect(self.database_path) as database:
                row = database.execute(
                    "SELECT * FROM projects WHERE id = ?",
                    (str(item["converted_project_id"]),),
                ).fetchone()
            return {"opportunity": item, "project": dict(row) if row else None, "idempotent": True}
        if str(item.get("status") or "").upper() not in {"QUALIFIED", "WAITING_OWNER"}:
            item = self.qualify(opportunity_id, owner_approved=owner_approved).get("opportunity", item)
        if str(item.get("status") or "").upper() == "WAITING_OWNER" and not owner_approved:
            raise PermissionError("Human Owner approval is required before converting this opportunity")
        if str(item.get("status") or "").upper() != "QUALIFIED":
            raise ValueError("Only a qualified opportunity can become a project")
        brief = self._record_brief(item)
        project_objective = str(objective or (brief.title + ": " + brief.client_needs.summary)).strip()
        project = db.create_project(project_name or brief.title, workspace, database_path=self.database_path)
        project_id = str(project["id"])
        specification = self.requirements.analyze(brief)
        handoff = self.requirements.handoff(specification, target_role="project_manager", project_id=project_id)
        plan, organization = self.director.organize_project(project_id, project_objective, technologies=brief.client_needs.technical_areas, risks=brief.risks.items, deliverables=brief.client_needs.deliverables, database_path=self.database_path)
        updated = owner_control.update_project_opportunity(opportunity_id, status="CONVERTED_TO_PROJECT", converted_project_id=project_id, converted_at=db.utc_now(), owner_gate_status="approved" if owner_approved else "not_required", last_action="converted_to_project", database_path=self.database_path)
        return {"opportunity": updated, "project": project, "requirements": _as_dict(specification), "handoff": handoff, "team_plan": plan.as_dict(), "organization": _as_dict(organization)}

    def start(self, opportunity_id: str, *, objective: str | None = None) -> dict[str, object]:
        item = owner_control.get_project_opportunity(opportunity_id, database_path=self.database_path)
        if not item:
            raise KeyError(opportunity_id)
        project_id = item.get("converted_project_id")
        if not project_id or str(item.get("status")) != "CONVERTED_TO_PROJECT":
            raise ValueError("Opportunity must be converted before execution starts")
        brief = self._record_brief(item)
        project_objective = str(objective or (brief.title + ": " + brief.client_needs.summary)).strip()
        result = self.supervisor.start_objective(project_id=str(project_id), objective=project_objective)
        owner_control.update_project_opportunity(opportunity_id, last_action="execution_started", database_path=self.database_path)
        return {"opportunity": owner_control.get_project_opportunity(opportunity_id, database_path=self.database_path), "execution": result}


__all__ = ["OPPORTUNITY_STATES", "OpportunityIntakeService"]
