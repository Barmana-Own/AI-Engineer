#!/usr/bin/env python3
"""Create missing Stage 02 scaffolds without overwriting existing project artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

UI_TEMPLATE = """# Stage 02 UI Architecture - TODO Project Name

## 1. Executive Design Summary
TODO

## 2. Authoritative Inputs
TODO

## 3. UI Coverage Model
TODO

## 4. Role-to-Navigation Architecture
TODO

## 5. UI Flow Catalog
TODO

## 6. Screen Inventory
TODO

## 7. Layout Pattern Catalog
TODO

## 8. Component Usage Map
TODO

## 9. Interaction State Matrix
TODO

## 10. Responsive Behavior Matrix
TODO

## 11. Accessibility Architecture
TODO

## 12. Localization and RTL Architecture
TODO

## 13. Content and Microcopy Rules
TODO

## 14. Traceability Matrix
TODO

## 15. Assumptions, Open Questions, Risks, and Conflicts
TODO

## 16. Stage 03 Implementation Notes
TODO
"""

DESIGN_TEMPLATE = """# Stage 02 Design System - TODO Project Name

## 1. Design System Intent
TODO

## 2. Material Design Decisions
TODO

## 3. Token Architecture
TODO

## 4. Color System
TODO

## 5. Typography System
TODO

## 6. Spacing and Sizing
TODO

## 7. Radius, Border, Elevation, and Layering
TODO

## 8. Iconography
TODO

## 9. Motion
TODO

## 10. Layout Foundations
TODO

## 11. Component Catalog
TODO

## 12. Form and Validation Patterns
TODO

## 13. Data Display Patterns
TODO

## 14. Overlay Patterns
TODO

## 15. Feedback and Status Patterns
TODO

## 16. Data Visualization
TODO

## 17. Accessibility Rules
TODO

## 18. RTL and Localization Rules
TODO

## 19. Prohibited One-off Patterns
TODO
"""

HANDOFF_TEMPLATE = """# Stage 03 Handoff - TODO Project Name

## Authoritative Inputs
TODO

## Product and UI Scope
TODO

## Immutable / High-Confidence Decisions
TODO

## Route and Screen Obligations
TODO

## Navigation and Layout Contracts
TODO

## Component Contracts
TODO

## Design Token Source of Truth
TODO

## State and Error Obligations
TODO

## Responsive Obligations
TODO

## Accessibility Obligations
TODO

## Localization / RTL Obligations
TODO

## Traceability and Acceptance
TODO

## Open Non-Blocking Questions and Reversible Assumptions
TODO

## Stage 03 Prohibitions
TODO

## Stage 03 Start Condition
TODO
"""

TOKENS = {
    "schema_version": "1.0",
    "meta": {
        "name": "TODO Project design tokens",
        "direction_support": ["ltr"],
    },
    "primitive": {},
    "semantic": {
        "color": {},
        "typography": {},
        "space": {},
        "radius": {},
        "motion": {},
        "breakpoint": {},
    },
    "component": {},
}


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    docs = root / "docs"
    design = root / "design"
    docs.mkdir(parents=True, exist_ok=True)
    design.mkdir(parents=True, exist_ok=True)

    created = []
    targets = [
        (docs / "02-ui-architecture.md", UI_TEMPLATE),
        (docs / "02-design-system.md", DESIGN_TEMPLATE),
        (docs / "02-stage-03-handoff.md", HANDOFF_TEMPLATE),
        (design / "tokens.json", json.dumps(TOKENS, ensure_ascii=False, indent=2) + "\n"),
    ]

    for path, content in targets:
        if write_if_missing(path, content):
            created.append(str(path.relative_to(root)))

    print(json.dumps({"created": created, "workspace": str(root)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
