from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import collaboration_store, store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.project_management import list_work_queue
from app.coordination.roles import get_role_contract, resolve_role
from app.db import create_project, initialize_database
from app.memory.store import MemoryStore
from app.organization import SEOManagerAgent


class SEOManagerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("SEO project", "Improve organic acquisition", database_path=self.path)
        self.other_project = create_project("Other site", "Keep SEO context isolated", database_path=self.path)
        self.agent = SEOManagerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, project_id: str | None = None, title: str = "SEO strategy") -> CoordinationTask:
        task = CoordinationTask(
            project_id=project_id or self.project["id"],
            title=title,
            description="Manage evidence-backed SEO work",
            role="seo_manager",
            expected_outputs=("SEOReport", "SEOQualityGate"),
            acceptance_criteria=("SEO work has independent evidence",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_role_contract_profile_and_alias_are_managerial_read_only(self) -> None:
        contract = get_role_contract("seo_manager")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertEqual(contract.writable_scope, ("none",))
        self.assertIn("technical_seo_audit", contract.capabilities)
        self.assertIn("create_decision", contract.allowed_tools)
        self.assertEqual(resolve_role("seo-manager"), "seo_manager")
        profile = self.agent.ensure_profile()
        self.assertEqual(profile.role, "seo_manager")
        self.assertEqual(profile.department.value, "PRODUCT")

    def test_site_profile_marks_unknowns_and_is_project_scoped(self) -> None:
        profile = self.agent.create_site_profile(
            self.project["id"], site_domain=None, business_type="B2B SaaS",
            products_services=("analytics",), target_languages=("fa",),
        )
        self.assertEqual(profile.site_domain, "DATA NOT AVAILABLE")
        self.assertIn("site_domain", profile.unknown_fields)
        messages = store.list_messages(project_id=self.project["id"], database_path=self.path)
        self.assertTrue(any(row["topic"] == "seo_site_profile" for row in messages))
        other_messages = store.list_messages(project_id=self.other_project["id"], database_path=self.path)
        self.assertFalse(other_messages)

    def test_audit_preserves_data_unavailable_without_fabricating_metrics(self) -> None:
        task = self._task()
        findings = self.agent.audit_site(
            task.id,
            audit={
                "robots_txt": {"data_available": False},
                "canonical_tags": {
                    "title": "Missing canonical",
                    "problem": "Product pages have no canonical link",
                    "evidence": ["HTML inspection: /products/a has no rel=canonical"],
                    "affected_urls_or_files": ["/products/a"],
                    "responsible_role": "frontend",
                    "severity": "HIGH",
                },
            },
        )
        unavailable = next(item for item in findings if item.category == "robots_txt")
        self.assertEqual(unavailable.evidence, ("DATA NOT AVAILABLE",))
        self.assertEqual(unavailable.confidence, 0.0)
        self.assertNotIn("traffic", " ".join(unavailable.evidence).casefold())
        observed = next(item for item in findings if item.category == "canonical_tags")
        self.assertEqual(observed.responsible_role, "frontend")
        self.assertTrue(observed.message_id)

    def test_priority_calculation_distinguishes_critical_and_low(self) -> None:
        critical = self.agent.calculate_priority(
            seo_impact="critical", business_impact="critical", severity="critical",
            affected_page_count=500, implementation_effort="low", dependency="high", confidence=95,
        )
        low = self.agent.calculate_priority(
            seo_impact="low", business_impact="low", severity="low",
            affected_page_count=1, implementation_effort="high", dependency="low", confidence=20,
        )
        self.assertEqual(critical, "CRITICAL")
        self.assertEqual(low, "LOW")

    def test_keyword_mapping_persists_and_flags_cannibalization(self) -> None:
        clusters = self.agent.build_keyword_map(
            self.project["id"],
            (
                {"name": "API monitoring", "keywords": ("api monitoring",), "intent": "COMMERCIAL", "language": "en", "region": "US", "target_page": "/monitoring", "priority": "HIGH"},
                {"name": "Monitoring tools", "keywords": ("monitoring tools",), "intent": "COMMERCIAL", "language": "en", "region": "US", "target_page": "/monitoring", "priority": "MEDIUM"},
            ),
        )
        self.assertEqual(clusters[1].status, "cannibalization")
        messages = store.list_messages(project_id=self.project["id"], database_path=self.path)
        self.assertEqual(len([row for row in messages if row["topic"] == "seo_keyword_map"]), 2)
        other_messages = store.list_messages(project_id=self.other_project["id"], database_path=self.path)
        self.assertFalse(other_messages)

    def test_backlog_generation_delegates_existing_role_and_queue(self) -> None:
        parent = self._task()
        finding = {
            "title": "Missing canonical",
            "problem": "Canonical tags are absent",
            "evidence": ("HTML inspection: /catalog",),
            "seo_impact": "high",
            "affected_urls_or_files": ("/catalog",),
            "recommended_action": "Add a canonical link element",
            "responsible_role": "frontend",
            "priority": "HIGH",
            "acceptance_criteria": ("Canonical resolves to /catalog",),
            "verification_method": "Inspect rendered HTML",
        }
        tasks = self.agent.generate_backlog_tasks(parent.id, (finding,))
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].responsible_role, "frontend")
        saved = store.get_task(tasks[0].task_id, database_path=self.path)
        self.assertEqual(saved["role"], "frontend")
        queue = list_work_queue(project_id=self.project["id"], database_path=self.path)
        self.assertTrue(any(item["item_ref"] == tasks[0].task_id for item in queue))
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=tasks[0].task_id, database_path=self.path)
        self.assertIn("frontend", {row["recipient_role"] for row in handoffs})

    def test_decision_requires_evidence_and_is_persisted(self) -> None:
        with self.assertRaises(ValueError):
            self.agent.record_decision(self.project["id"], title="URL policy", context="", decision="", evidence=())
        decision = self.agent.record_decision(
            self.project["id"], title="Canonical policy", context="Duplicate product URLs exist",
            decision="Use one canonical URL per product intent", options=("consolidate", "leave duplicates"),
            arguments=("Reduces cannibalization",), evidence=("audit:duplicate-pages-1",),
        )
        rows = collaboration_store.list_decisions(project_id=self.project["id"], database_path=self.path)
        self.assertIn(decision["decision_id"], {row["decision_id"] for row in rows})
        self.assertEqual(decision["decision_maker"], "seo_manager")

    def test_quality_gate_requires_evidence_and_can_verify_success(self) -> None:
        task = self._task()
        failed = self.agent.quality_gate(task.id, status="SEO_VERIFIED")
        self.assertEqual(failed.status, "SEO_FAILED")
        self.assertTrue(failed.blocking_reasons)
        passed = self.agent.verify_seo_task(
            task.id, observed={"canonical": "/catalog"}, expected={"canonical": "/catalog"},
            evidence=("html:/catalog rel=canonical",), verification_method="Rendered HTML inspection",
        )
        self.assertEqual(passed.status, "SEO_VERIFIED")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.BLOCKER.value, {row["message_type"] for row in messages})
        self.assertIn(MessageType.RESULT.value, {row["message_type"] for row in messages})

    def test_verification_failure_records_actionable_blocker(self) -> None:
        task = self._task()
        gate = self.agent.verify_seo_task(
            task.id, observed={"sitemap": False}, expected={"sitemap": True},
            evidence=("inspection:/sitemap.xml",), verification_method="HTTP and XML inspection", responsible_role="devops",
        )
        self.assertEqual(gate.status, "SEO_FAILED")
        self.assertTrue(any("does not satisfy" in reason for reason in gate.blocking_reasons))
        self.assertEqual(gate.responsible_role, "devops")

    def test_project_memory_is_evidence_gated_and_isolated(self) -> None:
        with self.assertRaises(ValueError):
            self.agent.remember_validated_knowledge(self.project["id"], summary="Canonical policy", content={"rule": "one"}, evidence=(), lifecycle="validated")
        self.agent.remember_validated_knowledge(
            self.project["id"], summary="Canonical policy", content={"rule": "one canonical per intent"},
            evidence=("review:seo-1",), lifecycle="validated",
        )
        memories = self.agent.retrieve_knowledge(self.project["id"], query="canonical")
        self.assertTrue(memories)
        self.assertFalse(self.agent.retrieve_knowledge(self.other_project["id"], query="canonical"))

    def test_report_contains_only_supplied_evidence(self) -> None:
        report = self.agent.report(
            self.project["id"], summary="No analytics source was connected.",
            blockers=("DATA NOT AVAILABLE: Search Console",), next_actions=("Connect an approved analytics source",),
        )
        self.assertEqual(report.project_id, self.project["id"])
        messages = store.list_messages(project_id=self.project["id"], database_path=self.path)
        self.assertTrue(any(row["topic"] == "seo_report" for row in messages))
        self.assertIn("DATA NOT AVAILABLE", report.blockers[0])


if __name__ == "__main__":
    unittest.main()