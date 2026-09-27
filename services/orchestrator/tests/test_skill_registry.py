from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.skill_registry import (
    SkillRegistry,
    UnknownSkillError,
    normalize_outer_package_name,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_SKILLS = {
    "project-analysis-prompt-engineering",
    "design-system-ui-architecture",
    "frontend-architecture",
    "backend-architecture",
    "database-architecture",
    "api-integration",
    "authentication-authorization",
    "application-security",
    "software-testing",
    "qa-debugging",
    "deployment-production",
    "fullstack-final-review",
}


class SkillRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = SkillRegistry(REPOSITORY_ROOT)

    def test_all_imported_skills_are_discoverable_and_unique(self) -> None:
        ids = set(self.registry.ids())
        self.assertEqual(ids, EXPECTED_SKILLS)
        self.assertEqual(len(ids), len(self.registry.skills))
        self.assertEqual(len(self.registry.inventory()), 12)

    def test_stage12_outer_package_is_normalized_without_changing_skill_id(self) -> None:
        self.assertEqual(
            normalize_outer_package_name("12-ullstack-final-review"),
            "12-fullstack-final-review",
        )
        skill = self.registry.get("fullstack-final-review")
        self.assertEqual(skill.skill_id, "fullstack-final-review")
        self.assertEqual(skill.source_outer_package, "12-ullstack-final-review")
        self.assertEqual(skill.normalized_outer_package, "12-fullstack-final-review")

    def test_skill_documents_and_external_metadata_are_preserved(self) -> None:
        for skill_id in self.registry.ids():
            descriptor = self.registry.get(skill_id)
            document = self.registry.load_skill_document(skill_id)
            self.assertTrue(document.startswith("---"), skill_id)
            self.assertTrue(descriptor.skill_file.is_file(), skill_id)
            self.assertTrue(descriptor.openai_metadata_file.is_file(), skill_id)
            self.assertTrue(descriptor.scripts or descriptor.references, skill_id)

        metadata = self.registry.get("backend-architecture").openai_metadata_file.read_text(
            encoding="utf-8"
        )
        self.assertIn("allow_implicit_invocation: true", metadata)
        self.assertTrue(self.registry.get("backend-architecture").external_allow_implicit_invocation)

    def test_external_implicit_invocation_cannot_bypass_router(self) -> None:
        skill_id = "backend-architecture"
        self.assertFalse(
            self.registry.activation_allowed(
                skill_id,
                router_approved=False,
                task_id="task-1",
                role="backend",
                project_id="project-1",
            )
        )
        self.assertFalse(
            self.registry.activation_allowed(
                skill_id,
                router_approved=True,
                task_id=None,
                role="backend",
                project_id="project-1",
            )
        )
        self.assertTrue(
            self.registry.activation_allowed(
                skill_id,
                router_approved=True,
                task_id="task-1",
                role="backend",
                project_id="project-1",
            )
        )

    def test_unknown_skill_is_rejected(self) -> None:
        with self.assertRaises(UnknownSkillError):
            self.registry.get("not-installed")
        with self.assertRaises(UnknownSkillError):
            self.registry.get("../backend-architecture")

    def test_database_remains_authoritative_for_project_state(self) -> None:
        policy = json.loads(
            (REPOSITORY_ROOT / "skills" / "software-delivery" / "integration-policy.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(self.registry.state_authority, "orchestrator_database")
        self.assertEqual(policy["state"]["authoritative_store"], "orchestrator_database")
        self.assertEqual(policy["state"]["project_state_json"], "compatibility_view_only")
        self.assertTrue(policy["state"]["skills_must_not_create_execution_state"])

    def test_scripts_are_declared_behind_the_execution_gateway(self) -> None:
        policy = json.loads(
            (REPOSITORY_ROOT / "skills" / "software-delivery" / "integration-policy.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            policy["script_execution"]["gateway"],
            ["agent_worker", "tool_policy", "local_agent"],
        )
        self.assertFalse(policy["script_execution"]["direct_model_execution"])
        for descriptor in self.registry.skills:
            for script in descriptor.scripts:
                self.assertIn(
                    script.execution,
                    {"local-agent-policy", "tool-policy-and-local-agent", "network-policy-and-local-agent", "compatibility-adapter-only"},
                )
                self.assertTrue(script.classification)


if __name__ == "__main__":
    unittest.main()
