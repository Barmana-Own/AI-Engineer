#!/usr/bin/env python3
"""Create missing Stage 01 scaffolds without overwriting existing project files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STAGE = "01-project-analysis-prompt-engineering"
NEXT_STAGE = "02-design-system-ui-architecture"

SOURCE_MAP = """# Stage 01 Source Map — {title}

## Authority Policy

## Source Inventory

| Source ID | Source / Path | Type | Owner | Authority | Freshness | Covers | Limitations |
|---|---|---|---|---|---|---|---|

## Explicit Constraints Extracted

## Known Gaps

## Source Conflicts

## Research Triggers
"""

BRIEF = """# {title} — Stage 01 Project Brief

## 1. Project Identity

## 2. Executive Summary

## 3. Product Objective

## 4. Problem Statement

## 5. Scope
### In Scope
### Out of Scope
### Optional / Future Scope
### Release / MVP Intent

## 6. Target Users and Roles

## 7. Primary User Journeys

## 8. Business Rules

## 9. Core Modules

## 10. External Integrations

## 11. Major Data Domains

## 12. Initial Security and Privacy Concerns

## 13. Constraints

## 14. Assumptions

## 15. Decisions

## 16. Risks

## 17. Open Questions

## 18. Conflicts

## 19. Initial Technical Direction

## 20. Stage 02 Handoff Summary
"""

REQUIREMENTS = """# {title} — Requirements

## Functional Requirements

## Non-Functional Requirements

## Traceability Summary

| Requirement | Actor/System | Journey/Module | Business Rule / Integration | Source refs | Confidence |
|---|---|---|---|---|---|
"""

DOMAIN_MAP = """# Domain & Integration Map — {title}

## Canonical Vocabulary

| Term | Canonical Meaning | Source | Aliases / Avoid |
|---|---|---|---|

## Conceptual Data Domains

## External Integrations

## Dependency Summary

## Stage-Boundary Note
"""

RISK_REGISTER = """# Stage 01 Risk, Assumption & Decision Register — {title}

## Assumptions

## Decisions

## Risks

## Open Questions

## Source Conflicts
"""

TRACEABILITY = """# Stage 01 Traceability Matrix — {title}

## Actor to Journey Coverage

| Actor | Journeys | Coverage note |
|---|---|---|

## Journey to Functional Requirement Coverage

| Journey | Functional Requirements | Exception coverage | Status |
|---|---|---|---|

## Business Rule Enforcement

| Business Rule | Enforced by FR/NFR | Status |
|---|---|---|

## Module Coverage

| Module | FRs | NFRs | Primary roles/journeys |
|---|---|---|---|

## Integration Coverage

| Integration | FRs/NFRs | Failure behavior covered? | Evidence/Assumption | Status |
|---|---|---|---|---|

## Assumption Impact

| Assumption | Affected IDs | Risk if wrong | Validation owner/stage |
|---|---|---|---|

## Risk Impact

| Risk | Affected IDs | Mitigation owner/stage | Status |
|---|---|---|---|

## Evidence Coverage

| Evidence | Claim / affected IDs | Freshness | Confidence |
|---|---|---|---|

## Requirement Source Index

| Requirement | Actor/System | Journey/Module | Rule/Integration | Source | Confidence | Evidence/Assumption |
|---|---|---|---|---|---|---|

## Coverage Summary
"""

READINESS = """# Stage 01 Readiness Review — {title}

## Review Metadata

## Quality Score

| Category | Max | Score | Rationale |
|---|---:|---:|---|
| Product framing and scope | 12 | 0 | Pending review |
| Actors, journeys, business rules | 18 | 0 | Pending review |
| Functional requirements | 20 | 0 | Pending review |
| Non-functional requirements | 12 | 0 | Pending review |
| Domain, integrations, security, privacy | 12 | 0 | Pending review |
| Traceability and evidence | 12 | 0 | Pending review |
| Risk and uncertainty management | 6 | 0 | Pending review |
| Stage 02 handoff quality | 8 | 0 | Pending review |
| **TOTAL** | **100** | **0** | Pending review |

## Hard Gate Checklist

