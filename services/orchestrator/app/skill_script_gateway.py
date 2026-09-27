"""Policy-gated execution boundary for imported engineering skill scripts.

Imported skills are playbooks, not model tools.  This module provides the
single boundary used by a worker when a playbook helper is needed:

    Agent Worker -> Tool Policy -> Local Agent

The policy layer never starts a subprocess, opens a socket, or writes a file.
It only creates a bounded execution plan.  The Local Agent adapter is the
only component allowed to perform the operation, and the compatibility
adapter is the only route for the legacy ``project-state.json`` view.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from app.clients import request_json
from app.config import settings
from app.skill_registry import SkillDescriptor, SkillRegistry, SkillScript


class SkillExecutionError(ValueError):
    """Raised when a skill request fails a safety or authorization gate."""


class SkillApprovalRequired(SkillExecutionError):
    """Raised when a high-risk script has no valid server-side approval."""


class SkillExecutionTimeout(SkillExecutionError):
    """Raised when a requested script timeout is outside the bounded policy."""


KNOWN_EXECUTION_ROUTES = frozenset(
    {
        "local-agent-policy",
        "tool-policy-and-local-agent",
        "network-policy-and-local-agent",
        "compatibility-adapter-only",
    }
)
REQUIRED_CHAIN = ("agent_worker", "tool_policy", "local_agent")
SAFE_ARTIFACT_DIRECTORIES = frozenset({"docs", "artifacts", "reports"})
MAX_TIMEOUT_SECONDS = 600
MAX_OUTPUT_BYTES = 1024 * 1024
DEFAULT_OUTPUT_BYTES = 64 * 1024
TRUSTED_EXECUTABLES = frozenset(
    {
        "python",
        "python3",
        "py",
        "pytest",
        "npm",
        "npm.cmd",
        "pnpm",
        "pnpm.cmd",
        "yarn",
        "yarn.cmd",
        "bun",
        "bun.exe",
        "git",
        "dotnet",
        "composer",
    }
)
NETWORK_CLASSES = frozenset({"NETWORK_CHECK"})
COMMAND_CLASSES = frozenset({"COMMAND_RUNNER", "TEST_RUNNER"})
WRITE_CAPABILITIES = frozenset(
    {"evidence_write", "release_artifact_write", "artifact_write"}
)
SECRET_HEADER_NAMES = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "x-access-token",
        "x-refresh-token",
    }
)
SECRET_KEY_PATTERN = re.compile(
    r"(?i)(authorization|proxy-authorization|cookie|set-cookie|x-api-key|"
    r"x-auth-token|x-access-token|x-refresh-token|api[_-]?key|access[_-]?token|"
    r"refresh[_-]?token|client[_-]?secret|password|passwd|secret|private[_-]?key)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
BEARER_PATTERN = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [^\\r\\n]+-----.*?-----END [^\\r\\n]+-----",
    flags=re.DOTALL,
)
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
SHELL_META_PATTERN = re.compile(r"[\r\n;&|<>`]|\$\(")
SENSITIVE_QUERY_KEYS = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "key",
        "secret",
        "password",
        "authorization",
    }
)
BLOCKED_NETWORK_HOSTS = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.google.com",
        "instance-data.ec2.internal",
    }
)


def _bounded_text(value: object, limit: int) -> str:
    text = str(value or "")
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text
    marker = "\n...[output truncated by skill gateway]..."
    allowed = max(0, limit - len(marker.encode("utf-8")))
    return encoded[:allowed].decode("utf-8", errors="replace") + marker


def redact_text(value: object, *, limit: int = MAX_OUTPUT_BYTES) -> str:
    """Redact credentials before evidence, logs, or trace persistence."""

    text = PRIVATE_KEY_PATTERN.sub("[REDACTED PRIVATE KEY]", str(value or ""))
    text = BEARER_PATTERN.sub("[REDACTED AUTHORIZATION]", text)
    text = SECRET_KEY_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
    return _bounded_text(text, limit)


def redact_headers(headers: Mapping[str, object] | None) -> dict[str, str]:
    """Return a safe copy of headers without credential values."""

    result: dict[str, str] = {}
    for name, value in (headers or {}).items():
        key = str(name)
        if key.casefold() in SECRET_HEADER_NAMES:
            result[key] = "[REDACTED]"
        else:
            result[key] = redact_text(value, limit=8 * 1024)
    return result


def _normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if not parsed.scheme or not parsed.netloc:
        raise SkillExecutionError("Network target must be an absolute URL.")
    if parsed.username or parsed.password:
        raise SkillExecutionError("Network target must not contain credentials.")
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise SkillExecutionError("Only HTTP(S) network targets are allowed.")
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


def validate_network_target(
    url: str,
    *,
    declared_targets: Sequence[str] = (),
    approved_targets: Sequence[str] = (),
    allow_localhost: bool = True,
) -> str:
    """Validate a declared project/deployment health target without fetching it."""

    normalized = _normalize_url(url)
    parsed = urlsplit(normalized)
    host = (parsed.hostname or "").casefold()
    if host in BLOCKED_NETWORK_HOSTS:
        raise SkillExecutionError("Cloud metadata targets are blocked.")
    if any(key.casefold() in SENSITIVE_QUERY_KEYS for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
        raise SkillExecutionError("Credential-bearing query parameters are blocked.")

    declared = {_normalize_url(item) for item in declared_targets if str(item).strip()}
    approved = {_normalize_url(item) for item in approved_targets if str(item).strip()}
    if normalized in declared or normalized in approved:
        return normalized

    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if allow_localhost and host in local_hosts:
        raise SkillExecutionError("Localhost target must be explicitly declared for this task.")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise SkillExecutionError("Private, loopback, link-local, and reserved targets must be declared.")
    raise SkillExecutionError("Network target is not declared or approved for this project.")


def _relative_parts(value: str, *, field: str) -> tuple[str, ...]:
    raw = str(value or ".").strip().replace("\\", "/")
    if CONTROL_PATTERN.search(raw):
        raise SkillExecutionError(f"{field} contains control characters.")
    supplied = PurePosixPath(raw or ".")
    if supplied.is_absolute() or (supplied.parts and ":" in supplied.parts[0]):
        raise SkillExecutionError(f"{field} must be relative to the workspace.")
    if ".." in supplied.parts:
        raise SkillExecutionError(f"{field} cannot escape the workspace.")
    return tuple(part for part in supplied.parts if part not in {"", "."})


def _is_within(path: Path, roots: Sequence[Path]) -> bool:
    resolved = path.resolve(strict=False)
    for root in roots:
        try:
            resolved.relative_to(root.resolve(strict=False))
        except ValueError:
            continue
        return True
    return False


def resolve_workspace_path(
    workspace: str | Path,
    relative_path: str,
    *,
    allowed_roots: Sequence[str | Path],
) -> Path:
    """Resolve a path and reject traversal/symlink escapes."""

    workspace_path = Path(workspace).expanduser().resolve(strict=False)
    roots = tuple(Path(item).expanduser().resolve(strict=False) for item in allowed_roots)
    if not roots or not _is_within(workspace_path, roots):
        raise SkillExecutionError("Workspace is outside the configured project roots.")
    parts = _relative_parts(relative_path, field="Workspace path")
    target = (workspace_path.joinpath(*parts)).resolve(strict=False)
    if not _is_within(target, (workspace_path,)):
        raise SkillExecutionError("Path escapes the workspace.")
    return target


def validate_artifact_path(
    workspace: str | Path,
    artifact_path: str,
    *,
    allowed_roots: Sequence[str | Path],
    compatibility: bool = False,
) -> Path:
    """Allow writes only to declared evidence/report locations."""

    parts = _relative_parts(artifact_path, field="Artifact path")
    if not parts:
        raise SkillExecutionError("Artifact path is required.")
    first = parts[0].casefold()
    if compatibility:
        if tuple(part.casefold() for part in parts) != ("project-state.json",):
            raise SkillExecutionError("Compatibility updates may target only project-state.json.")
    elif first not in SAFE_ARTIFACT_DIRECTORIES:
        raise SkillExecutionError("Skill artifacts must be under docs/, artifacts/, or reports/.")
    return resolve_workspace_path(
        workspace,
        "/".join(parts),
        allowed_roots=allowed_roots,
    )


def _validate_token(token: str, *, field: str) -> str:
    value = str(token)
    if not value or CONTROL_PATTERN.search(value) or SHELL_META_PATTERN.search(value):
        raise SkillExecutionError(f"{field} contains shell metacharacters or control characters.")
    if ".." in PurePosixPath(value.replace("\\", "/")).parts:
        raise SkillExecutionError(f"{field} contains a traversal segment.")
    return value


def _validate_declared_command(
    command: Sequence[str],
    *,
    declared_commands: Sequence[Sequence[str]],
    workspace: Path,
    allowed_roots: Sequence[Path],
) -> tuple[str, ...]:
    normalized = tuple(_validate_token(token, field="Command argument") for token in command)
    if not normalized:
        raise SkillExecutionError("A command is required for command/test scripts.")
    if tuple(normalized) not in {tuple(str(item) for item in row) for row in declared_commands}:
        raise SkillExecutionError("Command is not an exact repository-declared task command.")
    executable = Path(normalized[0]).name.casefold()
    if executable not in TRUSTED_EXECUTABLES:
        raise SkillExecutionError("Command executable is not in the trusted build/test set.")
    path_flags = {
        "--root",
        "--output",
        "--workspace",
        "--project-root",
        "--cwd",
        "--path",
    }
    for index, token in enumerate(normalized[1:], start=1):
        candidate = token
        if candidate.startswith("--") and "=" in candidate:
            flag, candidate = candidate.split("=", 1)
            if flag not in path_flags:
                continue
        elif index and normalized[index - 1] not in path_flags:
            if not ("/" in candidate or "\\" in candidate or Path(candidate).suffix):
                continue
        if candidate.startswith("-"):
            continue
        path_candidate = Path(candidate).expanduser()
        if path_candidate.is_absolute() or (len(candidate) > 1 and candidate[1] == ":"):
            if not _is_within(path_candidate, (*allowed_roots, workspace)):
                raise SkillExecutionError("Command path argument escapes the configured roots.")
        elif "/" in candidate or "\\" in candidate:
            if not _is_within((workspace / candidate).resolve(strict=False), (workspace,)) and not _is_within((Path(candidate)).resolve(strict=False), allowed_roots):
                raise SkillExecutionError("Command path argument escapes the workspace.")
    return normalized


def _required_capabilities(descriptor: SkillDescriptor, script: SkillScript) -> tuple[frozenset[str], ...]:
    classes = {item.upper() for item in script.classification}
    requirements: list[frozenset[str]] = []
    if "NETWORK_CHECK" in classes:
        requirements.append(frozenset({"health_check"}))
    if "TEST_RUNNER" in classes:
        requirements.append(frozenset({"test_runner", "frontend_test", "backend_test", "migration_test", "api_test", "contract_test", "security_test", "safe_build", "health_check"}))
    elif "COMMAND_RUNNER" in classes:
        requirements.append(frozenset({"safe_build", "safe_validation", "test_runner", "frontend_build", "backend_test", "api_test", "contract_test", "security_scan"}))
    if "PURE_VALIDATOR" in classes and not requirements:
        requirements.append(frozenset({"safe_validation", "security_scan", "database_inspection", "evidence_write"}))
    if "ARTIFACT_WRITER" in classes:
        requirements.append(WRITE_CAPABILITIES)
    return tuple(requirements)


@dataclass(frozen=True)
class SkillScriptRequest:
    skill_id: str
    script_name: str
    role: str
    task_id: str
    project_id: str
    workspace: str
    router_approved: bool
    role_tools: frozenset[str] = frozenset()
    task_tools: frozenset[str] = frozenset()
    global_tools: frozenset[str] = frozenset()
    requested_capability: str | None = None
    command: tuple[str, ...] = ()
    declared_commands: tuple[tuple[str, ...], ...] = ()
    task_plan_authorized: bool = False
    cwd: str = "."
    url: str | None = None
    declared_targets: tuple[str, ...] = ()
    approved_targets: tuple[str, ...] = ()
    artifact_path: str | None = None
    approval_id: str | None = None
    client_approved: bool = False
    timeout_seconds: int = 120
    output_limit: int = DEFAULT_OUTPUT_BYTES
    execution_chain: tuple[str, ...] = ()
    headers: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillExecutionPlan:
    skill_id: str
    script_name: str
    role: str
    task_id: str
    project_id: str
    script_path: str
    route: str
    classification: tuple[str, ...]
    capability: str
    workspace: str
    cwd: str
    command: tuple[str, ...]
    url: str | None
    artifact_path: str | None
    approval_required: bool
    approval_id: str | None
    action_hash: str
    timeout_seconds: int
    output_limit: int
    redacted_headers: Mapping[str, str]

    def action_payload(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "script_name": self.script_name,
            "role": self.role,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "script_path": self.script_path,
            "route": self.route,
            "classification": list(self.classification),
            "capability": self.capability,
            "workspace": self.workspace,
            "cwd": self.cwd,
            "command": list(self.command),
            "url": self.url,
            "artifact_path": self.artifact_path,
            "timeout_seconds": self.timeout_seconds,
            "output_limit": self.output_limit,
        }


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    reason: str = ""


class SkillToolPolicy(Protocol):
    def authorize(self, plan: SkillExecutionPlan) -> ToolPolicyDecision:
        """Authorize the already-scoped plan using the worker's tool policy."""


