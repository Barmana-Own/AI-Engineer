"""Deterministic keyword, intent, mapping, and brief helpers."""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from uuid import uuid4

from .models import FindingSeverity, KeywordCluster, KeywordPageMap


_SPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[^\w\u0600-\u06ff-]+", re.UNICODE)


def normalize_keyword(value: str) -> str:
    text = str(value or "").strip().replace("ي", "ی").replace("ك", "ک")
    text = _SPACE.sub(" ", text)
    return text.casefold()


def import_keywords_csv(content: str, *, column: str = "keyword") -> tuple[str, ...]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or column not in reader.fieldnames:
        raise ValueError(f"CSV must contain a '{column}' column.")
    values: list[str] = []
    for row in reader:
        value = normalize_keyword(row.get(column, ""))
        if value and value not in values:
            values.append(value)
    return tuple(values[:10_000])


def classify_intent(keyword: str) -> str:
    normalized = normalize_keyword(keyword)
    tokens = set(_TOKEN.split(normalized))
    if tokens & {"how", "what", "why", "guide", "tutorial", "چی", "چگونه", "راهنما"}:
        return "INFORMATIONAL"
    if tokens & {"buy", "price", "pricing", "quote", "خرید", "قیمت"}:
        return "TRANSACTIONAL"
    if tokens & {"best", "review", "compare", "comparison", "بهترین", "مقایسه"}:
        return "COMMERCIAL"
    if tokens & {"near", "nearby", "نزدیک", "منطقه"}:
        return "LOCAL"
    return "NAVIGATIONAL" if len(tokens) <= 2 else "COMMERCIAL"


def cluster_keywords(values: list[str] | tuple[str, ...]) -> tuple[KeywordCluster, ...]:
    normalized = list(dict.fromkeys(normalize_keyword(value) for value in values if normalize_keyword(value)))
    groups: list[list[str]] = []
    for keyword in normalized:
        tokens = set(_TOKEN.split(keyword)) - {""}
        match: list[str] | None = None
        for group in groups:
            group_tokens = set().union(*(set(_TOKEN.split(item)) for item in group)) - {""}
            overlap = len(tokens & group_tokens) / max(1, len(tokens | group_tokens))
            if overlap >= 0.35:
                match = group
                break
        if match is None:
            groups.append([keyword])
        else:
            match.append(keyword)
    result: list[KeywordCluster] = []
    for group in groups:
        ordered = tuple(sorted(group, key=lambda item: (len(item), item)))
        result.append(KeywordCluster(str(uuid4()), ordered[0], ordered, classify_intent(ordered[0]), evidence=("QUALITATIVE_SEMANTIC_CLUSTER", "DATA_SOURCE_REQUIRED_FOR_VOLUME")))
    return tuple(result)


def map_keywords_to_pages(
    clusters: tuple[KeywordCluster, ...],
    pages: tuple[str, ...] | list[str],
    *,
    existing_targets: dict[str, str] | None = None,
) -> tuple[KeywordPageMap, ...]:
    page_list = tuple(dict.fromkeys(str(page) for page in pages if str(page).strip()))
    targets = existing_targets or {}
    maps: list[KeywordPageMap] = []
    seen_targets: dict[str, str] = {}
    for cluster in clusters:
        target = targets.get(cluster.primary_keyword)
        conflict = None
        if target and target in seen_targets.values():
            conflict = "KEYWORD_CANNIBALIZATION_POSSIBLE"
        elif target:
            seen_targets[cluster.primary_keyword] = target
        current = target if target in page_list else None
        maps.append(KeywordPageMap(
            mapping_id=str(uuid4()),
            cluster_id=cluster.cluster_id,
            target_page=target,
            current_page=current,
            intent=cluster.intent,
            page_type="landing" if cluster.intent in {"TRANSACTIONAL", "COMMERCIAL", "LOCAL"} else "article",
            conflict=conflict,
            priority=FindingSeverity.HIGH if conflict else FindingSeverity.MEDIUM,
        ))
    return tuple(maps)


def content_brief(cluster: KeywordCluster, *, audience: str = "unknown", conversion_objective: str = "unknown") -> dict[str, object]:
    return {
        "brief_id": str(uuid4()),
        "primary_topic": cluster.primary_keyword,
        "secondary_topics": list(cluster.terms[1:10]),
        "audience": audience,
        "search_intent": cluster.intent,
        "questions_to_answer": [],
        "recommended_structure": ["intent-aligned introduction", "evidence or explanation", "next action"],
        "internal_links": [],
        "metadata_recommendation": {"data_source": "SEO analysis; no ranking metrics inferred"},
        "schema_opportunity": None,
        "conversion_objective": conversion_objective,
    }
