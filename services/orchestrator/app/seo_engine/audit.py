"""Bounded crawler and evidence-based SEO rules."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urldefrag, urljoin, urlsplit
from uuid import uuid4

from .html import extract_page_evidence
from .models import (
    AuditSnapshot,
    CrawlPolicy,
    EvidenceProvenance,
    FindingSeverity,
    FindingStatus,
    PageEvidence,
    PlatformDetection,
    SeoFinding,
)
from .security import SafeHttpClient, SafeHttpResponse, UnsafeTargetError, same_host, validate_url


Fetch = Callable[[str], SafeHttpResponse | tuple[int, dict[str, str], bytes | str]]


def _finding(
    site_id: str,
    category: str,
    severity: FindingSeverity,
    resource: str,
    title: str,
    description: str,
    *,
    evidence: tuple[str, ...] = (),
    impact: str = "",
    action: str = "",
    role: str = "seo_specialist",
    acceptance: str = "",
    verification: str = "HTML or source inspection",
    snapshot_id: str | None = None,
    provenance: EvidenceProvenance = EvidenceProvenance.OBSERVED,
) -> SeoFinding:
    return SeoFinding(
        finding_id=str(uuid4()),
        site_id=site_id,
        category=category,
        severity=severity,
        confidence=0.95 if evidence else 0.65,
        resource=resource,
        title=title,
        description=description,
        evidence=evidence,
        provenance=provenance,
        impact=impact,
        recommended_action=action,
        responsible_role=role,
        acceptance_criteria=acceptance,
        verification_method=verification,
        status=FindingStatus.OPEN,
        source_snapshot_id=snapshot_id,
    )


@dataclass(frozen=True)
class CrawlOutput:
    pages: tuple[PageEvidence, ...]
    findings: tuple[SeoFinding, ...]


class BoundedCrawler:
    def __init__(self, *, policy: CrawlPolicy | None = None, client: SafeHttpClient | None = None) -> None:
        self.policy = policy or CrawlPolicy()
        self.client = client

    def crawl(
        self,
        *,
        site_id: str,
        base_url: str,
        fetch: Fetch | None = None,
        rendered_pages: dict[str, str] | None = None,
    ) -> CrawlOutput:
        safe_base = validate_url(base_url, allow_local=bool(self.client and self.client.allow_local))
        fetcher = fetch or (self.client.fetch if self.client else None)
        if fetcher is None:
            raise ValueError("A bounded fetcher is required for a crawl.")
        queue: deque[tuple[str, int]] = deque([(safe_base, 0)])
        seen: set[str] = set()
        pages: list[PageEvidence] = []
        findings: list[SeoFinding] = []
        while queue and len(pages) < self.policy.max_pages:
            url, depth = queue.popleft()
            url, _fragment = urldefrag(url)
            if url in seen or not same_host(safe_base, url):
                continue
            seen.add(url)
            try:
                response = fetcher(url)
                if isinstance(response, SafeHttpResponse):
                    status_code, headers, body, final_url = response.status_code, response.headers, response.body, response.redirected_to
                else:
                    status_code, headers, body = response
                    final_url = None
                evidence = extract_page_evidence(
                    url,
                    body,
                    status_code=status_code,
                    content_type=headers.get("content-type"),
                    final_url=final_url,
                    rendered_html=(rendered_pages or {}).get(url),
                )
            except (OSError, ValueError, UnsafeTargetError) as exc:
                findings.append(_finding(
                    site_id, "crawl", FindingSeverity.HIGH, url,
                    "Page could not be inspected", str(exc),
                    evidence=("FETCH_ERROR",),
                    action="Make the declared URL reachable and retry the audit.",
                    verification="Repeat the bounded crawl.",
                ))
                continue
            pages.append(evidence)
            findings.extend(self._page_rules(site_id, evidence))
            if depth < self.policy.max_depth and (evidence.content_type or "").casefold().startswith("text/html"):
                for link in evidence.links:
                    if same_host(safe_base, link) and link not in seen and len(queue) < self.policy.max_pages * 2:
                        queue.append((link, depth + 1))
        for resource_name, resource_path in (("robots.txt", "/robots.txt"), ("sitemap.xml", "/sitemap.xml")):
            resource_url = urljoin(safe_base, resource_path)
            try:
                resource_response = fetcher(resource_url)
                resource_status = resource_response.status_code if isinstance(resource_response, SafeHttpResponse) else int(resource_response[0])
            except (KeyError, OSError, ValueError, UnsafeTargetError):
                continue
            if resource_status >= 400:
                findings.append(_finding(
                    site_id, "crawlability", FindingSeverity.LOW, resource_url,
                    f"{resource_name} unavailable",
                    f"Observed HTTP status {resource_status} for {resource_name}.",
                    evidence=(f"status_code={resource_status}",),
                    action=f"Add or intentionally omit {resource_name} with a documented decision.",
                    acceptance=f"{resource_name} is available when required by the project.",
                    verification="HTTP inspection.",
                ))
        findings.extend(self._site_rules(site_id, pages))
        return CrawlOutput(tuple(pages), tuple(findings))

    @staticmethod
    def _page_rules(site_id: str, page: PageEvidence) -> list[SeoFinding]:
        findings: list[SeoFinding] = []
        if page.status_code is not None and page.status_code >= 400:
            findings.append(_finding(site_id, "indexability", FindingSeverity.HIGH, page.url, "HTTP error response", f"Observed HTTP status {page.status_code}.", evidence=(f"status_code={page.status_code}",), impact="Users and crawlers may not reach this resource.", action="Repair the route or redirect it to the correct canonical resource.", acceptance="The URL returns the intended 2xx response or a deliberate redirect.", verification="HTTP status inspection."))
        if not page.title:
            findings.append(_finding(site_id, "metadata", FindingSeverity.HIGH, page.url, "Missing title", "No title element was observed in the inspected document.", evidence=("title=missing",), impact="Search engines and users lack a primary page label.", action="Add a unique, descriptive title in the page template.", acceptance="A unique title is present in raw or rendered HTML.", verification="HTML inspection."))
        elif not 30 <= len(page.title) <= 60:
            findings.append(_finding(site_id, "metadata", FindingSeverity.MEDIUM, page.url, "Title length outside guidance", f"Observed title length {len(page.title)}; this is a heuristic, not a ranking claim.", evidence=(f"title_length={len(page.title)}",), impact="The title may be truncated or underspecified.", action="Review the title for clarity and length.", acceptance="Title meets the project rule or an explicit exception is recorded.", verification="HTML inspection."))
        if not page.meta_description:
            findings.append(_finding(site_id, "metadata", FindingSeverity.MEDIUM, page.url, "Missing meta description", "No meta description was observed.", evidence=("meta_description=missing",), impact="Search snippets may be less controlled.", action="Add a useful description aligned to page intent.", acceptance="A non-empty description is emitted for the page template.", verification="HTML inspection."))
        if not page.canonical:
            findings.append(_finding(site_id, "indexability", FindingSeverity.MEDIUM, page.url, "Missing canonical", "No canonical link was observed.", evidence=("canonical=missing",), impact="Duplicate URL handling is not explicit.", action="Define a canonical URL strategy for the template.", acceptance="The canonical resolves to the intended URL.", verification="HTML inspection."))
        if not page.headings or not any(level == "h1" for level, _ in page.headings):
            findings.append(_finding(site_id, "on_page", FindingSeverity.MEDIUM, page.url, "Missing H1", "No H1 heading was observed.", evidence=("h1=missing",), impact="Page hierarchy is less explicit for users and crawlers.", action="Add one meaningful H1 matching the page intent.", acceptance="Exactly one intentional H1 is rendered.", verification="HTML inspection."))
        for image in page.images_without_alt[:20]:
            findings.append(_finding(site_id, "accessibility", FindingSeverity.LOW, page.url, "Image missing alt text", f"Observed image without alt text: {image}.", evidence=(f"image={image}",), impact="Important visual content may be inaccessible.", action="Add concise, meaningful alt text or mark decorative images appropriately.", acceptance="Non-decorative images have appropriate alt attributes.", verification="HTML inspection."))
        if page.meta_robots and "noindex" in page.meta_robots.casefold():
            findings.append(_finding(site_id, "indexability", FindingSeverity.HIGH, page.url, "noindex directive observed", "The page emits a noindex directive.", evidence=(f"meta_robots={page.meta_robots}",), impact="The page is explicitly excluded from indexing signals.", action="Confirm the directive is intentional for this page.", acceptance="The directive matches the approved SEO requirement.", verification="Raw and rendered HTML inspection."))
        return findings

    @staticmethod
    def _site_rules(site_id: str, pages: list[PageEvidence]) -> list[SeoFinding]:
        findings: list[SeoFinding] = []
        by_title: dict[str, list[str]] = {}
        by_canonical: dict[str, list[str]] = {}
        for page in pages:
            if page.title:
                by_title.setdefault(page.title.casefold(), []).append(page.url)
            if page.canonical:
                by_canonical.setdefault(page.canonical, []).append(page.url)
        for title, urls in by_title.items():
            if len(urls) > 1:
                findings.append(_finding(site_id, "on_page", FindingSeverity.MEDIUM, ", ".join(urls[:5]), "Duplicate page titles", f"The title is shared by {len(urls)} inspected pages.", evidence=(f"title={title[:200]}",), action="Assign distinct page titles to distinct search intents.", acceptance="Each indexable page has an intentional title.", verification="Crawl comparison."))
        for canonical, urls in by_canonical.items():
            if len(urls) > 1 and len(set(urls)) > 1:
                findings.append(_finding(site_id, "indexability", FindingSeverity.MEDIUM, canonical, "Multiple pages share a canonical", f"Observed canonical target on {len(urls)} pages.", evidence=(f"canonical={canonical}",), action="Confirm consolidation is intentional and documented.", acceptance="Canonical mapping matches the approved page strategy.", verification="Crawl comparison."))
        linked = {link for page in pages for link in page.links}
        for page in pages:
            if len(pages) > 1 and page.url not in linked and page.url != pages[0].url:
                findings.append(_finding(site_id, "internal_linking", FindingSeverity.LOW, page.url, "Potential orphan page", "The page was crawled but no inspected page linked to it.", evidence=("inbound_links=0",), action="Add a relevant internal link or document why the page is intentionally isolated.", acceptance="Important pages have a deliberate internal-link path.", verification="Crawl graph inspection."))
        return findings