class ApprovalVerifier(Protocol):
    def is_valid(self, *, approval_id: str, action_hash: str, request: SkillScriptRequest) -> bool:
        """Verify an exact, unexpired, server-side approval record."""


class LocalAgentExecutionClient(Protocol):
    async def preview_skill_script(self, plan: SkillExecutionPlan) -> Mapping[str, Any]:
        """Ask Local Agent to classify the generated command/network operation."""

    async def run_skill_script(self, plan: SkillExecutionPlan, *, approved: bool) -> Mapping[str, Any]:
        """Execute only the prepared plan through Local Agent."""


class CompatibilityAdapter(Protocol):
    async def apply_skill_state_view(self, plan: SkillExecutionPlan) -> Mapping[str, Any]:
        """Apply a DB-backed compatibility view without letting a script own state."""


class DefaultSkillToolPolicy:
    """Least-privilege set intersection for a prepared skill plan."""

    def __init__(self, request: SkillScriptRequest, registry: SkillRegistry) -> None:
        self.request = request
        self.registry = registry

    def authorize(self, plan: SkillExecutionPlan) -> ToolPolicyDecision:
        descriptor, _ = self.registry.get_script(plan.skill_id, plan.script_name)
        capabilities = set(self.request.role_tools)
        capabilities &= set(self.request.task_tools)
        capabilities &= set(self.request.global_tools)
        capabilities &= set(descriptor.allowed_tools)
        if plan.capability not in capabilities:
            return ToolPolicyDecision(False, "Effective role/task/global/skill capability intersection denied the request.")
        if plan.route not in KNOWN_EXECUTION_ROUTES:
            return ToolPolicyDecision(False, "Unknown skill execution route.")
        return ToolPolicyDecision(True, "Skill execution is authorized by the bounded tool policy.")


