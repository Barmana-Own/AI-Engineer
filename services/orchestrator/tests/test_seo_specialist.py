from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.project_management import list_work_queue
from app.coordination.roles import get_role_contract, resolve_role
from app.db import create_project, initialize_database
from app.organization import SEOManagerAgent, SEOSpecialistAgent


class SEOSpecialistAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("SEO site", "Evidence-backed SEO work", database_path=self.path)
        self.other_project = create_project("Other site", "Isolation test", database_path=self.path)
        self.agent = SEOSpecialistAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, project_id: str | None = None, role: str = "seo_specialist") -> CoordinationTask:
        task = CoordinationTask(
            project_id=project_id or self.project["id"], title="SEO analysis", description="Inspect a bounded site scope",
            role=role, expected_outputs=("SEOFinding",), acceptance_criteria=("Evidence is persisted",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_role_contract_profile_alias_and_permissions(self) -> None:
        contract = get_role_contract("seo_specialist")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertEqual(contract.writable_scope, ("none",))
        self.assertNotIn("write_file", contract.allowed_tools)
        self.assertIn("keyword_clustering", contract.capabilities)
        self.assertEqual(resolve_role("seo-specialist"), "seo_specialist")
        profile = self.agent.ensure_profile()
        self.assertEqual(profile.role, "seo_specialist")
        self.assertEqual(profile.department.value, "RESEARCH")

    def test_technical_finding_is_structured_and_persisted(self) -> None:
        task = self._task()
        finding = self.agent.create_finding(
            task.id, category="canonical_tags", severity="HIGH", resource="/products/a",
            description="Canonical link is missing", evidence=("HTML inspection: no rel=canonical",),
            impact="Duplicate URL signals may be consolidated incorrectly", recommended_action="Add the approved canonical link",
            responsible_role="frontend", acceptance_criteria=("Canonical resolves to /products/a",),
            verification_method="Inspect rendered HTML",
        )
        self.assertEqual(finding.status, "open")
        self.assertEqual(finding.responsible_role, "frontend")
        self.assertTrue(finding.message_id)
        messages = store.list_messages(project_id=self.project["id"], topic="seo_specialist_finding", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.EVIDENCE.value)

    def test_on_page_analysis_marks_missing_element_without_inventing_analytics(self) -> None:
        task = self._task()
        findings = self.agent.analyze_on_page(task.id, ({
            "url": "/pricing", "title": "", "evidence": ("Rendered HTML: title element is empty",),
            "responsible_role": "frontend", "priority": "HIGH",
        },))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].category, "on_page")
        self.assertNotIn("traffic", " ".join(item["description"] for item in findings[0].evidence).casefold())

    def test_keyword_clusters_detect_cannibalization_and_isolate_projects(self) -> None:
        task = self._task()
        clusters = self.agent.analyze_keywords(task.id, (
            {"name": "API monitoring", "keywords": ("api monitoring",), "intent": "COMMERCIAL", "target_page": "/monitoring", "evidence": ("Existing page inventory",)},
            {"name": "Monitoring tools", "keywords": ("monitoring tools",), "intent": "COMMERCIAL", "target_page": "/monitoring", "evidence": ("Existing page inventory",)},
        ))
        self.assertEqual(clusters[1].status, "cannibalization")
        self.assertEqual(len(store.list_messages(project_id=self.project["id"], topic="seo_specialist_keyword_cluster", database_path=self.path)), 2)
        self.assertFalse(store.list_messages(project_id=self.other_project["id"], topic="seo_specialist_keyword_cluster", database_path=self.path))

    def test_content_gap_and_content_brief_use_existing_message_bus(self) -> None:
        task = self._task()
        gaps = self.agent.analyze_content_gaps(task.id, ({
            "target_intent": "INFORMATIONAL", "target_cluster": "api monitoring",
            "recommended_page_type": "guide", "purpose": "Answer setup questions",
            "suggested_outline": ("Concepts", "Implementation"), "conversion_objective": "Request a demo",
            "evidence": ("Existing requirements and page inventory",), "priority": "MEDIUM",
        },))
        self.assertEqual(gaps[0].status, "open")
        brief = self.agent.create_content_brief(
            task.id, page_objective="Explain API monitoring", audience="Engineering teams",
            search_intent="INFORMATIONAL", primary_topic="API monitoring", secondary_topics=("alerts",),
            questions_to_answer=("What is monitored?",), recommended_structure=("H1", "H2"),
            internal_links=("/pricing",), metadata_recommendation="Describe the guide", schema_opportunity="Article",
            cta_objective="Request a demo", evidence=("Requirements review",),
        )
        self.assertTrue(brief.message_id)
        self.assertTrue(store.list_messages(project_id=self.project["id"], topic="seo_specialist_content_brief", database_path=self.path))

    def test_internal_link_recommendation_requires_explicit_pages_and_context(self) -> None:
        task = self._task()
        with self.assertRaises(ValueError):
            self.agent.recommend_internal_links(task.id, ({"source_page": "/a", "target_page": "/b"},))
        rows = self.agent.recommend_internal_links(task.id, ({
            "source_page": "/guide", "target_page": "/pricing", "anchor_context": "compare plans",
            "reason": "Relevant commercial next step", "evidence": ("Crawl link inventory",),
        },))
        self.assertEqual(rows[0].source_page, "/guide")

    def test_implementation_request_creates_existing_task_queue_and_handoff(self) -> None:
        parent = self._task()
        request = self.agent.create_implementation_request(
            parent.id, title="Add canonical", description="Implement the approved canonical policy",
            evidence=("HTML inspection: /products/a has no canonical",), affected_resource="/products/a",
            responsible_role="frontend", acceptance_criteria=("Rendered canonical is /products/a",),
            verification_method="Rendered HTML inspection", priority="HIGH",
        )
        saved = store.get_task(request.task_id, database_path=self.path)
        self.assertEqual(saved["role"], "frontend")
        self.assertTrue(saved["writer"])
        self.assertTrue(any(item["item_ref"] == request.task_id for item in list_work_queue(project_id=self.project["id"], database_path=self.path)))
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=request.task_id, database_path=self.path)
        self.assertEqual(handoffs[0]["recipient_role"], "frontend")
        with self.assertRaises(ValueError):
            self.agent.create_implementation_request(parent.id, title="Bad", description="", affected_resource="/x", responsible_role="seo_specialist", acceptance_criteria=("x",), verification_method="inspect")

    def test_verification_failure_creates_revision_handoff_and_success_can_promote_memory(self) -> None:
        parent = self._task()
        request = self.agent.create_implementation_request(
            parent.id, title="Fix metadata", description="Update title and canonical", evidence=("HTML inspection",),
            affected_resource="/pricing", responsible_role="frontend", acceptance_criteria=("Metadata matches spec",),
            verification_method="Rendered HTML inspection",
        )
        failed = self.agent.verify_implementation(request.task_id, observed={"canonical": "/wrong"}, expected={"canonical": "/pricing"}, evidence=("Rendered HTML",), verification_method="HTML inspection", responsible_role="frontend")
        self.assertEqual(failed.status, "SEO_FAILED")
        self.assertTrue(failed.handoff_id)
        passed = self.agent.verify_implementation(request.task_id, observed={"canonical": "/pricing"}, expected={"canonical": "/pricing"}, evidence=("Rendered HTML: canonical=/pricing",), verification_method="HTML inspection", responsible_role="frontend")
        self.assertEqual(passed.status, "SEO_VERIFIED")
        memory = self.agent.promote_verified_memory(self.project["id"], summary="Pricing canonical template", content={"canonical": "/pricing"}, evidence=("SEO verification",), verification=passed)
        self.assertEqual(memory["lifecycle"], "validated")
        self.assertTrue(self.agent.retrieve_knowledge(self.project["id"], query="canonical"))
        with self.assertRaises(ValueError):
            self.agent.promote_verified_memory(self.other_project["id"], summary="Leak", content={}, evidence=("x",), verification=passed)

    def test_false_analytics_claim_is_not_presented_as_observed(self) -> None:
        task = self._task()
        finding = self.agent.create_finding(
            task.id, category="performance", severity="HIGH", resource="/", description="Ranking improved",
            evidence=("Ranking improved",), impact="Traffic increased", recommended_action="Keep monitoring",
            responsible_role="researcher", acceptance_criteria=("Approved data source is attached",), verification_method="Use an approved analytics source",
        )
        self.assertEqual(finding.status, "data_not_available")
        self.assertIn("DATA SOURCE REQUIRED", " ".join(item["description"] for item in finding.evidence))

    def test_analysis_requires_specialist_task_and_preserves_project_isolation(self) -> None:
        non_specialist = self._task(role="frontend")
        with self.assertRaises(ValueError):
            self.agent.create_finding(non_specialist.id, category="title", severity="LOW", resource="/", description="Issue", evidence=("HTML",), impact="low", recommended_action="Fix", responsible_role="frontend", acceptance_criteria=("fixed",), verification_method="HTML")
        other = self._task(project_id=self.other_project["id"])
        finding = self.agent.create_finding(other.id, category="robots_txt", severity="INFO", resource="/robots.txt", description="Inspection unavailable", evidence=(), impact="DATA NOT AVAILABLE", recommended_action="Inspect robots.txt", responsible_role="devops", acceptance_criteria=("Inspection evidence",), verification_method="HTTP inspection")
        self.assertEqual(finding.project_id, self.other_project["id"])
        self.assertFalse(store.list_messages(project_id=self.project["id"], topic="seo_specialist_finding", database_path=self.path))



    def test_manager_can_delegate_read_only_analysis_to_specialist(self) -> None:
        from app.organization import SEOManagerAgent
        manager = SEOManagerAgent(self.path)
        parent = self._task(role="seo_manager")
        delegated = manager.delegate_task(
            parent.id, title="Inspect hreflang", problem="Multilingual evidence is required",
            responsible_role="seo-specialist", evidence=("Requirements specify fa and en",),
            acceptance_criteria=("Hreflang inspection evidence is attached",),
            verification_method="Inspect rendered alternate links", priority="MEDIUM",
        )
        self.assertEqual(delegated.responsible_role, "seo_specialist")
        saved = store.get_task(delegated.task_id, database_path=self.path)
        self.assertEqual(saved["role"], "seo_specialist")
        self.assertFalse(saved["writer"])

if __name__ == "__main__":
    unittest.main()
