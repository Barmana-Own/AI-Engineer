from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app.db import initialize_database
from app.coordination.e2e import (
    DEFAULT_OBJECTIVE,
    EngineeringDemoRunner,
    load_trace,
)


class EndToEndEngineeringWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "orchestrator.db"
        self.workspace = self.root / "fixture"
        initialize_database(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_real_persisted_workflow_produces_evidence_and_trace(self) -> None:
        result = EngineeringDemoRunner(
            self.database,
            self.workspace,
            objective=DEFAULT_OBJECTIVE,
        ).run(simulate_restart=True)

        self.assertTrue(result["final_result"]["completed"], result["final_result"])
        self.assertEqual(result["final_result"]["run_status"], "completed")
        self.assertGreaterEqual(len(result["messages"]), 15)
        self.assertGreaterEqual(len(result["handoffs"]), 10)
        self.assertGreaterEqual(len(result["lessons"]), 1)
        self.assertTrue(all(item["state"] == "completed" for item in result["tasks"]))
        self.assertTrue({"service.py", "client.py", "contracts.py", "app.py", "README.md", "REVIEW_NOTES.md"} <= set(result["files"]))

        event_types = {event["event_type"] for event in result["events"]}
        self.assertIn("parallel_batch_started", event_types)
        self.assertIn("write_conflict_protection", event_types)
        self.assertIn("orchestrator_restart", event_types)
        self.assertIn("startup_recovery", event_types)
        self.assertIn("review_rejected", event_types)
        self.assertIn("release_verification", event_types)

        test_events = [event for event in result["events"] if event["event_type"] == "test_execution"]
        self.assertGreaterEqual(len(test_events), 2)
        self.assertTrue(any(not event["payload"]["passed"] for event in test_events))
        self.assertTrue(any(event["payload"]["passed"] for event in test_events))
        self.assertTrue(any(item["lifecycle"] in {"validated", "trusted"} for item in result["lessons"]))

        trace_file = Path(result["trace_path"])
        self.assertTrue(trace_file.is_file())
        loaded = load_trace(self.database, result["run_id"])
        self.assertEqual(loaded["run_id"], result["run_id"])
        self.assertGreaterEqual(len(loaded["events"]), len(result["events"]))

    def test_completed_run_can_be_loaded_and_resumed_after_restart(self) -> None:
        first = EngineeringDemoRunner(self.database, self.workspace).run(simulate_restart=True)
        resumed = EngineeringDemoRunner(self.database, self.workspace).resume(first["run_id"])
        self.assertTrue(resumed["final_result"]["completed"])
        self.assertEqual(resumed["run_id"], first["run_id"])
        self.assertEqual(resumed["final_result"]["run_status"], "completed")
        self.assertTrue(Path(resumed["trace_path"]).exists())

    @unittest.skipUnless(
        os.getenv("AI_ENGINE_REAL_MODEL_SMOKE") == "1",
        "requires an explicitly configured model-gateway smoke environment",
    )
    def test_optional_real_model_smoke(self) -> None:
        self.skipTest("real-model smoke is deployment-specific; deterministic orchestration remains the required gate")


if __name__ == "__main__":
    unittest.main()

