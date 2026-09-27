#!/usr/bin/env python3
"""Validate Stage 02 artifacts using deterministic structural and traceability checks."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGE = "02-design-system-ui-architecture"
PREVIOUS_STAGE = "01-project-analysis-prompt-engineering"
NEXT_STAGE = "03-frontend-architecture"

REQUIRED_FILES = [
    "docs/02-ui-architecture.md",
    "docs/02-design-system.md",
    "docs/02-stage-03-handoff.md",
    "design/tokens.json",
    "project-state.json",
]

UI_SECTIONS = [
    "Authoritative Inputs",
    "Role-to-Navigation Architecture",
    "UI Flow Catalog",
    "Screen Inventory",
    "Layout Pattern Catalog",
    "Interaction State Matrix",
    "Responsive Behavior Matrix",
    "Accessibility Architecture",
    "Traceability Matrix",
]

DESIGN_SECTIONS = [
    "Design System Intent",
    "Token Architecture",
    "Color System",
    "Typography System",
    "Component Catalog",
    "Form and Validation Patterns",
    "Accessibility Rules",
]

HANDOFF_SECTIONS = [
    "Authoritative Inputs",
    "Route and Screen Obligations",
    "Navigation and Layout Contracts",
    "Component Contracts",
    "Design Token Source of Truth",
    "State and Error Obligations",
    "Responsive Obligations",
    "Accessibility Obligations",
    "Traceability and Acceptance",
    "Stage 03 Prohibitions",
]

STAGE02_PREFIXES = ("NAV", "FLW", "SCR", "LAY", "CMP", "UXR", "DSD")
STAGE01_PREFIXES = ("ROLE", "JRN", "BR", "FR", "NFR", "INT", "DOM", "DEC", "ASM", "RSK", "Q", "EVD", "CONFLICT")
ID_RE = re.compile(r"\b(" + "|".join(STAGE02_PREFIXES + STAGE01_PREFIXES) + r")-\d{3,}\b")
TOKEN_REF_RE = re.compile(r"^\{([A-Za-z0-9_.-]+)\}$")
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME)\b|\[Project Name\]", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def has_heading(text: str, heading: str) -> bool:
    pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(heading) + r".*$", re.IGNORECASE | re.MULTILINE)
    return bool(pattern.search(text))


def extract_ids(text: str, prefixes: tuple[str, ...] | None = None) -> set[str]:
    ids = set(ID_RE.findall(text))
    if prefixes is None:
        return ids
    allowed = set(prefixes)
    return {value for value in ids if value.split("-", 1)[0] in allowed}


def get_path(root: Any, path: str) -> Any:
    current = root
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def walk_values(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            yield from walk_values(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{path}[{index}]"
            yield from walk_values(item, child)
    else:
        yield path, value


def token_reference_errors(tokens: dict) -> list[str]:
    errors: list[str] = []
    refs: dict[str, str] = {}
    for path, value in walk_values(tokens):
        if isinstance(value, str):
            match = TOKEN_REF_RE.match(value.strip())
            if match:
                target = match.group(1)
                refs[path] = target
                try:
                    get_path(tokens, target)
                except KeyError:
                    errors.append(f"Missing token reference target: {path} -> {target}")

    for start in refs:
        seen: set[str] = set()
        current = start
        while current in refs:
            if current in seen:
                errors.append(f"Circular token reference detected from {start}")
                break
            seen.add(current)
            current = refs[current]
    return sorted(set(errors))


def completed_stage_count(completed: list, stage: str) -> int:
    count = 0
    for item in completed:
        value = item.get("stage") if isinstance(item, dict) else item
        if value == stage:
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    parser.add_argument("--output", default="docs/02-stage02-validation.json")
    parser.add_argument("--strict-pass", action="store_true")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    issues: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}

    def add(severity: str, code: str, message: str, artifact: str | None = None) -> None:
        item: dict[str, Any] = {"severity": severity, "code": code, "message": message}
        if artifact:
            item["artifact"] = artifact
        issues.append(item)

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            add("ERROR", "MISSING_FILE", f"Required artifact is missing: {rel}", rel)

    texts: dict[str, str] = {}
    for rel in REQUIRED_FILES:
        path = root / rel
        if path.exists() and path.suffix.lower() == ".md":
            texts[rel] = read_text(path)

    section_contracts = {
        "docs/02-ui-architecture.md": UI_SECTIONS,
        "docs/02-design-system.md": DESIGN_SECTIONS,
        "docs/02-stage-03-handoff.md": HANDOFF_SECTIONS,
    }
    for rel, headings in section_contracts.items():
        text = texts.get(rel)
        if text is None:
            continue
        for heading in headings:
            if not has_heading(text, heading):
                add("ERROR", "MISSING_SECTION", f"Required section not found: {heading}", rel)
        if PLACEHOLDER_RE.search(text):
            add("WARNING", "PLACEHOLDER_TEXT", "Document still contains TODO/TBD/FIXME or template placeholder text.", rel)

    ui_text = texts.get("docs/02-ui-architecture.md", "")
    design_text = texts.get("docs/02-design-system.md", "")
    handoff_text = texts.get("docs/02-stage-03-handoff.md", "")
    combined = "\n".join([ui_text, design_text, handoff_text])

    stage02_ids = extract_ids(combined, STAGE02_PREFIXES)
    by_prefix = Counter(value.split("-", 1)[0] for value in stage02_ids)
    metrics["stage02_id_counts"] = dict(sorted(by_prefix.items()))

    for prefix in ("NAV", "FLW", "SCR", "LAY", "CMP"):
        if by_prefix.get(prefix, 0) == 0:
            add("ERROR", "MISSING_ID_FAMILY", f"No {prefix}-### identifiers found in Stage 02 artifacts.")
    if by_prefix.get("DSD", 0) == 0:
        add("WARNING", "NO_DESIGN_DECISIONS", "No DSD-### material design-system decisions were found.")

    ui_id_counts = Counter(extract_ids(ui_text, STAGE02_PREFIXES))
    for value, count in sorted(ui_id_counts.items()):
        prefix = value.split("-", 1)[0]
        if prefix in {"FLW", "SCR", "LAY"} and count < 1:
            add("WARNING", "LOW_REFERENCE_COUNT", f"Identifier {value} has weak linkage in UI architecture.")

    screen_ids = {v for v in extract_ids(ui_text, ("SCR",))}
    missing_handoff_screens = sorted(v for v in screen_ids if v not in handoff_text)
    if missing_handoff_screens:
        add(
            "ERROR",
            "HANDOFF_SCREEN_GAP",
            "Stage 03 handoff does not reference all screen IDs: " + ", ".join(missing_handoff_screens),
            "docs/02-stage-03-handoff.md",
        )

    component_ids = {v for v in extract_ids(design_text, ("CMP",))}
    orphan_components = sorted(v for v in component_ids if v not in ui_text and v not in handoff_text)
    if orphan_components:
        add(
            "WARNING",
            "ORPHAN_COMPONENT",
            "Component IDs appear only in the design-system document and are not mapped to UI/handoff: " + ", ".join(orphan_components),
            "docs/02-design-system.md",
        )

    stage1_handoff_path = root / "docs/01-stage-02-handoff.md"
    if stage1_handoff_path.exists():
        stage1_handoff = read_text(stage1_handoff_path)
        handoff_ids = extract_ids(stage1_handoff, STAGE01_PREFIXES)
        metrics["stage01_handoff_ids"] = len(handoff_ids)
        missing_role_journey = sorted(
            value for value in handoff_ids
            if value.split("-", 1)[0] in {"ROLE", "JRN"} and value not in combined
        )
        if missing_role_journey:
            add(
                "ERROR",
                "PRIMARY_TRACEABILITY_GAP",
                "Stage 01 role/journey IDs from the handoff are missing from Stage 02 artifacts: " + ", ".join(missing_role_journey),
            )
        missing_design_affecting = sorted(
            value for value in handoff_ids
            if value.split("-", 1)[0] in {"FR", "NFR", "BR", "INT", "ASM", "Q", "DEC"} and value not in combined
        )
        if missing_design_affecting:
            add(
                "WARNING",
                "TRACEABILITY_GAP",
                "Some Stage 01 handoff IDs are not referenced in Stage 02 artifacts: " + ", ".join(missing_design_affecting),
            )
    else:
        add("WARNING", "NO_STAGE1_HANDOFF", "docs/01-stage-02-handoff.md is missing; verify equivalent Stage 01 inputs were intentionally used.")

    token_path = root / "design/tokens.json"
    if token_path.exists():
        try:
            tokens = load_json(token_path)
        except Exception as exc:
            add("ERROR", "TOKENS_JSON", f"design/tokens.json is not valid JSON: {exc}", "design/tokens.json")
            tokens = None
        if isinstance(tokens, dict):
            if tokens.get("schema_version") != "1.0":
                add("ERROR", "TOKEN_SCHEMA_VERSION", "design/tokens.json must use schema_version 1.0.", "design/tokens.json")
            for key in ("meta", "primitive", "semantic"):
                if not isinstance(tokens.get(key), dict):
                    add("ERROR", "TOKEN_TOP_LEVEL", f"Token top-level key must be an object: {key}", "design/tokens.json")
            semantic = tokens.get("semantic") if isinstance(tokens.get("semantic"), dict) else {}
            for group in ("color", "typography", "space", "radius", "motion", "breakpoint"):
                value = semantic.get(group)
                if not isinstance(value, dict):
                    add("ERROR", "TOKEN_GROUP", f"Missing semantic token group: {group}", "design/tokens.json")
                elif not value:
                    add("ERROR", "EMPTY_TOKEN_GROUP", f"Semantic token group is empty: {group}", "design/tokens.json")
            meta = tokens.get("meta") if isinstance(tokens.get("meta"), dict) else {}
            if not isinstance(meta.get("name"), str) or not meta.get("name", "").strip():
                add("ERROR", "TOKEN_META", "Token meta.name must be a non-empty string.", "design/tokens.json")
            if PLACEHOLDER_RE.search(json.dumps(tokens, ensure_ascii=False)):
                add("ERROR", "TOKEN_PLACEHOLDER", "Token file still contains TODO/TBD/FIXME placeholder values.", "design/tokens.json")
            for message in token_reference_errors(tokens):
                add("ERROR", "TOKEN_REFERENCE", message, "design/tokens.json")

    state_path = root / "project-state.json"
    if state_path.exists():
        try:
            state = load_json(state_path)
        except Exception as exc:
            add("ERROR", "STATE_JSON", f"project-state.json is not valid JSON: {exc}", "project-state.json")
            state = None
        if isinstance(state, dict):
            if state.get("schema_version") != "1.0":
                add("ERROR", "STATE_SCHEMA_VERSION", "project-state.json schema_version must be 1.0.", "project-state.json")
            workflow = state.get("workflow")
            if not isinstance(workflow, dict):
                add("ERROR", "STATE_WORKFLOW", "project-state.json workflow must be an object.", "project-state.json")
            else:
                records = workflow.get("stage_records")
                completed = workflow.get("completed_stages")
                if not isinstance(records, dict):
                    add("ERROR", "STATE_RECORDS", "workflow.stage_records must be an object.", "project-state.json")
                    records = {}
                if not isinstance(completed, list):
                    add("ERROR", "STATE_COMPLETED", "workflow.completed_stages must be an array.", "project-state.json")
                    completed = []
                stage1 = records.get(PREVIOUS_STAGE) if isinstance(records, dict) else None
                if isinstance(stage1, dict) and stage1.get("status") != "PASS":
                    add("ERROR", "STAGE1_NOT_PASS", "Stage 01 is recorded but is not PASS.", "project-state.json")
                elif not isinstance(stage1, dict):
                    add("WARNING", "STAGE1_RECORD_MISSING", "Stage 01 workflow record is missing; verify equivalent Stage 01 completion evidence.", "project-state.json")

                if args.strict_pass:
                    stage2 = records.get(STAGE) if isinstance(records, dict) else None
                    if not isinstance(stage2, dict) or stage2.get("status") != "PASS":
                        add("ERROR", "STRICT_STAGE_STATUS", "Strict PASS requires Stage 02 stage record status PASS.", "project-state.json")
                    if workflow.get("current_stage") != NEXT_STAGE or workflow.get("next_stage") != NEXT_STAGE:
                        add("ERROR", "STRICT_TRANSITION", f"Strict PASS requires current_stage and next_stage to be {NEXT_STAGE}.", "project-state.json")
                    count = completed_stage_count(completed, STAGE)
                    if count != 1:
                        add("ERROR", "STRICT_COMPLETED_COUNT", f"Strict PASS requires Stage 02 exactly once in completed_stages; found {count}.", "project-state.json")

    for required in (
        "docs/02-ui-architecture.md",
        "docs/02-design-system.md",
        "design/tokens.json",
        "project-state.json",
    ):
        if required not in handoff_text and handoff_text:
            add("WARNING", "HANDOFF_SOURCE_REFERENCE", f"Stage 03 handoff does not explicitly reference {required}.", "docs/02-stage-03-handoff.md")

    errors = sum(1 for item in issues if item["severity"] == "ERROR")
    warnings = sum(1 for item in issues if item["severity"] == "WARNING")
    report = {
        "stage": STAGE,
        "validated_at": utc_now(),
        "strict_pass": args.strict_pass,
        "result": "PASS" if errors == 0 else "FAIL",
        "counts": {"errors": errors, "warnings": warnings, "issues": len(issues)},
        "metrics": metrics,
        "issues": issues,
        "note": "Machine validation does not replace the semantic quality gate defined by the Stage 02 skill.",
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
