# Stage 02 UI Architecture - [Project Name]

## 1. Executive Design Summary
- Execution mode: CREATE | RESUME | REPAIR
- Product/UI scope summary
- Primary design constraints
- Key assumptions/questions

## 2. Authoritative Inputs
List Stage 01 and accepted Stage 02 sources with paths and relevant IDs.

## 3. UI Coverage Model
Summarize primary roles, journeys, requirements, rules, integrations, constraints, and design obligations.

## 4. Role-to-Navigation Architecture
For each `NAV-*` include role coverage, destinations, visibility conditions, adaptive behavior, and related IDs.

## 5. UI Flow Catalog
For each `FLW-*` include actor, trigger, steps, branches, validation, success/failure, recovery, screens, and source IDs.

## 6. Screen Inventory
For every `SCR-*` use a consistent contract:

### SCR-001 - [Name]
- Purpose:
- Roles:
- Related journeys:
- Related requirements/rules/integrations:
- Entry/route intent:
- Layout: LAY-###
- Primary action:
- Secondary actions:
- Required information:
- Permission behavior:
- Components: CMP-###
- States:
- Validation/recovery:
- Responsive behavior:
- Accessibility:
- Localization/RTL:
- Assumptions/questions:

## 7. Layout Pattern Catalog
Define every `LAY-*`, regions, hierarchy, width, scroll/sticky behavior, and adaptive transformation.

## 8. Component Usage Map
Map screens to `CMP-*` component families. Detailed component contracts may live in the design-system document.

## 9. Interaction State Matrix
Include loading, empty, error, success, permission, stale, partial, offline/degraded, action-pending, action-failure, and destructive states as applicable.

## 10. Responsive Behavior Matrix
Map high-impact screens/layouts to narrow, medium, and wide behavior. Use behavior-driven breakpoints from tokens.

## 11. Accessibility Architecture
Record target/assumption and screen-specific exceptions or critical obligations.

## 12. Localization and RTL Architecture
Document direction, bidi, date/number/currency, icon, table, chart, and text expansion behavior when relevant.

## 13. Content and Microcopy Rules
Define action-label, error, empty-state, confirmation, terminology, formatting, and truncation rules.

## 14. Traceability Matrix
Map Stage 01 IDs to `NAV-*`, `FLW-*`, `SCR-*`, `LAY-*`, `CMP-*`, `UXR-*`, or `DSD-*`.

## 15. Assumptions, Open Questions, Risks, and Conflicts
Reference shared stable IDs from `project-state.json`.

## 16. Stage 03 Implementation Notes
Summarize only implementation-relevant architectural obligations; the formal handoff lives in `docs/02-stage-03-handoff.md`.
