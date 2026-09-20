from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db
from app.routers import projects
from app.schemas import ProjectCreateRequest


class ProjectRouterRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "projects.db"
        self.workspace_root = Path(self._temporary_directory.name) / "workspaces"
        self._database_path_patch = patch.object(db, "DATABASE_PATH", self.database_path)
        self._workspace_root_patch = patch.object(projects, "WORKSPACE_ROOT", self.workspace_root)
        self._database_path_patch.start()
        self._workspace_root_patch.start()
        db.initialize_database()

    def tearDown(self) -> None:
        self._workspace_root_patch.stop()
        self._database_path_patch.stop()
        self._temporary_directory.cleanup()

    def test_create_retrieve_and_repeated_get_are_read_only(self) -> None:
        created = projects.project_create(
            ProjectCreateRequest(name="Regression project", workspace="regression-project")
        )
        self.assertEqual(created.name, "Regression project")
        self.assertEqual(created.workspace, "regression-project")

        before = db.get_project(created.id)
        self.assertIsNotNone(before)
        with db.connect() as connection:
            team_count_before = connection.execute(
                "SELECT COUNT(*) FROM project_team_members WHERE project_id = ?",
                (created.id,),
            ).fetchone()[0]
        self.assertGreater(team_count_before, 0)

        first_get = projects.project_get(created.id)
        after_first_get = db.get_project(created.id)
        with db.connect() as connection:
            team_count_after_first_get = connection.execute(
                "SELECT COUNT(*) FROM project_team_members WHERE project_id = ?",
                (created.id,),
            ).fetchone()[0]

        second_get = projects.project_get(created.id)
        after_second_get = db.get_project(created.id)
        with db.connect() as connection:
            team_count_after_second_get = connection.execute(
                "SELECT COUNT(*) FROM project_team_members WHERE project_id = ?",
                (created.id,),
            ).fetchone()[0]

        self.assertEqual(first_get.model_dump(), second_get.model_dump())
        self.assertEqual(before, after_first_get)
        self.assertEqual(after_first_get, after_second_get)
        self.assertEqual(team_count_before, team_count_after_first_get)
        self.assertEqual(team_count_after_first_get, team_count_after_second_get)
        self.assertEqual(first_get.name, "Regression project")
        self.assertEqual(first_get.workspace, "regression-project")


if __name__ == "__main__":
    unittest.main()