| Gate | Result | Evidence / rationale |
|---|---|---|
| GATE-01 Required artifacts complete | FAIL | Pending analysis |
| GATE-02 Stable IDs unique | FAIL | Pending analysis |
| GATE-03 No dangling references | FAIL | Pending analysis |
| GATE-04 FR contract complete | FAIL | Pending analysis |
| GATE-05 NFR contract complete | FAIL | Pending analysis |
| GATE-06 MUST requirements supported/testable | FAIL | Pending analysis |
| GATE-07 Major journeys covered by FRs | FAIL | Pending analysis |
| GATE-08 Confirmed integrations covered | N/A | Pending analysis |
| GATE-09 Research-derived requirements evidenced | N/A | Pending analysis |
| GATE-10 No blocking open questions | FAIL | Pending analysis |
| GATE-11 No open CRITICAL/HIGH findings | FAIL | Pending analysis |
| GATE-12 Stage 02 handoff ready and boundary-safe | FAIL | Pending analysis |
| GATE-13 State synchronized | FAIL | Pending analysis |
| GATE-14 Machine validator passes | N/A | Run validator after semantic review |
| GATE-15 Strict-pass validator after commit | N/A | Performed after PASS state commit |

## Quality Attribute Review

## Conditional Domain Lens Review

## Adversarial Findings

## Remaining Open Questions

## Stage Boundary Audit

## Final Recommendation
- Recommended status: REPAIR_REQUIRED
- Quality score: 0/100
- Open CRITICAL findings: 0
- Open HIGH findings: 0
- Blocking questions: 0
- Repair summary / blocker: Stage 01 analysis has not yet been completed.
"""

HANDOFF = """# Stage 02 Handoff — {title}

## Authoritative Inputs
- `docs/01-source-map.md`
- `docs/01-project-brief.md`
- `docs/01-requirements.md`
- `docs/01-domain-integration-map.md`
- `docs/01-risk-register.md`
- `docs/01-traceability-matrix.md`
- `project-state.json`
- `docs/01-readiness-review.md`

## Product Definition

## Scope Baseline

## Immutable / High-Confidence Decisions

## Roles Requiring UI Coverage

## Journeys Requiring Experience Coverage

## Permission Intent

## Domain Vocabulary That UI Must Preserve

## Integration-Affecting UX Constraints

## Localization, Accessibility, and Device Constraints

## Design-Affecting Requirements

## Open Non-Blocking Questions

## Known Risks for Stage 02

## Stage 02 Directive

## Stage 02 Prohibitions
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", help="Project workspace root")
    parser.add_argument("--title", required=True, help="Project title")
    parser.add_argument("--goal", default="", help="Optional one-sentence project goal")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    docs = root / "docs"
    created: list[str] = []

    candidates = {
        docs / "01-source-map.md": SOURCE_MAP.format(title=args.title),
        docs / "01-project-brief.md": BRIEF.format(title=args.title),
        docs / "01-requirements.md": REQUIREMENTS.format(title=args.title),
        docs / "01-domain-integration-map.md": DOMAIN_MAP.format(title=args.title),
        docs / "01-risk-register.md": RISK_REGISTER.format(title=args.title),
        docs / "01-traceability-matrix.md": TRACEABILITY.format(title=args.title),
        docs / "01-readiness-review.md": READINESS.format(title=args.title),
        docs / "01-stage-02-handoff.md": HANDOFF.format(title=args.title),
    }
    skipped: list[str] = []
    for path, content in candidates.items():
        if write_if_missing(path, content):
            created.append(str(path.relative_to(root)))
        else:
            skipped.append(str(path.relative_to(root)))

    state_path = root / "project-state.json"
    if not state_path.exists():
        state = {
            "schema_version": "1.0",
            "project": {
                "name": args.title,
                "summary": args.goal or "Stage 01 analysis in progress",
            },
            "workflow": {
                "current_stage": STAGE,
                "next_stage": NEXT_STAGE,
                "stage_records": {
                    STAGE: {
                        "status": "IN_PROGRESS",
                        "artifacts": created.copy(),
                        "quality": {
                            "score": None,
                            "hard_gates_passed": False,
                            "open_critical_findings": 0,
                            "open_high_findings": 0,
                            "blocking_questions": 0,
                            "validator_passed": False,
                        },
                        "updated_at": now_iso(),
                    }
                },
                "completed_stages": [],
            },
            "sources": [],
            "decisions": [],
            "assumptions": [],
            "risks": [],
            "open_questions": [],
            "conflicts": [],
            "evidence": [],
            "review_findings": [],
        }
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append("project-state.json")
    else:
        skipped.append("project-state.json")

    print(json.dumps({"created": created, "skipped_existing": skipped}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
