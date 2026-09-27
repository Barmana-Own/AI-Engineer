"""Read-only source inspection adapters for common web stacks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .detector import detect_from_source
from .models import EvidenceProvenance, FindingSeverity, SeoFinding
from .audit import _finding


class CodebaseSeoAdapter:
    """Inspect source without modifying files or running arbitrary commands."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()

    def inspect(self, *, site_id: str) -> tuple[SeoFinding, ...]:
        if not self.workspace.is_dir():
            return (_finding(site_id, "source", FindingSeverity.HIGH, str(self.workspace), "Source workspace unavailable", "The declared source workspace does not exist.", evidence=("SOURCE_NOT_AVAILABLE",), action="Provide a readable project workspace.", verification="Filesystem inspection.", provenance=EvidenceProvenance.SOURCE_CODE),)
        detection = detect_from_source(self.workspace)
        findings: list[SeoFinding] = []
        package = self._package()
        if detection.platform.value in {"react_spa", "vite_react"}:
            index_candidates = [self.workspace / "index.html", self.workspace / "public" / "index.html"]
            if not any(path.exists() for path in index_candidates):
                findings.append(_finding(site_id, "rendering", FindingSeverity.MEDIUM, str(self.workspace), "SPA entry HTML not found", "A React source tree was detected but no inspectable HTML entry was found.", evidence=(f"platform={detection.platform.value}",), action="Verify SSR/prerender or provide the production entry document for audit.", verification="Build or rendered page inspection.", provenance=EvidenceProvenance.SOURCE_CODE))
            elif self._html_missing_head_metadata(index_candidates):
                findings.append(_finding(site_id, "metadata", FindingSeverity.HIGH, str(index_candidates[0]), "Entry document has incomplete metadata", "The source entry document lacks one or more title/description/canonical signals.", evidence=("SOURCE_ENTRY_HEAD_INCOMPLETE",), action="Implement metadata through the page/template layer and verify rendered output.", verification="Rendered HTML inspection.", provenance=EvidenceProvenance.SOURCE_CODE))
        if not (self.workspace / "robots.txt").exists():
            findings.append(_finding(site_id, "crawlability", FindingSeverity.LOW, str(self.workspace / "robots.txt"), "robots.txt not present in source", "No robots.txt artifact was found in the declared source workspace.", evidence=("robots.txt=missing",), action="Add or intentionally omit robots.txt with a documented decision.", verification="Deployment URL inspection.", provenance=EvidenceProvenance.SOURCE_CODE))
        if not (self.workspace / "public" / "sitemap.xml").exists() and not (self.workspace / "sitemap.xml").exists():
            findings.append(_finding(site_id, "crawlability", FindingSeverity.LOW, str(self.workspace), "Sitemap artifact not found", "No sitemap.xml artifact was found in common source locations.", evidence=("sitemap.xml=missing",), action="Generate a sitemap when the site's scale and architecture require one.", verification="Deployment URL inspection.", provenance=EvidenceProvenance.SOURCE_CODE))
        if package and "express" in self._dependencies(package):
            findings.append(_finding(site_id, "integration", FindingSeverity.INFO, str(self.workspace / "package.json"), "Express source adapter available", "The source contains an Express dependency; server-rendered metadata and route responses should be audited separately.", evidence=("express_dependency=observed",), action="Audit API/rendering routes where they produce HTML.", verification="Route and response inspection.", provenance=EvidenceProvenance.SOURCE_CODE))
        return tuple(findings)

    def _package(self) -> dict[str, Any]:
        path = self.workspace / "package.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, UnicodeError):
            return {}

    @staticmethod
    def _dependencies(package: dict[str, Any]) -> set[str]:
        result: set[str] = set()
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            value = package.get(key)
            if isinstance(value, dict):
                result.update(str(item).casefold() for item in value)
        return result

    @staticmethod
    def _html_missing_head_metadata(candidates: list[Path]) -> bool:
        for path in candidates:
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace").casefold()
            except OSError:
                continue
            if "<title" in text and "description" in text:
                return False
        return True