class SkillScriptPolicy:
    """Create safe execution plans without performing any side effect."""

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        *,
        allowed_workspace_roots: Sequence[str | Path] | None = None,
    ) -> None:
        self.registry = registry or SkillRegistry()
        repository_root = self.registry.repository_root
        roots = tuple(allowed_workspace_roots or (repository_root, repository_root / "workspaces"))
        self.allowed_workspace_roots = tuple(Path(item).expanduser().resolve(strict=False) for item in roots)

    def plan(self, request: SkillScriptRequest) -> SkillExecutionPlan:
        if request.execution_chain != REQUIRED_CHAIN:
            raise SkillExecutionError("Skill scripts may only be invoked by Agent Worker -> Tool Policy -> Local Agent.")
        if not request.router_approved or not request.task_id or not request.project_id or not request.role:
            raise SkillExecutionError("A router-approved, task-scoped role context is required.")
        descriptor, script = self.registry.get_script(request.skill_id, request.script_name)
        if not self.registry.activation_allowed(
            request.skill_id,
            router_approved=request.router_approved,
            task_id=request.task_id,
            role=request.role,
            project_id=request.project_id,
        ):
            raise SkillExecutionError("Skill activation was not approved by the Skill Router.")
        route = script.execution
        if route not in KNOWN_EXECUTION_ROUTES:
            raise SkillExecutionError("Skill manifest contains an unsupported execution route.")

        workspace = Path(request.workspace).expanduser().resolve(strict=False)
        if not _is_within(workspace, self.allowed_workspace_roots):
            raise SkillExecutionError("Workspace is outside the configured project roots.")
        cwd = resolve_workspace_path(workspace, request.cwd, allowed_roots=self.allowed_workspace_roots)
        relative_cwd = cwd.relative_to(workspace).as_posix() if cwd != workspace else "."
        script_path = (descriptor.root / "scripts" / script.name).resolve(strict=False)
        if not _is_within(script_path, (descriptor.root / "scripts",)):
            raise SkillExecutionError("Skill script path escapes its declared skill directory.")

        classes = tuple(str(item).upper() for item in script.classification)
        requirements = _required_capabilities(descriptor, script)
        effective = set(request.role_tools) & set(request.task_tools) & set(request.global_tools) & set(descriptor.allowed_tools)
        if request.requested_capability:
            capability = request.requested_capability
            if capability not in effective:
                raise SkillExecutionError("Requested capability is outside the effective permission intersection.")
        else:
            candidates = [sorted(group & effective) for group in requirements]
            if any(not group for group in candidates):
                raise SkillExecutionError("The effective permission intersection cannot authorize this script.")
            capability = next((item for group in candidates for item in group), "")
            if not capability:
                raise SkillExecutionError("No bounded capability was selected for this script.")
        for group in requirements:
            if not (group & effective):
                raise SkillExecutionError("The effective permission intersection cannot authorize a required script capability.")

        if set(classes) & COMMAND_CLASSES and not request.task_plan_authorized:
            raise SkillExecutionError("Command execution requires an explicitly authorized task plan.")
        if set(classes) & COMMAND_CLASSES:
            command = _validate_declared_command(
                request.command,
                declared_commands=request.declared_commands,
                workspace=workspace,
                allowed_roots=self.allowed_workspace_roots,
            )
        else:
            command = tuple(_validate_token(item, field="Script argument") for item in request.command)

        normalized_url: str | None = None
        if set(classes) & NETWORK_CLASSES:
            if not request.url:
                raise SkillExecutionError("Network-check scripts require a declared URL.")
            normalized_url = validate_network_target(
                request.url,
                declared_targets=request.declared_targets,
                approved_targets=request.approved_targets,
            )
        elif request.url:
            raise SkillExecutionError("Only network-check scripts may receive a URL.")

        normalized_artifact: str | None = None
        if "ARTIFACT_WRITER" in classes:
            if route == "compatibility-adapter-only":
                if not request.artifact_path:
                    raise SkillExecutionError("Compatibility updates require project-state.json as their target.")
                validate_artifact_path(
                    workspace,
                    request.artifact_path,
                    allowed_roots=self.allowed_workspace_roots,
                    compatibility=True,
                )
            else:
                if not request.artifact_path:
                    raise SkillExecutionError("Artifact-writing scripts require an evidence path.")
                validate_artifact_path(
                    workspace,
                    request.artifact_path,
                    allowed_roots=self.allowed_workspace_roots,
                )
            normalized_artifact = "/".join(_relative_parts(request.artifact_path, field="Artifact path"))
        elif request.artifact_path:
            raise SkillExecutionError("This script is not declared as an artifact writer.")

        if request.timeout_seconds < 1 or request.timeout_seconds > MAX_TIMEOUT_SECONDS:
            raise SkillExecutionTimeout(f"Skill script timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds.")
        if request.output_limit < 1 or request.output_limit > MAX_OUTPUT_BYTES:
            raise SkillExecutionError(f"Skill output limit must be between 1 and {MAX_OUTPUT_BYTES} bytes.")

        risk = str(descriptor.risk_class).casefold()
        approval_required = risk in {"critical", "high"} or bool(set(classes) & NETWORK_CLASSES)
        action = {
            "skill_id": descriptor.skill_id,
            "script_name": script.name,
            "role": request.role,
            "task_id": request.task_id,
            "project_id": request.project_id,
            "script_path": script_path.relative_to(self.registry.repository_root).as_posix(),
            "route": route,
            "classification": list(classes),
            "capability": capability,
            "workspace": str(workspace),
            "cwd": relative_cwd,
            "command": list(command),
            "url": normalized_url,
            "artifact_path": normalized_artifact,
            "timeout_seconds": request.timeout_seconds,
            "output_limit": request.output_limit,
        }
        action_hash = hashlib.sha256(
            json.dumps(action, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return SkillExecutionPlan(
            skill_id=descriptor.skill_id,
            script_name=script.name,
            role=request.role,
            task_id=request.task_id,
            project_id=request.project_id,
            script_path=action["script_path"],
            route=route,
            classification=classes,
            capability=capability,
            workspace=str(workspace),
            cwd=relative_cwd,
            command=command,
            url=normalized_url,
            artifact_path=normalized_artifact,
            approval_required=approval_required,
            approval_id=request.approval_id,
            action_hash=action_hash,
            timeout_seconds=request.timeout_seconds,
            output_limit=request.output_limit,
            redacted_headers=redact_headers(request.headers),
        )


class HttpLocalAgentExecutionClient:
    """Adapter for the existing Local Agent HTTP endpoints.

    This adapter intentionally sends only the generated, policy-approved
    command to Local Agent.  It never invokes a skill script locally.
    """

    def __init__(self, *, local_agent_url: str | None = None) -> None:
        self.local_agent_url = (local_agent_url or settings.local_agent_url).rstrip("/")

    async def preview_skill_script(self, plan: SkillExecutionPlan) -> Mapping[str, Any]:
        return await request_json(
            "POST",
            f"{self.local_agent_url}/terminal/preview",
            json={
                "command": render_command(plan.command),
                "cwd": plan.cwd,
                "shell": "powershell",
            },
        )

    async def run_skill_script(self, plan: SkillExecutionPlan, *, approved: bool) -> Mapping[str, Any]:
        return await request_json(
            "POST",
            f"{self.local_agent_url}/terminal/run",
            json={
                "command": render_command(plan.command),
                "cwd": plan.cwd,
                "shell": "powershell",
                # This boolean is only a downstream compatibility signal. The
                # authoritative approval was checked by SkillScriptGateway.
                "approved": bool(approved),
                "timeout_seconds": plan.timeout_seconds,
            },
            timeout_seconds=plan.timeout_seconds + 30,
        )


def render_command(command: Sequence[str]) -> str:
    """Render a validated argv tuple without accepting shell syntax."""

    rendered: list[str] = []
    for item in command:
        value = str(item)
        if not value or CONTROL_PATTERN.search(value) or SHELL_META_PATTERN.search(value):
            raise SkillExecutionError("Cannot render an unsafe command argument.")
        if re.search(r"[\s\"']", value):
            rendered.append('"' + value.replace('"', '\\"') + '"')
        else:
            rendered.append(value)
    return " ".join(rendered)


class SkillScriptGateway:
    """Execute a manifest script through policy and the existing Local Agent."""

    def __init__(
        self,
        *,
        policy: SkillScriptPolicy | None = None,
        local_agent: LocalAgentExecutionClient | None = None,
        tool_policy: SkillToolPolicy | None = None,
        approval_verifier: ApprovalVerifier | None = None,
        compatibility_adapter: CompatibilityAdapter | None = None,
    ) -> None:
        self.policy = policy or SkillScriptPolicy()
        self.local_agent = local_agent
        self.tool_policy = tool_policy
        self.approval_verifier = approval_verifier
        self.compatibility_adapter = compatibility_adapter

    def prepare(self, request: SkillScriptRequest) -> SkillExecutionPlan:
        return self.policy.plan(request)

    async def execute(self, request: SkillScriptRequest) -> Mapping[str, Any]:
        plan = self.prepare(request)
        if self.tool_policy is None:
            raise SkillExecutionError("Skill execution requires the existing Agent Worker tool policy.")
        decision = self.tool_policy.authorize(plan)
        if not decision.allowed:
            raise SkillExecutionError(decision.reason)

        if plan.route == "compatibility-adapter-only":
            if plan.approval_required and not self._approval_valid(request, plan):
                raise SkillApprovalRequired(
                    "A valid server-side approval bound to this exact compatibility action is required."
                )
            if self.compatibility_adapter is None:
                raise SkillExecutionError("Project-state changes require the database compatibility adapter.")
            result = await self.compatibility_adapter.apply_skill_state_view(plan)
            return self._safe_result(plan, result)

        if self.local_agent is None:
            raise SkillExecutionError("Skill execution requires the existing Local Agent adapter.")

        try:
            preview = await asyncio.wait_for(
                self.local_agent.preview_skill_script(plan),
                timeout=plan.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise SkillExecutionTimeout("Local Agent skill preview timed out.") from exc
        if str(preview.get("risk") or "").casefold() == "blocked":
            raise SkillExecutionError("Local Agent blocked the skill script command.")
        downstream_requires_approval = bool(preview.get("requires_approval"))
        approval_valid = self._approval_valid(request, plan)
        if (plan.approval_required or downstream_requires_approval) and not approval_valid:
            raise SkillApprovalRequired(
                "A valid server-side approval bound to this exact skill action is required."
            )
        try:
            result = await asyncio.wait_for(
                self.local_agent.run_skill_script(plan, approved=approval_valid),
                timeout=plan.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise SkillExecutionTimeout("Local Agent skill execution timed out.") from exc
        self._validate_network_result(plan, result)
        return self._safe_result(plan, result)

    def _approval_valid(self, request: SkillScriptRequest, plan: SkillExecutionPlan) -> bool:
        if not plan.approval_required and not request.approval_id:
            return False
        if not request.approval_id or self.approval_verifier is None:
            return False
        return bool(
            self.approval_verifier.is_valid(
                approval_id=request.approval_id,
                action_hash=plan.action_hash,
                request=request,
            )
        )

    @staticmethod
    def _validate_network_result(plan: SkillExecutionPlan, result: Mapping[str, Any]) -> None:
        if "NETWORK_CHECK" not in plan.classification or not plan.url:
            return

        def visit(value: object) -> None:
            if isinstance(value, Mapping):
                for key, item in value.items():
                    if str(key) in {"url", "response_url"} and item:
                        try:
                            observed = _normalize_url(str(item))
                        except SkillExecutionError as exc:
                            raise SkillExecutionError("Network evidence contains an invalid URL.") from exc
                        if observed != plan.url:
                            raise SkillExecutionError("Network check followed an undeclared or unexpected redirect target.")
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(result)

    @staticmethod
    def _safe_result(plan: SkillExecutionPlan, result: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = {
            "skill_id": plan.skill_id,
            "script_name": plan.script_name,
            "task_id": plan.task_id,
            "project_id": plan.project_id,
            "route": plan.route,
            "classification": list(plan.classification),
            "action_hash": plan.action_hash,
            "status": str(result.get("status") or ("success" if result.get("ok") else "failed")),
            "ok": bool(result.get("ok", result.get("exit_code") == 0)),
            "stdout": redact_text(result.get("stdout") or "", limit=plan.output_limit),
            "stderr": redact_text(result.get("stderr") or "", limit=plan.output_limit),
            "result": redact_text(json.dumps(dict(result), ensure_ascii=False), limit=plan.output_limit),
        }
        return payload


__all__ = [
    "ApprovalVerifier",
    "CompatibilityAdapter",
    "DefaultSkillToolPolicy",
    "HttpLocalAgentExecutionClient",
    "LocalAgentExecutionClient",
    "SkillApprovalRequired",
    "SkillExecutionError",
    "SkillExecutionPlan",
    "SkillExecutionTimeout",
    "SkillScriptGateway",
    "SkillScriptPolicy",
    "SkillScriptRequest",
    "ToolPolicyDecision",
    "redact_headers",
    "redact_text",
    "render_command",
    "resolve_workspace_path",
    "validate_artifact_path",
    "validate_network_target",
]
