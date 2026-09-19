"""Persistent organizational layer for AI-Engineer.

The package composes existing coordination roles, task DAGs, messages and
memory. It does not create alternate execution primitives.
"""

from .director import CompanyDirector, TeamPlanner
from .sales import (
    ClientNeedsSummary,
    CommercialEscalation,
    OpportunityBrief,
    OpenQuestions,
    ProposalDraft,
    RecommendedNextAction,
    Risks,
    SalesAgent,
)
from .requirements import (
    AcceptanceCriteria,
    Assumptions,
    Constraints,
    FunctionalRequirements,
    NonFunctionalRequirements,
    OutOfScopeItems,
    ProjectSummary,
    RequirementEntry,
    RequirementsAgent,
    RequirementsSpecification,
)
from .models import (
    AgentProfile,
    Department,
    EmployeeStatus,
    ProjectComplexity,
    ProjectOrganizationPlan,
    ProjectTeamMember,
)
from .store import (
    ensure_employee,
    get_employee,
    get_project_organization,
    list_employees,
    list_project_team,
    save_project_organization,
    update_employee_status,
)

__all__ = [
    "AgentProfile",
    "CompanyDirector",
    "Department",
    "EmployeeStatus",
    "ProjectComplexity",
    "ProjectOrganizationPlan",
    "ProjectTeamMember",
    "TeamPlanner",
    "SalesAgent",
    "RequirementsAgent",
    "RequirementsSpecification",
    "RequirementEntry",
    "ProjectSummary",
    "FunctionalRequirements",
    "NonFunctionalRequirements",
    "AcceptanceCriteria",
    "Constraints",
    "Assumptions",
    "OutOfScopeItems",
    "ClientNeedsSummary",
    "CommercialEscalation",
    "OpportunityBrief",
    "OpenQuestions",
    "ProposalDraft",
    "RecommendedNextAction",
    "Risks",
    "ensure_employee",
    "get_employee",
    "get_project_organization",
    "list_employees",
    "list_project_team",
    "save_project_organization",
    "update_employee_status",
]

from .project_manager import (
    DeliverablePlan,
    MilestonePlan,
    ProjectManager,
    ProjectManagerAgent,
    ProjectStatusReport,
    ScopeEscalation,
)

__all__ += [
    "DeliverablePlan",
    "MilestonePlan",
    "ProjectManager",
    "ProjectManagerAgent",
    "ProjectStatusReport",
    "ScopeEscalation",
]
from .engineering_manager import (
    BlockerReport,
    EngineeringManager,
    EngineeringManagerAgent,
    TechnicalConflictResolution,
    TechnicalDelegation,
    TechnicalReadiness,
)

__all__ += [
    "BlockerReport",
    "EngineeringManager",
    "EngineeringManagerAgent",
    "TechnicalConflictResolution",
    "TechnicalDelegation",
    "TechnicalReadiness",
]
from .architect import (
    APIContract,
    ArchitectAgent,
    ArchitectureChallenge,
    ArchitectureProposal,
    ArchitectureRevision,
    ArchitectureRisk,
    ComponentMap,
    DataFlow,
    SoftwareArchitect,
    SoftwareArchitectAgent,
    TechnologyDecision,
)

__all__ += [
    "APIContract",
    "ArchitectAgent",
    "ArchitectureChallenge",
    "ArchitectureProposal",
    "ArchitectureRevision",
    "ArchitectureRisk",
    "ComponentMap",
    "DataFlow",
    "SoftwareArchitect",
    "SoftwareArchitectAgent",
    "TechnologyDecision",
]
from .ux_designer import (
    AccessibilityRequirement,
    ComponentRequirement,
    DesignNotes,
    InteractionSpecification,
    ResponsiveRule,
    ScreenDefinition,
    UXDesigner,
    UXDesignerAgent,
    UXDesignSpecification,
    UXUIDesignerAgent,
    UserFlow,
)

