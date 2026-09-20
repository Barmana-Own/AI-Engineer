from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import re

from app.coordination.roles import get_role_contract, resolve_role

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
    get_project_team_plan,
    save_project_organization,
)


class TeamPlanner:
    """Canonical project staffing and execution-plan policy.

    The returned plan is the single source used by organization persistence and
    the coordination Supervisor. It deliberately selects only roles justified
    by the objective and declared scope.
    """

    _ROLE_ORDER = (
        "project_manager",
        "requirements",
        "researcher",
        "engineering_manager",
        "architect",
        "ux_designer",
        "backend",
        "frontend",
        "implementer",
        "devops",
        "integration",
        "seo_manager",
        "seo_specialist",
        "security",
        "docs",
        "tester",
        "reviewer",
        "release_verifier",
    )

    _DEPARTMENTS = {
        "project_manager": Department.PRODUCT,
        "requirements": Department.PRODUCT,
        "researcher": Department.RESEARCH,
        "engineering_manager": Department.ENGINEERING,
        "architect": Department.ENGINEERING,
        "ux_designer": Department.ENGINEERING,
        "backend": Department.ENGINEERING,
        "frontend": Department.ENGINEERING,
        "implementer": Department.ENGINEERING,
        "devops": Department.OPERATIONS,
        "integration": Department.ENGINEERING,
        "seo_manager": Department.PRODUCT,
        "seo_specialist": Department.RESEARCH,
        "security": Department.SECURITY,
        "docs": Department.DOCUMENTATION,
        "tester": Department.QUALITY,
        "reviewer": Department.QUALITY,
        "release_verifier": Department.OPERATIONS,
    }

    _TITLES = {
        "project_manager": "Manage project deliverables and dependencies",
        "requirements": "Clarify requirements and acceptance criteria",
        "researcher": "Research evidence and domain constraints",
        "engineering_manager": "Coordinate technical execution",
        "architect": "Define architecture and interfaces",
        "ux_designer": "Define user flows and interaction requirements",
        "backend": "Implement backend and data scope",
        "frontend": "Implement client and user-facing scope",
        "implementer": "Implement the scoped change",
        "devops": "Prepare build, deployment, and operational changes",
        "integration": "Integrate compatible component changes",
        "seo_manager": "Plan and coordinate the SEO workstream",
        "seo_specialist": "Perform evidence-based SEO analysis and verification",
        "security": "Review security-sensitive changes",
        "docs": "Update documentation and operational guidance",
        "tester": "Run verification and regression tests",
        "reviewer": "Independently review the implementation",
        "release_verifier": "Verify release evidence and acceptance criteria",
    }

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
        values = [
            str(item).strip()
            for item in (*technologies, *required_skills, *risks, *deliverables)
            if str(item).strip()
        ]
        large_signals = (
            "platform",
            "migration",
            "security",
            "frontend",
            "backend",
            "integration",
            "production",
            "multi-service",
            "multi service",
            "distributed",
            "compliance",
            "full-stack",
            "full stack",
        )
        signal_count = sum(1 for signal in large_signals if signal in objective_lower)
        if signal_count >= 2 or len(values) >= 8 or len(objective) >= 1200:
            return ProjectComplexity.LARGE
        if signal_count == 1 or len(values) >= 3 or len(objective) >= 500:
            return ProjectComplexity.MEDIUM
        return ProjectComplexity.SMALL

    @staticmethod
    def _corpus(objective: str, values: Iterable[str] = ()) -> str:
        return " ".join([str(objective), *(str(value) for value in values)]).casefold()

    @staticmethod
    def _has(corpus: str, *signals: str) -> bool:
        for signal in signals:
            normalized = signal.casefold()
            if len(normalized) <= 3:
                if re.search(r"(?<!\w)" + re.escape(normalized) + r"(?!\w)", corpus):
                    return True
            elif normalized in corpus:
                return True
        return False

    def select_roles(
        self,
        objective: str,
        *,
        complexity: ProjectComplexity | str | None = None,
        technologies: Iterable[str] = (),
        required_skills: Iterable[str] = (),
        risks: Iterable[str] = (),
        deliverables: Iterable[str] = (),
    ) -> tuple[tuple[str, str], ...]:
        """Return deterministic role/reason selections.

        Selection is evidence-driven. A role is not added merely because it
        exists in the registry or appeared in an older fixed workflow.
        """
        objective = str(objective).strip()
        selected_complexity = self.infer_complexity(
            objective,
            technologies=technologies,
            required_skills=required_skills,
            risks=risks,
            deliverables=deliverables,
            complexity=complexity,
        )
        corpus = self._corpus(
            objective,
            (*technologies, *required_skills, *risks, *deliverables),
        )
        maintenance = self._has(
            corpus,
            "bug",
            "fix",
            "hotfix",
            "patch",
            "regression",
            "typo",
            "isolated",
            "error",
            "retry",
            "repair",
        )
        seo = self._has(
            corpus,
            "seo",
            "search engine optimization",
            "keyword",
            "canonical tag",
            "robots.txt",
            "sitemap",
            "indexability",
            "search intent",
        )
        docs = self._has(
            corpus,
            "documentation",
            "docs",
            "readme",
            "runbook",
            "api reference",
            "release notes",
        )
        frontend = self._has(
            corpus,
            "frontend",
            "front-end",
            "user interface",
            "ui",
            "client",
            "react",
            "electron",
            "component",
            "screen",
            "responsive",
            "css",
        )
        backend = self._has(
            corpus,
            "backend",
            "back-end",
            "api",
            "server",
            "database",
            "sqlite",
            "migration",
            "endpoint",
            "fastapi",
            "python service",
            "authentication",
            "authorization",
        )
        full_stack = (frontend and backend) or self._has(
            corpus,
            "full-stack",
            "full stack",
            "end-to-end application",
            "web application",
            "frontend and backend",
            "client and api",
        )
        security = self._has(
            corpus,
            "security",
            "authentication",
            "authorization",
            "credential",
            "secret",
            "token",
            "payment",
            "privacy",
            "external exposure",
            "production access",
            "permission",
        )
        devops = self._has(
            corpus,
            "deploy",
            "deployment",
            "devops",
            "docker",
            "container",
            "ci/cd",
            "pipeline",
            "environment",
            "startup",
            "server configuration",
            "reverse proxy",
        )
        seo_research = self._has(
            corpus, "keyword research", "keyword strategy", "keyword cluster", "competitor", "content gap", "search volume",
            "search intent", "keyword map", "content strategy",
        )
        seo_technical = self._has(
            corpus, "technical seo", "canonical", "metadata", "meta description",
            "robots.txt", "sitemap", "redirect", "indexability", "structured data",
            "schema", "crawlability", "hreflang", "page speed", "core web vitals",
        )
        seo_implementation = seo and self._has(
            corpus, "improve", "fix", "implement", "update", "optimize",
            "optimization", "repair", "correct", "remediate", "change",
        )
        seo_frontend = seo_implementation and (
            frontend
            or self._has(corpus, "canonical", "metadata", "meta description", "structured data", "schema", "hreflang", "title tag")
        )
        seo_backend = seo_implementation and (
            backend
            or self._has(corpus, "api", "server", "database", "application logic")
        )
        seo_devops = seo_implementation and (
            devops
            or self._has(corpus, "robots.txt", "sitemap", "redirect", "crawlability", "server status", "performance", "hosting")
        )
        if seo_implementation and seo_technical and not (seo_frontend or seo_backend or seo_devops):
            seo_frontend, seo_devops = True, True
        ux = self._has(corpus, "ux", "user flow", "interaction design", "accessibility", "wireframe")
        integration = full_stack or self._has(
            corpus,
            "integration",
            "service-to-service",
            "contract",
            "connect components",
            "cross-component",
        )
        substantial = (
            full_stack
            or (complexity is not None and selected_complexity in {ProjectComplexity.MEDIUM, ProjectComplexity.LARGE})
            or len(objective) >= 500
            or self._has(
                corpus,
                "architecture",
                "architect",
                "redesign",
                "migration",
                "platform",
                "multi-service",
                "system design",
            )
        )
        vague_new = self._has(corpus, "new project", "build", "create", "develop", "design")
        docs_only = docs and not any((seo, frontend, backend, devops, integration, security, ux))
        seo_only = seo and not seo_implementation and not any((frontend, backend, devops, integration))

        role_reasons: dict[str, str] = {}

        def add(role: str, reason: str) -> None:
            canonical = resolve_role(role)
            if canonical not in role_reasons:
                role_reasons[canonical] = reason

        if seo_only:
            add("engineering_manager", "Coordinates the bounded SEO workstream without owning content or production code.")
            add("seo_manager", "The objective contains an SEO strategy, audit, or search-intent work area.")
            add("seo_specialist", "Evidence-based SEO analysis and verification are required for the SEO backlog.")
            if seo_research:
                add("researcher", "Keyword, competitor, or content-gap evidence is required and no analytics are fabricated.")
            add("tester", "SEO acceptance criteria require independent verification.")
        elif seo:
            if seo_implementation or seo_frontend or seo_backend or seo_devops:
                add("project_manager", "Engineering handoffs and SEO verification require deliverable and dependency coordination.")
            add("requirements", "SEO acceptance criteria and implementation boundaries must be explicit before changes are scheduled.")
            add("engineering_manager", "Coordinates technical SEO execution and delegates production changes to least-privilege engineers.")
            add("seo_manager", "Owns SEO strategy, prioritization, delegation, and the SEO quality gate.")
            add("seo_specialist", "Produces evidence-based SEO findings and independently verifies implementation output.")
            if seo_research:
                add("researcher", "Keyword, competitor, or content-gap evidence is required and no analytics are fabricated.")
            if seo_backend:
                add("backend", "The SEO finding requires server, API, or application-layer changes.")
            if seo_frontend:
                add("frontend", "The SEO finding requires metadata, template, schema, or rendered-client changes.")
            if seo_devops:
                add("devops", "The SEO finding requires robots, sitemap, redirects, hosting, or performance configuration.")
            if (seo_frontend and seo_devops) or (seo_backend and (seo_frontend or seo_devops)):
                add("integration", "SEO changes cross component or server boundaries and require contract validation.")
            if security:
                add("security", "SEO implementation crosses a security-sensitive trust boundary.")
            if docs:
                add("docs", "SEO implementation changes require synchronized technical documentation.")
            add("tester", "SEO acceptance criteria require independent verification and regression evidence.")
        elif docs_only:
            add("engineering_manager", "Coordinates documentation changes and keeps the work scoped.")
            add("docs", "The requested deliverable is documentation or operational guidance.")
        else:
            if full_stack or selected_complexity == ProjectComplexity.LARGE or self._has(corpus, "milestone", "schedule", "deliverables"):
                add("project_manager", "Cross-area deliverables or schedule/dependency coordination is required.")
            if full_stack or substantial or vague_new:
                add("requirements", "Requirements and acceptance criteria must be made explicit before multi-step execution.")
            add("engineering_manager", "Every executable engineering team needs a technical coordinator and completion gate.")
            if substantial:
                add("architect", "The scope has enough components, risk, or architecture change to require an explicit design.")
            if ux and frontend:
                add("ux_designer", "User-flow and interaction requirements affect the frontend scope.")
            if backend:
                add("backend", "The objective names backend, API, server, persistence, or data work.")
            if frontend:
                add("frontend", "The objective names client, UI, frontend, or user-facing work.")
            if not backend and not frontend and not seo:
                add("implementer", "No specialized implementation area was identified; a bounded general implementer is appropriate.")
            if devops:
                add("devops", "Build, deployment, environment, or operational changes are in scope.")
            if integration:
                add("integration", "Multiple components or explicit interface/contract integration is required.")
            if security:
                add("security", "The objective crosses a security-sensitive trust boundary and needs independent review.")
            if docs:
                add("docs", "Documentation changes are part of the requested deliverables.")
            add("tester", "Independent tests and acceptance evidence are required.")
        add("reviewer", "An independent review is required before release.")
        add("release_verifier", "Release evidence must be checked independently of implementation status.")
        return tuple((role, role_reasons[role]) for role in self._ROLE_ORDER if role in role_reasons)

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
        selected_roles = self.select_roles(
            objective,
            complexity=complexity,
            technologies=technologies,
            required_skills=required_skills,
            risks=risks,
            deliverables=deliverables,
        )
        role_reasons = dict(selected_roles)
        members: list[ProjectTeamMember] = []
        departments: list[Department] = [Department.EXECUTIVE]
        for role, _reason in selected_roles:
            department = self._DEPARTMENTS[role]
            if department not in departments:
                departments.append(department)
            contract = get_role_contract(role)
            members.append(
                ProjectTeamMember(
                    agent_id=f"employee-{role.replace('_', '-')}",
                    role=role,
                    department=department,
                    status=EmployeeStatus.AVAILABLE,
                    is_lead=role in {"project_manager", "engineering_manager", "seo_manager"},
                    display_name=contract.name,
                )
            )
        engineering_manager_id = next(
            (member.agent_id for member in members if member.role == "engineering_manager"),
            "employee-engineering-manager",
        )
        project_manager_id = next(
            (member.agent_id for member in members if member.role == "project_manager"),
            None,
        )
        selection_basis = (
            f"objective={objective[:500]}",
            f"complexity={selected.value}",
            f"selected_roles={','.join(role for role, _ in selected_roles)}",
        )
        rationale = (
            "The Company Director selected an execution team from the objective and declared scope.",
            "Only selected roles are persisted as active project members and scheduled in the task DAG.",
        )
        responsibilities = tuple(
            (
                role,
                "; ".join(get_role_contract(role).responsibilities[:3])
                or get_role_contract(role).purpose,
            )
            for role, _ in selected_roles
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
            role_reasons=tuple(role_reasons.items()),
            role_responsibilities=responsibilities,
            selection_basis=selection_basis,
            plan_id=f"team-plan-{project_id}",
        )

    def build_execution_specs(
        self,
        selected_roles: Iterable[str],
    ) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
        """Build a DAG recipe from the selected plan, never from a fixed team."""
        selected = {resolve_role(role) for role in selected_roles}
        ordered = [role for role in self._ROLE_ORDER if role in selected]

        def present(*roles: str) -> tuple[str, ...]:
            return tuple(role for role in roles if role in selected)

        implementation_roles = present(
            "backend",
            "frontend",
            "implementer",
            "devops",
            "seo_specialist",
        )
        specs: list[tuple[str, str, tuple[str, ...]]] = []
        for role in ordered:
            if role == "project_manager":
                dependencies = present("requirements")
            elif role == "requirements":
                dependencies = ()
            elif role == "engineering_manager":
                dependencies = ()
            elif role == "architect":
                dependencies = present("project_manager", "requirements", "engineering_manager")
            elif role == "ux_designer":
                dependencies = present("architect", "requirements", "engineering_manager")
            elif role in {"backend", "frontend", "implementer", "devops"}:
                dependencies = present("architect", "requirements", "engineering_manager")
            elif role == "integration":
                dependencies = present("backend", "frontend", "implementer", "devops")
                if not dependencies:
                    dependencies = present("architect", "engineering_manager")
            elif role == "researcher":
                dependencies = present("requirements", "seo_manager")
            elif role == "seo_manager":
                dependencies = present("project_manager", "requirements", "engineering_manager")
            elif role == "seo_specialist":
                dependencies = present("seo_manager")
            elif role == "security":
                dependencies = present(*implementation_roles, "integration")
            elif role == "docs":
                dependencies = present(*implementation_roles, "integration", "architect", "seo_manager", "seo_specialist")
            elif role == "tester":
                dependencies = present("integration")
                if not dependencies:
                    dependencies = present(*implementation_roles, "security", "docs")
            elif role == "reviewer":
                dependencies = present("tester", "security", "docs", "seo_specialist")
            elif role == "release_verifier":
                dependencies = present("reviewer", "security", "docs", "tester", "seo_manager")
            else:
                dependencies = ()
            specs.append((role, self._TITLES.get(role, f"Execute {role}"), dependencies))
        return tuple(specs)


class CompanyDirector:
    """Executive coordinator that delegates technical work to the existing Supervisor."""

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
        persist_execution_plan: bool = True,
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
        organization = save_project_organization(
            plan,
            database_path=database_path,
            persist_team_plan=persist_execution_plan,
        )
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
        team_plan = get_project_team_plan(project_id, database_path=database_path)
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
            "team_plan": team_plan,
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
