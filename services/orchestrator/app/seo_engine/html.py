"""Evidence-only HTML extraction for raw and rendered documents."""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

from .models import PageEvidence


_WHITESPACE = re.compile(r"\s+")


class _EvidenceParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title: str | None = None
        self.meta_description: str | None = None
        self.meta_robots: str | None = None
        self.canonical: str | None = None
        self.hreflang: list[dict[str, str]] = []
        self.headings: list[tuple[str, str]] = []
        self.links: list[str] = []
        self.images_without_alt: list[str] = []
        self.json_ld_types: list[str] = []
        self.lang: str | None = None
        self.text_parts: list[str] = []
        self._title_parts: list[str] = []
        self._in_title = False
        self._active_heading: str | None = None
        self._heading_parts: list[str] = []
        self._in_script_jsonld = False
        self._jsonld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.casefold()
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag_name == "html" and values.get("lang"):
            self.lang = values["lang"].strip()[:20]
        if tag_name == "title":
            self._title_parts = []
            self._in_title = True
        if tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._active_heading = tag_name
            self._heading_parts = []
        if tag_name == "meta":
            name = values.get("name", "").casefold()
            if name == "description":
                self.meta_description = values.get("content", "").strip()[:1_000]
            elif name == "robots":
                self.meta_robots = values.get("content", "").strip()[:500]
        if tag_name == "link":
            rel = {item.strip().casefold() for item in values.get("rel", "").split()}
            href = values.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonical = urljoin(self.base_url, href)
            if "alternate" in rel and values.get("hreflang") and href:
                self.hreflang.append({
                    "lang": values["hreflang"][:30],
                    "href": urljoin(self.base_url, href),
                })
        if tag_name == "a" and values.get("href"):
            self.links.append(urljoin(self.base_url, values["href"].strip()))
        if tag_name == "img" and not values.get("alt", "").strip():
            self.images_without_alt.append(urljoin(self.base_url, values.get("src", "")) if values.get("src") else "inline-image")
        if tag_name == "script" and values.get("type", "").casefold() == "application/ld+json":
            self._in_script_jsonld = True
            self._jsonld_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.casefold()
        if tag_name == "title":
            title = _WHITESPACE.sub(" ", " ".join(self._title_parts)).strip()
            self.title = title[:500] if title else None
            self._in_title = False
        if tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._active_heading == tag_name:
            heading = _WHITESPACE.sub(" ", " ".join(self._heading_parts)).strip()
            if heading:
                self.headings.append((tag_name, heading[:500]))
            self._active_heading = None
            self._heading_parts = []
        if tag_name == "script" and self._in_script_jsonld:
            raw = "".join(self._jsonld_parts).strip()
            try:
                payload = json.loads(raw)
                entries = payload if isinstance(payload, list) else [payload]
                for entry in entries:
                    if isinstance(entry, dict):
                        value = entry.get("@type")
                        if isinstance(value, list):
                            self.json_ld_types.extend(str(item)[:100] for item in value)
                        elif value:
                            self.json_ld_types.append(str(value)[:100])
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
            self._in_script_jsonld = False
            self._jsonld_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_script_jsonld:
            self._jsonld_parts.append(data)
        elif self._active_heading:
            self._heading_parts.append(data)
        else:
            self.text_parts.append(data)
        if self._in_title:
            self._title_parts.append(data)


def extract_page_evidence(
    url: str,
    html: str | bytes,
    *,
    status_code: int | None = 200,
    content_type: str | None = "text/html",
    final_url: str | None = None,
    rendered_html: str | bytes | None = None,
) -> PageEvidence:
    raw = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else str(html)
    parser = _EvidenceParser(url)
    parser.feed(raw)
    parser.close()
    rendered_parser: _EvidenceParser | None = None
    if rendered_html is not None:
        rendered_text = rendered_html.decode("utf-8", errors="replace") if isinstance(rendered_html, bytes) else str(rendered_html)
        rendered_parser = _EvidenceParser(url)
        rendered_parser.feed(rendered_text)
        rendered_parser.close()
        # Rendered DOM is authoritative only when raw HTML omitted the signal.
        parser.title = parser.title or rendered_parser.title
        parser.meta_description = parser.meta_description or rendered_parser.meta_description
        parser.meta_robots = parser.meta_robots or rendered_parser.meta_robots
        parser.canonical = parser.canonical or rendered_parser.canonical
        parser.hreflang = parser.hreflang or rendered_parser.hreflang
        parser.headings = parser.headings or rendered_parser.headings
        parser.links = parser.links or rendered_parser.links
        parser.images_without_alt = parser.images_without_alt or rendered_parser.images_without_alt
        parser.json_ld_types = parser.json_ld_types or rendered_parser.json_ld_types
        parser.lang = parser.lang or rendered_parser.lang
    text = _WHITESPACE.sub(" ", " ".join(parser.text_parts)).strip()
    if not text and rendered_parser is not None:
        text = _WHITESPACE.sub(" ", " ".join(rendered_parser.text_parts)).strip()
    rendered_hash = None
    rendered_observed = rendered_html is not None
    if rendered_html is not None:
        rendered = rendered_html.decode("utf-8", errors="replace") if isinstance(rendered_html, bytes) else str(rendered_html)
        rendered_hash = hashlib.sha256(rendered.encode("utf-8", errors="replace")).hexdigest()
    return PageEvidence(
        url=url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        title=parser.title,
        meta_description=parser.meta_description,
        meta_robots=parser.meta_robots,
        canonical=parser.canonical,
        hreflang=tuple(parser.hreflang[:50]),
        headings=tuple(parser.headings[:100]),
        links=tuple(dict.fromkeys(parser.links))[:200],
        images_without_alt=tuple(dict.fromkeys(parser.images_without_alt))[:100],
        json_ld_types=tuple(dict.fromkeys(parser.json_ld_types))[:50],
        lang=parser.lang,
        word_count=len(text.split()),
        raw_html_hash=hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest(),
        rendered_html_hash=rendered_hash,
        raw_observed=True,
        rendered_observed=rendered_observed,
    )
