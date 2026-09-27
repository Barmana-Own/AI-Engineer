# Detailed Stage 08 Execution Workflow

## Table of contents

1. Working principles
2. Phase 0 - Preflight
3. Phase 1 - Scope lock
4. Phase 2 - Architecture and attack surface
5. Phase 3 - Threat model
6. Phase 4 - Security-domain review
7. Phase 5 - Candidate triage
8. Phase 6 - Confirmation and prioritization
9. Phase 7 - Remediation loop
10. Phase 8 - Verification and regression
11. Phase 9 - Reporting and handoff
12. Decision rules and anti-patterns

## 1. Working principles

Operate from evidence. Do not equate presence of a risky function with a vulnerability, and do not equate absence of scanner findings with security.

Use this execution order for each security domain:

1. identify the security invariant;
2. identify every relevant entry point and trust transition;
3. trace data/control flow to the protected asset/action;
4. inspect preventive and detective controls;
5. search for bypass paths and inconsistent enforcement;
6. reproduce safely when useful;
7. record evidence and confidence;
8. remediate root cause;
9. add regression coverage;
10. retest the original condition.

Prefer complete coverage of high-risk flows over shallow review of every file.

## 2. Phase 0 - Preflight

### 2.1 Read prior artifacts

Inspect, when present:

- `project-state.json`;
- architecture/requirements documentation;
- Stage 05-07 reports or equivalent;
- API specifications;
- database schema/migrations;
- deployment/container configuration;
- existing test suites;
- security-related documentation;
- environment examples without reading real secret values into output.

Determine the security-sensitive product flows promised by earlier stages. Stage 08 must protect intended behavior; it must not silently remove requirements to avoid a security problem.

### 2.2 Capture repository baseline

When Git exists, record:

- branch;
- HEAD commit;
- `git status --short`;
- pre-existing modified/untracked files;
- whether the worktree is clean.

Do not reset or clean the worktree. Treat pre-existing changes as user-owned. Re-check the diff at the end.

### 2.3 Inventory technology and commands

Identify:

- frontend/backend frameworks;
- languages and runtimes;
- package managers and lockfiles;
- database/ORM/query layer;
- caches/queues/object storage;
- reverse proxies/API gateways;
- authentication/session libraries;
- upload/parser/media libraries;
- external integrations;
- container/orchestration configuration;
- CI/CD definitions;
- test, lint, typecheck and build commands.

Run `python3 scripts/security_preflight.py <project-root>` when available. Treat output as inventory, not a security verdict.

### 2.4 Establish stage change policy

Default to minimal, reviewable changes. Do not perform unrelated refactors. If a security fix requires an architectural change, document why the current architecture cannot enforce the required invariant safely.

## 3. Phase 1 - Scope lock

Create a small scope table in the report:

| Target | Environment | Ownership | Active testing allowed? | Notes |
|---|---|---|---|---|

Classify all remote hosts using `scope-and-safe-testing.md`. If external authorization is unclear, do not ask the host to prove it is vulnerable; prove the local code/configuration weakness instead.

Define test identities where applicable:

- anonymous;
- normal user A;
- normal user B in same tenant;
- normal user in different tenant;
- privileged/operator role;
- administrator;
- service/webhook identity.

Use synthetic test data.

## 4. Phase 2 - Architecture and attack surface

### 4.1 Enumerate entry points

Search for:

- HTTP routes and route handlers;
- server actions/RPC/GraphQL resolvers;
- WebSocket/event handlers;
- CLI commands reachable by operators;
- background workers/queue consumers;
- scheduled jobs;
- webhooks/callbacks;
- file uploads/imports;
- file downloads/exports;
- URL fetch/import features;
- admin/debug/metrics/health endpoints;
- login/recovery/invite endpoints;
- public/static assets with generated configuration;
- mobile/deep-link interfaces if in scope.

### 4.2 Enumerate protected assets

At minimum consider:

- credentials and session/token material;
- personal/customer data;
- financial/payment state;
- business records;
- private documents/media;
- tenant boundaries;
- administrative operations;
- audit logs;
- signing/encryption keys;
- integration credentials;
- intellectual property/source artifacts;
- expensive compute/storage/notification capacity.

### 4.3 Draw trust boundaries

Record each transition where data or authority crosses a boundary:

- browser -> server;
- app -> database;
- app -> cache/queue;
- app -> object storage;
- external webhook -> app;
- app -> third-party API;
- worker -> privileged internal service;
- reverse proxy -> application;
- tenant/user -> shared service/data layer;
- CI/build -> artifact/runtime.

