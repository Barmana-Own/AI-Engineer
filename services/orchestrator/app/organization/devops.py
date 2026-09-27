from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_HIGH_RISK_OPERATIONS = frozenset(
    {
        "production_deployment",
        "service_restart",
        "dns_change",
        "remote_publication",
        "destructive_database_migration",
        "infrastructure_modification",
    }
)
_RELEASE_TARGETS = frozenset({"release_verifier", "operations", "engineering_manager", "supervisor"})


def _clean(value: object, *, max_chars: int = 4000) -> str:
    cleaned, _ = sanitize_text(str(value or ""), max_chars=max_chars)
    return cleaned.strip()


def _sequence(values: object | None) -> tuple[object, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, Mapping)):
        return (values,)
    try:
        return tuple(values)  # type: ignore[arg-type]
    except TypeError:
        return (values,)


def _items(values: object | None, *, limit: int = 100, max_chars: int = 2000) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        item = _clean(value, max_chars=max_chars)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return tuple(result)


def _bool_result(value: object) -> bool:
    if isinstance(value, Mapping):
        if "passed" in value:
            return bool(value["passed"])
        if "success" in value:
            return bool(value["success"])
        if "ok" in value:
            return bool(value["ok"])
    return bool(value)


@dataclass(frozen=True)
class DeploymentPlan:
    plan_id: str
    project_id: str
    task_id: str
    release_candidate: str
    environment: str
    operations: tuple[str, ...]
    configuration_files: tuple[str, ...]
    changed_files: tuple[str, ...]
    migration: str | None
    health_endpoint: str | None
    smoke_tests: tuple[str, ...]
    rollback_steps: tuple[str, ...]
    risk_level: str
    requires_approval: bool
    status: str = "planned"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in (
            "operations",
            "configuration_files",
            "changed_files",
            "smoke_tests",
            "rollback_steps",
        ):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class DeploymentApproval:
    approval_id: str
    plan_id: str
    approved_by: str
    approval_reference: str
    scope: tuple[str, ...]
    status: str = "approved"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["scope"] = list(self.scope)
        return result


@dataclass(frozen=True)
class HealthCheckResult:
    check_id: str
    plan_id: str
    passed: bool
    endpoint: str | None
    evidence: tuple[str, ...]
    status: str
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class SmokeTestResult:
    smoke_id: str
    plan_id: str
    passed: bool
    tests: tuple[str, ...]
    evidence: tuple[str, ...]
    status: str
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["tests"] = list(self.tests)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class RollbackResult:
    rollback_id: str
    plan_id: str
    success: bool
    reason: str
    steps: tuple[str, ...]
    status: str
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["steps"] = list(self.steps)
        return result


@dataclass(frozen=True)
class DeploymentResult:
    deployment_id: str
    plan_id: str
    environment: str
    success: bool
    health_passed: bool
    smoke_passed: bool
    rolled_back: bool
    status: str
    evidence: tuple[str, ...]
    error: str | None = None
    message_id: str | None = None
    rollback_id: str | None = None
    handoff_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


DeploymentRecord = DeploymentResult


