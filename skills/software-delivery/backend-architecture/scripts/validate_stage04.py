#!/usr/bin/env python3
"""Validate Stage 04 backend-architecture completion artifacts.

The validator is intentionally stack-agnostic. It validates orchestration artifacts,
quality evidence, stage boundaries, and handoff completeness without assuming a
specific language, framework, ORM, or database.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


STAGE_ID = "04-backend-architecture"
NEXT_STAGE = "05-database-architecture"


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str | None = None


class Validator:
    def __init__(self, root: Path, strict_warnings: bool = False) -> None:
        self.root = root.resolve()
        self.strict_warnings = strict_warnings
        self.findings: list[Finding] = []

    def error(self, code: str, message: str, path: Path | None = None) -> None:
        self.findings.append(Finding("ERROR", code, message, self._rel(path)))

    def warn(self, code: str, message: str, path: Path | None = None) -> None:
        self.findings.append(Finding("WARNING", code, message, self._rel(path)))

    def info(self, code: str, message: str, path: Path | None = None) -> None:
        self.findings.append(Finding("INFO", code, message, self._rel(path)))

    def _rel(self, path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return str(path.resolve().relative_to(self.root))
        except ValueError:
            return str(path)

    def read_json(self, path: Path, code: str) -> Any | None:
        if not path.is_file():
            self.error(f"{code}_MISSING", "Required JSON artifact is missing.", path)
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self.error(f"{code}_INVALID", f"Invalid JSON: {exc}", path)
            return None

    def validate(self) -> None:
        if not self.root.is_dir():
            self.error("PROJECT_ROOT_MISSING", "Project root does not exist.", self.root)
            return

        docs = self.root / "docs"
        architecture_path = docs / "04-backend-architecture.md"
        evidence_path = docs / "04-backend-architecture.evidence.json"
        handoff_path = docs / "04-stage05-handoff.json"
        state_path = self.root / "project-state.json"

        self.validate_architecture_doc(architecture_path)
        evidence = self.read_json(evidence_path, "EVIDENCE")
        handoff = self.read_json(handoff_path, "HANDOFF")
        state = self.read_json(state_path, "PROJECT_STATE")

        if isinstance(evidence, dict):
            self.validate_evidence(evidence, evidence_path)
        if isinstance(handoff, dict):
            self.validate_handoff(handoff, handoff_path)
        if state is not None:
            self.validate_project_state(state, state_path)

        if isinstance(evidence, dict):
            self.validate_backend_root(evidence, evidence_path)
            self.validate_changed_files(evidence, evidence_path)

    def validate_architecture_doc(self, path: Path) -> None:
        if not path.is_file():
            self.error("ARCH_DOC_MISSING", "Required architecture document is missing.", path)
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.error("ARCH_DOC_READ_FAILED", str(exc), path)
            return

        if len(text.strip()) < 800:
            self.error("ARCH_DOC_TOO_THIN", "Architecture document is too short to evidence Stage 04 work.", path)

        topic_groups = {
            "RECONNAISSANCE": ["reconnaissance", "repository", "backend root"],
            "TRACEABILITY": ["traceability", "requirement"],
            "ARCHITECTURE_DECISION": ["architecture", "decision", "rationale"],
            "MODULES": ["module", "ownership"],
            "DOMAIN": ["domain", "invariant"],
            "USE_CASES": ["use case", "application"],
            "AUTHORIZATION": ["authorization", "tenant"],
            "PORTS": ["repository port", "external service port", "ports"],
            "TRANSACTIONS": ["transaction", "atomic"],
            "IDEMPOTENCY_CONCURRENCY": ["idempot", "concurr", "race"],
            "VALIDATION_ERRORS": ["validation", "error"],
            "CONFIG_LOGGING": ["configuration", "logging", "observability"],
            "TESTING": ["testing", "verification", "test"],
            "HANDOFF": ["stage 05", "handoff", "database"],
            "RISKS": ["risk", "assumption", "defer"],
        }
        lowered = text.lower()
        for code, tokens in topic_groups.items():
            if not any(token in lowered for token in tokens):
                self.error(
                    f"ARCH_DOC_{code}_MISSING",
                    f"Architecture document does not appear to cover required topic: {code.lower()}.",
                    path,
                )

    def validate_evidence(self, data: dict[str, Any], path: Path) -> None:
        if data.get("stage") != STAGE_ID:
            self.error("EVIDENCE_STAGE_INVALID", f"Expected stage '{STAGE_ID}'.", path)
        if data.get("status") != "PASS":
            self.error("EVIDENCE_STATUS_NOT_PASS", "Evidence status must be PASS before Stage 04 completion.", path)

        backend_root = data.get("backend_root")
        if not isinstance(backend_root, str) or not backend_root.strip():
            self.error("EVIDENCE_BACKEND_ROOT_MISSING", "Evidence must record the detected backend_root.", path)

        commands = data.get("commands")
        if not isinstance(commands, list) or not commands:
            self.error("EVIDENCE_COMMANDS_MISSING", "Evidence must contain executed or explicitly NOT_RUN verification commands.", path)
        else:
            pass_count = 0
            for idx, item in enumerate(commands):
                if not isinstance(item, dict):
                    self.error("EVIDENCE_COMMAND_INVALID", f"commands[{idx}] must be an object.", path)
                    continue
                status = item.get("status")
                if status not in {"PASS", "FAIL", "NOT_RUN"}:
                    self.error("EVIDENCE_COMMAND_STATUS_INVALID", f"commands[{idx}] has invalid status '{status}'.", path)
                if status == "FAIL":
                    self.error("EVIDENCE_COMMAND_FAILED", f"commands[{idx}] is still FAIL: {item.get('command', '<unknown>')}", path)
                if status == "PASS":
                    pass_count += 1
                    if item.get("exit_code") not in (0, None):
                        self.error("EVIDENCE_EXIT_CODE_MISMATCH", f"commands[{idx}] says PASS with non-zero exit code.", path)
                if status == "NOT_RUN" and not item.get("reason"):
                    self.warn("EVIDENCE_NOT_RUN_REASON_MISSING", f"commands[{idx}] is NOT_RUN without a reason.", path)
            if pass_count == 0:
                self.error("EVIDENCE_NO_EXECUTED_PASS", "At least one real verification command must have PASS evidence.", path)

        checks = data.get("checks")
        mandatory_checks = {
            "stage03_precondition",
            "requirement_traceability",
            "domain_application_boundary",
            "transport_boundary",
            "authorization_model",
            "persistence_abstraction",
            "stage05_boundary_respected",
        }
        if not isinstance(checks, dict):
            self.error("EVIDENCE_CHECKS_MISSING", "Evidence must contain a checks object.", path)
        else:
            for check in sorted(mandatory_checks):
                value = checks.get(check)
                if value != "PASS":
                    self.error("EVIDENCE_CHECK_NOT_PASS", f"Mandatory check '{check}' must be PASS, found {value!r}.", path)

        for key in ("changed_files", "warnings", "residual_risks"):
            if key not in data:
                self.warn("EVIDENCE_FIELD_MISSING", f"Recommended evidence field '{key}' is missing.", path)

    def validate_handoff(self, data: dict[str, Any], path: Path) -> None:
        if data.get("stage") != STAGE_ID:
            self.error("HANDOFF_STAGE_INVALID", f"Expected stage '{STAGE_ID}'.", path)
        if data.get("next_stage") != NEXT_STAGE:
            self.error("HANDOFF_NEXT_STAGE_INVALID", f"Expected next_stage '{NEXT_STAGE}'.", path)

        modules = data.get("modules")
        if not isinstance(modules, list) or not modules:
            self.error("HANDOFF_MODULES_MISSING", "Stage 05 handoff must contain at least one backend module.", path)
            return

        seen_names: set[str] = set()
        for idx, module in enumerate(modules):
            if not isinstance(module, dict):
                self.error("HANDOFF_MODULE_INVALID", f"modules[{idx}] must be an object.", path)
                continue
            name = module.get("name")
            if not isinstance(name, str) or not name.strip():
                self.error("HANDOFF_MODULE_NAME_MISSING", f"modules[{idx}] has no valid name.", path)
                continue
            if name in seen_names:
                self.error("HANDOFF_MODULE_DUPLICATE", f"Duplicate module name '{name}'.", path)
            seen_names.add(name)

            recommended = (
                "repository_ports",
                "transaction_boundaries",
                "uniqueness_requirements",
                "query_patterns",
                "concurrency_requirements",
                "idempotency_requirements",
                "retention_and_audit",
                "sensitive_data",
            )
            for field in recommended:
                if field not in module:
                    self.warn("HANDOFF_MODULE_FIELD_MISSING", f"Module '{name}' is missing '{field}'.", path)

        for field in (
            "cross_module_atomicity",
            "event_outbox_candidates",
            "existing_persistence_to_reconcile",
            "assumptions",
            "risks",
            "blocked_questions",
        ):
            if field not in data:
                self.warn("HANDOFF_FIELD_MISSING", f"Handoff is missing recommended top-level field '{field}'.", path)

        raw = json.dumps(data, ensure_ascii=False).lower()
        physical_schema_terms = [
            r"\bcreate\s+table\b",
            r"\bforeign\s+key\b",
            r"\bprimary\s+key\b",
            r"\bcreate\s+index\b",
        ]
        for pattern in physical_schema_terms:
            if re.search(pattern, raw):
                self.warn(
                    "HANDOFF_PHYSICAL_SCHEMA_DETAIL",
                    "Handoff appears to contain physical relational-schema detail that normally belongs to Stage 05.",
                    path,
                )
                break

    def validate_project_state(self, data: Any, path: Path) -> None:
        stage03 = self.find_stage_status(data, "03")
        if "PASS" not in stage03:
            self.error("STATE_STAGE03_NOT_PASS", "Could not verify Stage 03 PASS in project-state.json.", path)

        stage04 = self.find_stage_status(data, "04")
        if "PASS" not in stage04:
            self.error("STATE_STAGE04_NOT_PASS", "Could not verify Stage 04 PASS in project-state.json.", path)

        serialized = json.dumps(data, ensure_ascii=False).lower()
        if NEXT_STAGE not in serialized:
            self.warn("STATE_NEXT_STAGE_MISSING", f"project-state.json does not mention '{NEXT_STAGE}'.", path)

    def find_stage_status(self, node: Any, stage_prefix: str) -> set[str]:
        statuses: set[str] = set()

        def walk(value: Any, inherited_key: str | None = None) -> None:
            if isinstance(value, dict):
                identity_parts = []
                if inherited_key:
                    identity_parts.append(inherited_key)
                for key in ("id", "stage", "name", "stage_id"):
                    item = value.get(key)
                    if isinstance(item, (str, int)):
                        identity_parts.append(str(item))
                identity = " ".join(identity_parts).lower()
                if self.stage_identity_matches(identity, stage_prefix):
                    status = value.get("status")
                    if isinstance(status, str):
                        statuses.add(status.upper())
                    elif status is True:
                        statuses.add("PASS")
                for key, item in value.items():
                    if self.stage_identity_matches(str(key).lower(), stage_prefix):
                        if isinstance(item, str):
                            statuses.add(item.upper())
                        elif item is True:
                            statuses.add("PASS")
                        elif isinstance(item, dict):
                            status = item.get("status")
                            if isinstance(status, str):
                                statuses.add(status.upper())
                    walk(item, str(key))
            elif isinstance(value, list):
                for item in value:
                    walk(item, inherited_key)

        walk(node)
        return statuses

    @staticmethod
    def stage_identity_matches(identity: str, stage_prefix: str) -> bool:
        patterns = [
            rf"(^|[^0-9]){re.escape(stage_prefix)}([^0-9]|$)",
            rf"stage[_ -]?{re.escape(stage_prefix)}([^0-9]|$)",
        ]
        return any(re.search(pattern, identity, flags=re.IGNORECASE) for pattern in patterns)

    def validate_backend_root(self, evidence: dict[str, Any], path: Path) -> None:
        value = evidence.get("backend_root")
        if not isinstance(value, str) or not value.strip():
            return
        candidate = (self.root / value).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            self.error("BACKEND_ROOT_OUTSIDE_PROJECT", "backend_root resolves outside project root.", path)
            return
        if not candidate.exists():
            self.error("BACKEND_ROOT_NOT_FOUND", f"Recorded backend_root does not exist: {value}", path)

    def validate_changed_files(self, evidence: dict[str, Any], path: Path) -> None:
        files = evidence.get("changed_files")
        if not isinstance(files, list):
            return

        secret_patterns = [
            re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ]
        suspicious_exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".rb", ".php", ".cs", ".env", ".yaml", ".yml", ".json"}

        for raw in files:
            if not isinstance(raw, str) or not raw.strip():
                continue
            candidate = (self.root / raw).resolve()
            try:
                candidate.relative_to(self.root)
            except ValueError:
                self.warn("CHANGED_FILE_OUTSIDE_PROJECT", f"Changed file is outside project root: {raw}", path)
                continue
            if not candidate.is_file() or candidate.suffix.lower() not in suspicious_exts:
                continue
            try:
                if candidate.stat().st_size > 1_000_000:
                    continue
                text = candidate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern in secret_patterns:
                if pattern.search(text):
                    self.error(
                        "POSSIBLE_HARDCODED_SECRET",
                        f"Possible hard-coded secret detected in changed file '{raw}'. Review before PASS.",
                        candidate,
                    )
                    break

    @property
    def errors(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "ERROR"]

    @property
    def warnings(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "WARNING"]

    def exit_code(self) -> int:
        if self.errors:
            return 1
        if self.strict_warnings and self.warnings:
            return 1
        return 0


def render_text(findings: Iterable[Finding], root: Path) -> str:
    items = list(findings)
    lines = [f"Stage 04 validation root: {root}"]
    if not items:
        lines.append("PASS: no findings")
        return "\n".join(lines)

    order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    for item in sorted(items, key=lambda x: (order.get(x.level, 9), x.code, x.path or "")):
        location = f" [{item.path}]" if item.path else ""
        lines.append(f"{item.level} {item.code}{location}: {item.message}")

    error_count = sum(1 for item in items if item.level == "ERROR")
    warning_count = sum(1 for item in items if item.level == "WARNING")
    lines.append(f"Summary: {error_count} error(s), {warning_count} warning(s)")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Stage 04 backend architecture artifacts")
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to validate")
    parser.add_argument("--strict-warnings", action="store_true", help="Treat warnings as validation failure")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.project_root)
    validator = Validator(root, strict_warnings=args.strict_warnings)
    validator.validate()

    if args.json_output:
        payload = {
            "status": "PASS" if validator.exit_code() == 0 else "FAIL",
            "project_root": str(root.resolve()),
            "errors": len(validator.errors),
            "warnings": len(validator.warnings),
            "findings": [asdict(item) for item in validator.findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(validator.findings, root.resolve()))
        if validator.exit_code() == 0:
            print("STAGE_04_VALIDATION: PASS")
        else:
            print("STAGE_04_VALIDATION: FAIL")

    return validator.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
