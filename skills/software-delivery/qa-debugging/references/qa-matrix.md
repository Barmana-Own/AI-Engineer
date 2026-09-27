# QA Matrix and Coverage Design

## Table of contents

1. Purpose
2. Traceability model
3. Coverage dimensions
4. Criticality classification
5. Scenario design procedure
6. Role and permission matrix
7. State-transition matrix
8. Boundary matrix
9. Environment and device matrix
10. Coverage completeness rules
11. Execution statuses
12. Anti-patterns

## 1. Purpose

Build `docs/10-qa-matrix.md` as the authoritative Stage 10 coverage ledger. The matrix must answer: what requirement was tested, by whom, from what state, through which action, against what expected result, with what evidence, and what happened.

## 2. Traceability model

Prefer this chain:

`Requirement/Rule -> Role -> Journey -> State -> Scenario -> Expected Result -> Evidence -> Defect/Fix if needed`

Every release-critical requirement must have at least one downstream executed scenario or an explicit blocker.

Every P0/P1 defect should point back to one or more affected matrix rows.

## 3. Coverage dimensions

Consider these dimensions independently before combining them:

### Product dimension

- capability/module;
- requirement;
- business rule;
- user journey;
- state transition;
- integration.

### Actor dimension

- anonymous visitor;
- authenticated standard user;
- privileged user;
- owner/non-owner;
- admin/operator/reviewer/approver;
- service account/system actor where applicable.

### Data dimension

- no data;
- typical data;
- maximum/large data;
- invalid data;
- stale data;
- duplicate data;
- cross-tenant/cross-owner data;
- deleted/archived data;
- sensitive data.

### Time/state dimension

- initial;
- pending;
- approved/rejected;
- expired;
- cancelled;
- retried;
- concurrently modified;
- resumed after refresh/relogin.

### Platform dimension

- viewport class;
- browser family when relevant;
- RTL/LTR locale;
- keyboard/touch interaction;
- network degradation where testable.

### Trust dimension

- authorized action;
- unauthorized action;
- direct API access;
- object-level access;
- malformed input;
- repeated/replayed request.

## 4. Criticality classification

Mark each row as:

- **Release-critical:** failure prevents intended release purpose, causes serious authorization/data risk, or breaks required operation.
- **Important:** meaningful functionality that can tolerate a limited defect if safe workaround exists.
- **Supporting:** lower-risk secondary behavior.
- **Polish:** cosmetic or low-impact quality.

Execute release-critical rows first and require evidence for all of them before PASS.

## 5. Scenario design procedure

For each requirement or rule:

1. Identify the actor.
2. Identify preconditions.
3. Identify starting entity/application state.
4. Define the action.
5. Define visible expected behavior.
6. Define API/domain expected behavior.
7. Define persisted or downstream expected state.
8. Add at least one important negative or boundary variant.
9. Add authorization expectation where relevant.
10. Add device/locale variant where UI risk exists.
11. Define evidence method.
12. Assign criticality.

Do not create redundant combinatorial explosion. Use pairwise/risk-based combinations for lower-risk dimensions while fully covering release-critical role/state boundaries.

## 6. Role and permission matrix

For protected capabilities, use a compact permission matrix before detailed scenarios.

Example columns:

| Capability | Anonymous | User | Owner | Reviewer | Admin | Server enforcement checked |
|---|---|---|---|---|---|---|

Values:

- Allow
- Deny
- Conditional
- N/A

For every `Deny`, include at least one server-side denial test if the capability is reachable through an API or direct route.

For every `Conditional`, write the condition explicitly, such as ownership, organization membership, status, feature flag, or approval state.

## 7. State-transition matrix

For important mutable entities, document valid and invalid transitions.

Example:

| From | Action | To | Allowed roles | Expected side effects | Invalid alternative |
|---|---|---|---|---|---|

Check:

- valid transition succeeds once;
- repeated transition is idempotent or safely rejected;
- forbidden transition is denied;
- stale actor cannot transition outdated state;
- side effects happen exactly as intended;
- failure does not leave half-applied state.

## 8. Boundary matrix

For each input or resource with constraints, include relevant boundaries:

- empty;
- minimum - 1;
- minimum;
- typical;
- maximum;
- maximum + 1;
- malformed;
- duplicate;
- Unicode/RTL/bidirectional text where relevant;
- very long words/URLs;
- file type mismatch;
- file size boundary;
- date/time boundary;
- timezone/day rollover;
- numeric precision/rounding;
- negative/zero values when meaningful.

Do not test every mathematical boundary if the product does not expose it; select those tied to requirements or failure risk.

## 9. Environment and device matrix

Use project-defined breakpoints first. If none exist, choose representative classes rather than arbitrary device brands.

Suggested classes:

- narrow mobile;
- standard mobile;
- tablet/small laptop;
- desktop;
- wide desktop for layout expansion/overflow checks.

For each high-risk UI flow, verify at least one narrow and one desktop-class viewport. Add intermediate widths for complex tables, dashboards, sidebars, or multi-column forms.

If multiple browsers are required by project requirements, represent them explicitly. Otherwise do not claim cross-browser support beyond what was tested.

## 10. Coverage completeness rules

Before PASS, verify:

- every release-critical requirement appears in the matrix;
- every release-critical actor has at least one executed journey;
- every privileged capability has allow and deny coverage;
- every critical state machine has valid and invalid transition coverage;
- every state-changing integration has success and relevant failure coverage;
- every critical upload/file path has validation and failure coverage;
- every critical UI flow has responsive coverage;
- every critical form has validation/error coverage;
- every fixed P0/P1 has a regression row/test;
- every unexecuted critical row is a blocker, not silently omitted.

## 11. Execution statuses

Use only clear statuses:

- `PASS` - executed and expected result proven.
- `FAIL` - executed and defect observed.
- `BLOCKED` - cannot execute because a real dependency/capability is unavailable.
- `NOT_RUN` - planned but not executed yet.
- `N/A` - demonstrably not applicable; include reason.

Do not use `PASS_WITH_NOTES` to hide a defect. Record PASS for the tested expectation and track the defect separately if truly non-blocking.

## 12. Anti-patterns

Avoid:

- a matrix containing only page names;
- one generic "admin works" row for many permissions;
- checking UI visibility without server authorization;
- listing automated test names without mapping to requirements;
- marking a requirement covered because code appears to implement it;
- collapsing all mobile widths into a single visual glance;
- ignoring persisted state after successful UI feedback;
- excluding known failing scenarios from the matrix;
- counting a mocked third-party integration as a live integration pass.
