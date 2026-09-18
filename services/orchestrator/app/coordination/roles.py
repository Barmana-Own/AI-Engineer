from __future__ import annotations
from .models import RoleContract, WritePermission
_READ = ("read_file", "list_files", "search", "inspect", "read_memory")
_WRITE = _READ + ("write_file", "replace_text", "run_tests", "checkpoint")
def _role(id: str, name: str, purpose: str, responsibilities: tuple[str, ...], capabilities: tuple[str, ...], tools: tuple[str, ...], write: WritePermission, profile: str = "balanced", inputs: tuple[str, ...] = ("objective", "project_context"), outputs: tuple[str, ...] = ("summary", "evidence", "next_action"), escalation: tuple[str, ...] = ("Escalate blockers to supervisor.",)) -> RoleContract:
    return RoleContract(id, name, purpose, responsibilities, capabilities, tools, write, profile, inputs, outputs, escalation)
ROLE_REGISTRY: dict[str, RoleContract] = {
    "supervisor": _role("supervisor", "Engineering Supervisor", "Manage an engineering objective and coordinate specialists.", ("validate scope", "delegate work", "resolve disagreements", "approve completion"), ("orchestration", "scheduling", "decision"), _READ, WritePermission.READ_ONLY, "reasoning", escalation=("Resolve conflicts after bounded discussion.", "Stop terminal failures after retry budget.")),
    "requirements": _role("requirements", "Requirements Analyst", "Turn objectives into testable requirements.", ("clarify scope", "define acceptance criteria", "identify risks"), ("analysis", "requirements"), _READ, WritePermission.READ_ONLY),
    "planner": _role("planner", "Product Planner", "Decompose requirements into an executable task graph.", ("sequence work", "define dependencies", "estimate outputs"), ("planning", "dag"), _READ, WritePermission.READ_ONLY),
    "architect": _role("architect", "Software Architect", "Design coherent boundaries and contracts.", ("choose interfaces", "identify conflicts", "review tradeoffs"), ("architecture", "design"), _READ, WritePermission.READ_ONLY),
    "researcher": _role("researcher", "Researcher / Inspector", "Collect bounded evidence from the project and trusted sources.", ("inspect code", "cite evidence", "surface unknowns"), ("research", "evidence"), _READ, WritePermission.READ_ONLY),
    "backend": _role("backend", "Backend Engineer", "Implement server-side behavior in an assigned scope.", ("edit backend", "preserve contracts", "add tests"), ("backend", "implementation"), _WRITE, WritePermission.SCOPED),
    "frontend": _role("frontend", "Frontend Engineer", "Implement client behavior in an assigned scope.", ("edit frontend", "preserve UI contracts", "add tests"), ("frontend", "implementation"), _WRITE, WritePermission.SCOPED),
    "implementer": _role("implementer", "General Implementer", "Apply a scoped implementation with evidence.", ("edit assigned files", "run validation", "report diff"), ("implementation", "tools"), _WRITE, WritePermission.SCOPED),
    "tester": _role("tester", "Test Engineer", "Verify behavior and produce reproducible evidence.", ("run tests", "add regression tests", "classify failures"), ("testing", "validation"), _READ + ("run_tests",), WritePermission.READ_ONLY),
    "debugger": _role("debugger", "Debugger", "Repair a proven failure within a bounded scope.", ("reproduce failure", "fix root cause", "hand back for test"), ("debugging", "recovery"), _WRITE, WritePermission.SCOPED),
    "reviewer": _role("reviewer", "Code Reviewer", "Review changes for correctness and maintainability.", ("inspect diff", "challenge assumptions", "request revisions"), ("review", "quality"), _READ + ("diff",), WritePermission.READ_ONLY),
    "security": _role("security", "Security Reviewer", "Find and remediate material security risks.", ("threat model", "review trust boundaries", "verify fixes"), ("security", "risk"), _READ + ("diff",), WritePermission.READ_ONLY),
    "integration": _role("integration", "Integration Engineer", "Join compatible work and verify service contracts.", ("check conflicts", "run integration checks", "coordinate merges"), ("integration", "contracts"), _READ + ("run_tests",), WritePermission.SCOPED),
    "docs": _role("docs", "Documentation Engineer", "Keep operational and technical documentation accurate.", ("update docs", "record decisions", "document risks"), ("documentation",), _WRITE, WritePermission.SCOPED),
    "release_verifier": _role("release_verifier", "Release Verification Agent", "Confirm release readiness from independent evidence.", ("run final checks", "verify migrations", "report blockers"), ("release", "verification"), _READ + ("run_tests",), WritePermission.READ_ONLY, "reasoning"),
}
ROLE_ALIASES = {"manager": "supervisor", "monitor": "supervisor", "inspector": "researcher", "scout": "researcher", "verifier": "tester", "tests": "tester", "test-verifier": "tester", "local-agent": "implementer", "orchestrator": "supervisor", "ui": "frontend", "desktop": "integration", "gateway": "backend"}
def resolve_role(role_id: str) -> str:
    normalized = str(role_id or "").strip().casefold()
    return ROLE_ALIASES.get(normalized, normalized) if normalized in ROLE_ALIASES or normalized in ROLE_REGISTRY else "researcher"
def get_role_contract(role_id: str) -> RoleContract:
    return ROLE_REGISTRY[resolve_role(role_id)]
def list_role_contracts() -> list[dict[str, object]]:
    return [contract.as_dict() for contract in ROLE_REGISTRY.values()]
