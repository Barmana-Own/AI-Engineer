from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|private[_-]?key)\b\s*[:=]\s*["']?[^\s,;"']+"),
    re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"\b(?:ghp_|github_pat_|sk-[A-Za-z0-9_-]{10,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    re.compile(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?):\/\/[^\s]+"),
)
_REDACTED = "[REDACTED]"


def sanitize_text(value: object, *, max_chars: int = 16_000) -> tuple[str, bool]:
    text = str(value or "")
    changed = False
    for pattern in _SECRET_PATTERNS:
        text, count = pattern.subn(_REDACTED, text)
        changed = changed or bool(count)
    if len(text) > max_chars:
        text = text[:max_chars] + "?"
        changed = True
    return text, changed


def sanitize_value(value: Any, *, max_items: int = 50) -> tuple[Any, bool]:
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        changed = False
        for key, item in list(value.items())[:max_items]:
            clean, item_changed = sanitize_value(item, max_items=max_items)
            output[str(key)[:128]] = clean
            changed = changed or item_changed
        return output, changed
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        output = []
        changed = False
        for item in list(value)[:max_items]:
            clean, item_changed = sanitize_value(item, max_items=max_items)
            output.append(clean)
            changed = changed or item_changed
        return output, changed
    if isinstance(value, (str, bytes, bytearray)):
        raw = value.decode("utf-8", "replace") if isinstance(value, (bytes, bytearray)) else value
        return sanitize_text(raw)
    return value, False


def sanitize_memory(summary: object, content: object, evidence: object) -> tuple[str, dict[str, Any], list[dict[str, Any]], bool]:
    clean_summary, summary_changed = sanitize_text(summary, max_chars=4_000)
    clean_content, content_changed = sanitize_value(content if isinstance(content, Mapping) else {"value": content})
    clean_evidence, evidence_changed = sanitize_value(evidence if isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes, bytearray)) else [])
    if not isinstance(clean_content, dict):
        clean_content = {"value": clean_content}
    if not isinstance(clean_evidence, list):
        clean_evidence = []
    if len(json.dumps(clean_content, ensure_ascii=False, default=str).encode("utf-8")) > 32_000:
        clean_content = {"summary": clean_summary}
        content_changed = True
    return clean_summary, clean_content, [item for item in clean_evidence if isinstance(item, dict)][:20], bool(summary_changed or content_changed or evidence_changed)


def contains_secret_like(value: object) -> bool:
    _, changed = sanitize_text(value, max_chars=64_000)
    return changed

