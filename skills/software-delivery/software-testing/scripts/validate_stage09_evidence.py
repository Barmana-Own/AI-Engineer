#!/usr/bin/env python3
"""Validate Stage 09 evidence consistency before emitting PASS.

This validator is intentionally conservative. It validates the machine-readable
summary, required markdown artifacts, and the Stage 09 record in project-state.
It does not determine whether individual tests are semantically correct.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_PLAN_HEADINGS = [
    "# Stage 09 Test Plan",
    "## Context and Inputs",
    "## Requirement and Risk Traceability",
    "## Suite Plan",
    "## Exit Criteria",
]

REQUIRED_RESULTS_HEADINGS = [
    "# Stage 09 Test Results",
    "## Executive Verdict",
    "## Commands Executed",
    "## Suite Results",
    "## Requirement and Risk Coverage",
    "## Unresolved Failures and Blockers",
    "## Quality Gate Evaluation",
    "## Final Verdict",
]

ALLOWED_TOP = {"PASS", "FAIL", "BLOCKED"}
ALLOWED_SUITE = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "NOT_APPLICABLE"}
ALLOWED_ENVIRONMENTS = {
    "LOCAL_EPHEMERAL", "LOCAL_PERSISTENT_TEST", "CI_EPHEMERAL",
    "REMOTE_TEST_SANDBOX", "SHARED_STAGING", "PRODUCTION_OR_UNSAFE", "UNKNOWN"
}


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_json(path: Path, v: Validation) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        v.error(f"Missing required file: {path}")
    except json.JSONDecodeError as exc:
        v.error(f"Invalid JSON in {path}: {exc}")
    except Exception as exc:
        v.error(f"Could not read {path}: {exc}")
    return None


def require_headings(path: Path, headings: list[str], v: Validation) -> None:
    if not path.is_file():
        v.error(f"Missing required file: {path}")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text.strip()) < 100:
        v.error(f"Artifact is suspiciously short: {path}")
    for heading in headings:
        if heading not in text:
            v.error(f"Missing heading in {path.name}: {heading}")


def nonnegative_int(value: Any, label: str, v: Validation) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        v.error(f"{label} must be a non-negative integer")
        return None
    return value


def _looks_like_stage09(value: dict[str, Any]) -> bool:
    sid = str(value.get("id", value.get("stage", value.get("stage_id", "")))).lower().strip()
    name = str(value.get("name", value.get("stage_name", ""))).lower().strip()
    sid_norm = sid.replace("stage", "").replace("_", "").replace("-", "").replace(" ", "")
    return (
        sid_norm in {"09", "9", "09softwaretesting", "9softwaretesting", "softwaretesting"}
        or "software testing" in name
        or "software-testing" in name
    )


def stage09_state(project_state: Any) -> str | None:
    if not isinstance(project_state, dict):
        return None
    completed = project_state.get("completed_stages")
    if isinstance(completed, dict):
        # Prefer an explicit Stage 09 key.
        for key, value in completed.items():
            key_norm = str(key).lower().replace("stage", "").replace("_", "").replace("-", "").replace(" ", "").strip()
            if key_norm in {"09", "9", "09softwaretesting", "9softwaretesting", "softwaretesting"}:
                if isinstance(value, dict):
                    status = value.get("status")
                    return status.upper() if isinstance(status, str) else None
                if isinstance(value, str):
                    return value.upper()
        # Otherwise accept only records that explicitly identify themselves as Stage 09.
        for value in completed.values():
            if isinstance(value, dict) and _looks_like_stage09(value):
                status = value.get("status")
                if isinstance(status, str):
                    return status.upper()
    elif isinstance(completed, list):
        for value in completed:
            if isinstance(value, dict) and _looks_like_stage09(value):
                status = value.get("status")
                if isinstance(status, str):
                    return status.upper()
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    docs = root / "docs"
    plan = docs / "09-test-plan.md"
    results = docs / "09-test-results.md"
    summary_path = docs / "09-test-summary.json"
    state_path = root / "project-state.json"

    v = Validation()
    require_headings(plan, REQUIRED_PLAN_HEADINGS, v)
    require_headings(results, REQUIRED_RESULTS_HEADINGS, v)
    summary = load_json(summary_path, v)
    project_state = load_json(state_path, v)

    if isinstance(summary, dict):
        if str(summary.get("stage")) != "09":
            v.error("summary.stage must be '09'")

        status = str(summary.get("status", "")).upper()
        if status not in ALLOWED_TOP:
            v.error(f"summary.status must be one of {sorted(ALLOWED_TOP)}")

        if not isinstance(summary.get("stage08_verified"), bool):
            v.error("summary.stage08_verified must be boolean")

        environment = str(summary.get("environment_classification", "")).upper()
        if environment not in ALLOWED_ENVIRONMENTS:
            v.error(f"summary.environment_classification must be one of {sorted(ALLOWED_ENVIRONMENTS)}")

        commands = summary.get("commands")
        if not isinstance(commands, list) or not commands:
            v.error("summary.commands must be a non-empty array of actually executed material commands")
        else:
            for i, cmd in enumerate(commands):
                if not isinstance(cmd, dict):
                    v.error(f"commands[{i}] must be an object")
                    continue
                if not str(cmd.get("command", "")).strip():
                    v.error(f"commands[{i}].command is required")
                cstatus = str(cmd.get("status", "")).upper()
                if cstatus not in {"PASS", "FAIL", "BLOCKED"}:
                    v.error(f"commands[{i}].status must be PASS/FAIL/BLOCKED")
                if "exit_code" not in cmd:
                    v.warn(f"commands[{i}] has no exit_code; use null only when a process could not start")
                else:
                    exit_code = cmd.get("exit_code")
                    if exit_code is not None and (isinstance(exit_code, bool) or not isinstance(exit_code, int)):
                        v.error(f"commands[{i}].exit_code must be integer or null")
                    if cstatus == "PASS" and exit_code not in (0, None):
                        v.error(f"commands[{i}] is PASS but has non-zero exit_code={exit_code}")

        suites = summary.get("suites")
        failed_or_blocked_suites = 0
        critical_not_run_from_suites = []
        if not isinstance(suites, list) or not suites:
            v.error("summary.suites must be a non-empty array")
        else:
            for i, suite in enumerate(suites):
                if not isinstance(suite, dict):
                    v.error(f"suites[{i}] must be an object")
                    continue
                sstatus = str(suite.get("status", "")).upper()
                if sstatus not in ALLOWED_SUITE:
                    v.error(f"suites[{i}].status must be one of {sorted(ALLOWED_SUITE)}")
                if sstatus in {"FAIL", "BLOCKED"}:
                    failed_or_blocked_suites += 1
                criticality = str(suite.get("criticality", "")).upper()
                if sstatus == "NOT_RUN" and criticality in {"P0", "P1"}:
                    critical_not_run_from_suites.append(str(suite.get("id", f"index-{i}")))
                    if not str(suite.get("not_run_reason", "")).strip():
                        v.error(f"Critical NOT_RUN suite {suite.get('id', i)} lacks not_run_reason")
                parsed_counts = {}
                for count_name in ("passed", "failed", "skipped"):
                    if count_name in suite and suite[count_name] is not None:
                        parsed_counts[count_name] = nonnegative_int(suite[count_name], f"suites[{i}].{count_name}", v)
                if sstatus == "PASS" and parsed_counts.get("failed") not in (None, 0):
                    v.error(f"suites[{i}] is PASS but failed count is non-zero")
                if sstatus == "NOT_RUN" and not str(suite.get("not_run_reason", "")).strip():
                    v.error(f"NOT_RUN suite {suite.get('id', i)} lacks not_run_reason")

        rc = summary.get("risk_coverage")
        if not isinstance(rc, dict):
            v.error("summary.risk_coverage is required")
            p0_total = p0_covered = p1_total = p1_covered = None
        else:
            p0_total = nonnegative_int(rc.get("p0_total"), "risk_coverage.p0_total", v)
            p0_covered = nonnegative_int(rc.get("p0_covered"), "risk_coverage.p0_covered", v)
            p1_total = nonnegative_int(rc.get("p1_total"), "risk_coverage.p1_total", v)
            p1_covered = nonnegative_int(rc.get("p1_covered"), "risk_coverage.p1_covered", v)
            if p0_total is not None and p0_covered is not None and p0_covered > p0_total:
                v.error("P0 covered count exceeds P0 total")
            if p1_total is not None and p1_covered is not None and p1_covered > p1_total:
                v.error("P1 covered count exceeds P1 total")

        unresolved = summary.get("unresolved_failures")
        if not isinstance(unresolved, list):
            v.error("summary.unresolved_failures must be an array")
            unresolved = []

        flaky = summary.get("unresolved_flaky_tests")
        if not isinstance(flaky, list):
            v.error("summary.unresolved_flaky_tests must be an array")
            flaky = []

        critical_not_run = summary.get("critical_not_run")
        if not isinstance(critical_not_run, list):
            v.error("summary.critical_not_run must be an array")
            critical_not_run = []

        next_stage = summary.get("next_stage")

        authz = summary.get("authz_negative_paths")
        sec = summary.get("security_regressions")

        artifacts = summary.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            v.error("summary.artifacts must be a non-empty array")
        else:
            for i, artifact in enumerate(artifacts):
                if not isinstance(artifact, str) or not artifact.strip():
                    v.error(f"artifacts[{i}] must be a non-empty path string")
                    continue
                apath = Path(artifact)
                if not apath.is_absolute():
                    apath = root / apath
                if not apath.exists():
                    v.error(f"Artifact listed in summary does not exist: {artifact}")

        if status == "PASS":
            if environment in {"PRODUCTION_OR_UNSAFE", "UNKNOWN"}:
                v.error("PASS is not allowed for PRODUCTION_OR_UNSAFE or UNKNOWN environment classification")
            if summary.get("stage08_verified") is not True:
                v.error("PASS requires stage08_verified=true")
            if p0_total is not None and p0_covered is not None and p0_total != p0_covered:
                v.error("PASS requires complete P0 coverage")
            if p1_total is not None and p1_covered is not None and p1_total != p1_covered:
                v.error("PASS requires complete P1 coverage")
            if failed_or_blocked_suites:
                v.error("PASS cannot contain FAIL/BLOCKED suites")
            if unresolved:
                v.error("PASS requires unresolved_failures to be empty")
            if flaky:
                v.error("PASS requires unresolved_flaky_tests to be empty")
            if critical_not_run:
                v.error("PASS requires critical_not_run to be empty after equivalent-evidence decisions are resolved")
            if critical_not_run_from_suites:
                v.error(f"PASS cannot contain critical NOT_RUN suites: {critical_not_run_from_suites}")
            if next_stage != "10-qa-debugging":
                v.error("PASS requires next_stage='10-qa-debugging'")

            for label, block in (("authz_negative_paths", authz), ("security_regressions", sec)):
                if isinstance(block, dict) and block.get("required") is True:
                    failed = block.get("failed", 0)
                    not_run = block.get("not_run", 0)
                    if failed != 0 or not_run != 0:
                        v.error(f"PASS requires required {label} to have failed=0 and not_run=0")
        elif status in {"FAIL", "BLOCKED"} and next_stage == "10-qa-debugging":
            v.error(f"{status} must not set next_stage to 10-qa-debugging")

    state = stage09_state(project_state)
    if isinstance(summary, dict):
        summary_status = str(summary.get("status", "")).upper()
        if state is None:
            v.error("Could not find a Stage 09 status in project-state.json completed_stages")
        elif state != summary_status:
            v.error(f"project-state Stage 09 status ({state}) disagrees with summary ({summary_status})")

    if v.warnings:
        print("Warnings:")
        for warning in v.warnings:
            print(f"- {warning}")

    if v.errors:
        print("Stage 09 evidence validation FAILED:")
        for error in v.errors:
            print(f"- {error}")
        return 1

    print("Stage 09 evidence validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
