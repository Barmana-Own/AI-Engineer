import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app import db
from app.agent_service import (
    _autonomous_target_paths,
    _apply_subagent_requirements,
    _deterministic_autonomous_recovery_step,
    _normalize_autonomous_validation_step,
    _read_file,
    _unwrap_model_action,
)
from app.routers.agent import autonomy_run_status
from app.subagents import (
    HANDOFF_SCHEMA_VERSION,
    SECTION_ROLE_KEYS,
    build_execution_phases,
    build_handoff,
    build_role_instruction,
    configured_subagent_roles,
    get_subagent_role,
    list_section_subagents,
)


class SubagentRegistryTests(unittest.TestCase):
    @patch("app.routers.agent.list_subagent_handoffs")
    @patch("app.routers.agent.get_task")
    @patch("app.routers.agent.get_autonomy_run")
    def test_run_status_includes_bounded_handoff_aggregates(
        self,
        get_run,
        get_task,
        list_handoffs,
    ):
        get_run.return_value = {
            "id": "run-1",
            "project_id": "project-1",
            "status": "running",
            "requested_cycles": 2,
            "completed_cycles": 1,
            "task_ids": ["task-1", "task-2"],
            "error": None,
            "updated_at": "2026-08-15T00:00:00+00:00",
        }
        get_task.side_effect = [
            {"status": "completed"},
            {"status": "running"},
        ]
        list_handoffs.return_value = [
            {"role": "architect", "status": "completed"},
            {"role": "architect", "status": "completed"},
            {"role": "verifier", "status": "blocked"},
        ]

        result = autonomy_run_status("run-1")

        self.assertEqual(result["task_status_counts"], {"completed": 1, "running": 1})
        self.assertEqual(result["handoff_count"], 3)
        self.assertEqual(
            result["handoff_status_counts"],
            {"completed": 2, "blocked": 1},
        )
        self.assertEqual(
            result["handoff_role_counts"],
            {"architect": 2, "verifier": 1},
        )
        self.assertEqual(result["manager"]["role"], "monitor")
        self.assertTrue(result["manager"]["single_writer"])

    def test_every_product_section_has_a_specialist(self):
        expected = {
            "product",
            "architecture",
            "orchestrator",
            "model-gateway",
            "local-agent",
            "control-center",
            "desktop",
            "tests",
            "security",
            "docs",
            "recovery",
            "integration",
        }
        self.assertTrue(expected.issubset(SECTION_ROLE_KEYS))
        self.assertEqual(
            {item["section"] for item in list_section_subagents()},
            expected,
        )

    def test_alias_and_validation_contract(self):
        self.assertEqual(get_subagent_role("scout").key, "inspector")
        self.assertEqual(get_subagent_role("manager").key, "monitor")
        self.assertEqual(get_subagent_role("unknown-model-role").key, "inspector")
        self.assertEqual(
            [role.key for role in configured_subagent_roles("unknown-model-role,planner")],
            ["planner"],
        )
        verifier = get_subagent_role("verifier")
        instruction = build_role_instruction(
            role=verifier,
            goal="Verify the current project.",
            cycle=1,
            total_cycles=1,
            memory_text="{}",
        )
        self.assertIn("Run the real project validation command", instruction)
        self.assertIn("strictly observational", instruction)

    def test_target_parser_ignores_learned_memory_paths(self):
        instruction = """TARGET FILE: services/orchestrator/app/autonomy.py
LEARNED MEMORY:
- Previous target: apps/control-center/src/api.ts
"""
        self.assertEqual(
            _autonomous_target_paths(instruction),
            ["services/orchestrator/app/autonomy.py"],
        )
    def test_speed_phases_bound_readers_and_isolate_writers(self):
        roles = [
            get_subagent_role("inspector"),
            get_subagent_role("planner"),
            get_subagent_role("implementer"),
            get_subagent_role("verifier"),
            get_subagent_role("reviewer"),
        ]
        phases = build_execution_phases(roles, max_parallel_readers=2)
        self.assertEqual(
            [[role.key for role in phase] for phase in phases],
            [["inspector", "planner"], ["implementer"], ["verifier", "reviewer"]],
        )
        self.assertTrue(all(len(phase) <= 2 for phase in phases))
        self.assertTrue(
            all(
                len(phase) == 1 or all(role.read_only for role in phase)
                for phase in phases
            )
        )

    def test_read_only_verifier_keeps_validation_requirement(self):
        verifier = get_subagent_role("verifier")
        requirements = _apply_subagent_requirements(
            {"read": True, "mutation": True, "diff": True, "validation": True},
            verifier,
        )
        self.assertFalse(requirements["mutation"])
        self.assertFalse(requirements["diff"])
        self.assertTrue(requirements["validation"])

    def test_nested_gateway_tool_call_is_unwrapped(self):
        action = _unwrap_model_action({
            "tool_call": {"apply_patch": {"edits": [{"path": "x.py"}]}}
        })
        self.assertEqual(action["tool"], "apply_patch")
        self.assertEqual(action["arguments"]["edits"][0]["path"], "x.py")

    def test_model_validation_command_uses_service_virtualenv(self):
        step = {
            "tool": "run_terminal",
            "arguments": {
                "command": "python -m unittest discover -s tests -q",
                "cwd": "services/orchestrator",
            },
        }
        normalized = _normalize_autonomous_validation_step(step, autonomous=True)
        self.assertEqual(
            normalized["arguments"]["command"],
            ".\\.venv\\Scripts\\python.exe -m unittest discover -s tests -q",
        )
        unchanged = _normalize_autonomous_validation_step(step, autonomous=False)
        self.assertEqual(unchanged["arguments"]["command"], normalized["arguments"]["command"])

    def test_model_summary_fallback_starts_at_explicit_target(self):
        step = _deterministic_autonomous_recovery_step(
            "task-summary",
            [],
            {"mutation": True, "validation": True},
            False,
            ["services/local-agent/app/main.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "read_file")
        self.assertEqual(step["arguments"]["path"], "services/local-agent/app/main.py")

    def test_supervisor_resume_recovery_includes_planning_runs(self):
        content = '                if run["status"] not in {"queued", "running"}:\n'
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/autonomy.py"}},
            "outcome": {
                "tool": "read_file",
                "ok": True,
                "result": {"path": "services/orchestrator/app/autonomy.py", "content": content},
            },
        }, {
            "step": {"tool": "git_checkpoint", "arguments": {}},
            "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
        }]
        step = _deterministic_autonomous_recovery_step(
            "task-supervisor-resume",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/orchestrator/app/autonomy.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn('"queued", "planning", "running"', step["arguments"]["new"])
    def test_role_contract_recovery_adds_reviewer_handoff(self):
        content = '        capabilities=("read", "diff", "evidence"),\n'
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/subagents.py"}},
            "outcome": {
                "tool": "read_file",
                "ok": True,
                "result": {"path": "services/orchestrator/app/subagents.py", "content": content},
            },
        }, {
            "step": {"tool": "git_checkpoint", "arguments": {}},
            "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
        }]
        step = _deterministic_autonomous_recovery_step(
            "task-role-contract",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/orchestrator/app/subagents.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn('"handoff"', step["arguments"]["new"])

    def test_control_center_status_recovery(self):
        content = 'export function listRunSubagents(runId: string): Promise<SubagentHandoff[]> {\n'
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "apps/control-center/src/api.ts"}},
            "outcome": {
                "tool": "read_file",
                "ok": True,
                "result": {"path": "apps/control-center/src/api.ts", "content": content},
            },
        }, {
            "step": {"tool": "git_checkpoint", "arguments": {}},
            "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
        }]
        step = _deterministic_autonomous_recovery_step(
            "task-control-center",
            results,
            {"mutation": True, "validation": True},
            False,
            ["apps/control-center/src/api.ts"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn("getAutonomyRunStatus", step["arguments"]["new"])
    def test_supervisor_resume_recovery_includes_open_runs(self):
        content = '            if any(run["status"] in {"queued", "running"} for run in open_runs):\n'
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/autonomy.py"}},
            "outcome": {
                "tool": "read_file",
                "ok": True,
                "result": {"path": "services/orchestrator/app/autonomy.py", "content": content},
            },
        }, {
            "step": {"tool": "git_checkpoint", "arguments": {}} ,
            "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
        }]
        step = _deterministic_autonomous_recovery_step(
            "task-supervisor-open-runs",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/orchestrator/app/autonomy.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn('"planning", "running", "awaiting_approval"', step["arguments"]["new"])
    def test_read_only_verifier_recovery_runs_validation(self):
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/autonomy.py"}},
            "outcome": {
                "tool": "read_file",
                "ok": True,
                "result": {"path": "services/orchestrator/app/autonomy.py", "content": "# current"},
            },
        }]
        step = _deterministic_autonomous_recovery_step(
            "task-verifier",
            results,
            {"mutation": False, "validation": True},
            True,
            ["services/orchestrator/app/autonomy.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "run_terminal")
        self.assertEqual(step["arguments"]["cwd"], "services/orchestrator")
        self.assertTrue(step["arguments"]["command"].startswith(".\\.venv\\Scripts\\python.exe -m"))
    def test_validation_recovery_uses_service_virtualenv(self):
        results = [
            {
                "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/subagents.py"}},
                "outcome": {"tool": "read_file", "ok": True, "result": {
                    "path": "services/orchestrator/app/subagents.py", "content": "current"
                }},
            },
            {
                "step": {"tool": "git_checkpoint", "arguments": {}},
                "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
            },
            {
                "step": {"tool": "replace_text", "arguments": {"path": "services/orchestrator/app/subagents.py"}},
                "outcome": {"tool": "replace_text", "ok": True, "result": {
                    "path": "services/orchestrator/app/subagents.py"
                }},
            },
        ]
        step = _deterministic_autonomous_recovery_step(
            "task-validation",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/orchestrator/app/subagents.py"],
        )
        self.assertEqual(step["tool"], "run_terminal")
        self.assertIn(".venv\\Scripts\\python.exe", step["arguments"]["command"])

    def test_read_only_summary_fallback_starts_at_explicit_target(self):
        step = _deterministic_autonomous_recovery_step(
            "task-read-only-summary",
            [],
            {"mutation": False, "validation": False},
            True,
            ["services/orchestrator/app/subagents.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "read_file")
        self.assertEqual(step["arguments"]["path"], "services/orchestrator/app/subagents.py")

    def test_local_agent_recovery_produces_a_guarded_capabilities_patch(self):
        content = '''from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root() -> dict:
    return {"service": "Local Agent"}
'''
        results = [
            {
                "step": {"tool": "read_file", "arguments": {"path": "services/local-agent/app/main.py"}},
                "outcome": {
                    "tool": "read_file",
                    "ok": True,
                    "result": {"path": "services/local-agent/app/main.py", "content": content},
                },
            },
            {
                "step": {"tool": "git_checkpoint", "arguments": {}},
                "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
            },
        ]
        step = _deterministic_autonomous_recovery_step(
            "task-123",
            results,
            {"mutation": True, "validation": True},
            False,
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn("capabilities", step["arguments"]["new"])

    def test_local_agent_recovery_refines_existing_capabilities(self):
        content = '''@app.get("/capabilities")
def capabilities() -> dict:
    return {
        "service": settings.app_name,
        "workspace_guarded": True,
        "mutation_requires_checkpoint": True,
        "read_only_tools": ["files", "terminal_preview", "health"],
    }
'''
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "services/local-agent/app/main.py"}},
            "outcome": {
                "tool": "read_file",
                "ok": True,
                "result": {"path": "services/local-agent/app/main.py", "content": content},
            },
        }, {
            "step": {"tool": "git_checkpoint", "arguments": {}},
            "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
        }]
        step = _deterministic_autonomous_recovery_step(
            "task-capabilities",
            results,
            {"mutation": True, "validation": True},
            False,
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn('"checkpoint_scope": "project"', step["arguments"]["new"])

    def test_local_agent_recovery_finishes_when_capabilities_are_hardened(self):
        content = """@app.get(\"/capabilities\")
def capabilities() -> dict:
    return {
        "workspace_guarded": True,
        "mutation_requires_checkpoint": True,
        "checkpoint_scope": "project",
    }
"""
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "services/local-agent/app/main.py"}},
            "outcome": {"tool": "read_file", "ok": True, "result": {
                "path": "services/local-agent/app/main.py", "content": content
            }},
        }, {
            "step": {"tool": "git_checkpoint", "arguments": {}},
            "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
        }]
        step = _deterministic_autonomous_recovery_step(
            "task-capabilities-hardened",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/local-agent/app/main.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "finish_task")
        self.assertTrue(step["arguments"]["no_change"])

    def test_db_recovery_compacts_duplicate_memory_evidence(self):
        content = '''    detail = {
        "instruction": instruction_text[:4_000],
        "validations": validations[-10:],
        "failures": failures[-10:],
    }
'''
        results = [
            {
                "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/db.py"}},
                "outcome": {
                    "tool": "read_file",
                    "ok": True,
                    "result": {"path": "services/orchestrator/app/db.py", "content": content},
                },
            },
            {
                "step": {"tool": "git_checkpoint", "arguments": {}},
                "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
            },
        ]
        step = _deterministic_autonomous_recovery_step(
            "task-db",
            results,
            {"mutation": True, "validation": True},
            False,
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn("dict.fromkeys(validations)", step["arguments"]["new"])

    def test_db_recovery_versions_existing_memory_evidence(self):
        content = '''    validations = list(dict.fromkeys(validations))
    failures = list(dict.fromkeys(failures))
    detail = {
        "instruction": instruction_text[:4_000],
        "validations": validations[-10:],
        "failures": failures[-10:],
    }
'''
        results = [
            {
                "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/db.py"}},
                "outcome": {"tool": "read_file", "ok": True, "result": {
                    "path": "services/orchestrator/app/db.py", "content": content
                }},
            },
            {
                "step": {"tool": "git_checkpoint", "arguments": {}},
                "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
            },
        ]
        step = _deterministic_autonomous_recovery_step(
            "task-memory-schema",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/orchestrator/app/db.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "replace_text")
        self.assertIn('"schema_version": "1.1"', step["arguments"]["new"])

    def test_gateway_target_recovery_finishes_when_dedupe_exists(self):
        content = "key = normalized.casefold()\\nif normalized and key not in seen:"
        results = [
            {
                "step": {"tool": "read_file", "arguments": {"path": "services/model-gateway/app/router.py"}},
                "outcome": {"tool": "read_file", "ok": True, "result": {
                    "path": "services/model-gateway/app/router.py", "content": content
                }},
            },
            {
                "step": {"tool": "git_checkpoint", "arguments": {}},
                "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
            },
        ]
        step = _deterministic_autonomous_recovery_step(
            "task-gateway-routing",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/model-gateway/app/router.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "finish_task")
        self.assertTrue(step["arguments"]["no_change"])

    def test_test_target_recovery_finishes_when_coverage_exists(self):
        content = """def test_items_have_explicit_project_contracts():
    pass

def test_selection_skips_recently_failed_target():
    pass
"""
        results = [
            {
                "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/tests/test_autonomous_backlog.py"}},
                "outcome": {"tool": "read_file", "ok": True, "result": {
                    "path": "services/orchestrator/tests/test_autonomous_backlog.py",
                    "content": content,
                }},
            },
            {
                "step": {"tool": "git_checkpoint", "arguments": {}},
                "outcome": {"tool": "git_checkpoint", "ok": True, "result": {}},
            },
        ]
        step = _deterministic_autonomous_recovery_step(
            "task-test-coverage",
            results,
            {"mutation": True, "validation": True},
            False,
            ["services/orchestrator/tests/test_autonomous_backlog.py"],
        )
        self.assertIsNotNone(step)
        self.assertEqual(step["tool"], "finish_task")
        self.assertTrue(step["arguments"]["no_change"])


    def test_handoff_is_versioned_and_bounded(self):
        handoff = build_handoff(
            run_id="run-1",
            project_id="project-1",
            role="gateway",
            status="completed",
            summary="Gateway inspected.",
            changed_files=["services\\model-gateway\\app\\router.py"],
            validations=[{"command": "python -m pytest -q", "ok": True}],
            previous_handoff_ids=["h-0"],
            confidence=1.4,
        )
        self.assertEqual(handoff["schema_version"], HANDOFF_SCHEMA_VERSION)
        self.assertEqual(handoff["section"], "model-gateway")
        self.assertEqual(handoff["changed_files"], ["services/model-gateway/app/router.py"])
        self.assertEqual(handoff["confidence"], 1.0)


class AgentReadGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_workspace_alias_read_is_normalized_to_listing(self):
        listing = {"path": ".", "entries": [{"name": "README.md", "type": "file"}]}
        with patch("app.agent_service._list_files", new=AsyncMock(return_value=listing)) as mocked:
            result = await _read_file("ai-engineer", "ai-engineer")

        self.assertTrue(result["directory"])
        self.assertEqual(result["content"], "")
        mocked.assert_awaited_once_with("ai-engineer", ".")


class MemoryPersistenceTests(unittest.TestCase):
    def test_terminal_memory_evidence_is_unique_and_bounded(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database_path = Path(directory) / "orchestrator.db"
            with patch.object(db, "DATABASE_PATH", database_path):
                db.initialize_database()
                project = db.create_project("Memory", "memory-test")
                task = db.create_task(project["id"], "Implement bounded memory evidence.")
                db.update_task(
                    task["id"],
                    status="completed",
                    final_output="done",
                    results=[
                        {
                            "step": {"tool": "run_terminal", "arguments": {
                                "command": "v" * 5_000,
                            }},
                            "outcome": {"tool": "run_terminal", "ok": True},
                        },
                        {
                            "step": {"tool": "replace_text", "arguments": {
                                "path": "services/orchestrator/app/db.py",
                            }},
                            "outcome": {"tool": "replace_text", "ok": True},
                        },
                        {
                            "step": {"tool": "run_terminal", "arguments": {}},
                            "outcome": {
                                "tool": "run_terminal",
                                "ok": False,
                                "error": "e" * 5_000,
                            },
                        },
                    ],
                )
                memories = db.search_memories(project["id"], limit=5)
                self.assertEqual(len(memories), 1)
                detail = memories[0]["detail"]
                self.assertEqual(detail["schema_version"], "1.2")
                self.assertEqual(detail["changed_files"], ["services/orchestrator/app/db.py"])
                self.assertLessEqual(len(detail["validations"][0]), db.MEMORY_ITEM_LIMIT + 3)
                self.assertLessEqual(len(detail["failures"][0]), db.MEMORY_ITEM_LIMIT + 3)


class SubagentHandoffDbTests(unittest.TestCase):
    def test_handoff_round_trip_and_order(self):
        # sqlite connections are intentionally shared by the lightweight DB
        # helpers; ignore Windows' transient WAL lock during temp cleanup.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database_path = Path(directory) / "orchestrator.db"
            with patch.object(db, "DATABASE_PATH", database_path):
                db.initialize_database()
                project = db.create_project("Handoff", "handoff-test")
                run = db.create_autonomy_run(project["id"], "test", 1)
                first = db.create_subagent_handoff(
                    run_id=run["id"],
                    project_id=project["id"],
                    role="requirements",
                    section="product",
                    status="running",
                )
                second = db.create_subagent_handoff(
                    run_id=run["id"],
                    project_id=project["id"],
                    role="architect",
                    section="architecture",
                    status="queued",
                    previous_handoff_ids=[first["id"]],
                )
                db.update_subagent_handoff(
                    first["id"],
                    status="completed",
                    summary="requirements ready",
                    evidence=[{"observation": "acceptance criteria"}],
                )
                rows = db.list_subagent_handoffs(run["id"])
                self.assertEqual([row["id"] for row in rows], [first["id"], second["id"]])
                self.assertEqual(rows[0]["status"], "completed")
                self.assertEqual(rows[1]["previous_handoff_ids"], [first["id"]])


if __name__ == "__main__":
    unittest.main()
