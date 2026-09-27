# Stage 03 Handoff - [Project Name]

## Authoritative Inputs
- `docs/01-project-brief.md`
- `docs/01-requirements.md`
- `docs/01-stage-02-handoff.md`
- `docs/02-ui-architecture.md`
- `docs/02-design-system.md`
- `design/tokens.json`
- `project-state.json`

## Product and UI Scope
One concise paragraph. Do not rewrite the project brief.

## Immutable / High-Confidence Decisions
List relevant `DEC-*`, `DSD-*`, and explicit user constraints Stage 03 must preserve.

## Route and Screen Obligations
List `SCR-*` with route/entry intent, role coverage, and related `FLW-*`/`JRN-*`.

## Navigation and Layout Contracts
List required `NAV-*` and `LAY-*` behavior.

## Component Contracts
List `CMP-*` families Stage 03 should implement/reuse and identify high-risk interaction requirements.

## Design Token Source of Truth
State that `design/tokens.json` is authoritative. Explain any transformation constraints without choosing implementation syntax unless Stage 03 owns that decision.

## State and Error Obligations
Summarize the state matrix and any critical retry, recovery, destructive, stale, partial, or permission behavior.

## Responsive Obligations
List behavior changes Stage 03 must preserve across defined breakpoints.

## Accessibility Obligations
List target/assumption, keyboard, focus, semantics, labels/errors, reduced motion, reflow, async feedback, and complex-widget expectations.

## Localization / RTL Obligations
List direction, bidi, date/number/currency, icon mirroring, table/chart behavior, and text expansion rules.

## Traceability and Acceptance
Require Stage 03 implementation to preserve Stage 02 IDs or an explicit mapping and demonstrate coverage for design-affecting Stage 01 IDs.

## Open Non-Blocking Questions and Reversible Assumptions
List `Q-*` and `ASM-*` that Stage 03 must keep reversible.

## Stage 03 Prohibitions
- Do not silently redefine product scope.
- Do not replace the design system with ad hoc per-page styling.
- Do not drop error/loading/permission states because mock data works.
- Do not remove accessibility or RTL requirements for implementation convenience.
- Do not treat hidden UI as authorization enforcement.
- Do not invent backend/API behavior that Stage 03 does not own.

## Stage 03 Start Condition
Stage 03 may begin only when Stage 02 is PASS and the required Stage 02 artifacts are present and internally consistent.
