# Stage 02 Validation Contract

## Machine gate

The bundled validator checks deterministic evidence that can be evaluated safely without interpreting product intent.

It should verify:

- required Stage 02 files exist;
- required Markdown sections exist;
- `design/tokens.json` parses and has the required token groups;
- Stage 02 stable IDs appear in expected artifacts;
- primary Stage 01 handoff IDs are referenced by Stage 02 artifacts when the handoff exists;
- Stage 03 handoff references the authoritative Stage 02 sources;
- `project-state.json` has a compatible workflow structure;
- strict PASS mode confirms Stage 02 is marked PASS and completed exactly once.

Machine validation is necessary but not sufficient.

## Semantic gate

Manually verify:

- product scope fidelity;
- completeness of role/journey coverage;
- quality of information architecture;
- coherence of exception/recovery flows;
- reuse quality of the component system;
- consistency of design-system decisions;
- responsive behavior quality;
- accessibility actionability;
- localization/RTL correctness;
- implementation readiness;
- absence of speculative screens/components;
- absence of orphan screens and unexplained decisions.

## Severity

Classify validation findings as:

- `ERROR`: must be fixed before PASS.
- `WARNING`: may pass only if semantic review confirms the exception is intentional and documented.
- `INFO`: useful metadata or coverage summary.

## Strict PASS

`--strict-pass` should fail when Stage 02 is not recorded as PASS, is absent or duplicated in completed stages, required final artifacts are missing, or the current/next stage transition is inconsistent.