For each boundary, identify authentication, authorization, validation, confidentiality and integrity assumptions.

## 5. Phase 3 - Threat model

For each high-value flow, answer:

- What asset/action is protected?
- Who should be able to access it?
- What identifier or state selects the asset/action?
- What happens if the client changes that identifier/state?
- Which checks are server-side and authoritative?
- Can a lower-privileged actor reach the code path?
- Can repeated/concurrent/replayed calls create a harmful state?
- Can external input cause the server to contact or parse something unsafe?
- What would be the business impact of failure?

Create at least one abuse case for each relevant category:

- identity/account takeover;
- object/tenant access bypass;
- privilege escalation;
- unauthorized state transition;
- data exfiltration/exposure;
- financial/credit/quota abuse;
- arbitrary code/query execution;
- resource exhaustion/denial-of-wallet;
- unsafe integration/callback behavior;
- malicious file/content handling.

Rank flows by potential impact and exposure. Review the highest-risk flows first, but do not omit mandatory domains.

## 6. Phase 4 - Security-domain review

Execute the dedicated reference for each applicable domain. For every domain, maintain three lists:

- `VERIFIED`: control exists and evidence supports it;
- `FINDING`: security invariant can be violated or is materially weak;
- `N/A`: architecture makes the control irrelevant, with rationale.

Never use `VERIFIED` when the only evidence is a comment, README claim or intended architecture. Verify code/configuration/tests.

### 6.1 Authentication and authorization

Read `auth-and-access-control.md`. Prioritize authorization because API authorization errors frequently have high business impact.

### 6.2 API and business logic

Read `api-and-business-logic.md`. Treat valid-looking requests that violate business rules as security-relevant when they create unauthorized value/state/access.

### 6.3 Input/browser/injection

Read `input-browser-injection.md`. Trace source -> transformation -> sink rather than scanning isolated strings.

### 6.4 SSRF/files/parsers/integrations

Read `ssrf-files-parsers.md`. Inspect redirect chains, archive extraction and asynchronous processing, not only initial HTTP handlers.

### 6.5 Data/crypto/secrets

Read `data-crypto-secrets.md`. Distinguish intentional public data from accidental exposure.

### 6.6 Supply chain

Read `dependency-supply-chain.md`. Advisory severity alone does not prove project exploitability; project usage and reachable code paths matter.

### 6.7 Runtime/infrastructure

Read `runtime-container-infra.md`. Review deployment artifacts in the repository even if deployment is not running locally.

### 6.8 Logging/errors

Read `logging-errors-observability.md`. Security logging must be useful without creating a second data-leak channel.

## 7. Phase 5 - Candidate triage

Run available native tooling before inventing custom substitutes. Examples include package-manager audit commands, test suites, linters/security plugins already configured in the project, secret scanners already present, container/config scanners already present, and framework diagnostics.

Run `scripts/security_pattern_scan.py` as a supplemental triage pass. Its output is never authoritative.

For every candidate:

1. open the exact code path;
2. identify untrusted source and sensitive sink/action;
3. identify authentication/authorization/validation/encoding between them;
4. determine whether the path is reachable in the deployed architecture;
5. identify prerequisites and affected role/tenant;
6. decide whether evidence supports `CONFIRMED`, `STRONG`, `SUSPECTED` or `FALSE_POSITIVE`.

Close false positives explicitly so repeated scans do not keep rediscovering them without context.

## 8. Phase 6 - Confirmation and prioritization

### 8.1 Prefer safe confirmation

Use this order:

1. code/data-flow proof;
2. unit/integration test that demonstrates the failed security invariant;
3. local runtime reproduction;
4. authorized test-environment request;
5. production request only with explicit authorization and low-risk method.

Do not increase test impact merely to make the finding look more convincing.

### 8.2 Create the finding ledger entry

Before remediation, record:

- stable ID;
- title;
- severity;
- confidence;
- status;
- affected component and location;
- affected actors/tenants;
- prerequisites/exposure;
- violated security invariant;
- concise evidence;
- impact;
- root cause;
- remediation plan;
- regression-test plan.

Use `evidence-and-severity.md`.

### 8.3 Prioritize

Order work by:

1. Critical confirmed/strong;
2. High confirmed/strong;
3. security defects that can invalidate multiple findings at once (e.g. missing centralized authorization);
4. Medium confirmed;
5. lower-confidence candidates needing cheap disproof/confirmation;
6. Low/Info hardening.

## 9. Phase 7 - Remediation loop

For each confirmed material finding:

