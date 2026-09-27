from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from app.skill_registry import SkillRegistry, UnknownSkillError
from app.skill_script_gateway import (
    REQUIRED_CHAIN,
    DefaultSkillToolPolicy,
    SkillApprovalRequired,
    SkillExecutionError,
    SkillExecutionTimeout,
    SkillScriptGateway,
    SkillScriptPolicy,
    SkillScriptRequest,
    ToolPolicyDecision,
    redact_headers,
    redact_text,
    validate_artifact_path,
    validate_network_target,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class RecordingLocalAgent:
    def __init__(self, *, preview: dict[str, object] | None = None) -> None:
        self.preview_result = preview or {"risk": "safe", "requires_approval": False}
        self.previewed: list[object] = []
        self.executed: list[tuple[object, bool]] = []

    async def preview_skill_script(self, plan: object) -> dict[str, object]:
        self.previewed.append(plan)
        return dict(self.preview_result)

    async def run_skill_script(self, plan: object, *, approved: bool) -> dict[str, object]:
        self.executed.append((plan, approved))
        return {
            "ok": True,
            "status": "success",
            "stdout": "Authorization: Bearer should-not-persist",
            "stderr": "Cookie=session-secret",
            "exit_code": 0,
        }


class TimeoutLocalAgent(RecordingLocalAgent):
    async def preview_skill_script(self, plan: object) -> dict[str, object]:
        raise asyncio.TimeoutError()


class RedirectLocalAgent(RecordingLocalAgent):
    async def run_skill_script(self, plan: object, *, approved: bool) -> dict[str, object]:
        return {
            "ok": True,
            "status": "success",
            "url": "https://unexpected.invalid/health",
            "response_url": "https://unexpected.invalid/health",
            "exit_code": 0,
        }


class RecordingCompatibilityAdapter:
    def __init__(self) -> None:
        self.calls: list[object] = []

    async def apply_skill_state_view(self, plan: object) -> dict[str, object]:
        self.calls.append(plan)
        return {"ok": True, "status": "compatibility_view_updated"}


class ExactApproval:
    def __init__(self, *, valid: bool = True) -> None:
        self.valid = valid
        self.seen: list[tuple[str, str]] = []

    def is_valid(self, *, approval_id: str, action_hash: str, request: SkillScriptRequest) -> bool:
        self.seen.append((approval_id, action_hash))
        return self.valid and approval_id == "approval-1"


class AllowingToolPolicy:
    def __init__(self) -> None:
        self.plans: list[object] = []

    def authorize(self, plan: object) -> ToolPolicyDecision:
        self.plans.append(plan)
        return ToolPolicyDecision(True, "test policy allowed the already-scoped plan")


class SkillScriptPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = SkillRegistry(REPOSITORY_ROOT)
        cls.policy = SkillScriptPolicy(cls.registry, allowed_workspace_roots=(REPOSITORY_ROOT,))

    def request(self, **overrides: object) -> SkillScriptRequest:
        values: dict[str, object] = {
            "skill_id": "project-analysis-prompt-engineering",
            "script_name": "validate_stage01.py",
            "role": "requirements",
            "task_id": "task-1",
            "project_id": "project-1",
            "workspace": str(REPOSITORY_ROOT),
            "router_approved": True,
            "role_tools": frozenset({"evidence_write"}),
            "task_tools": frozenset({"evidence_write"}),
            "global_tools": frozenset({"evidence_write"}),
            "requested_capability": "evidence_write",
            "artifact_path": "reports/skill-evidence.json",
            "execution_chain": REQUIRED_CHAIN,
            "task_plan_authorized": True,
        }
        values.update(overrides)
        return SkillScriptRequest(**values)

    def test_untrusted_skill_script_path_is_rejected(self) -> None:
        with self.assertRaises(UnknownSkillError):
            self.registry.get_script("project-analysis-prompt-engineering", "../outside.py")

    def test_direct_model_invocation_without_worker_chain_is_rejected(self) -> None:
        request = self.request(execution_chain=())
        with self.assertRaises(SkillExecutionError):
            self.policy.plan(request)

    def test_workspace_and_artifact_escape_are_rejected(self) -> None:
        with self.assertRaises(SkillExecutionError):
            self.policy.plan(self.request(cwd="./../outside"))
        with self.assertRaises(SkillExecutionError):
            validate_artifact_path(
                REPOSITORY_ROOT,
                "src/unsafe.py",
                allowed_roots=(REPOSITORY_ROOT,),
            )
        with self.assertRaises(SkillExecutionError):
            validate_artifact_path(
                REPOSITORY_ROOT,
                "reports/../../unsafe.json",
                allowed_roots=(REPOSITORY_ROOT,),
            )

    def test_reviewer_skill_cannot_gain_shell_from_final_review(self) -> None:
        request = self.request(
            skill_id="fullstack-final-review",
            script_name="run_check.py",
            role="reviewer",
            role_tools=frozenset({"read_file", "diff", "safe_validation"}),
            task_tools=frozenset({"read_file", "diff", "safe_validation"}),
            global_tools=frozenset({"read_file", "diff", "safe_validation"}),
            requested_capability="safe_validation",
            command=("python", "skills/software-delivery/fullstack-final-review/scripts/run_check.py"),
            declared_commands=(("python", "skills/software-delivery/fullstack-final-review/scripts/run_check.py"),),
        )
        with self.assertRaises(SkillExecutionError):
            self.policy.plan(request)

    def test_command_must_be_exactly_repository_declared(self) -> None:
        request = self.request(
            skill_id="frontend-architecture",
            script_name="frontend_quality_gate.py",
            role="frontend",
            role_tools=frozenset({"frontend_test", "evidence_write"}),
            task_tools=frozenset({"frontend_test", "evidence_write"}),
            global_tools=frozenset({"frontend_test", "evidence_write"}),
            requested_capability="frontend_test",
            command=("python", "-c", "import os"),
            declared_commands=(("python", "skills/software-delivery/frontend-architecture/scripts/frontend_quality_gate.py"),),
        )
        with self.assertRaises(SkillExecutionError):
            self.policy.plan(request)

    def test_shell_substitution_is_rejected(self) -> None:
        request = self.request(
            skill_id="frontend-architecture",
            script_name="frontend_quality_gate.py",
            role="frontend",
            role_tools=frozenset({"frontend_test", "evidence_write"}),
            task_tools=frozenset({"frontend_test", "evidence_write"}),
            global_tools=frozenset({"frontend_test", "evidence_write"}),
            requested_capability="frontend_test",
            command=("python", "$(whoami)"),
            declared_commands=(("python", "$(whoami)"),),
        )
        with self.assertRaises(SkillExecutionError):
            self.policy.plan(request)

    def test_command_requires_authorized_task_plan(self) -> None:
        request = self.request(
            skill_id="frontend-architecture",
            script_name="frontend_quality_gate.py",
            role="frontend",
            role_tools=frozenset({"frontend_test", "evidence_write"}),
            task_tools=frozenset({"frontend_test", "evidence_write"}),
            global_tools=frozenset({"frontend_test", "evidence_write"}),
            requested_capability="frontend_test",
            task_plan_authorized=False,
            command=("python", "skills/software-delivery/frontend-architecture/scripts/frontend_quality_gate.py"),
            declared_commands=(("python", "skills/software-delivery/frontend-architecture/scripts/frontend_quality_gate.py"),),
        )
        with self.assertRaises(SkillExecutionError):
            self.policy.plan(request)

    def test_project_state_script_uses_compatibility_adapter_only(self) -> None:
        request = self.request(
            skill_id="project-analysis-prompt-engineering",
            script_name="update_project_state.py",
            artifact_path="project-state.json",
        )
        plan = self.policy.plan(request)
        self.assertEqual(plan.route, "compatibility-adapter-only")

    def test_arbitrary_and_metadata_network_targets_are_rejected(self) -> None:
        with self.assertRaises(SkillExecutionError):
            validate_network_target("https://example.com/health")
        with self.assertRaises(SkillExecutionError):
            validate_network_target(
                "http://169.254.169.254/latest/meta-data",
                declared_targets=("http://169.254.169.254/latest/meta-data",),
            )

    def test_local_health_target_requires_exact_declaration(self) -> None:
        target = "http://127.0.0.1:8012/health"
        self.assertEqual(
            validate_network_target(target, declared_targets=(target,)),
            target,
        )

    def test_secret_redaction_covers_headers_and_evidence_text(self) -> None:
        headers = redact_headers({"Authorization": "Bearer abc", "X-Trace": "safe"})
        self.assertEqual(headers["Authorization"], "[REDACTED]")
        self.assertEqual(headers["X-Trace"], "safe")
        redacted = redact_text("Authorization: Bearer abc\npassword=plain\n-----BEGIN PRIVATE KEY-----x-----END PRIVATE KEY-----")
        self.assertNotIn("abc", redacted)
        self.assertNotIn("plain", redacted)
        self.assertNotIn("PRIVATE KEY-----x", redacted)

    def test_timeout_and_output_limits_are_bounded(self) -> None:
        with self.assertRaises(SkillExecutionTimeout):
            self.policy.plan(self.request(timeout_seconds=601))
        with self.assertRaises(SkillExecutionError):
            self.policy.plan(self.request(output_limit=1024 * 1024 + 1))


class SkillScriptGatewayTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = SkillRegistry(REPOSITORY_ROOT)
        cls.policy = SkillScriptPolicy(cls.registry, allowed_workspace_roots=(REPOSITORY_ROOT,))

    def request(self, **overrides: object) -> SkillScriptRequest:
        values: dict[str, object] = {
            "skill_id": "project-analysis-prompt-engineering",
            "script_name": "validate_stage01.py",
            "role": "requirements",
            "task_id": "task-1",
            "project_id": "project-1",
            "workspace": str(REPOSITORY_ROOT),
            "router_approved": True,
            "role_tools": frozenset({"evidence_write"}),
            "task_tools": frozenset({"evidence_write"}),
            "global_tools": frozenset({"evidence_write"}),
            "requested_capability": "evidence_write",
            "artifact_path": "reports/skill-evidence.json",
            "execution_chain": REQUIRED_CHAIN,
            "task_plan_authorized": True,
        }
        values.update(overrides)
        return SkillScriptRequest(**values)

    async def test_gateway_requires_local_agent_and_tool_policy(self) -> None:
        local = RecordingLocalAgent()
        gateway = SkillScriptGateway(policy=self.policy, local_agent=local)
        with self.assertRaises(SkillExecutionError):
            await gateway.execute(self.request())

        gateway = SkillScriptGateway(
            policy=self.policy,
            tool_policy=AllowingToolPolicy(),
        )
        with self.assertRaises(SkillExecutionError):
            await gateway.execute(self.request())

    async def test_safe_script_runs_only_through_local_agent_and_redacts_result(self) -> None:
        local = RecordingLocalAgent()
        gateway = SkillScriptGateway(
            policy=self.policy,
            local_agent=local,
            tool_policy=AllowingToolPolicy(),
        )
        result = await gateway.execute(self.request())
        self.assertTrue(result["ok"])
        self.assertEqual(len(local.previewed), 1)
        self.assertEqual(len(local.executed), 1)
        self.assertNotIn("should-not-persist", str(result))
        self.assertNotIn("session-secret", str(result))

    async def test_dangerous_command_requires_server_approval_not_boolean(self) -> None:
        local = RecordingLocalAgent(preview={"risk": "approval_required", "requires_approval": True})
        request = self.request(
            skill_id="deployment-production",
            script_name="self_test.py",
            role="devops",
            role_tools=frozenset({"safe_build", "health_check", "evidence_write"}),
            task_tools=frozenset({"safe_build", "health_check", "evidence_write"}),
            global_tools=frozenset({"safe_build", "health_check", "evidence_write"}),
            requested_capability="safe_build",
            command=("python", "skills/software-delivery/deployment-production/scripts/self_test.py"),
            declared_commands=(("python", "skills/software-delivery/deployment-production/scripts/self_test.py"),),
            url="http://127.0.0.1:8012/health",
            declared_targets=("http://127.0.0.1:8012/health",),
            artifact_path="reports/self-test.json",
            client_approved=True,
        )
        gateway = SkillScriptGateway(
            policy=self.policy,
            local_agent=local,
            tool_policy=DefaultSkillToolPolicy(request, self.registry),
        )
        with self.assertRaises(SkillApprovalRequired):
            await gateway.execute(request)
        self.assertEqual(local.executed, [])

        approval = ExactApproval()
        approved_request = SkillScriptRequest(**{**request.__dict__, "approval_id": "approval-1"})
        gateway = SkillScriptGateway(
            policy=self.policy,
            local_agent=local,
            tool_policy=DefaultSkillToolPolicy(approved_request, self.registry),
            approval_verifier=approval,
        )
        result = await gateway.execute(approved_request)
        self.assertTrue(result["ok"])
        self.assertEqual(len(local.executed), 1)
        self.assertEqual(local.executed[0][1], True)
        self.assertEqual(approval.seen[0][0], "approval-1")

    async def test_approved_health_check_is_scoped_to_declared_target(self) -> None:
        local = RecordingLocalAgent()
        request = self.request(
            skill_id="deployment-production",
            script_name="smoke_http.py",
            role="devops",
            role_tools=frozenset({"health_check", "evidence_write"}),
            task_tools=frozenset({"health_check", "evidence_write"}),
            global_tools=frozenset({"health_check", "evidence_write"}),
            requested_capability="health_check",
            url="http://127.0.0.1:8012/health",
            declared_targets=("http://127.0.0.1:8012/health",),
            artifact_path="reports/health.json",
            approval_id="approval-1",
        )
        gateway = SkillScriptGateway(
            policy=self.policy,
            local_agent=local,
            tool_policy=DefaultSkillToolPolicy(request, self.registry),
            approval_verifier=ExactApproval(),
        )
        result = await gateway.execute(request)
        self.assertTrue(result["ok"])
        self.assertEqual(len(local.executed), 1)

    async def test_local_agent_timeout_is_reported_as_bounded_failure(self) -> None:
        gateway = SkillScriptGateway(
            policy=self.policy,
            local_agent=TimeoutLocalAgent(),
            tool_policy=AllowingToolPolicy(),
        )
        with self.assertRaises(SkillExecutionTimeout):
            await gateway.execute(self.request())

    async def test_network_redirect_evidence_is_rejected(self) -> None:
        target = "http://127.0.0.1:8012/health"
        request = self.request(
            skill_id="deployment-production",
            script_name="smoke_http.py",
            role="devops",
            role_tools=frozenset({"health_check", "evidence_write"}),
            task_tools=frozenset({"health_check", "evidence_write"}),
            global_tools=frozenset({"health_check", "evidence_write"}),
            requested_capability="health_check",
            url=target,
            declared_targets=(target,),
            artifact_path="reports/health.json",
            approval_id="approval-1",
        )
        gateway = SkillScriptGateway(
            policy=self.policy,
            local_agent=RedirectLocalAgent(),
            tool_policy=DefaultSkillToolPolicy(request, self.registry),
            approval_verifier=ExactApproval(),
        )
        with self.assertRaises(SkillExecutionError):
            await gateway.execute(request)

    async def test_high_risk_compatibility_update_requires_server_approval(self) -> None:
        request = self.request(
            skill_id="application-security",
            script_name="update_project_state.py",
            role="security",
            role_tools=frozenset({"evidence_write"}),
            task_tools=frozenset({"evidence_write"}),
            global_tools=frozenset({"evidence_write"}),
            requested_capability="evidence_write",
            artifact_path="project-state.json",
        )
        adapter = RecordingCompatibilityAdapter()
        gateway = SkillScriptGateway(
            policy=self.policy,
            tool_policy=DefaultSkillToolPolicy(request, self.registry),
            compatibility_adapter=adapter,
        )
        with self.assertRaises(SkillApprovalRequired):
            await gateway.execute(request)
        approved = SkillScriptRequest(**{**request.__dict__, "approval_id": "approval-1"})
        gateway = SkillScriptGateway(
            policy=self.policy,
            tool_policy=DefaultSkillToolPolicy(approved, self.registry),
            approval_verifier=ExactApproval(),
            compatibility_adapter=adapter,
        )
        result = await gateway.execute(approved)
        self.assertTrue(result["ok"])
        self.assertEqual(len(adapter.calls), 1)
    async def test_compatibility_adapter_is_used_instead_of_local_agent(self) -> None:
        adapter = RecordingCompatibilityAdapter()
        request = self.request(
            skill_id="project-analysis-prompt-engineering",
            script_name="update_project_state.py",
            artifact_path="project-state.json",
        )
        gateway = SkillScriptGateway(
            policy=self.policy,
            tool_policy=DefaultSkillToolPolicy(request, self.registry),
            compatibility_adapter=adapter,
        )
        result = await gateway.execute(request)
        self.assertTrue(result["ok"])
        self.assertEqual(len(adapter.calls), 1)


if __name__ == "__main__":
    unittest.main()
