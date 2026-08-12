import unittest

from app.autonomy import AUTONOMOUS_BACKLOG, build_backlog_goal


class AutonomousBacklogTests(unittest.TestCase):
    def test_items_have_explicit_project_contracts(self):
        self.assertTrue(AUTONOMOUS_BACKLOG)
        for item in AUTONOMOUS_BACKLOG:
            goal = build_backlog_goal(item)
            self.assertIn(f"BACKLOG_KEY: {item.key}", goal)
            self.assertIn(f"TARGET FILE: {item.target}", goal)
            self.assertIn(f"VALIDATION COMMAND: {item.validation}", goal)
            self.assertTrue(item.target.startswith(("services/", "apps/", "packages/")))


    def test_targets_are_unique(self):
        targets = [item.target for item in AUTONOMOUS_BACKLOG]
        self.assertEqual(len(targets), len(set(targets)))