### 9.1 Freeze the invariant

Write a test or a precise expected-behavior statement before or alongside the fix. The invariant should describe what must never be possible, not the implementation detail.

Examples:

- User A cannot read/update User B's object merely by changing an object ID.
- A webhook body without a valid signature cannot cause a state transition.
- A password-reset token cannot be reused after successful reset.
- A private object is not downloadable without current authorization.

### 9.2 Fix the root cause

Prefer:

- centralized authorization helpers/policies;
- schema allowlists over denylist filtering;
- parameterized APIs over string construction;
- framework encoding/escaping over manual escaping;
- server-side state/ownership checks over client-provided role/state;
- cryptographic verification libraries over custom crypto;
- idempotency/transactions/locking where state integrity requires it;
- private storage plus controlled signed access over public object exposure;
- safe defaults at the shared boundary rather than fixes at one endpoint.

### 9.3 Avoid security regressions

Check whether the fix:

- breaks legitimate role access;
- creates tenant leakage elsewhere;
- changes API response contracts unexpectedly;
- weakens observability;
- adds a new bypass path;
- introduces incompatible dependency upgrades;
- moves secrets into another exposed channel;
- relies on client-side enforcement.

### 9.4 Verify immediately

Run the targeted regression test and the original reproduction condition. Only then change finding status from `IN_REMEDIATION` to `FIXED`.

If the attempted fix fails, keep the finding open and iterate. Do not lower severity because remediation is difficult.

## 10. Phase 8 - Verification and regression

### 10.1 Targeted retest

Every fixed Critical/High/Medium finding must have explicit retest evidence. Re-read the final code, because a passing test can itself be incorrectly designed.

### 10.2 Boundary matrix regression

For material authorization paths, test a matrix such as:

| Actor | Own object | Other same-tenant object | Other-tenant object | Privileged action |
|---|---:|---:|---:|---:|
| Anonymous | deny/allow by design | deny | deny | deny |
| User A | expected | deny unless designed | deny | deny |
| Tenant admin | expected | expected by policy | deny | policy-specific |
| Global admin | policy-specific | policy-specific | policy-specific | expected |

Adapt to the actual role model.

### 10.3 General regression

Run available relevant commands such as:

- unit tests;
- integration/API tests;
- security regression tests;
- lint;
- typecheck;
- build;
- migration/schema validation if touched;
- dependency audit;
- secrets scan if available.

Do not fabricate a "full pass" if the project lacks tests. State limitations and write missing high-value tests within Stage 08 when feasible.

### 10.4 Diff review

Inspect changed files and diff:

- verify only intended files changed;
- verify pre-existing user changes remain;
- search for debug code, temporary bypasses, test credentials and TODOs introduced during remediation;
- ensure report statements match the final code, not an earlier attempt.

## 11. Phase 9 - Reporting and handoff

Create `docs/08-security-review.md` from `report-template.md` and `docs/security/08-security-findings.json` from `evidence-and-severity.md`.

The report must be useful to Stage 09. Include specific security regression tests that Stage 09 should preserve or expand. Identify high-risk flows that deserve broad functional/negative testing next.

Update `project-state.json` after the final gate decision. Preserve unknown keys. Use `project-state-schema.md` and `scripts/update_project_state.py` when compatible with the existing state format.

Run `scripts/validate_security_artifacts.py`. Treat a PASS artifact validation failure as a Stage 08 completion failure until corrected.

## 12. Decision rules and anti-patterns

### Continue working rather than stopping when

- a test fails because of a Stage 08 change;
- a security fix is incomplete;
- a scanner reports candidates that can be triaged locally;
- a dependency advisory needs reachability analysis;
- documentation is missing but can be derived from code;
- the project has pre-existing changes that can be preserved.

### Use FAIL when

- a known Critical/High within project control remains unresolved;
- authorization boundaries are still demonstrably broken;
- required security regression tests cannot be made reliable due to unresolved project defects;
- Stage 08 changes leave relevant build/tests broken;
- evidence/reporting is insufficient to justify PASS.

### Use BLOCKED when

A truly external dependency prevents required verification/remediation and cannot safely be mocked or inferred. Document the exact missing dependency and what evidence would unblock the stage.

### Never

- declare PASS based only on static analysis;
- declare a vulnerability solely from a regex/scanner hit;
- auto-approve residual risk;
- hide a failing security test;
- delete or reset unrelated user work;
- force dependency upgrades without compatibility verification;
- add broad allowlists/exceptions that merely mask the issue;
- perform unauthorized external exploitation.
