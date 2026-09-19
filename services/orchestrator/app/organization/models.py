from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Department(str, Enum):
    EXECUTIVE = "EXECUTIVE"
    PRODUCT = "PRODUCT"
    ENGINEERING = "ENGINEERING"
    QUALITY = "QUALITY"
    SECURITY = "SECURITY"
    RESEARCH = "RESEARCH"
    OPERATIONS = "OPERATIONS"
    DOCUMENTATION = "DOCUMENTATION"


class EmployeeStatus(str, Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    AVAILABLE = "available"
    PLANNING = "planning"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    REVIEWING = "reviewing"
    MEETING = "meeting"
    PAUSED = "paused"
    FAILED = "failed"


class ProjectComplexity(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    role: str
    display_name: str
    department: Department
    capabilities: tuple[str, ...] = ()
    specializations: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    write_permission: str = "read_only"
    model_profile: str = "balanced"
    status: EmployeeStatus = EmployeeStatus.OFFLINE
    active_project: str | None = None
    current_tasks: tuple[str, ...] = ()
    experience_summary: str = ""
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "display_name": self.display_name,
            "department": self.department.value,
            "capabilities": list(self.capabilities),
            "specializations": list(self.specializations),
            "allowed_tools": list(self.allowed_tools),
            "write_permission": self.write_permission,
            "model_profile": self.model_profile,
            "status": self.status.value,
            "active_project": self.active_project,
            "current_tasks": list(self.current_tasks),
            "experience_summary": self.experience_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ProjectTeamMember:
    agent_id: str
    role: str
    department: Department
    status: EmployeeStatus = EmployeeStatus.AVAILABLE
    is_lead: bool = False
    display_name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "department": self.department.value,
            "status": self.status.value,
            "is_lead": self.is_lead,
            "display_name": self.display_name,
        }


@dataclass(frozen=True)
class ProjectOrganizationPlan:
    project_id: str
    objective: str
    complexity: ProjectComplexity
    project_manager_id: str | None
    engineering_manager_id: str
    departments: tuple[Department, ...]
    members: tuple[ProjectTeamMember, ...]
    phase: str = "initiating"
    priority: int = 50
    team_state: str = "forming"
    rationale: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "objective": self.objective,
            "complexity": self.complexity.value,
            "project_manager_id": self.project_manager_id,
            "engineering_manager_id": self.engineering_manager_id,
            "departments": [department.value for department in self.departments],
            "members": [member.as_dict() for member in self.members],
            "phase": self.phase,
            "priority": self.priority,
            "team_state": self.team_state,
            "rationale": list(self.rationale),
            "risks": list(self.risks),
        }


@dataclass(frozen=True)
class ProjectOrganization:
    project: dict[str, Any]
    members: tuple[ProjectTeamMember, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        result = dict(self.project)
        result["team_members"] = [member.as_dict() for member in self.members]
        return result