__all__ += [
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
from .backend_engineer import (
    BackendClaim,
    BackendEngineer,
    BackendEngineerAgent,
    BackendImplementationPlan,
    BackendImplementationResult,
)

__all__ += [
    "BackendClaim",
    "BackendEngineer",
    "BackendEngineerAgent",
    "BackendImplementationPlan",
    "BackendImplementationResult",
]

from .frontend_engineer import (
    APIClarificationRequest,
    FrontendClaim,
    FrontendEngineer,
    FrontendEngineerAgent,
    FrontendImplementationPlan,
    FrontendImplementationResult,
    FrontendIntegrationIssue,
)

__all__ += [
    "APIClarificationRequest",
    "FrontendClaim",
    "FrontendEngineer",
    "FrontendEngineerAgent",
    "FrontendImplementationPlan",
    "FrontendImplementationResult",
    "FrontendIntegrationIssue",
]
from .integration_engineer import (
    ContractMismatch,
    IntegrationEngineer,
    IntegrationEngineerAgent,
    IntegrationFailure,
    IntegrationReport,
    IntegrationSuccess,
    RevisionRequest,
)

__all__ += [
    "ContractMismatch",
    "IntegrationEngineer",
    "IntegrationEngineerAgent",
    "IntegrationFailure",
    "IntegrationReport",
    "IntegrationSuccess",
    "RevisionRequest",
]

from .test_engineer import (
    AcceptanceCriteriaVerification,
    DefectReport,
    QAEngineerAgent,
    RegressionVerification,
    RepairLoop,
    TestEngineer,
    TestEngineerAgent,
    TesterAgent,
    TestPlan,
)

__all__ += [
    "AcceptanceCriteriaVerification",
    "DefectReport",
    "QAEngineerAgent",
    "RegressionVerification",
    "RepairLoop",
    "TestEngineer",
    "TestEngineerAgent",
    "TesterAgent",
    "TestPlan",
]

from .debugger import (
    DebugAgent,
    Debugger,
    DebuggerAgent,
    FailureMemory,
    FailureReproduction,
    RepairResult,
    RootCauseRecord,
)

__all__ += [
    "DebugAgent",
    "Debugger",
    "DebuggerAgent",
    "FailureMemory",
    "FailureReproduction",
    "RepairResult",
    "RootCauseRecord",
]

from .reviewer import (
    CodeReview,
    CodeReviewer,
    CodeReviewerAgent,
    ReviewEvidence,
    ReviewFinding,
    ReviewRecord,
    Reviewer,
    ReviewerAgent,
)

__all__ += [
    "CodeReview",
    "CodeReviewer",
    "CodeReviewerAgent",
    "ReviewEvidence",
    "ReviewFinding",
    "ReviewRecord",
    "Reviewer",
    "ReviewerAgent",
]


from .security import (
    SecurityAgent,
    SecurityEngineerAgent,
    SecurityEvidence,
    SecurityFinding,
    SecurityReview,
    SecurityReviewRecord,
    SecurityReviewer,
)

__all__ += [
    "SecurityAgent",
    "SecurityEngineerAgent",
    "SecurityEvidence",
    "SecurityFinding",
    "SecurityReview",
    "SecurityReviewRecord",
    "SecurityReviewer",
]

from .devops import (
    DeploymentAgent,
    DeploymentApproval,
    DeploymentEngineerAgent,
    DeploymentPlan,
    DeploymentRecord,
    DeploymentResult,
    DevOpsAgent,
    DevopsAgent,
    HealthCheckResult,
    RollbackResult,
    SmokeTestResult,
)

__all__ += [
    "DeploymentAgent",
    "DeploymentApproval",
    "DeploymentEngineerAgent",
    "DeploymentPlan",
    "DeploymentRecord",
    "DeploymentResult",
    "DevOpsAgent",
    "DevopsAgent",
    "HealthCheckResult",
    "RollbackResult",
    "SmokeTestResult",
]

from .documentation import (
    DocumentationAgent,
    DocumentationDriftItem,
    DocumentationDriftReport,
    DocumentationEngineerAgent,
    DocumentationEvidence,
    DocumentationUpdate,
    DocsAgent,
    ReleaseNotes,
)

__all__ += [
    "DocumentationAgent",
    "DocumentationDriftItem",
    "DocumentationDriftReport",
    "DocumentationEngineerAgent",
    "DocumentationEvidence",
    "DocumentationUpdate",
    "DocsAgent",
    "ReleaseNotes",
]

from .release_verifier import (
    ReleaseBlocker,
    ReleaseVerification,
    ReleaseVerificationAgent,
    ReleaseVerifier,
    ReleaseVerifierAgent,
    VerificationEvidence,
)

__all__ += [
    "ReleaseBlocker",
    "ReleaseVerification",
    "ReleaseVerificationAgent",
    "ReleaseVerifier",
    "ReleaseVerifierAgent",
    "VerificationEvidence",
]

from .seo_manager import (
    SEO_AUDIT_CATEGORIES,
    SEO_INTENTS,
    SEO_PRIORITIES,
    SEO_STATUSES,
    SEOAuditFinding,
    SEOBacklogTask,
    SEOKeywordCluster,
    SEOManager,
    SEOManagerAgent,
    SEOProjectProfile,
    SEOQualityGate,
    SEOReport,
)

__all__ += [
    "SEO_AUDIT_CATEGORIES",
    "SEO_INTENTS",
    "SEO_PRIORITIES",
    "SEO_STATUSES",
    "SEOAuditFinding",
    "SEOBacklogTask",
    "SEOKeywordCluster",
    "SEOManager",
    "SEOManagerAgent",
    "SEOProjectProfile",
    "SEOQualityGate",
    "SEOReport",
]
from .seo_specialist import (
    AGENT_ID as SEO_SPECIALIST_AGENT_ID,
    DISPLAY_NAME as SEO_SPECIALIST_DISPLAY_NAME,
    ROLE as SEO_SPECIALIST_ROLE,
    SEOContentBrief,
    SEOContentGap,
    SEOFinding,
    SEOImplementationRequest,
    SEOInternalLinkRecommendation,
    SEOSpecialist,
    SEOSpecialistAgent,
    SEOVerification,
)

__all__ += [
    "SEO_SPECIALIST_AGENT_ID",
    "SEO_SPECIALIST_DISPLAY_NAME",
    "SEO_SPECIALIST_ROLE",
    "SEOContentBrief",
    "SEOContentGap",
    "SEOFinding",
    "SEOImplementationRequest",
    "SEOInternalLinkRecommendation",
    "SEOSpecialist",
    "SEOSpecialistAgent",
    "SEOVerification",
]