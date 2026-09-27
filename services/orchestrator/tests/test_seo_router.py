from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import db
from app.config import settings


class SeoRouterTests(unittest.TestCase):
    def test_register_source_site_audit_and_delegate_through_existing_task_api(self) -> None:
        database_path = Path(tempfile.gettempdir()) / "ai-engineer-seo-router-test.db"
        workspace_path = Path(tempfile.mkdtemp(prefix="seo-router-", dir=settings.workspace_root))
        workspace_name = workspace_path.name
        try:
            with patch.object(db, "DATABASE_PATH", database_path):
                db.initialize_database()
                from app.main import app

                client = TestClient(app)
                project = client.post(
                    "/v1/projects",
                    json={"name": "SEO Router", "workspace": workspace_name},
                )
                self.assertEqual(project.status_code, 200, project.text)
                project_id = project.json()["id"]
                site = client.post(
                    "/v1/seo/sites",
                    json={
                        "project_id": project_id,
                        "name": "Fixture",
                        "source_mode": "source_code_only",
                        "workspace": str(workspace_path),
                    },
                )
                self.assertEqual(site.status_code, 201, site.text)
                site_id = site.json()["id"]
                # Simulate an Orchestrator restart: persisted site data must hydrate the in-memory facade.
                from app.routers import seo as seo_router
                seo_router.engine._sites.clear()
                detection = client.post(f"/v1/seo/sites/{site_id}/detect-platform", json={})
                self.assertEqual(detection.status_code, 200, detection.text)
                audit = client.post(f"/v1/seo/sites/{site_id}/audits", json={"baseline": True})
                self.assertEqual(audit.status_code, 200, audit.text)
                body = audit.json()
                self.assertTrue(body["findings"])
                audit_id = body["snapshot"]["id"]
                pages = client.get(f"/v1/seo/audits/{audit_id}/pages")
                self.assertEqual(pages.status_code, 200, pages.text)
                comparison = client.get(f"/v1/seo/sites/{site_id}/audits/compare", params={"baseline_id": audit_id, "current_id": audit_id})
                self.assertEqual(comparison.status_code, 200, comparison.text)
                finding_id = body["findings"][0]["id"]
                with patch("app.routers.seo.run_agent_task") as worker:
                    delegated = client.post(
                        f"/v1/seo/sites/{site_id}/findings/{finding_id}/delegate",
                        json={"assigned_role": "seo_specialist"},
                    )
                    self.assertEqual(delegated.status_code, 200, delegated.text)
                    self.assertTrue(worker.called)
                verified = client.post(
                    f"/v1/seo/sites/{site_id}/findings/{finding_id}/verify",
                    json={"passed": True, "evidence": ["fixture re-audit"]},
                )
                self.assertEqual(verified.status_code, 200, verified.text)
                self.assertEqual(verified.json()["status"], "verified")
        finally:
            shutil.rmtree(workspace_path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
