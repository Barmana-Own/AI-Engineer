from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app import db
from app.seo_engine.audit import BoundedCrawler
from app.seo_engine.codebase import CodebaseSeoAdapter
from app.seo_engine.detector import detect_from_html, detect_from_source
from app.seo_engine.engine import SEOEngine
from app.seo_engine.html import extract_page_evidence
from app.seo_engine.keywords import classify_intent, cluster_keywords, normalize_keyword
from app.seo_engine.models import CrawlPolicy, FindingSeverity, FindingStatus, Platform, SourceMode
from app.seo_engine.persistence import create_site, get_finding, list_findings, save_snapshot, update_finding_status
from app.seo_engine.providers import MockSearchConsoleProvider, MockWordPressAdapter, NoDataSearchConsoleProvider, RestWordPressAdapter
from app.seo_engine.security import UnsafeTargetError, validate_url


class SeoEngineTests(unittest.TestCase):
    def test_platform_detection_supports_react_vite_and_express(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"dependencies": {"react": "x", "vite": "x", "express": "x"}}), encoding="utf-8")
            detection = detect_from_source(root)
        self.assertEqual(detection.platform, Platform.VITE_REACT)
        self.assertIn(Platform.NODE_EXPRESS, detection.related_platforms)
        self.assertEqual(detect_from_html('<div id="__NEXT_DATA__"></div>').platform, Platform.NEXTJS)

    def test_html_parser_preserves_raw_and_rendered_evidence(self) -> None:
        evidence = extract_page_evidence(
            "https://example.com/",
            '<html lang="fa"><head><title>Example</title><meta name="description" content="Desc"><link rel="canonical" href="/"></head><body><h1>Heading</h1><img src="/a.png"><a href="/about">About</a></body></html>',
            rendered_html="<html><head><title>Rendered</title></head></html>",
        )
        self.assertEqual(evidence.title, "Example")
        self.assertEqual(evidence.lang, "fa")
        self.assertTrue(evidence.raw_html_hash)
        self.assertTrue(evidence.rendered_html_hash)
        self.assertEqual(evidence.images_without_alt, ("https://example.com/a.png",))

    def test_rendered_dom_supplies_missing_metadata_signals(self) -> None:
        evidence = extract_page_evidence(
            "https://example.com/",
            "<html><head></head><body></body></html>",
            rendered_html="<html><head><title>Rendered title</title><meta name=\"description\" content=\"Rendered description\"><link rel=\"canonical\" href=\"/\"></head><body><h1>Rendered heading</h1></body></html>",
        )
        self.assertEqual(evidence.title, "Rendered title")
        self.assertEqual(evidence.meta_description, "Rendered description")
        self.assertEqual(evidence.canonical, "https://example.com/")
        self.assertTrue(evidence.rendered_observed)

    def test_crawler_is_bounded_and_same_host_only(self) -> None:
        pages = {
            "https://example.com/": '<html><body><a href="/ok">OK</a><a href="https://evil.example/x">external</a></body></html>',
            "https://example.com/ok": '<html><head><title>OK</title><meta name="description" content="A"><link rel="canonical" href="/ok"></head><body><h1>OK</h1></body></html>',
        }

        def fetch(url: str):
            return (200, {"content-type": "text/html"}, pages[url])

        output = BoundedCrawler(policy=CrawlPolicy(max_pages=2, max_depth=2)).crawl(site_id="site", base_url="https://example.com/", fetch=fetch)
        self.assertEqual({page.url for page in output.pages}, {"https://example.com/", "https://example.com/ok"})
        self.assertLessEqual(len(output.pages), 2)

    def test_audit_creates_findings_without_fabricating_metrics(self) -> None:
        engine = SEOEngine()
        site = engine.register_site(project_id="project-a", name="Fixture", base_url="https://example.com", source_mode=SourceMode.PUBLIC_URL_ONLY)
        result = engine.audit(site.site_id, fetch=lambda _url: (200, {"content-type": "text/html"}, "<html><body><h1>Missing metadata</h1></body></html>"), baseline=True)
        self.assertTrue(result.snapshot.baseline)
        self.assertTrue(any(item.category == "metadata" for item in result.snapshot.findings))
        self.assertEqual(result.snapshot.provider_state["search_console"], "no_data")
        self.assertTrue(all("ranking" not in item.description.casefold() for item in result.snapshot.findings))

    def test_source_only_codebase_findings_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"dependencies": {"react": "x", "vite": "x", "express": "x"}}), encoding="utf-8")
            findings = CodebaseSeoAdapter(root).inspect(site_id="site")
            self.assertTrue(findings)
            self.assertFalse((root / "reports").exists())

    def test_keyword_normalization_cluster_and_intent(self) -> None:
        self.assertEqual(normalize_keyword("  كالا  "), "کالا")
        clusters = cluster_keywords(["buy shoes", "shoes price", "how to clean shoes"])
        self.assertGreaterEqual(len(clusters), 2)
        self.assertEqual(classify_intent("how to clean shoes"), "INFORMATIONAL")

    def test_wordpress_adapter_is_draft_first(self) -> None:
        adapter = MockWordPressAdapter("http://localhost:8080")
        post = adapter.create_draft(title="Draft", content="Content")
        self.assertEqual(post["status"], "draft")
        with self.assertRaises(PermissionError):
            adapter.publish(post["id"])

    def test_wordpress_status_is_allowlisted_before_request(self) -> None:
        adapter = RestWordPressAdapter(
            base_url="https://example.com",
            username="service-user",
            application_password="server-side-only",
        )
        with self.assertRaises(ValueError):
            adapter.list_posts(status="draft&include=private")

    def test_search_console_provider_labels_mock_and_no_data(self) -> None:
        for provider, mode in ((MockSearchConsoleProvider(), "mock"), (NoDataSearchConsoleProvider(), "no_data")):
            result = provider.query(site_url="https://example.com", start_date="2026-01-01", end_date="2026-01-02")
            self.assertEqual(result["mode"], mode)
            self.assertFalse(result["data_available"])

    def test_url_safety_rejects_private_and_credential_targets(self) -> None:
        with self.assertRaises(UnsafeTargetError):
            validate_url("http://127.0.0.1:8000")
        with self.assertRaises(UnsafeTargetError):
            validate_url("https://user:password@example.com/")
        self.assertEqual(validate_url("http://localhost:3000", allow_local=True), "http://localhost:3000/")

    def test_project_site_and_finding_persistence_are_isolated(self) -> None:
        path = Path(tempfile.gettempdir()) / f"ai-engineer-seo-test-isolation-{uuid4().hex}.db"
        with patch.object(db, "DATABASE_PATH", path):
            db.initialize_database()
            project_a = db.create_project("A", str(path.parent / "workspace-a"))
            project_b = db.create_project("B", str(path.parent / "workspace-b"))
            engine = SEOEngine()
            site_a = engine.register_site(project_id=project_a["id"], name="A", base_url="https://a.example", source_mode=SourceMode.PUBLIC_URL_ONLY)
            site_b = engine.register_site(project_id=project_b["id"], name="B", base_url="https://b.example", source_mode=SourceMode.PUBLIC_URL_ONLY)
            persisted_a = create_site(site_a)
            persisted_b = create_site(site_b)
            self.assertNotEqual(persisted_a["project_id"], persisted_b["project_id"])
            result = engine.audit(site_a.site_id, fetch=lambda _url: (200, {"content-type": "text/html"}, "<html></html>"))
            saved = save_snapshot(result.snapshot)
            findings = list_findings(site_a.site_id, snapshot_id=saved["id"])
            self.assertTrue(findings)
            self.assertFalse(list_findings(site_b.site_id))
            finding = get_finding(findings[0]["id"])
            self.assertIsNotNone(finding)
            self.assertEqual(update_finding_status(findings[0]["id"], "verified", evidence=["re-audit passed"])["status"], "verified")


if __name__ == "__main__":
    unittest.main()