class DevOpsAgent:
    """Controlled deployment planner/executor using the existing message and handoff bus."""

    ROLE = "devops"
    DISPLAY_NAME = "DevOps / Deployment Engineer"
    AGENT_ID = "employee-devops"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id=self.AGENT_ID,
            display_name=self.DISPLAY_NAME,
            department=Department.OPERATIONS,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"DevOps task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("DevOps Agent can only operate devops tasks")
        return task

    def _publish(
        self,
        *,
        message_type: MessageType,
        subject: str,
        body: str,
        project_id: str,
        task_id: str | None = None,
        run_id: str | None = None,
        recipient_role: str | None = None,
        references: object = (),
        topic: str = "devops_operations",
    ) -> dict[str, object]:
        return self.bus.publish(
            sender_role=self.ROLE,
            message_type=message_type,
            subject=_clean(subject, max_chars=500),
            body=_clean(body, max_chars=20_000),
            project_id=project_id,
            task_id=task_id,
            run_id=run_id,
            recipient_role=recipient_role,
            references=_items(references, max_chars=512),
            topic=topic,
        )

    def create_plan(
        self,
        task_id: str,
        *,
        release_candidate: str,
        environment: str,
        operations: object = (),
        configuration_files: object = (),
        changed_files: object = (),
        migration: str | None = None,
        health_endpoint: str | None = None,
        smoke_tests: object = (),
        rollback_steps: object = (),
        risk_level: str | None = None,
        run_id: str | None = None,
    ) -> DeploymentPlan:
        task = self._task(task_id)
        candidate = _clean(release_candidate, max_chars=256)
        target_environment = _clean(environment, max_chars=128).casefold()
        if not candidate or not target_environment:
            raise ValueError("deployment plan requires a release candidate and environment")
        operation_items = tuple(item.casefold() for item in _items(operations, max_chars=128))
        config_items = _items(configuration_files, max_chars=512)
        changed = _items(changed_files, max_chars=512)
        smoke = _items(smoke_tests, max_chars=1000)
        rollback = _items(rollback_steps, max_chars=1000)
        normalized_migration = _clean(migration, max_chars=512) or None
        endpoint = _clean(health_endpoint, max_chars=1000) or None
        if endpoint:
            parsed = urlparse(endpoint)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("health endpoint must be an http(s) URL")
        high_risk = target_environment in {"production", "prod"} or bool(_HIGH_RISK_OPERATIONS.intersection(operation_items))
        if normalized_migration and "destructive" in normalized_migration.casefold():
            high_risk = True
        computed_risk = _clean(risk_level, max_chars=32).casefold() if risk_level else ("high" if high_risk else "medium")
        if computed_risk not in {"low", "medium", "high", "critical"}:
            raise ValueError("risk level must be low, medium, high or critical")
        if high_risk and not rollback:
            raise ValueError("high-risk deployment plans require rollback steps")
        plan = DeploymentPlan(
            plan_id=str(uuid4()),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            release_candidate=candidate,
            environment=target_environment,
            operations=operation_items,
            configuration_files=config_items,
            changed_files=changed,
            migration=normalized_migration,
            health_endpoint=endpoint,
            smoke_tests=smoke,
            rollback_steps=rollback,
            risk_level=computed_risk,
            requires_approval=high_risk or computed_risk in {"high", "critical"},
            status="awaiting_approval" if high_risk or computed_risk in {"high", "critical"} else "ready",
        )
        message = self._publish(
            message_type=MessageType.PROPOSAL,
            subject=f"Deployment plan: {candidate}",
            body=json.dumps(plan.as_dict(), ensure_ascii=False),
            project_id=plan.project_id,
            task_id=plan.task_id,
            run_id=run_id or task.get("run_id"),
            recipient_role="engineering_manager" if plan.requires_approval else "release_verifier",
            references=plan.changed_files + plan.configuration_files + plan.rollback_steps,
            topic="deployment_plan",
        )
        return DeploymentPlan(**{**asdict(plan), "message_id": str(message["message_id"])})

    plan = create_plan
    plan_deployment = create_plan

    def approve_plan(
        self,
        plan: DeploymentPlan,
        *,
        approved_by: str,
        approval_reference: str,
        scope: object = (),
        run_id: str | None = None,
    ) -> DeploymentApproval:
        approver = _clean(approved_by, max_chars=256)
        reference = _clean(approval_reference, max_chars=512)
        if not approver or not reference:
            raise PermissionError("deployment approval requires an approver and policy reference")
        if not plan.requires_approval:
            raise ValueError("approval is only required for high-risk deployment plans")
        approval = DeploymentApproval(
            approval_id=str(uuid4()),
            plan_id=plan.plan_id,
            approved_by=approver,
            approval_reference=reference,
            scope=_items(scope, max_chars=512),
        )
        message = self._publish(
            message_type=MessageType.DECISION,
            subject=f"Deployment approval: {plan.release_candidate}",
            body=json.dumps(approval.as_dict(), ensure_ascii=False),
            project_id=plan.project_id,
            task_id=plan.task_id,
            run_id=run_id,
            recipient_role="devops",
            references=(f"plan:{plan.plan_id}", f"approval:{approval.approval_id}", reference),
            topic="deployment_approval",
        )
        return DeploymentApproval(**{**asdict(approval), "message_id": str(message["message_id"])})

    approve = approve_plan

    def verify_health(
        self,
        plan: DeploymentPlan,
        *,
        checker: Callable[[], object] | None = None,
        evidence: object = (),
        run_id: str | None = None,
    ) -> HealthCheckResult:
        passed = False
        refs = list(_items(evidence, max_chars=512))
        try:
            if checker is not None:
                passed = _bool_result(checker())
            elif plan.health_endpoint:
                request = Request(plan.health_endpoint, headers={"User-Agent": "AI-Engineer-HealthCheck/1"})
                with urlopen(request, timeout=10) as response:  # nosec B310 - endpoint is validated as http(s) above
                    passed = 200 <= int(response.status) < 400
            else:
                raise ValueError("health verification requires a checker or health endpoint")
        except Exception as exc:  # bounded operational evidence; details are sanitized
            refs.append(f"health-error:{_clean(exc, max_chars=512)}")
            passed = False
        if passed:
            refs.append("health-check:passed")
        result = HealthCheckResult(
            check_id=str(uuid4()),
            plan_id=plan.plan_id,
            passed=passed,
            endpoint=plan.health_endpoint,
            evidence=tuple(dict.fromkeys(refs)),
            status="passed" if passed else "failed",
        )
        message = self._publish(
            message_type=MessageType.RESULT if passed else MessageType.BLOCKER,
            subject=f"Health check: {plan.release_candidate}",
            body=json.dumps(result.as_dict(), ensure_ascii=False),
            project_id=plan.project_id,
            task_id=plan.task_id,
            run_id=run_id,
            recipient_role="release_verifier",
            references=result.evidence,
            topic="deployment_health_check",
        )
        return HealthCheckResult(**{**asdict(result), "message_id": str(message["message_id"])})

    health_check = verify_health

    def run_smoke_tests(
        self,
        plan: DeploymentPlan,
        *,
        runner: Callable[[], object] | None = None,
        tests: object = (),
        evidence: object = (),
        run_id: str | None = None,
    ) -> SmokeTestResult:
        test_items = _items(tests, max_chars=1000) or plan.smoke_tests
        refs = list(_items(evidence, max_chars=512))
        passed = False
        try:
            if runner is not None:
                passed = _bool_result(runner())
            elif test_items:
                raise ValueError("smoke test runner is required; test names alone are not proof")
            else:
                raise ValueError("smoke verification requires a runner")
        except Exception as exc:
            refs.append(f"smoke-error:{_clean(exc, max_chars=512)}")
            passed = False
        if passed:
            refs.append("smoke-tests:passed")
        result = SmokeTestResult(
            smoke_id=str(uuid4()),
            plan_id=plan.plan_id,
            passed=passed,
            tests=test_items,
            evidence=tuple(dict.fromkeys(refs)),
            status="passed" if passed else "failed",
        )
        message = self._publish(
            message_type=MessageType.RESULT if passed else MessageType.BLOCKER,
            subject=f"Smoke tests: {plan.release_candidate}",
            body=json.dumps(result.as_dict(), ensure_ascii=False),
            project_id=plan.project_id,
            task_id=plan.task_id,
            run_id=run_id,
            recipient_role="release_verifier",
            references=result.evidence,
            topic="deployment_smoke_test",
        )
        return SmokeTestResult(**{**asdict(result), "message_id": str(message["message_id"])})

    smoke_test = run_smoke_tests

    def rollback(
        self,
        plan: DeploymentPlan,
        *,
        reason: str,
        executor: Callable[[tuple[str, ...]], object] | None = None,
        run_id: str | None = None,
    ) -> RollbackResult:
        clean_reason = _clean(reason, max_chars=2000) or "Deployment verification failed"
        steps = plan.rollback_steps
        success = False
        try:
            if executor is None:
                raise ValueError("rollback executor is required for an actual rollback")
            success = _bool_result(executor(steps))
        except Exception as exc:
            clean_reason = f"{clean_reason}; rollback-error: {_clean(exc, max_chars=512)}"
            success = False
        result = RollbackResult(
            rollback_id=str(uuid4()),
            plan_id=plan.plan_id,
            success=success,
            reason=clean_reason,
            steps=steps,
            status="rolled_back" if success else "rollback_failed",
        )
        message = self._publish(
            message_type=MessageType.RESULT if success else MessageType.BLOCKER,
            subject=f"Rollback: {plan.release_candidate}",
            body=json.dumps(result.as_dict(), ensure_ascii=False),
            project_id=plan.project_id,
            task_id=plan.task_id,
            run_id=run_id,
            recipient_role="engineering_manager",
            references=(f"plan:{plan.plan_id}", f"rollback:{result.rollback_id}"),
            topic="deployment_rollback",
        )
        return RollbackResult(**{**asdict(result), "message_id": str(message["message_id"])})

    rollback_deployment = rollback

    def deploy(
        self,
        plan: DeploymentPlan,
        *,
        approval: DeploymentApproval | None = None,
        executor: Callable[[DeploymentPlan], object] | None = None,
        health_checker: Callable[[], object] | None = None,
        smoke_runner: Callable[[], object] | None = None,
        rollback_executor: Callable[[tuple[str, ...]], object] | None = None,
        dry_run: bool = False,
        run_id: str | None = None,
    ) -> DeploymentResult:
        if plan.requires_approval and (approval is None or approval.plan_id != plan.plan_id):
            self._publish(
                message_type=MessageType.BLOCKER,
                subject=f"Deployment approval required: {plan.release_candidate}",
                body=json.dumps({"plan_id": plan.plan_id, "environment": plan.environment}, ensure_ascii=False),
                project_id=plan.project_id,
                task_id=plan.task_id,
                run_id=run_id,
                recipient_role="engineering_manager",
                references=(f"plan:{plan.plan_id}",),
                topic="deployment_approval_gate",
            )
            raise PermissionError("deployment plan requires an authorized approval before execution")
        if not dry_run and executor is None:
            raise ValueError("an explicit deployment executor is required; DevOps will not execute arbitrary commands")
        deployment_id = str(uuid4())
        evidence: list[str] = [f"plan:{plan.plan_id}"]
        start = self._publish(
            message_type=MessageType.STATUS,
            subject=f"Deployment started: {plan.release_candidate}",
            body=json.dumps({"deployment_id": deployment_id, "plan": plan.as_dict(), "dry_run": dry_run}, ensure_ascii=False),
            project_id=plan.project_id,
            task_id=plan.task_id,
            run_id=run_id,
            recipient_role="release_verifier",
            references=(f"plan:{plan.plan_id}",),
            topic="deployment_started",
        )
        error: str | None = None
        deployed = False
        try:
            deployed = True if dry_run else _bool_result(executor(plan))  # type: ignore[misc]
            if not deployed:
                raise RuntimeError("deployment executor reported failure")
            evidence.append("deployment:completed")
        except Exception as exc:
            error = _clean(exc, max_chars=2000)
            deployed = False
        health = self.verify_health(plan, checker=health_checker, run_id=run_id) if deployed else None
        smoke = self.run_smoke_tests(plan, runner=smoke_runner, run_id=run_id) if deployed else None
        health_passed = bool(health and health.passed)
        smoke_passed = bool(smoke and smoke.passed)
        if deployed and health_passed and smoke_passed:
            evidence.extend(("health-check:passed", "smoke-tests:passed"))
            handoff = AgentHandoff(
                sender_role=self.ROLE,
                recipient_role="release_verifier",
                summary=f"Deployment ready for release verification: {plan.release_candidate}",
                completed=("Deployment executor completed.", "Health check passed.", "Smoke tests passed."),
                artifacts=("DeploymentPlan", "DeploymentResult", "HealthCheckResult", "SmokeTestResult"),
                changed_files=plan.changed_files,
                decisions=(f"environment:{plan.environment}",),
                risks=(),
                remaining_work=("Perform release verification and record the final release decision.",),
                verification=tuple(evidence),
                run_id=run_id,
                project_id=plan.project_id,
                task_id=plan.task_id,
            )
            handoff_row = self.handoffs.submit(handoff)
            final = DeploymentResult(deployment_id, plan.plan_id, plan.environment, True, True, True, False, "succeeded", tuple(evidence), message_id=str(start["message_id"]), handoff_id=str(handoff_row["handoff_id"]))
            self._publish(
                message_type=MessageType.RESULT,
                subject=f"Deployment succeeded: {plan.release_candidate}",
                body=json.dumps(final.as_dict(), ensure_ascii=False),
                project_id=plan.project_id,
                task_id=plan.task_id,
                run_id=run_id,
                recipient_role="release_verifier",
                references=(f"deployment:{deployment_id}", f"handoff:{handoff_row['handoff_id']}"),
                topic="deployment_result",
            )
            return final
        if deployed and not error:
            error = "deployment verification failed"
        rollback_result = self.rollback(plan, reason=error or "deployment failed", executor=rollback_executor, run_id=run_id)
        evidence.append(f"rollback:{rollback_result.status}")
        final = DeploymentResult(
            deployment_id,
            plan.plan_id,
            plan.environment,
            False,
            health_passed,
            smoke_passed,
            rollback_result.success,
            "rolled_back" if rollback_result.success else "failed",
            tuple(evidence),
            error=error,
            message_id=str(start["message_id"]),
            rollback_id=rollback_result.rollback_id,
        )
        self._publish(
            message_type=MessageType.BLOCKER,
            subject=f"Deployment failed: {plan.release_candidate}",
            body=json.dumps(final.as_dict(), ensure_ascii=False),
            project_id=plan.project_id,
            task_id=plan.task_id,
            run_id=run_id,
            recipient_role="engineering_manager",
            references=(f"deployment:{deployment_id}", f"rollback:{rollback_result.rollback_id}"),
            topic="deployment_result",
        )
        return final

    execute = deploy
    deploy_release = deploy


DeploymentEngineerAgent = DevOpsAgent
DevopsAgent = DevOpsAgent
DeploymentAgent = DevOpsAgent


__all__ = [
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
