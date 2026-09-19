from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .models import (
    Department,
    EmployeeStatus,
    ProjectComplexity,
    ProjectOrganizationPlan,
    ProjectTeamMember,
)
from .store import (
    ensure_employee,
    get_project_organization,
    list_project_team,
    save_project_organization,
)

class TeamPlanner:
    """Deterministic staffing policy; execution remains in coordination.Supervisor."""

    _SMALL_ROLES = (
        ("engineering_manager", Department.ENGINEERING, True),
        ("implementer", Department.ENGINEERING, False),
        ("tester", Department.QUALITY, False),
        ("reviewer", Department.QUALITY, False),
    )
    _MEDIUM_ROLES = (
        ("engineering_manager", Department.ENGINEERING, True),
        ("architect", Department.ENGINEERING, False),
        ("implementer", Department.ENGINEERING, False),
        ("integration", Department.ENGINEERING, False),
        ("tester", Department.QUALITY, False),
        ("reviewer", Department.QUALITY, False),
        ("docs", Department.DOCUMENTATION, False),
    )
    _LARGE_ROLES = (
        ("project_manager", Department.PRODUCT, True),
        ("requirements", Department.PRODUCT, False),
        ("engineering_manager", Department.ENGINEERING, True),
        ("architect", Department.ENGINEERING, False),
        ("backend", Department.ENGINEERING, False),
        ("frontend", Department.ENGINEERING, False),
        ("integration", Department.ENGINEERING, False),
        ("tester", Department.QUALITY, False),
        ("security", Department.SECURITY, False),
        ("docs", Department.DOCUMENTATION, False),
        ("release_verifier", Department.OPERATIONS, False),
    )

    def infer_complexity(
        self,
        objective: str,
        *,
        technologies: Iterable[str] = (),
        required_skills: Iterable[str] = (),
        risks: Iterable[str] = (),
        deliverables: Iterable[str] = (),
        complexity: ProjectComplexity | str | None = None,
    ) -> ProjectComplexity:
        if complexity:
            try:
                return (
                    complexity
                    if isinstance(complexity, ProjectComplexity)
                    else ProjectComplexity(str(complexity).lower())
                )
            except ValueError as exc:
                raise ValueError(f"Unsupported project complexity: {complexity}") from exc
        objective_lower = objective.casefold()
        values = [str(item).strip() for item in (
            *technologies, *required_skills, *risks, *deliverables
        ) if str(item).strip()]
        large_signals = (
            "platform", "migration", "security", "frontend", "backend",
            "integration", "production", "multi-service", "multi service",
            "distributed", "compliance",
        )
        signal_count = sum(1 for signal in large_signals if signal in objective_lower)
        if signal_count >= 2 or len(values) >= 8 or len(objective) >= 1200:
            return ProjectComplexity.LARGE
        if signal_count == 1 or len(values) >= 3 or len(objective) >= 500:
            return ProjectComplexity.MEDIUM
        return ProjectComplexity.SMALL

    def plan(
        self,
        project_id: str,
        objective: str,
        *,
        complexity: ProjectComplexity | str | None = None,
        technologies: Iterable[str] = (),
        required_skills: Iterable[str] = (),
        risks: Iterable[str] = (),
        deliverables: Iterable[str] = (),
        priority: int = 50,
    ) -> ProjectOrganizationPlan:
        objective = str(objective).strip()
        if len(objective) < 3:
            raise ValueError("Project objective must contain at least 3 characters")
        selected = self.infer_complexity(
            objective,
            technologies=technologies,
            required_skills=required_skills,
            risks=risks,
            deliverables=deliverables,
            complexity=complexity,
        )
        role_rows = {
            ProjectComplexity.SMALL: self._SMALL_ROLES,
            ProjectComplexity.MEDIUM: self._MEDIUM_ROLES,
            ProjectComplexity.LARGE: self._LARGE_ROLES,
        }[selected]
        members: list[ProjectTeamMember] = []
        departments: list[Department] = [Department.EXECUTIVE]
        for role, department, is_lead in role_rows:
            if department not in departments:
                departments.append(department)
            members.append(
                ProjectTeamMember(
                    agent_id=f"employee-{role.replace('_', '-')}",
                    role=role,
                    department=department,
                    status=EmployeeStatus.AVAILABLE,
                    is_lead=is_lead,
                )
            )
        project_manager_id = next(
            (member.agent_id for member in members if member.role == "project_manager"),
            None,
        )
        engineering_manager_id = next(
            member.agent_id for member in members if member.role == "engineering_manager"
        )
        rationale = (
            f"{selected.value} staffing policy selected from objective and declared scope.",
            "Specialists are persistent profiles; execution remains in the existing task DAG.",
        )
        return ProjectOrganizationPlan(
            project_id=project_id,
            objective=objective,
            complexity=selected,
            project_manager_id=project_manager_id,
            engineering_manager_id=engineering_manager_id,
            departments=tuple(departments),
            members=tuple(members),
            priority=max(0, min(100, int(priority))),
            rationale=rationale,
            risks=tuple(str(item).strip() for item in risks if str(item).strip()),
        )


class CompanyDirector:
    """Executive coordinator that delegates technical work to the existing supervisor."""

    ROLE = "company_director"
    DISPLAY_NAME = "Company Director"

    def ensure_profile(self, *, database_path: str | Path | None = None):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-company-director",
            display_name=self.DISPLAY_NAME,
            department=Department.EXECUTIVE,
            status=EmployeeStatus.AVAILABLE,
            database_path=database_path,
        )

    def organize_project(
        self,
        project_id: str,
        objective: str,
        *,
        complexity: ProjectComplexity | str | None = None,
        technologies: Iterable[str] = (),
        required_skills: Iterable[str] = (),
        risks: Iterable[str] = (),
        deliverables: Iterable[str] = (),
        priority: int = 50,
        database_path: str | Path | None = None,
    ):
        self.ensure_profile(database_path=database_path)
        plan = TeamPlanner().plan(
            project_id,
            objective,
            complexity=complexity,
            technologies=technologies,
            required_skills=required_skills,
            risks=risks,
            deliverables=deliverables,
            priority=priority,
        )
        organization = save_project_organization(plan, database_path=database_path)
        return plan, organization

    def executive_report(
        self, project_id: str, *, database_path: str | Path | None = None
    ) -> dict[str, object]:
        organization = get_project_organization(project_id, database_path=database_path)
        if not organization:
            raise KeyError(f"Project not found: {project_id}")
        project = organization.project
        members = list(organization.members)
        blocked = [member.role for member in members if member.status == EmployeeStatus.BLOCKED]
        stalled = project.get("team_state") in {"stalled", "blocked"} or bool(blocked)
        return {
            "project_id": project_id,
            "project_name": project.get("name"),
            "phase": project.get("phase"),
            "priority": project.get("priority"),
            "team_state": project.get("team_state"),
            "project_manager_id": project.get("project_manager_id"),
            "engineering_manager_id": project.get("engineering_manager_id"),
            "departments": project.get("departments", []),
            "team_size": len(members),
            "blocked_roles": blocked,
            "stalled": stalled,
            "owner_escalation_required": stalled,
            "delegates_technical_execution": True,
            "team_members": [member.as_dict() for member in members],
        }

    def initiate_postmortem(self, project_id: str, reason: str) -> dict[str, str]:
        """Return a structured request for the existing supervisor/memory pipeline."""
        return {
            "project_id": project_id,
            "requested_by": self.ROLE,
            "reason": str(reason).strip()[:2000],
            "next_action": "Create a bounded review task and persist validated lessons.",
        }
