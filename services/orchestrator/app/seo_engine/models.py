"""Bounded, platform-neutral data contracts for SEO work.

The contracts deliberately describe evidence and provenance.  They do not
invent rankings, traffic, search volume, or indexing state when a provider is
not connected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Platform(StrEnum):
    WORDPRESS = "wordpress"
    REACT_SPA = "react_spa"
    VITE_REACT = "vite_react"
    NEXTJS = "nextjs"
    NODE_EXPRESS = "node_express"
    STATIC = "static"
    GENERIC_WEB = "generic_web"
    UNKNOWN = "unknown"


class SourceMode(StrEnum):
    PUBLIC_URL_ONLY = "public_url_only"
    SOURCE_CODE_ONLY = "source_code_only"
    PUBLIC_URL_AND_SOURCE = "public_url_and_source"
    WORDPRESS_API = "wordpress_api"


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(StrEnum):
    OPEN = "open"
    FIX_IN_PROGRESS = "fix_in_progress"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"


class EvidenceProvenance(StrEnum):
    OBSERVED = "observed"
    SOURCE_CODE = "source_code"
    RENDERED_PAGE = "rendered_page"
    SEARCH_CONSOLE = "search_console"
    USER_PROVIDED = "user_provided"
    LAB_TEST = "lab_test"
    MODEL_INFERENCE = "model_inference"
    RECOMMENDATION = "recommendation"
    NO_DATA = "no_data"


@dataclass(frozen=True)
class CrawlPolicy:
    max_pages: int = 50
    max_depth: int = 3
    timeout_seconds: float = 10.0
    max_response_bytes: int = 2_000_000
    same_host_only: bool = True
    follow_redirects: bool = False
    render_javascript: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.max_pages <= 500:
            raise ValueError("max_pages must be between 1 and 500")
        if not 0 <= self.max_depth <= 12:
            raise ValueError("max_depth must be between 0 and 12")
        if not 0.5 <= self.timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be between 0.5 and 120")
        if not 10_000 <= self.max_response_bytes <= 20_000_000:
            raise ValueError("max_response_bytes is outside the safe bound")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlatformDetection:
    platform: Platform
    confidence: float
    evidence: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    related_platforms: tuple[Platform, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform.value,
            "confidence": round(max(0.0, min(self.confidence, 1.0)), 3),
            "evidence": list(self.evidence),
            "uncertainties": list(self.uncertainties),
            "related_platforms": [item.value for item in self.related_platforms],
        }


@dataclass(frozen=True)
class PageEvidence:
    url: str
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    title: str | None = None
    meta_description: str | None = None
    meta_robots: str | None = None
    canonical: str | None = None
    hreflang: tuple[dict[str, str], ...] = ()
    headings: tuple[tuple[str, str], ...] = ()
    links: tuple[str, ...] = ()
    images_without_alt: tuple[str, ...] = ()
    json_ld_types: tuple[str, ...] = ()
    lang: str | None = None
    word_count: int = 0
    raw_html_hash: str | None = None
    rendered_html_hash: str | None = None
    raw_observed: bool = True
    rendered_observed: bool = False
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SeoFinding:
    finding_id: str
    site_id: str
    category: str
    severity: FindingSeverity
    confidence: float
    resource: str
    title: str
    description: str
    evidence: tuple[str, ...] = ()
    provenance: EvidenceProvenance = EvidenceProvenance.OBSERVED
    impact: str = ""
    recommended_action: str = ""
    responsible_role: str = "seo_specialist"
    acceptance_criteria: str = ""
    verification_method: str = ""
    status: FindingStatus = FindingStatus.OPEN
    source_snapshot_id: str | None = None
    assigned_task_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("severity", "provenance", "status"):
            value[key] = value[key].value
        return value


@dataclass(frozen=True)
class AuditSnapshot:
    snapshot_id: str
    site_id: str
    project_id: str
    baseline: bool
    status: str
    platform: PlatformDetection
    pages: tuple[PageEvidence, ...] = ()
    findings: tuple[SeoFinding, ...] = ()
    crawl_policy: CrawlPolicy = field(default_factory=CrawlPolicy)
    provider_state: dict[str, str] = field(default_factory=dict)
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "site_id": self.site_id,
            "project_id": self.project_id,
            "baseline": self.baseline,
            "status": self.status,
            "platform": self.platform.as_dict(),
            "pages": [item.as_dict() for item in self.pages],
            "findings": [item.as_dict() for item in self.findings],
            "crawl_policy": self.crawl_policy.as_dict(),
            "provider_state": dict(self.provider_state),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class KeywordCluster:
    cluster_id: str
    primary_keyword: str
    terms: tuple[str, ...]
    intent: str
    language: str | None = None
    region: str | None = None
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KeywordPageMap:
    mapping_id: str
    cluster_id: str
    target_page: str | None
    current_page: str | None
    intent: str
    page_type: str
    conflict: str | None = None
    priority: FindingSeverity = FindingSeverity.MEDIUM

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["priority"] = self.priority.value
        return value


@dataclass(frozen=True)
class SeoSiteProfile:
    site_id: str
    project_id: str
    name: str
    base_url: str | None
    source_mode: SourceMode
    workspace: str | None = None
    platform: Platform = Platform.UNKNOWN
    language: str | None = None
    region: str | None = None
    conversion_objectives: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    crawl_policy: CrawlPolicy = field(default_factory=CrawlPolicy)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source_mode"] = self.source_mode.value
        value["platform"] = self.platform.value
        value["crawl_policy"] = self.crawl_policy.as_dict()
        return value


@dataclass(frozen=True)
class AuditResult:
    snapshot: AuditSnapshot
    keyword_clusters: tuple[KeywordCluster, ...] = ()
    keyword_maps: tuple[KeywordPageMap, ...] = ()
    content_briefs: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot": self.snapshot.as_dict(),
            "keyword_clusters": [item.as_dict() for item in self.keyword_clusters],
            "keyword_maps": [item.as_dict() for item in self.keyword_maps],
            "content_briefs": list(self.content_briefs),
        }
