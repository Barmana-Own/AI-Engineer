from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db
from app.skill_state import build_project_state_view, render_project_state_view


class SkillStateCompatibilityTests(unittest.TestCase):
    def test_view_reads_authoritative_database_records(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database_path = Path(directory) / "orchestrator.db"
            with patch.object(db, "DATABASE_PATH", database_path):
                db.initialize_database()
                project = db.create_project("Compatibility", "compatibility-test")
                task = db.create_task(project["id"], "Inspect the imported playbook.")
                run = db.create_autonomy_run(project["id"], "Validate skill import", 1)

                view = build_project_state_view(project["id"])
                self.assertEqual(view["authoritative_store"], "orchestrator_database")
                self.assertTrue(view["read_only"])
                self.assertEqual(view["project"]["id"], project["id"])
                self.assertEqual(view["tasks"][0]["id"], task["id"])
                self.assertEqual(view["autonomy_runs"][0]["id"], run["id"])


    def test_rendered_view_is_an_explicit_compatibility_artifact(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database_path = Path(directory) / "orchestrator.db"
            with patch.object(db, "DATABASE_PATH", database_path):
                db.initialize_database()
                project = db.create_project("Compatibility", "compatibility-output")
                payload = json.loads(render_project_state_view(project["id"]))
                self.assertEqual(payload["state_view"], "compatibility")
                self.assertEqual(payload["authoritative_store"], "orchestrator_database")


if __name__ == "__main__":
    unittest.main()
