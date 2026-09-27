#!/usr/bin/env python3
"""Production-grade structural and coverage validator for Stage 01 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

STAGE = "01-project-analysis-prompt-engineering"
NEXT_STAGE = "02-design-system-ui-architecture"

REQUIRED_ARTIFACTS = [
    "docs/01-source-map.md",
    "docs/01-project-brief.md",
    "docs/01-requirements.md",
    "docs/01-domain-integration-map.md",
    "docs/01-risk-register.md",
    "docs/01-traceability-matrix.md",
    "docs/01-readiness-review.md",
    "docs/01-stage-02-handoff.md",
]

SECTION_REQUIREMENTS = {
    "docs/01-source-map.md": [
        "Authority Policy", "Source Inventory", "Explicit Constraints Extracted", "Known Gaps",
        "Source Conflicts", "Research Triggers",
    ],
    "docs/01-requirements.md": ["Functional Requirements", "Non-Functional Requirements", "Traceability Summary"],
    "docs/01-project-brief.md": [
        "Project Identity", "Executive Summary", "Product Objective", "Problem Statement", "Scope",
        "In Scope", "Out of Scope", "Optional / Future Scope", "Release / MVP Intent",
        "Target Users and Roles", "Primary User Journeys", "Business Rules", "Core Modules",
        "External Integrations", "Major Data Domains", "Initial Security and Privacy Concerns",
        "Constraints", "Assumptions", "Decisions", "Risks", "Open Questions", "Conflicts",
        "Initial Technical Direction", "Stage 02 Handoff Summary",
    ],
    "docs/01-domain-integration-map.md": [
        "Canonical Vocabulary", "Conceptual Data Domains", "External Integrations", "Dependency Summary",
        "Stage-Boundary Note",
    ],
    "docs/01-risk-register.md": ["Assumptions", "Decisions", "Risks", "Open Questions", "Source Conflicts"],
    "docs/01-traceability-matrix.md": [
        "Actor to Journey Coverage", "Journey to Functional Requirement Coverage", "Business Rule Enforcement",
        "Module Coverage", "Integration Coverage", "Assumption Impact", "Risk Impact", "Evidence Coverage",
        "Requirement Source Index", "Coverage Summary",
    ],
    "docs/01-readiness-review.md": [
        "Review Metadata", "Quality Score", "Hard Gate Checklist", "Quality Attribute Review",
        "Conditional Domain Lens Review", "Adversarial Findings", "Remaining Open Questions",
        "Stage Boundary Audit", "Final Recommendation",
    ],
    "docs/01-stage-02-handoff.md": [
        "Authoritative Inputs", "Product Definition", "Scope Baseline", "Immutable / High-Confidence Decisions",
        "Roles Requiring UI Coverage", "Journeys Requiring Experience Coverage", "Permission Intent",
        "Domain Vocabulary That UI Must Preserve", "Integration-Affecting UX Constraints",
        "Localization, Accessibility, and Device Constraints", "Design-Affecting Requirements",
        "Open Non-Blocking Questions", "Known Risks for Stage 02", "Stage 02 Directive", "Stage 02 Prohibitions",
    ],
}

PRIORITIES = {"MUST", "SHOULD", "COULD"}
SOURCES = {"USER", "EXISTING_ARTIFACT", "RESEARCH", "ASSUMPTION", "MIXED"}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
INT_CLASSIFICATIONS = {"CONFIRMED", "ASSUMED", "OPTIONAL"}
FINDING_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
FINDING_STATUSES = {"OPEN", "RESOLVED", "DEFERRED"}
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD|FIXME|PLACEHOLDER|PENDING\s+REVIEW)\b", re.IGNORECASE)
ALL_ID_RE = re.compile(r"\b(?:SRC|ROLE|JRN|BR|MOD|INT|DOM|FR|NFR|ASM|DEC|RSK|Q|EVD|CONFLICT|FINDING)-\d{3}\b")
VAGUE_TERMS = ["user-friendly", "easy to use", "fast", "secure", "seamless", "robust", "flexible", "works correctly", "handle errors"]

READINESS_CATEGORIES = {
    "Product framing and scope": 12,
    "Actors, journeys, business rules": 18,
    "Functional requirements": 20,
    "Non-functional requirements": 12,
    "Domain, integrations, security, privacy": 12,
    "Traceability and evidence": 12,
    "Risk and uncertainty management": 6,
    "Stage 02 handoff quality": 8,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def input_hashes(root: Path) -> dict[str, str]:
    paths = list(REQUIRED_ARTIFACTS) + ["project-state.json"]
    if (root / "docs/01-research-evidence.md").exists():
        paths.append("docs/01-research-evidence.md")
    result: dict[str, str] = {}
    for rel in paths:
        path = root / rel
        if path.exists() and path.is_file():
            result[rel] = sha256_file(path)
    return result


def read_text(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"Missing required artifact: {path.relative_to(path.parents[1]) if len(path.parents) > 1 else path.name}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"Cannot read {path}: {exc}")
        return ""


def normalized_heading(line: str) -> str | None:
    m = re.match(r"^#{1,6}\s+(?:\d+\.\s*)?(.*?)(?:\s+#*)?$", line.strip())
    return m.group(1).strip() if m else None


def headings(text: str) -> list[str]:
    return [h for line in text.splitlines() if (h := normalized_heading(line))]


def section_body(text: str, heading_name: str) -> str | None:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        h = normalized_heading(line)
        if h != heading_name:
            continue
        level = len(line) - len(line.lstrip("#"))
        body: list[str] = []
        for later in lines[i + 1:]:
            stripped = later.strip()
            if stripped.startswith("#"):
                later_level = len(later) - len(later.lstrip("#"))
                if later_level <= level:
                    break
            body.append(later)
        return "\n".join(body).strip()
    return None


def require_sections(text: str, names: Iterable[str], label: str, errors: list[str]) -> None:
    found = set(headings(text))
    for name in names:
        if name not in found:
            errors.append(f"{label}: missing section heading '{name}'")
            continue
        body = section_body(text, name)
        if body is not None and not body.strip():
            errors.append(f"{label}: section '{name}' is empty; write content or an explicit None/Not applicable statement")


def parse_blocks(text: str, prefix: str) -> list[tuple[str, str]]:
    heading_pattern = re.compile(r"^###\s+.*$", re.MULTILINE)
    hs = list(heading_pattern.finditer(text))
    result: list[tuple[str, str]] = []
    for i, h in enumerate(hs):
        id_match = re.match(rf"^###\s+({re.escape(prefix)}-\d{{3}})\b", h.group(0))
        if not id_match:
            continue
        end = hs[i + 1].start() if i + 1 < len(hs) else len(text)
        result.append((id_match.group(1), text[h.start():end]))
    return result


def field_value(block: str, field: str) -> str | None:
    m = re.search(rf"^-\s+{re.escape(field)}:\s*(.*)$", block, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


def require_fields(req_id: str, block: str, fields: list[str], errors: list[str]) -> None:
    for field in fields:
        if field_value(block, field) is None:
            errors.append(f"{req_id}: missing field '{field}'")


def collect_definitions(texts: dict[str, str], evidence_text: str) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    defs: dict[str, set[str]] = {k: set() for k in [
        "SRC", "ROLE", "JRN", "BR", "MOD", "INT", "DOM", "FR", "NFR", "ASM", "DEC", "RSK", "Q", "EVD", "CONFLICT", "FINDING"
    ]}
    occurrences: dict[str, list[str]] = {k: [] for k in defs}

    def add(prefix: str, value: str, where: str) -> None:
        defs[prefix].add(value)
        occurrences[prefix].append(f"{value}@{where}")

    for m in re.finditer(r"^\|\s*(SRC-\d{3})\s*\|", texts.get("docs/01-source-map.md", ""), re.MULTILINE):
        add("SRC", m.group(1), "source-map")

    mapping = {
        "docs/01-project-brief.md": ["ROLE", "JRN", "BR", "MOD"],
        "docs/01-domain-integration-map.md": ["DOM", "INT"],
        "docs/01-risk-register.md": ["ASM", "DEC", "RSK", "Q", "CONFLICT"],
        "docs/01-requirements.md": ["FR", "NFR"],
        "docs/01-readiness-review.md": ["FINDING"],
    }
    for path, prefixes in mapping.items():
        text = texts.get(path, "")
        for prefix in prefixes:
            for item_id, _ in parse_blocks(text, prefix):
                add(prefix, item_id, path)
    for item_id, _ in parse_blocks(evidence_text, "EVD"):
        add("EVD", item_id, "research-evidence")
    return defs, occurrences


def validate_definition_uniqueness(occurrences: dict[str, list[str]], errors: list[str]) -> None:
    for prefix, items in occurrences.items():
        ids = [x.split("@", 1)[0] for x in items]
        for item_id, count in Counter(ids).items():
            if count > 1:
                errors.append(f"Duplicate canonical definition for {item_id}")


def validate_source_map(text: str, defs: dict[str, set[str]], errors: list[str], warnings: list[str]) -> None:
    if not defs["SRC"]:
        errors.append("Source map: define at least one SRC-* source")
    rows = [line for line in text.splitlines() if re.match(r"^\|\s*SRC-\d{3}\s*\|", line)]
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 8:
            errors.append(f"Source map: malformed source row: {row[:100]}")
            continue
        if any(not c for c in cells[:7]):
            errors.append(f"Source map: source row has empty required cell: {cells[0]}")
    if "ASSUMPTION_ONLY" in text and not re.search(r"\bASM-\d{3}\b", text):
        warnings.append("Source map: ASSUMPTION_ONLY appears without an ASM-* reference")


def validate_brief(text: str, defs: dict[str, set[str]], errors: list[str], warnings: list[str]) -> None:
    minimums = {"ROLE": 1, "JRN": 1, "BR": 1, "MOD": 1}
    for prefix, minimum in minimums.items():
        if len(defs[prefix]) < minimum:
            errors.append(f"Project brief: expected at least {minimum} {prefix}-* definition(s)")

    for item_id, block in parse_blocks(text, "ROLE"):
        require_fields(item_id, block, ["Responsibility", "Goals", "Core actions", "Data / permission intent", "Important interactions", "Related journeys", "Source refs", "Confidence"], errors)
        confidence = field_value(block, "Confidence")
        if confidence and confidence.upper() not in CONFIDENCE:
            errors.append(f"{item_id}: invalid Confidence '{confidence}'")

    for item_id, block in parse_blocks(text, "JRN"):
        require_fields(item_id, block, ["Trigger", "Initiating actor", "Preconditions", "Alternate paths", "Exception / failure paths", "Outcome / resulting state", "Related roles", "Related rules", "Related modules", "Related integrations", "Source refs", "Confidence"], errors)
        if not re.search(r"^-\s+Normal path:\s*$", block, re.MULTILINE | re.IGNORECASE):
            errors.append(f"{item_id}: missing multiline field 'Normal path'")
        elif not re.search(r"^\s+\d+\.\s+\S", block, re.MULTILINE):
            errors.append(f"{item_id}: Normal path must contain numbered steps")

    for item_id, block in parse_blocks(text, "BR"):
        require_fields(item_id, block, ["Rule", "Applies when", "Exception", "Affects", "Source refs", "Confidence"], errors)

    for item_id, block in parse_blocks(text, "MOD"):
        require_fields(item_id, block, ["Responsibility", "Primary roles", "Journeys supported", "Data domains", "Integrations", "Notes"], errors)

    for term in VAGUE_TERMS:
        if term in text.lower():
            warnings.append(f"Project brief: contains potentially vague term '{term}'")


def validate_domain_map(text: str, defs: dict[str, set[str]], errors: list[str], warnings: list[str]) -> dict[str, str]:
    if not defs["DOM"]:
        errors.append("Domain map: define at least one DOM-* conceptual data domain")

    for item_id, block in parse_blocks(text, "DOM"):
        require_fields(item_id, block, ["Definition", "Business ownership / related roles", "Lifecycle summary", "Sensitive data", "Related domains", "Authoritative source/system", "Related journeys", "Source", "Confidence"], errors)
        source = (field_value(block, "Source") or "").upper()
        confidence = (field_value(block, "Confidence") or "").upper()
        if source and source not in SOURCES:
            errors.append(f"{item_id}: invalid Source '{source}'")
        if confidence and confidence not in CONFIDENCE:
            errors.append(f"{item_id}: invalid Confidence '{confidence}'")

    int_classes: dict[str, str] = {}
    for item_id, block in parse_blocks(text, "INT"):
        require_fields(item_id, block, ["Purpose", "Classification", "Direction", "Interaction trigger/pattern", "Conceptual data exchanged", "Dependency / availability implication", "Failure / retry / idempotency concern", "Authentication / trust dependency", "Evidence / assumption", "Related requirements", "Source", "Confidence"], errors)
        cls = (field_value(block, "Classification") or "").upper()
        if cls not in INT_CLASSIFICATIONS:
            errors.append(f"{item_id}: invalid Classification '{cls}'")
        else:
            int_classes[item_id] = cls
        if cls == "CONFIRMED":
            related = field_value(block, "Related requirements") or ""
            if not re.search(r"\b(?:FR|NFR)-\d{3}\b", related):
                errors.append(f"{item_id}: CONFIRMED integration must reference at least one FR-* or NFR-*")
    return int_classes


def validate_risk_register(text: str, defs: dict[str, set[str]], errors: list[str], warnings: list[str]) -> None:
    contracts = {
        "ASM": ["Statement", "Impact", "Confidence", "Status", "Temporary / reversible", "Affected IDs", "Validation owner / stage", "Source"],
        "DEC": ["Statement", "Rationale", "Source", "Confidence", "Evidence IDs", "Affected IDs"],
        "RSK": ["Category", "Statement", "Likelihood", "Impact", "Trigger / early signal", "Mitigation direction", "Contingency / fallback", "Owner / responsible stage", "Affected IDs", "Status"],
        "Q": ["Question", "Blocking", "Why it matters", "Temporary assumption", "Owner", "Affected IDs", "Status"],
        "CONFLICT": ["Position A", "Source A", "Position B", "Source B", "Impact", "Resolution", "Status", "Blocking", "Affected IDs"],
    }
    for prefix, fields in contracts.items():
        for item_id, block in parse_blocks(text, prefix):
            require_fields(item_id, block, fields, errors)
            if prefix == "Q":
                val = (field_value(block, "Blocking") or "").lower()
                if val not in {"true", "false"}:
                    errors.append(f"{item_id}: Blocking must be true or false")
            if prefix == "CONFLICT":
                val = (field_value(block, "Blocking") or "").lower()
                if val not in {"true", "false"}:
                    errors.append(f"{item_id}: Blocking must be true or false")
            if prefix == "RSK":
                impact = (field_value(block, "Impact") or "").upper()
                likelihood = (field_value(block, "Likelihood") or "").upper()
                if impact not in CONFIDENCE or likelihood not in CONFIDENCE:
                    errors.append(f"{item_id}: Likelihood/Impact must be HIGH, MEDIUM, or LOW")
                if impact == "HIGH" and not (field_value(block, "Mitigation direction") or "").strip():
                    errors.append(f"{item_id}: HIGH-impact risk requires mitigation direction")

    if not defs["RSK"]:
        warnings.append("Risk register: no RSK-* records defined; verify that the project genuinely has no material Stage 01 risk")


def acceptance_bullets(block: str) -> list[str]:
    marker = re.search(r"^-\s+Acceptance criteria:\s*$", block, re.MULTILINE | re.IGNORECASE)
    if not marker:
        return []
    after = block[marker.end():]
    next_field = re.search(r"^-[ ]+(?:Related|Dependencies|Source|Source refs|Confidence|Evidence|Assumptions|Notes):", after, re.MULTILINE | re.IGNORECASE)
    region = after[:next_field.start()] if next_field else after
    return [m.group(1).strip() for m in re.finditer(r"^\s{2,}-\s+(.+)$", region, re.MULTILINE)]


def source_tokens(value: str) -> set[str]:
    return {s.strip().upper() for s in re.split(r"[+,/]", value) if s.strip()}


def validate_requirements(text: str, defs: dict[str, set[str]], errors: list[str], warnings: list[str]) -> dict:
    frs = parse_blocks(text, "FR")
    nfrs = parse_blocks(text, "NFR")
    if not frs:
        errors.append("Requirements: no FR-* functional requirements found")
    if not nfrs:
        errors.append("Requirements: no NFR-* non-functional requirements found")

    research_used = False
    assumption_used = False
    for kind, blocks in [("FR", frs), ("NFR", nfrs)]:
        for req_id, block in blocks:
            common = ["Priority", "Related", "Dependencies", "Source", "Source refs", "Confidence", "Evidence", "Assumptions", "Notes"]
            if kind == "FR":
                require_fields(req_id, block, ["Actor", "Requirement"] + common, errors)
                criteria = acceptance_bullets(block)
                if not criteria:
                    errors.append(f"{req_id}: missing at least one acceptance criterion bullet")
                for criterion in criteria:
                    low = criterion.lower()
                    if any(term in low for term in VAGUE_TERMS) and not re.search(r"\d", criterion):
                        warnings.append(f"{req_id}: potentially vague acceptance criterion: {criterion[:100]}")
                actor = field_value(block, "Actor") or ""
                if actor != "SYSTEM" and not re.search(r"\bROLE-\d{3}\b", actor):
                    errors.append(f"{req_id}: Actor must be SYSTEM or reference ROLE-*")
                related = field_value(block, "Related") or ""
                if not re.search(r"\b(?:JRN|MOD)-\d{3}\b", related):
                    errors.append(f"{req_id}: Related must reference at least one JRN-* or MOD-*")
                requirement = field_value(block, "Requirement") or ""
                if len(requirement) < 20:
                    warnings.append(f"{req_id}: requirement statement may be too short to be precise")
            else:
                require_fields(req_id, block, ["Category", "Target", "Verification"] + common, errors)
                target = field_value(block, "Target") or ""
                verification = field_value(block, "Verification") or ""
                if len(target) < 10:
                    errors.append(f"{req_id}: Target is too vague/short")
                if len(verification) < 10:
                    errors.append(f"{req_id}: Verification is too vague/short")

            priority = (field_value(block, "Priority") or "").upper()
            if priority not in PRIORITIES:
                errors.append(f"{req_id}: invalid Priority '{priority}'")
            source = field_value(block, "Source") or ""
            tokens = source_tokens(source)
            if not tokens or not tokens.issubset(SOURCES):
                errors.append(f"{req_id}: invalid Source '{source}'")
            confidence = (field_value(block, "Confidence") or "").upper()
            if confidence not in CONFIDENCE:
                errors.append(f"{req_id}: invalid Confidence '{confidence}'")

            source_refs = field_value(block, "Source refs") or ""
            if source_refs.lower() in {"", "none", "n/a", "not applicable"}:
                errors.append(f"{req_id}: Source refs must identify supporting SRC/DEC/ASM/EVD IDs")

            evidence = field_value(block, "Evidence") or ""
            assumptions = field_value(block, "Assumptions") or ""
            if "RESEARCH" in tokens:
                research_used = True
                if not re.search(r"\bEVD-\d{3}\b", evidence + " " + source_refs):
                    errors.append(f"{req_id}: RESEARCH source requires EVD-* in Evidence or Source refs")
            if "ASSUMPTION" in tokens:
                assumption_used = True
                if not re.search(r"\bASM-\d{3}\b", assumptions + " " + source_refs):
                    errors.append(f"{req_id}: ASSUMPTION source requires ASM-* in Assumptions or Source refs")

            if priority == "MUST" and confidence == "LOW" and not re.search(r"\b(?:DEC|ASM|EVD|SRC)-\d{3}\b", source_refs):
                errors.append(f"{req_id}: LOW-confidence MUST requirement needs an explicit supporting/temporary source reference")

            if PLACEHOLDER_RE.search(block):
                errors.append(f"{req_id}: contains unresolved placeholder language")

    return {
        "fr_count": len(frs),
        "nfr_count": len(nfrs),
        "research_used": research_used,
        "assumption_used": assumption_used,
        "fr_blocks": frs,
        "nfr_blocks": nfrs,
    }


def validate_research(root: Path, evidence_text: str, defs: dict[str, set[str]], research_used: bool, state: dict, errors: list[str], warnings: list[str]) -> None:
    path = root / "docs/01-research-evidence.md"
    state_evidence = state.get("evidence", []) if isinstance(state, dict) else []
    if research_used or defs["EVD"] or state_evidence:
        if not path.exists():
            errors.append("Research is referenced but docs/01-research-evidence.md is missing")
            return
        evds = parse_blocks(evidence_text, "EVD")
        if not evds:
            errors.append("Research evidence: no EVD-* blocks found")
        fields = ["Research question", "Claim supported", "Source title", "Publisher / owner", "Source locator", "Checked at", "Version / jurisdiction", "Authority level", "Confidence", "Affects", "Analyst interpretation", "Limitations"]
        for evd_id, block in evds:
            require_fields(evd_id, block, fields, errors)
            checked = field_value(block, "Checked at") or ""
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked):
                errors.append(f"{evd_id}: Checked at must use YYYY-MM-DD")
            affects = field_value(block, "Affects") or ""
            if not ALL_ID_RE.search(affects):
                errors.append(f"{evd_id}: Affects must reference at least one canonical ID")
    elif path.exists() and evidence_text.strip():
        warnings.append("Research evidence file exists but no requirement/state item appears to rely on research")


def validate_cross_references(texts: dict[str, str], evidence_text: str, defs: dict[str, set[str]], errors: list[str]) -> None:
    known = set().union(*defs.values())
    for path, text in list(texts.items()) + [("docs/01-research-evidence.md", evidence_text)]:
        for ref in sorted(set(ALL_ID_RE.findall(text))):
            if ref not in known:
                errors.append(f"{path}: references undefined ID {ref}")


def validate_coverage(defs: dict[str, set[str]], req_stats: dict, domain_classes: dict[str, str], texts: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    req_text = texts.get("docs/01-requirements.md", "")
    fr_text = "\n".join(block for _, block in req_stats.get("fr_blocks", []))
    all_req_text = req_text

    for jrn in sorted(defs["JRN"]):
        if jrn not in fr_text:
            errors.append(f"Coverage: {jrn} is not referenced by any FR-*")
    for br in sorted(defs["BR"]):
        if br not in all_req_text:
            errors.append(f"Coverage: {br} is not referenced by any FR/NFR")
    for mod in sorted(defs["MOD"]):
        if mod not in all_req_text:
            errors.append(f"Coverage: {mod} is not referenced by any FR/NFR")
    for role in sorted(defs["ROLE"]):
        actor_pattern = re.compile(rf"^-\s+Actor:\s*.*\b{re.escape(role)}\b", re.MULTILINE)
        if not actor_pattern.search(fr_text):
            warnings.append(f"Coverage: {role} is never the Actor of an FR-*; verify it is truly a system role")
    for int_id, cls in sorted(domain_classes.items()):
        if cls == "CONFIRMED" and int_id not in all_req_text:
            errors.append(f"Coverage: confirmed integration {int_id} is not referenced by any FR/NFR")

    trace = texts.get("docs/01-traceability-matrix.md", "")
    must_trace = defs["JRN"] | defs["BR"] | defs["MOD"] | defs["FR"] | defs["NFR"] | {i for i, c in domain_classes.items() if c == "CONFIRMED"}
    for item_id in sorted(must_trace):
        if item_id not in trace:
            errors.append(f"Traceability matrix: missing {item_id}")
    if re.search(r"\b(?:PARTIAL|MISSING|REPAIR_REQUIRED)\b", trace, re.IGNORECASE):
        errors.append("Traceability matrix contains PARTIAL/MISSING/REPAIR_REQUIRED coverage")


def validate_readiness(text: str, strict_pass: bool, errors: list[str], warnings: list[str]) -> dict:
    scores: dict[str, int] = {}
    for category, max_points in READINESS_CATEGORIES.items():
        pattern = rf"^\|\s*{re.escape(category)}\s*\|\s*{max_points}\s*\|\s*(\d+)\s*\|"
        m = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if not m:
            errors.append(f"Readiness review: missing score row '{category}'")
            continue
        score = int(m.group(1))
        if score < 0 or score > max_points:
            errors.append(f"Readiness review: score for '{category}' must be 0..{max_points}")
        scores[category] = score
    computed_total = sum(scores.values()) if len(scores) == len(READINESS_CATEGORIES) else None

    final_score_match = re.search(r"^-\s*Quality score:\s*(\d+)/100\s*$", text, re.MULTILINE | re.IGNORECASE)
    final_score = int(final_score_match.group(1)) if final_score_match else None
    if final_score is None:
        errors.append("Readiness review: Final Recommendation must include '- Quality score: NN/100'")
    elif computed_total is not None and final_score != computed_total:
        errors.append(f"Readiness review: final Quality score {final_score} does not equal category sum {computed_total}")
    if final_score is not None and final_score < 95:
        errors.append(f"Readiness review: quality score {final_score}/100 is below required 95")

    rec = re.search(r"^-\s*Recommended status:\s*(PASS|REPAIR_REQUIRED|BLOCKED)\s*$", text, re.MULTILINE | re.IGNORECASE)
    recommended = rec.group(1).upper() if rec else None
    if recommended != "PASS":
        errors.append("Readiness review: Recommended status must be PASS for validation")

    def final_count(label: str) -> int | None:
        m = re.search(rf"^-\s*{re.escape(label)}:\s*(\d+)\s*$", text, re.MULTILINE | re.IGNORECASE)
        return int(m.group(1)) if m else None

    critical = final_count("Open CRITICAL findings")
    high = final_count("Open HIGH findings")
    blockers = final_count("Blocking questions")
    for label, value in [("Open CRITICAL findings", critical), ("Open HIGH findings", high), ("Blocking questions", blockers)]:
        if value is None:
            errors.append(f"Readiness review: missing final count '{label}'")
        elif value != 0:
            errors.append(f"Readiness review: {label} must be 0, got {value}")

    gate_results: dict[str, str] = {}
    for n in range(1, 16):
        gate = f"GATE-{n:02d}"
        m = re.search(rf"^\|\s*{gate}\b[^|]*\|\s*(PASS|FAIL|N/A)\s*\|", text, re.MULTILINE | re.IGNORECASE)
        if not m:
            errors.append(f"Readiness review: missing hard gate row {gate}")
            continue
        result = m.group(1).upper()
        gate_results[gate] = result
        if n in {1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13} and result != "PASS":
            errors.append(f"Readiness review: {gate} must be PASS")
        if n in {8, 9} and result not in {"PASS", "N/A"}:
            errors.append(f"Readiness review: {gate} must be PASS or N/A")
        if n in {14, 15} and result == "FAIL":
            errors.append(f"Readiness review: {gate} cannot be FAIL")
        if strict_pass and n == 14 and result not in {"PASS", "N/A"}:
            errors.append("Readiness review: GATE-14 invalid during strict pass")

    findings = parse_blocks(text, "FINDING")
    open_critical = 0
    open_high = 0
    for finding_id, block in findings:
        require_fields(finding_id, block, ["Severity", "Status", "Finding", "Affected IDs / artifacts", "Resolution", "Owner if deferred"], errors)
        sev = (field_value(block, "Severity") or "").upper()
        status = (field_value(block, "Status") or "").upper()
        if sev not in FINDING_SEVERITIES:
            errors.append(f"{finding_id}: invalid Severity '{sev}'")
        if status not in FINDING_STATUSES:
            errors.append(f"{finding_id}: invalid Status '{status}'")
        if status == "OPEN" and sev == "CRITICAL":
            open_critical += 1
        if status == "OPEN" and sev == "HIGH":
            open_high += 1
    if critical is not None and open_critical != critical:
        errors.append(f"Readiness review: final CRITICAL count {critical} does not match open FINDING blocks {open_critical}")
    if high is not None and open_high != high:
        errors.append(f"Readiness review: final HIGH count {high} does not match open FINDING blocks {open_high}")

    qa_body = section_body(text, "Quality Attribute Review") or ""
    if len(qa_body.strip()) < 20:
        errors.append("Readiness review: Quality Attribute Review is too thin")
    lens_body = section_body(text, "Conditional Domain Lens Review") or ""
    if len(lens_body.strip()) < 20:
        errors.append("Readiness review: Conditional Domain Lens Review is too thin")
    boundary_body = section_body(text, "Stage Boundary Audit") or ""
    if len(boundary_body.strip()) < 20:
        errors.append("Readiness review: Stage Boundary Audit is too thin")

    return {
        "quality_score": final_score,
        "recommended_status": recommended,
        "open_critical_findings": critical,
        "open_high_findings": high,
        "blocking_questions": blockers,
        "gate_results": gate_results,
    }


def state_ids(records: object) -> set[str]:
    if not isinstance(records, list):
        return set()
    result = set()
    for item in records:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            result.add(item["id"])
    return result


def validate_state(path: Path, defs: dict[str, set[str]], readiness: dict, strict_pass: bool, errors: list[str], warnings: list[str]) -> dict:
    if not path.exists():
        errors.append("Missing required artifact: project-state.json")
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"project-state.json: invalid JSON: {exc}")
        return {}
    if not isinstance(state, dict):
        errors.append("project-state.json: root must be an object")
        return {}
    if state.get("schema_version") != "1.0":
        errors.append("project-state.json: schema_version must be '1.0'")
    project = state.get("project")
    if not isinstance(project, dict) or not str(project.get("name", "")).strip() or not str(project.get("summary", "")).strip():
        errors.append("project-state.json: project.name and project.summary are required")
    elif strict_pass and str(project.get("summary", "")).strip() == "Stage 01 analysis in progress":
        errors.append("project-state.json: replace bootstrap project.summary before strict PASS")

    sync = {
        "sources": "SRC",
        "decisions": "DEC",
        "assumptions": "ASM",
        "risks": "RSK",
        "open_questions": "Q",
        "conflicts": "CONFLICT",
        "evidence": "EVD",
        "review_findings": "FINDING",
    }
    for key, prefix in sync.items():
        if not isinstance(state.get(key), list):
            errors.append(f"project-state.json: {key} must be an array")
            continue
        ids = state_ids(state.get(key))
        missing = defs[prefix] - ids
        if missing:
            errors.append(f"project-state.json: {key} missing canonical IDs: {', '.join(sorted(missing))}")
        stale = ids - defs[prefix]
        if stale:
            warnings.append(f"project-state.json: {key} contains IDs not defined in current canonical docs: {', '.join(sorted(stale))}")

    questions = state.get("open_questions", [])
    blocking_state = [q for q in questions if isinstance(q, dict) and q.get("blocking") is True and str(q.get("status", "OPEN")).upper() != "ANSWERED"]
    if blocking_state:
        errors.append("project-state.json: unresolved blocking open questions prevent PASS")

    workflow = state.get("workflow")
    if not isinstance(workflow, dict):
        errors.append("project-state.json: workflow object is required")
        return state
    records = workflow.get("stage_records")
    record = records.get(STAGE) if isinstance(records, dict) else None
    if not isinstance(record, dict):
        errors.append(f"project-state.json: workflow.stage_records.{STAGE} is required")
        return state
    status = record.get("status")
    if status not in {"IN_PROGRESS", "PASS", "BLOCKED"}:
        errors.append(f"project-state.json: invalid Stage 01 status '{status}'")

    artifacts = record.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append("project-state.json: Stage 01 artifacts must be an array")
        artifacts = []
    missing_artifacts = set(REQUIRED_ARTIFACTS) - set(artifacts)
    if strict_pass and missing_artifacts:
        errors.append("project-state.json: PASS artifact list missing: " + ", ".join(sorted(missing_artifacts)))
    elif missing_artifacts:
        warnings.append("project-state.json: Stage 01 artifact list not yet complete")

    completed = workflow.get("completed_stages", [])
    completed_ids = [(item.get("stage") if isinstance(item, dict) else item) for item in completed] if isinstance(completed, list) else []

    quality = record.get("quality") if isinstance(record.get("quality"), dict) else {}
    if strict_pass:
        if status != "PASS":
            errors.append("project-state.json: strict PASS requires Stage 01 status PASS")
        if workflow.get("current_stage") != NEXT_STAGE or workflow.get("next_stage") != NEXT_STAGE:
            errors.append("project-state.json: strict PASS requires current_stage and next_stage to point to Stage 02")
        if completed_ids.count(STAGE) != 1:
            errors.append("project-state.json: strict PASS requires Stage 01 exactly once in completed_stages")
        expected_score = readiness.get("quality_score")
        if quality.get("score") != expected_score:
            errors.append(f"project-state.json: quality.score {quality.get('score')} does not match readiness score {expected_score}")
        if quality.get("hard_gates_passed") is not True:
            errors.append("project-state.json: strict PASS requires quality.hard_gates_passed=true")
        if quality.get("open_critical_findings") != 0 or quality.get("open_high_findings") != 0:
            errors.append("project-state.json: strict PASS requires zero open CRITICAL/HIGH findings")
        if quality.get("blocking_questions") != 0:
            errors.append("project-state.json: strict PASS requires zero blocking questions")
        if quality.get("validator_passed") is not True:
            errors.append("project-state.json: strict PASS requires quality.validator_passed=true")
    return state


def check_placeholders(texts: dict[str, str], evidence_text: str, errors: list[str]) -> None:
    for path, text in list(texts.items()) + [("docs/01-research-evidence.md", evidence_text)]:
        if text and PLACEHOLDER_RE.search(text):
            errors.append(f"{path}: unresolved placeholder language found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    parser.add_argument("--strict-pass", action="store_true")
    parser.add_argument("--output", help="Optional JSON report path relative to workspace or absolute")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    texts: dict[str, str] = {}
    for rel in REQUIRED_ARTIFACTS:
        texts[rel] = read_text(root / rel, errors)
    evidence_path = root / "docs/01-research-evidence.md"
    evidence_text = evidence_path.read_text(encoding="utf-8") if evidence_path.exists() else ""

    for rel, required_sections in SECTION_REQUIREMENTS.items():
        text = texts.get(rel, "")
        if text:
            require_sections(text, required_sections, rel, errors)

    defs, occurrences = collect_definitions(texts, evidence_text)
    validate_definition_uniqueness(occurrences, errors)
    validate_source_map(texts.get("docs/01-source-map.md", ""), defs, errors, warnings)
    validate_brief(texts.get("docs/01-project-brief.md", ""), defs, errors, warnings)
    domain_classes = validate_domain_map(texts.get("docs/01-domain-integration-map.md", ""), defs, errors, warnings)
    validate_risk_register(texts.get("docs/01-risk-register.md", ""), defs, errors, warnings)
    req_stats = validate_requirements(texts.get("docs/01-requirements.md", ""), defs, errors, warnings)
    readiness = validate_readiness(texts.get("docs/01-readiness-review.md", ""), args.strict_pass, errors, warnings)
    if any(cls == "CONFIRMED" for cls in domain_classes.values()) and readiness.get("gate_results", {}).get("GATE-08") != "PASS":
        errors.append("Readiness review: GATE-08 must be PASS when confirmed integrations exist")
    if req_stats.get("research_used") and readiness.get("gate_results", {}).get("GATE-09") != "PASS":
        errors.append("Readiness review: GATE-09 must be PASS when research-derived requirements exist")

    state = validate_state(root / "project-state.json", defs, readiness, args.strict_pass, errors, warnings)
    validate_research(root, evidence_text, defs, req_stats["research_used"], state, errors, warnings)
    validate_cross_references(texts, evidence_text, defs, errors)
    validate_coverage(defs, req_stats, domain_classes, texts, errors, warnings)
    check_placeholders(texts, evidence_text, errors)

    # Guard against duplicate IDs inside state arrays.
    if isinstance(state, dict):
        for key in ["sources", "decisions", "assumptions", "risks", "open_questions", "conflicts", "evidence", "review_findings"]:
            records = state.get(key, [])
            ids = [x.get("id") for x in records if isinstance(x, dict) and isinstance(x.get("id"), str)] if isinstance(records, list) else []
            dupes = sorted([x for x, count in Counter(ids).items() if count > 1])
            if dupes:
                errors.append(f"project-state.json: duplicate IDs in {key}: {', '.join(dupes)}")

    machine_score = max(0, 100 - (10 * len(errors)) - len(warnings))
    passed = not errors and machine_score >= 95
    report = {
        "validator": "stage01-production-validator-v2",
        "validated_at": utc_now(),
        "strict_pass": args.strict_pass,
        "passed": passed,
        "score": machine_score,
        "readiness_score": readiness.get("quality_score"),
        "stats": {
            "sources": len(defs["SRC"]),
            "roles": len(defs["ROLE"]),
            "journeys": len(defs["JRN"]),
            "business_rules": len(defs["BR"]),
            "modules": len(defs["MOD"]),
            "domains": len(defs["DOM"]),
            "integrations": len(defs["INT"]),
            "functional_requirements": len(defs["FR"]),
            "non_functional_requirements": len(defs["NFR"]),
            "assumptions": len(defs["ASM"]),
            "decisions": len(defs["DEC"]),
            "risks": len(defs["RSK"]),
            "open_questions": len(defs["Q"]),
            "evidence": len(defs["EVD"]),
            "conflicts": len(defs["CONFLICT"]),
            "review_findings": len(defs["FINDING"]),
        },
        "errors": errors,
        "warnings": warnings,
        "input_hashes": input_hashes(root),
    }

    if args.output:
        out = Path(args.output)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
