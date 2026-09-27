# Stage 02 Handoff Template

Create `docs/01-stage-02-handoff.md` with this structure.

# Stage 02 Handoff — [Project Name]

## Authoritative Inputs
- `docs/01-source-map.md`
- `docs/01-project-brief.md`
- `docs/01-requirements.md`
- `docs/01-domain-integration-map.md`
- `docs/01-risk-register.md`
- `docs/01-traceability-matrix.md`
- `project-state.json`
- `docs/01-research-evidence.md` when present
- `docs/01-readiness-review.md`

## Product Definition

One short paragraph. Do not rewrite the entire brief.

## Scope Baseline

Summarize IN / OUT / OPTIONAL boundaries relevant to design.

## Immutable / High-Confidence Decisions

List relevant DEC-* and explicit constraints Stage 02 must preserve.

## Roles Requiring UI Coverage

Map ROLE-* to the JRN-* flows they participate in.

## Journeys Requiring Experience Coverage

List JRN-* and the outcome each flow must support. Do not design screens here.

## Permission Intent

Summarize visibility/action boundaries needed for information architecture.

## Domain Vocabulary That UI Must Preserve

List the canonical terms from the domain map that should not be renamed casually.

## Integration-Affecting UX Constraints

List INT-* constraints that affect states, loading, retries, failures, callbacks, external redirects, or asynchronous behavior.

## Localization, Accessibility, and Device Constraints

Only confirmed or clearly assumed constraints; reference NFR-*/ASM-*.

## Design-Affecting Requirements

Reference the highest-impact FR-*, NFR-*, BR-*, INT-*, RSK-*, and ASM-*.

## Open Non-Blocking Questions

List Q-* that Stage 02 must keep reversible.

## Known Risks for Stage 02

List only risks that materially affect information architecture, interaction design, content, accessibility, or flow design.

## Stage 02 Directive

Tell Stage 02 to derive information architecture, design-system foundations, screen inventory, responsive behavior, and UI/UX flows from authoritative Stage 01 artifacts without redefining product scope.

## Stage 02 Prohibitions

- Do not change product scope without a documented conflict/decision.
- Do not invent new MUST features.
- Do not ignore out-of-scope/optional boundaries.
- Do not reinterpret canonical business terms without a documented reason.
- Do not hide unresolved assumptions by treating them as facts.
- Do not perform backend/database/deployment implementation unless Stage 02 explicitly owns such work.
