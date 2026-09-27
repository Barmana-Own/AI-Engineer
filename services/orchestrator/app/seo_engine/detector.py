"""Deterministic platform detection from source and observed HTML."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Platform, PlatformDetection


def detect_from_source(workspace: str | Path | None) -> PlatformDetection:
    root = Path(workspace).expanduser() if workspace else None
    if root is None or not root.exists() or not root.is_dir():
        return PlatformDetection(Platform.UNKNOWN, 0.0, uncertainties=("SOURCE_NOT_AVAILABLE",))
    evidence: list[str] = []
    package: dict[str, object] = {}
    package_path = root / "package.json"
    if package_path.exists():
        try:
            loaded = json.loads(package_path.read_text(encoding="utf-8"))
            package = loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError, UnicodeError):
            evidence.append("package.json unreadable")
    deps: dict[str, object] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = package.get(key)
        if isinstance(value, dict):
            deps.update(value)
    dep_names = {str(key).casefold() for key in deps}
    if (root / "wp-config.php").exists() or (root / "wp-content").exists():
        return PlatformDetection(Platform.WORDPRESS, 0.98, ("WordPress markers found in source",))
    if "next" in dep_names or any(root.glob("next.config.*")):
        evidence.append("Next.js dependency or config detected")
        return PlatformDetection(Platform.NEXTJS, 0.98, tuple(evidence), related_platforms=(Platform.REACT_SPA,))
    has_react = "react" in dep_names or "react-dom" in dep_names
    has_vite = "vite" in dep_names or any(root.glob("vite.config.*"))
    has_express = "express" in dep_names
    if has_react and has_vite:
        evidence.append("React and Vite markers detected")
        if has_express:
            evidence.append("Express dependency detected")
        return PlatformDetection(Platform.VITE_REACT, 0.96, tuple(evidence), related_platforms=(Platform.REACT_SPA, Platform.NODE_EXPRESS) if has_express else (Platform.REACT_SPA,))
    if has_react:
        evidence.append("React dependency detected")
        return PlatformDetection(Platform.REACT_SPA, 0.9, tuple(evidence), related_platforms=(Platform.NODE_EXPRESS,) if has_express else ())
    if has_express:
        evidence.append("Express dependency detected")
        return PlatformDetection(Platform.NODE_EXPRESS, 0.9, tuple(evidence))
    if any((root / name).exists() for name in ("index.html", "robots.txt", "sitemap.xml")):
        return PlatformDetection(Platform.STATIC, 0.7, ("Static web artifacts detected",))
    return PlatformDetection(Platform.UNKNOWN, 0.2, tuple(evidence), uncertainties=("PLATFORM_MARKERS_INSUFFICIENT",))


def detect_from_html(html: str, *, headers: dict[str, str] | None = None) -> PlatformDetection:
    text = str(html or "")
    lower = text.casefold()
    evidence: list[str] = []
    headers = {str(key).casefold(): str(value) for key, value in (headers or {}).items()}
    generator = headers.get("x-powered-by", "") + " " + text[:100_000]
    if "wp-content" in lower or "wordpress" in generator.casefold():
        evidence.append("WordPress marker observed in HTML or headers")
        return PlatformDetection(Platform.WORDPRESS, 0.9, tuple(evidence))
    if "__next_data__" in lower or "_next/static" in lower:
        evidence.append("Next.js runtime marker observed")
        return PlatformDetection(Platform.NEXTJS, 0.95, tuple(evidence), related_platforms=(Platform.REACT_SPA,))
    if "react" in lower or "data-reactroot" in lower:
        evidence.append("React marker observed")
        return PlatformDetection(Platform.REACT_SPA, 0.75, tuple(evidence))
    if "express" in headers.get("x-powered-by", "").casefold():
        return PlatformDetection(Platform.NODE_EXPRESS, 0.8, ("Express header observed",))
    return PlatformDetection(Platform.GENERIC_WEB, 0.35, uncertainties=("RUNTIME_NOT_IDENTIFIED",))


def merge_detection(*detections: PlatformDetection | None) -> PlatformDetection:
    normalized = [item for item in detections if item is not None]
    valid = [item for item in normalized if item.platform != Platform.UNKNOWN]
    if not valid:
        return normalized[0] if normalized else PlatformDetection(Platform.UNKNOWN, 0.0)
    best = max(valid, key=lambda item: item.confidence)
    evidence: list[str] = []
    uncertainties: list[str] = []
    related: list[Platform] = []
    for item in normalized:
        evidence.extend(item.evidence)
        uncertainties.extend(item.uncertainties)
        related.extend(item.related_platforms)
    return PlatformDetection(
        best.platform,
        min(1.0, best.confidence + (0.05 if len(valid) > 1 else 0.0)),
        tuple(dict.fromkeys(evidence))[:20],
        tuple(dict.fromkeys(uncertainties))[:20],
        tuple(dict.fromkeys(related))[:10],
    )
