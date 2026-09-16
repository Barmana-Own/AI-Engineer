import unittest
from unittest.mock import patch

from app.autonomy import AUTONOMOUS_BACKLOG, build_backlog_goal, select_autonomous_backlog_item
from app.agent_service import _autonomous_target_is_current


class AutonomousBacklogTests(unittest.TestCase):
    def test_security_boundary_target_recognizes_hardened_agent_service(self):
        results = [{
            "step": {"tool": "read_file", "arguments": {"path": "services/orchestrator/app/agent_service.py"}
            },
            "outcome": {
                "tool": "read_file",
                "ok": True,
                "result": {
                    "path": "services/orchestrator/app/agent_service.py",
                    "content": (
                        "_normalise_model_edit_arguments MODEL_ACTION_ALIASES "
                        "attempt_limit = 3 if autonomous _model_reported_verified_noop"
                    ),
                },
            },
        }]
        self.assertTrue(
            _autonomous_target_is_current(
                results, ["services/orchestrator/app/agent_service.py"]
            )
        )

    def test_items_have_explicit_project_contracts(self):
        self.assertTrue(AUTONOMOUS_BACKLOG)
        for item in AUTONOMOUS_BACKLOG:
            goal = build_backlog_goal(item)
            self.assertIn(f"BACKLOG_KEY: {item.key}", goal)
            self.assertIn(f"TARGET FILE: {item.target}", goal)
            self.assertIn(f"VALIDATION COMMAND: {item.validation}", goal)
            self.assertTrue(item.target.startswith(("services/", "apps/", "packages/", "README.md")))


    @patch("app.autonomy.search_memories")
    def test_selection_skips_recently_failed_target(self, search_memories):
        failed = AUTONOMOUS_BACKLOG[0]
        search_memories.return_value = [{
            "kind": "failed",
            "detail": {
                "status": "failed",
                "instruction": f"TARGET FILE: {failed.target}",
            },
        }]
        selected = select_autonomous_backlog_item("project")
        self.assertNotEqual(selected.target, failed.target)
    @patch("app.autonomy.list_autonomy_runs")
    @patch("app.autonomy.search_memories")
    def test_selection_skips_recently_failed_run_target(self, search_memories, list_autonomy_runs):
        search_memories.return_value = []
        failed = AUTONOMOUS_BACKLOG[0]
        list_autonomy_runs.return_value = [{
            "status": "failed",
            "goal": f"TARGET FILE: {failed.target}",
        }]

        selected = select_autonomous_backlog_item("project")

        self.assertNotEqual(selected.target, failed.target)

    @patch("app.autonomy.search_memories")
    def test_selection_rotates_after_bounded_memory_window(self, search_memories):
        repeated = next(item for item in AUTONOMOUS_BACKLOG if item.key == "test-coverage")
        search_memories.return_value = [
            {
                "kind": "success",
                "detail": {
                    "status": "completed",
                    "instruction": f"TARGET FILE: {repeated.target}",
                },
            }
            for _ in range(50)
        ]

        selected = select_autonomous_backlog_item("project")
        self.assertNotEqual(selected.target, repeated.target)

    @patch("app.autonomy.list_autonomy_runs")
    @patch("app.autonomy.search_memories")
    def test_selection_advances_after_completed_noop_runs(self, search_memories, list_autonomy_runs):
        search_memories.return_value = []
        list_autonomy_runs.return_value = [
            {
                "status": "completed",
                "goal": f"TARGET FILE: {item.target}",
            }
            for item in AUTONOMOUS_BACKLOG[:2]
        ]

        selected = select_autonomous_backlog_item("project")

        self.assertEqual(selected.target, AUTONOMOUS_BACKLOG[2].target)
    @patch("app.autonomy.list_autonomy_runs")
    @patch("app.autonomy.search_memories")
    def test_selection_does_not_starve_backlog_after_untouched_noop(
        self, search_memories, list_autonomy_runs
    ):
        noop_target = AUTONOMOUS_BACKLOG[-1]
        search_memories.return_value = [
            {
                "kind": "success",
                "detail": {
                    "status": "completed",
                    "instruction": f"TARGET FILE: {noop_target.target}",
                    "changed_files": [
                        item.target for item in AUTONOMOUS_BACKLOG[:-1]
                    ],
                },
            }
        ]
        list_autonomy_runs.return_value = [
            {
                "status": "completed",
                "goal": f"TARGET FILE: {noop_target.target}",
            }
        ]

        selected = select_autonomous_backlog_item("project")

        self.assertNotEqual(selected.target, noop_target.target)

    @patch("app.autonomy.list_autonomy_runs")
    @patch("app.autonomy.search_memories")
    def test_selection_retries_after_failed_targets_would_starve_backlog(
        self, search_memories, list_autonomy_runs
    ):
        noop_target = AUTONOMOUS_BACKLOG[-1]
        search_memories.return_value = [
            {
                "kind": "failed",
                "detail": {
                    "status": "failed",
                    "instruction": f"TARGET FILE: {item.target}",
                },
            }
            for item in AUTONOMOUS_BACKLOG[:-1]
        ]
        list_autonomy_runs.return_value = [
            {
                "status": "completed",
                "goal": f"TARGET FILE: {noop_target.target}",
            }
        ]

        selected = select_autonomous_backlog_item("project")

        self.assertNotEqual(selected.target, noop_target.target)

    @patch("app.autonomy.list_autonomy_runs")
    @patch("app.autonomy.search_memories")
    def test_selection_skips_verified_changed_target(self, search_memories, list_autonomy_runs):
        changed = AUTONOMOUS_BACKLOG[0]
        search_memories.return_value = [{
            "kind": "success",
            "detail": {
                "status": "completed",
                "instruction": f"TARGET FILE: {changed.target}",
                "changed_files": [changed.target.replace("/", "\\").upper()],
            },
        }]
        list_autonomy_runs.return_value = []

        selected = select_autonomous_backlog_item("project")

        self.assertNotEqual(selected.target, changed.target)
    def test_targets_are_unique(self):
        targets = [item.target for item in AUTONOMOUS_BACKLOG]
        self.assertEqual(len(targets), len(set(targets)))

    def test_every_domain_section_has_a_backlog_owner(self):
        sections = {item.section for item in AUTONOMOUS_BACKLOG}
        self.assertTrue(
            {
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
            }.issubset(sections)
        )

    @patch("app.autonomy.get_task")
    def test_validation_gate_requires_mutation_then_terminal_success(self, get_task):
        from app import autonomy

        def fake_task(task_id):
            if task_id == "writer":
                return {"results": [{"step": {"tool": "apply_patch"}, "outcome": {"tool": "apply_patch", "ok": True}}]}
            return {"results": [{"step": {"tool": "run_terminal"}, "outcome": {"tool": "run_terminal", "ok": True}}]}

        get_task.side_effect = fake_task
        self.assertTrue(autonomy._run_has_successful_validation(["writer", "verifier"]))

    @patch("app.autonomy.get_task")
    def test_validation_gate_rejects_validation_before_mutation(self, get_task):
        from app import autonomy

        get_task.return_value = {"results": [{"step": {"tool": "run_terminal"}, "outcome": {"tool": "run_terminal", "ok": True}}]}

        self.assertFalse(autonomy._run_has_successful_validation(["verifier"]))
