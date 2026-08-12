import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db
from app.agent_service import _apply_subagent_requirements, _unwrap_model_action
from app.subagents import (
    HANDOFF_SCHEMA_VERSION,
    SECTION_ROLE_KEYS,
    build_handoff,
    build_role_instruction,
    get_subagent_role,
    list_section_subagents,
)


class SubagentRegistryTests(unittest.TestCase):
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
