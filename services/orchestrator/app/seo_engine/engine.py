"""High-level SEO capability used by the existing orchestrator routes."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .audit import BoundedCrawler, Fetch
from .codebase import CodebaseSeoAdapter
from .detector import detect_from_html, detect_from_source, merge_detection
from .keywords import cluster_keywords, content_brief, map_keywords_to_pages
from .models import (
    AuditResult,
    AuditSnapshot,
    CrawlPolicy,
    FindingStatus,
    KeywordCluster,
    KeywordPageMap,
    Platform,
    SeoFinding,
    SeoSiteProfile,
    SourceMode,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SEOEngine:
    """A pure orchestration facade; persistence is supplied by the API layer."""

    def __init__(self) -> None:
        self._sites: dict[str, SeoSiteProfile] = {}
        self._snapshots: dict[str, AuditSnapshot] = {}

    def register_site(
        self,
        *,
        project_id: str,
        name: str,
        base_url: str | None,
        source_mode: SourceMode,
        workspace: str | None = None,
        language: str | None = None,
        region: str | None = None,
        crawl_policy: CrawlPolicy | None = None,
    ) -> SeoSiteProfile:
        if source_mode in {SourceMode.PUBLIC_URL_ONLY, SourceMode.PUBLIC_URL_AND_SOURCE, SourceMode.WORDPRESS_API} and not base_url:
            raise ValueError("A base_url is required for the selected source mode.")
        site = SeoSiteProfile(
            site_id=str(uuid4()), project_id=project_id, name=str(name).strip()[:200],
            base_url=base_url, source_mode=source_mode, workspace=workspace,
            language=language, region=region, crawl_policy=crawl_policy or CrawlPolicy(),
            unknowns=("SEARCH_CONSOLE_DATA_NOT_CONFIGURED",),
        )
        self._sites[site.site_id] = site
        return site

    def get_site(self, site_id: str) -> SeoSiteProfile | None:
        return self._sites.get(site_id)

    def detect_platform(self, site_id: str, *, html: str | None = None) -> SeoSiteProfile:
        site = self._require_site(site_id)
        source_detection = detect_from_source(site.workspace) if site.workspace else None
        html_detection = detect_from_html(html) if html is not None else None
        detection = merge_detection(*(item for item in (source_detection, html_detection) if item is not None))
        updated = replace(site, platform=detection.platform)
        self._sites[site_id] = updated
        return updated

    def audit(
        self,
        site_id: str,
        *,
        fetch: Fetch | None = None,
        rendered_pages: dict[str, str] | None = None,
        baseline: bool = False,
        html: str | None = None,
    ) -> AuditResult:
        site = self._require_site(site_id)
        site = self.detect_platform(site_id, html=html) if site.platform == Platform.UNKNOWN else site
        pages = ()
        findings: tuple[SeoFinding, ...] = ()
        if site.base_url and fetch is not None:
            output = BoundedCrawler(policy=site.crawl_policy).crawl(site_id=site.site_id, base_url=site.base_url, fetch=fetch, rendered_pages=rendered_pages)
            pages, findings = output.pages, output.findings
        elif site.workspace:
            findings = CodebaseSeoAdapter(site.workspace).inspect(site_id=site.site_id)
        else:
            findings = ()
        detections = tuple(item for item in (detect_from_source(site.workspace) if site.workspace else None, detect_from_html(html) if html else None) if item is not None)
        snapshot_id = str(uuid4())
        findings = tuple(replace(item, source_snapshot_id=snapshot_id) for item in findings)
        snapshot = AuditSnapshot(
            snapshot_id=snapshot_id, site_id=site.site_id, project_id=site.project_id,
            baseline=baseline, status="completed", platform=merge_detection(*detections) if detections else detect_from_source(None),
            pages=tuple(pages), findings=tuple(findings), crawl_policy=site.crawl_policy,
            provider_state={"search_console": "no_data", "analytics": "no_data"}, created_at=_now(),
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        return AuditResult(snapshot=snapshot)

    def re_audit(self, site_id: str, **kwargs: Any) -> AuditResult:
        return self.audit(site_id, baseline=False, **kwargs)

    def snapshots(self, site_id: str) -> tuple[AuditSnapshot, ...]:
        return tuple(item for item in self._snapshots.values() if item.site_id == site_id)

    def keyword_plan(
        self,
        site_id: str,
        keywords: list[str] | tuple[str, ...],
        *,
        pages: list[str] | tuple[str, ...] = (),
        existing_targets: dict[str, str] | None = None,
        audience: str = "unknown",
        conversion_objective: str = "unknown",
    ) -> tuple[tuple[KeywordCluster, ...], tuple[KeywordPageMap, ...], tuple[dict[str, object], ...]]:
        self._require_site(site_id)
        clusters = cluster_keywords(keywords)
        maps = map_keywords_to_pages(clusters, pages, existing_targets=existing_targets)
        briefs = tuple(content_brief(cluster, audience=audience, conversion_objective=conversion_objective) for cluster in clusters)
        return clusters, maps, briefs

    def verify_findings(self, findings: tuple[SeoFinding, ...] | list[SeoFinding], *, passed: bool, evidence: tuple[str, ...] = ()) -> tuple[SeoFinding, ...]:
        status = FindingStatus.VERIFIED if passed else FindingStatus.FAILED
        return tuple(replace(item, status=status, evidence=tuple(item.evidence) + tuple(evidence)) for item in findings)

    def _require_site(self, site_id: str) -> SeoSiteProfile:
        site = self._sites.get(site_id)
        if site is None:
            raise KeyError(site_id)
        return site
