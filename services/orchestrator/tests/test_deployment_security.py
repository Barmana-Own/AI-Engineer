from __future__ import annotations

from pathlib import Path
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.security import ControlPlaneAuthMiddleware


def _orchestrator_fixture() -> FastAPI:
    application = FastAPI()
    application.add_middleware(
        ControlPlaneAuthMiddleware,
        required=True,
        control_token="control-secret",
        owner_token="owner-secret",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/v1/projects")
    def projects() -> dict[str, str]:
        return {"status": "authorized"}

    @application.post("/v1/developer/projects/demo/git/rollback")
    def rollback() -> dict[str, str]:
        return {"status": "owner-authorized"}

    return application


class DeploymentSecurityTests(unittest.TestCase):
    def test_health_is_public_but_control_plane_requires_authentication(self) -> None:
        client = TestClient(_orchestrator_fixture())
        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.get("/v1/projects").status_code, 401)
        self.assertEqual(
            client.get("/v1/projects", headers={"X-AI-Engine-Token": "control-secret"}).status_code,
            200,
        )

    def test_high_risk_operation_requires_owner_token(self) -> None:
        client = TestClient(_orchestrator_fixture())
        control = {"X-AI-Engine-Token": "control-secret"}
        self.assertEqual(client.post("/v1/developer/projects/demo/git/rollback", headers=control).status_code, 403)
        owner = {**control, "X-AI-Engine-Owner-Token": "owner-secret"}
        self.assertEqual(client.post("/v1/developer/projects/demo/git/rollback", headers=owner).status_code, 200)

    def test_autonomy_and_auto_push_defaults_are_safe(self) -> None:
        settings = Settings(_env_file=None)
        self.assertFalse(settings.autonomous_mode_enabled)
        self.assertFalse(settings.autonomous_auto_push)

    def test_production_templates_require_auth_and_safe_defaults(self) -> None:
        root = Path(__file__).resolve().parents[3]
        orchestrator_env = (root / "services/orchestrator/.env.example").read_text(encoding="utf-8")
        gateway_env = (root / "services/model-gateway/.env.example").read_text(encoding="utf-8")
        launcher = (root / "deploy/windows-server/start-ai-engineer-server.ps1").read_text(encoding="utf-8")
        for name in ("CONTROL_PLANE_AUTH_REQUIRED", "CONTROL_PLANE_TOKEN", "OWNER_CONTROL_TOKEN", "MODEL_GATEWAY_TOKEN"):
            self.assertIn(name, orchestrator_env)
        self.assertIn("GATEWAY_AUTH_REQUIRED", gateway_env)
        self.assertIn("GATEWAY_AUTH_TOKEN", gateway_env)
        self.assertIn('Get-BooleanEnvironment "AI_ENGINE_AUTONOMOUS_MODE_ENABLED" $false', launcher)
        self.assertIn('Get-BooleanEnvironment "AI_ENGINE_AUTONOMOUS_AUTO_PUSH" $false', launcher)


if __name__ == "__main__":
    unittest.main()
