# Stage 03 Quality Gates

## Gate philosophy

A gate is evidence-based. Each check must be recorded as `PASS`, `FAIL`, `NOT_RUN`, or `NOT_APPLICABLE` with a reason/evidence.

`NOT_RUN` is not equivalent to PASS.

The final Stage 03 status may be PASS only if every mandatory gate is PASS or explicitly NOT_APPLICABLE for a defensible project-specific reason.

## Gate G0 - Preconditions [MANDATORY]

PASS requires:

- Stage 01 artifacts were found/read sufficiently to recover frontend requirements;
- Stage 02 artifacts were found/read sufficiently to recover approved UI architecture;
- Stage 02 status is confirmed PASS;
- any material contradiction is resolved or documented safely.

If Stage 02 is failed/blocked or required approved artifacts are genuinely unavailable, Stage 03 is BLOCKED.

## Gate G1 - Repository integrity [MANDATORY]

PASS requires:

- frontend root/workspace correctly identified;
- existing package manager/lockfile strategy preserved unless a documented necessary migration occurred;
- unrelated user changes were not destroyed;
- no duplicate competing frontend scaffold was created accidentally;
- final repository structure is coherent.

## Gate G2 - Requirement and route coverage [MANDATORY]

PASS requires:

- every critical Stage 01 journey has an implemented route/screen flow or an explicit deferred backend contract that does not prevent frontend completeness;
- Stage 02 required screens/layouts are implemented or a documented approved/safety correction exists;
- required not-found/error/permission UX exists where relevant;
- no critical route is a placeholder/TODO-only implementation;
- no critical action is a dead/no-op control.

## Gate G3 - Design system, responsive, RTL/localization [MANDATORY]

PASS requires:

- repeated UI patterns use coherent reusable primitives/tokens;
- responsive behavior is implemented for critical layouts;
- no known critical horizontal overflow/clipping remains;
- required RTL/LTR behavior is implemented;
- mixed-direction values are handled safely where needed;
- motion respects reduced-motion requirements when animation is present.

Browser visual checks should PASS when browser tooling is available. If browser tooling is unavailable, code-level fallback review may be `PASS` while browser evidence is `NOT_RUN`, but only if no known visual blocker exists and the implementation can still be verified through build/static inspection. Record this limitation as residual risk.

## Gate G4 - Data/API/state/form architecture [MANDATORY]

PASS requires:

- typed or equivalently explicit frontend domain/API contracts exist;
- data access is centralized enough to avoid ad hoc fetch logic across presentational UI;
- production behavior does not silently depend on fixtures/mocks;
- state ownership is rational and server state is not needlessly duplicated globally;
- critical forms have deterministic validation, pending/error/success behavior, and duplicate-submit protection;
- unresolved backend details are explicit handoff contracts rather than fabricated implementations.

## Gate G5 - Accessibility [MANDATORY]

PASS requires at minimum:

- semantic/structural review completed;
- critical controls are keyboard operable by implementation review and runtime check when available;
- focus-visible behavior exists;
- critical form inputs have accessible labeling/error association;
- icon-only controls have accessible names;
- no known severe keyboard trap remains;
- dynamic critical status/errors are exposed accessibly where needed.

Automated accessibility scans, when available, are supporting evidence only.

A known severe accessibility blocker on a critical journey is FAIL.

## Gate G6 - Security and privacy hygiene [MANDATORY]

PASS requires:

- no known client-bundled secret/private credential;
- no token/sensitive payload logging introduced by Stage 03;
- no unsafe raw HTML path without explicit sanitization/trust handling;
- untrusted redirect/navigation inputs are constrained where applicable;
- production fixture/debug fallbacks are absent;
- documentation does not claim frontend guards enforce server authorization.

Backend-only controls may be deferred, but the required backend contract must be documented.

## Gate G7 - Automated quality commands [MANDATORY WHEN EXECUTABLE]

For Node/typed projects, expected checks are determined from the repository scripts/configuration and normally include:

- lint;
- typecheck where a type system is in use;
- relevant automated tests;
- production build.

Rules:

- Any final lint/typecheck/build failure in Stage 03-owned frontend code => FAIL.
- Relevant automated test failure => FAIL.
- If a command is not defined but the project has an equivalent mechanism, run the equivalent.
- If no test command/tooling exists, record the gap; add proportionate tests/tooling when needed to verify critical Stage 03 behavior.
- If execution capability itself is unavailable and no trustworthy equivalent evidence can establish build correctness, Stage 03 cannot PASS and should be BLOCKED.

Do not mark PASS based on an earlier run if files changed afterward without rerunning affected checks.

## Gate G8 - Runtime smoke and visual behavior [CONDITIONALLY MANDATORY]

When runtime/browser tooling is available, PASS requires:

- app starts successfully using the real project command;
- critical routes render without unhandled runtime errors;
- critical interaction path can be exercised through available frontend adapters/data;
- representative desktop/mobile widths checked;
- required RTL/LTR variants checked;
- console/network failures are resolved or proven to be expected external backend gaps represented by explicit adapters.

When browser tooling is genuinely unavailable, record `NOT_RUN` for browser-specific checks and use static/build/test evidence. This alone does not force BLOCKED unless the project cannot be trusted without runtime verification (for example, highly visual interaction-heavy behavior with no automated/component coverage).

## Gate G9 - Performance [MANDATORY AT BASELINE LEVEL]

PASS requires:

- no known obvious unbounded list/render loop or catastrophic rerender pattern in critical paths;
- route/feature splitting is preserved/used where appropriate;
- large media uses the framework/project's production delivery pattern;
- production build does not knowingly ship development-only panels/fixtures;
- Stage 01 performance budgets, if any, are tested and met or the stage FAILS/BLOCKS according to cause.

Without explicit budgets, do not invent numeric compliance claims.

## Gate G10 - Documentation and handoff [MANDATORY]

PASS requires:

- `docs/03-frontend-architecture.md` reflects the final implementation;
- actual executed commands and outcomes are listed;
- route/journey coverage and known assumptions are recorded;
- API/backend contracts needed by Stage 04/later integration are explicit;
- residual non-blocking risks are listed;
- `project-state.json` records truthful Stage 03 evidence and points to Stage 04.

## Final decision algorithm

1. Evaluate G0-G10.
2. If any mandatory gate is FAIL due to fixable frontend engineering work, continue working; do not finish.
3. If a mandatory gate cannot be satisfied because of a true external/precondition blocker, record blocker evidence and finish `BLOCKED`.
4. If all mandatory gates PASS or are defensibly NOT_APPLICABLE, finish `PASS`.
5. Do not invent a `PARTIAL_PASS`, `PASS_WITH_WARNINGS`, or similar marker. Non-blocking risks belong in the report, not the stage status.

## Evidence standard

Good evidence includes:

- command + exit result + relevant summary;
- route/test name + result;
- file path implementing a contract;
- screenshot/browser observation when tooling supports it;
- explicit code inspection finding tied to a path;
- quality JSON generated from the final tree.

Weak evidence that must not be used alone:

- "looks correct";
- "should compile";
- "implemented according to best practices";
- prose copied from requirements;
- tests claimed without execution.
