# Frontend, Accessibility, and End-to-End Testing

## Purpose

Verify user-facing critical behavior without overfitting tests to DOM implementation details.

## Table of contents

1. Frontend test priorities
2. Component/interactions
3. Forms and validation
4. Loading/error/empty states
5. Auth and permission UI
6. Accessibility behavior
7. RTL/i18n considerations
8. E2E journey design
9. E2E data and isolation
10. Reliable browser synchronization
11. Visual testing boundary
12. Browser/device scope

## 1. Frontend test priorities

Prioritize frontend behavior that can cause business failure:
- critical forms;
- workflow transitions;
- permission-sensitive actions;
- data submission;
- error recovery;
- destructive confirmations;
- routing guards;
- stale/optimistic state handling;
- async loading and retry behavior.

Do not spend Stage 09 capacity on low-value CSS implementation assertions.

## 2. Component/interactions

Prefer user-observable queries and actions.

Test:
- what the user can see/read;
- what controls are enabled/disabled;
- input/output behavior;
- emitted action/state change;
- accessible role/name when practical;
- server error rendering and recovery.

Avoid tests coupled to internal component instance state or CSS class names unless those are the explicit contract.

## 3. Forms and validation

For P0/P1 forms, test:
- required fields;
- valid submission;
- server validation errors;
- client/server validation consistency for critical fields;
- submit disabled/pending behavior where important;
- duplicate-submit prevention;
- preservation/reset of entered data according to contract;
- file upload preview/status where applicable;
- keyboard submission behavior where applicable.

Do not assume frontend validation replaces backend validation.

## 4. Loading, error, and empty states

Test meaningful states:
- initial loading;
- no data;
- recoverable API error;
- retry success;
- authorization failure;
- stale request/out-of-order response behavior when the UI can encounter it;
- optimistic update rollback when used.

Avoid assertions based on arbitrary timeout duration.

## 5. Auth and permission UI

Frontend tests can verify user experience, but backend tests must prove authorization.

Frontend coverage can include:
- protected route redirect;
- session expiry handling;
- forbidden-action control hidden/disabled according to UX contract;
- role-specific navigation;
- logout state reset.

Never accept "button hidden" as proof the action is authorized safely.

## 6. Accessibility behavior

Where frontend tooling supports it, test critical accessibility behavior:
- form label/control association;
- accessible names for critical controls;
- keyboard-operable critical interactions;
- focus management for dialogs/errors where relevant;
- semantic roles;
- obvious automated axe-style violations in critical views if the project uses such tooling.

Automated accessibility testing is not a substitute for full manual accessibility review. Stage 10 may own broader exploratory validation.

## 7. RTL and i18n considerations

For Persian/Arabic RTL products, include relevant critical behavior:
- directional layout does not invert semantic control order incorrectly where testable;
- mixed Persian/Latin inputs remain usable;
- locale-specific date/number logic follows application contract;
- translated labels used by accessible queries are stable or test helpers are locale-aware;
- validation/error messages are displayed in the expected locale when contractually required.

Do not assert pixel-perfect RTL layout in normal behavior tests.

## 8. E2E journey design

Choose a small number of high-value flows.

A critical E2E should prove multiple real boundaries without trying to test every branch.

Examples:
- login → create core entity → verify persisted entity;
- applicant submits request → staff reviews → status transition visible;
- checkout/request → payment sandbox boundary → confirmation;
- upload → processing → authorized retrieval;
- role A creates item → role B cannot access it.

For each critical workflow family, include:
- at least one success journey;
- at least one meaningful failure/denial/recovery journey when practical.

## 9. E2E data and isolation

Use dedicated test users/data.

Preferred strategies:
- API/database setup endpoint restricted to test environment;
- fixture seeding script;
- factory through backend test helpers;
- disposable DB per run.

Avoid manual pre-seeded shared accounts when possible.

Every E2E run should be repeatable without a human resetting data.

## 10. Reliable browser synchronization

Wait for observable conditions, not arbitrary time.

Prefer:
- element visible/enabled;
- response complete;
- URL/state change;
- application-specific ready marker.

Avoid fixed `sleep`/`waitForTimeout` except for narrowly justified timing semantics.

Use stable locators:
- accessible role/name;
- stable test id when semantic locator is not practical;
- label/text scoped appropriately.

Do not depend on brittle DOM depth or generated CSS selectors.

## 11. Visual testing boundary

Visual regression tests are optional in Stage 09 unless the project already relies on them for critical behavior.

If present:
- keep baseline environment controlled;
- review baseline changes deliberately;
- do not auto-accept changed screenshots merely to pass.

Broad visual polish review belongs to Stage 10.

## 12. Browser/device scope

Stage 09 should execute the project's configured critical browser set where practical.

If the project has no established matrix, prioritize one representative browser for automated E2E and defer broad cross-browser/device exploratory coverage to Stage 10 unless a requirement explicitly makes it P0/P1.

Record exactly which browsers were run and which were not run.
