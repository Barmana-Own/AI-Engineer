# Stage 02 Traceability Contract

## Table of contents

1. Purpose
2. Required mapping directions
3. Coverage rules
4. Orphan rules
5. Assumptions and questions
6. Recommended matrix
7. Validation behavior

## 1. Purpose

Traceability proves that Stage 02 is a design realization of the accepted product definition rather than a separate speculative design exercise.

## 2. Required mapping directions

Maintain enough references to answer both directions:

- Product to UI: which navigation, flows, screens, layouts, components, and UX rules realize a Stage 01 obligation?
- UI to product: which accepted product obligation justifies each significant Stage 02 artifact?

## 3. Coverage rules

At minimum:

- every primary `ROLE-*` must map to relevant `NAV-*` and `SCR-*`;
- every primary `JRN-*` must map to one or more `FLW-*` and `SCR-*`;
- every design-affecting `FR-*` from the Stage 01 handoff must map to at least one Stage 02 artifact or be explicitly marked `NO_UI_IMPACT` with rationale;
- design-affecting `BR-*`, `NFR-*`, and `INT-*` must be reflected where they change interaction, content, state, accessibility, localization, responsiveness, or external-system feedback;
- permission intent must map to navigation/screen/action visibility rules;
- high-impact risks/questions must map to the design areas they affect.

## 4. Orphan rules

Treat these as defects unless explicitly justified:

- `SCR-*` with no Stage 01 product reason;
- `FLW-*` that does not support a journey or required operational exception;
- `CMP-*` used nowhere and not a foundational cross-cutting primitive;
- `NAV-*` leading only to speculative features;
- `DSD-*` contradicting an accepted product constraint.

## 5. Assumptions and questions

When an `ASM-*` or `Q-*` materially affects design, link it to affected `SCR-*`, `FLW-*`, `CMP-*`, or `DSD-*`. Prefer reversible design when the question is open.

## 6. Recommended matrix

Use a matrix in `docs/02-ui-architecture.md` such as:

| Source ID | Type | UI realization | Status | Notes |
|---|---|---|---|---|
| ROLE-001 | Role | NAV-001, SCR-001..005 | COVERED | ... |
| JRN-003 | Journey | FLW-002, SCR-006..009 | COVERED | ... |
| FR-014 | Functional requirement | SCR-007, CMP-011 | COVERED | ... |
| NFR-006 | Accessibility | UXR-004, CMP-* | COVERED | ... |
| FR-021 | Functional requirement | - | NO_UI_IMPACT | Backend-only behavior |

Use stable IDs rather than prose-only references.

## 7. Validation behavior

The bundled validator can detect identifier presence and handoff coverage heuristically. It cannot prove semantic correctness. Manual semantic review remains mandatory before PASS.
