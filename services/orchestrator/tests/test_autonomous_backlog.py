import unittest
from unittest.mock import patch

from app.autonomy import AUTONOMOUS_BACKLOG, build_backlog_goal, select_autonomous_backlog_item


class AutonomousBacklogTests(unittest.TestCase):
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
