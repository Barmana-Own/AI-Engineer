from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.I | re.S),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|private[_-]?key)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"\b(?:ghp|github_pat|sk|xox[baprs])_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s]+"),
)

def sanitize_text(value: str, max_chars: int = 16_000) -> tuple[str, bool]:
    text = str(value)
    changed = False
    for pattern in _SECRET_PATTERNS:
        text, count = pattern.subn("[REDACTED]", text)
        changed = changed or count > 0
    if len(text) > max_chars:
        text = text[:max_chars] + "?"
        changed = True
    return text, changed

def sanitize_value(value: Any, *, max_items: int = 100) -> tuple[Any, bool]:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, bytes):
        return sanitize_text(value.decode("utf-8", errors="replace"))
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        changed = False
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                changed = True
                break
            clean_key, key_changed = sanitize_text(str(key), max_chars=256)
            clean_item, item_changed = sanitize_value(item, max_items=max_items)
            output[clean_key] = clean_item
            changed = changed or key_changed or item_changed
        return output, changed
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        output = []
        changed = False
        for item in list(value)[:max_items]:
            clean_item, item_changed = sanitize_value(item, max_items=max_items)
            output.append(clean_item)
            changed = changed or item_changed
        if len(value) > max_items:
            changed = True
        return output, changed
    return value, False

def sanitize_memory(
    summary: str,
    content: Mapping[str, Any] | None,
    evidence: Sequence[Mapping[str, Any]] | None,
) -> tuple[str, dict[str, Any], list[dict[str, Any]], bool]:
    clean_summary, summary_changed = sanitize_text(summary, max_chars=4_000)
    clean_content_value, content_changed = sanitize_value(content or {})
    clean_evidence_value, evidence_changed = sanitize_value(list(evidence or []))
    clean_content = clean_content_value if isinstance(clean_content_value, dict) else {}
    clean_evidence = (
        [item for item in clean_evidence_value if isinstance(item, dict)]
        if isinstance(clean_evidence_value, list)
        else []
    )
    return clean_summary, clean_content, clean_evidence, summary_changed or content_changed or evidence_changed

def contains_secret_like(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(contains_secret_like(key) or contains_secret_like(item) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(contains_secret_like(item) for item in value)
    if isinstance(value, (str, bytes)):
        text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
        return any(pattern.search(text) for pattern in _SECRET_PATTERNS)
    return False
