# Testing, Evidence, and Stage 07 Quality Gate

## Contents

- [Purpose](#purpose)
- [Evidence principles](#evidence-principles)
- [Evidence document](#evidence-document)
- [Mandatory evidence classes](#mandatory-evidence-classes)
- [Required attack cases](#required-attack-cases)
- [Authorization matrix coverage check](#authorization-matrix-coverage-check)
- [Static-audit interpretation](#static-audit-interpretation)
- [Manual review checklist](#manual-review-checklist)
- [Hard-fail findings](#hard-fail-findings)
- [PASS algorithm](#pass-algorithm)
- [BLOCKED algorithm](#blocked-algorithm)


## Purpose

This is the mandatory verification contract for Stage 07. Use it to decide whether implementation evidence is strong enough to permit PASS.

## Evidence principles

1. Prefer executable evidence over prose.
2. Prefer integration/HTTP/service-boundary tests over isolated unit tests for authorization enforcement.
3. Use unit tests for policy logic, token helpers, state machines, and cryptographic-library integration where appropriate.
4. Every high-impact protected action needs at least one positive and one negative authorization path.
5. Every tenant/ownership boundary needs an explicit cross-boundary negative path.
6. Every credential lifecycle mechanism needs expiry/revocation/replay evidence applicable to its design.
7. A test that mocks away the middleware/policy being verified is not sufficient evidence for that middleware/policy.
8. `N/A` requires a concrete architectural reason.
9. `SKIPPED`, `TODO`, `NOT RUN`, `tool unavailable`, or `out of time` are not PASS and not valid N/A reasons.
10. Do not accept a manual UI observation as authorization evidence when an API test can exercise the server boundary.

## Evidence document

Create `docs/security/07-auth-test-evidence.md`.

Use this table shape:

| Evidence ID | Status | Requirement | Test/command | Result | Code/enforcement location | Notes |
|---|---|---|---|---|---|---|

Allowed status values:

- `PASS`
- `FAIL`
- `BLOCKED`
- `N/A`

Do not use ambiguous values such as `mostly pass`, `partial`, or `looks good`.

## Mandatory evidence classes

The exact individual rows can expand, but these evidence-class IDs must appear.

### AUTHN-01 - Authentication boundary

Prove:

- valid authentication succeeds;
- invalid authentication fails;
- missing credentials fail on protected actions;
- malformed credentials fail closed;
- account state is enforced.

Minimum status: PASS unless the project has no authenticated identities, in which case this entire skill should generally not have been triggered.

### AUTHN-02 - Credential security

Prove applicable credential handling:

- password verifier uses maintained secure primitive, or N/A if no passwords;
- secrets are not hard-coded/default;
- credentials are not logged;
- provider/token validation uses maintained verifier.

A static code location plus focused tests/runtime configuration can form combined evidence.

### SESS-01 - Session/token lifecycle

Prove applicable behaviors:

- expiry;
- logout/invalidation semantics;
- refresh/renewal behavior;
- revocation after security state changes according to documented policy;
- replay/rotation behavior when relevant.

For stateless short-lived access tokens, document what event cannot revoke them immediately and prove the accepted maximum stale window plus refresh/session denial behavior.

### CSRF-01 - Browser request integrity

For cookie-authenticated state-changing browser requests, prove CSRF protections reject an invalid/missing token or origin according to the chosen defense and valid requests succeed.

Mark N/A only when browser credentials are not automatically attached in a way that creates CSRF risk or when there is no browser state-changing surface. Explain architecture.

### AUTHZ-01 - Server-side policy enforcement

Prove:

- an allowed principal succeeds;
- an authenticated but unauthorized principal is denied;
- new/unknown/unmapped privileged action is not implicitly allowed;
- enforcement occurs on the server/trusted service boundary.

### AUTHZ-02 - Vertical privilege escalation resistance

Attempt lower-role -> higher-role actions including role/permission administration, admin endpoints, support operations, and privileged request fields.

Prove denial.

### AUTHZ-03 - Horizontal/object ownership isolation

Attempt access to another principal's resource using a known valid identifier.

Prove read/update/delete/download/bulk behavior as applicable.

### TENANT-01 - Cross-tenant isolation

Required for multi-tenant systems.

Attempt a same-role principal in tenant A against known valid resources/actions in tenant B.

Cover at least one high-value read and one high-impact write action, then expand across resource families based on matrix/risk.

N/A requires proof that no tenant boundary exists.

### PRIV-01 - Privilege freshness and revocation

Prove that role removal, membership removal, account suspension, or equivalent security state change takes effect inside the documented maximum stale window.

Test with a credential/session issued before the change.

### RECOV-01 - Recovery and verification

If recovery/verification exists, prove:

- expired token rejected;
- replayed/consumed token rejected;
- wrong account/purpose rejected;
- new reset/change invalidates old artifacts according to design;
- response does not enable unintended enumeration where that is a requirement;
- recovery cannot bypass required MFA/assurance silently.

### MFA-01 - MFA and step-up

If required by risk/product policy, prove:

- protected action denied without required challenge;
- succeeds after valid challenge;
- stale/expired/replayed challenge denied;
- disable/reset/recovery path has equivalent policy;
- backup/recovery code is single-use if present.

N/A requires explicit risk decision, not absence of implementation.

### FED-01 - Federation/OAuth/OIDC

If present, prove relevant negative cases such as:

- invalid state/nonce/PKCE;
- wrong issuer/audience;
- expired/untrusted token;
- unsafe return URL rejected;
- account-linking takeover path rejected.

N/A when no external/federated identity flow exists.

### ABUSE-01 - Auth abuse controls

Prove applicable rate/backoff controls and enumeration behavior on exposed auth endpoints. At least one focused test or controlled request sequence should show the control activates.

### AUDIT-01 - Security audit events

Prove selected high-impact events create structured audit records and secrets are absent.

At minimum sample:

- login success/failure;
- role or membership change;
- password/MFA reset or API key change when present;
- impersonation when present.

### FRONT-01 - Client auth state

For interactive clients, prove terminal session expiry/revocation and forbidden behavior are handled without client-side authorization assumptions.

N/A for API-only/headless services.

### STATIC-01 - Deterministic static auth audit

Run `scripts/auth_security_audit.py` when Python and repository files are available. Record:

- command;
- output path;
- high/medium findings;
- manual disposition;
- fixes and re-run result.

If the runtime genuinely cannot run the script but equivalent deterministic tooling exists, record equivalent evidence. If no deterministic scan can be executed, this is BLOCKED for a workflow that claims full autonomous Stage 07 verification.

### REG-01 - Regression gate

Record final results for relevant:

- auth tests;
- broader integration/E2E tests;
- lint;
- typecheck;
- build/compile;
- migration/schema validation.

A pre-existing unrelated failure can be documented separately only when Stage 07-focused tests and the affected build path are still demonstrably valid. Do not hide a failure introduced by Stage 07 as pre-existing.

## Required attack cases

Expand test coverage using the actual architecture. At minimum consider:

### Identity/account

- disabled/suspended user;
- unverified account restrictions;
- removed tenant membership;
- duplicate/linked external identity collision;
- deleted/closed account.

### Credential/session

- expired token;
- malformed token;
- wrong signature/key;
- wrong issuer/audience;
- wrong token purpose;
- revoked session;
- logout then reuse;
- old refresh token after rotation;
- concurrent refresh/redeem;
- role change with old token;
- password/MFA reset with old session.

### Authorization

- anonymous -> protected;
- user -> admin action;
- same tenant wrong role;
- same role wrong tenant;
- object ID substitution;
- nested ID substitution;
- mass assignment of role/tenant/owner/security fields;
- alternate HTTP method;
- bulk mixed IDs;
- export/report;
- file download/preview;
- websocket channel;
- background/async action;
- support/impersonation action.

### Recovery

- unknown account;
- wrong token;
- expired token;
- consumed token;
- token for different purpose;
- token after new request generation if old should be invalid;
- concurrent redemption;
- recovery after account suspension;
- recovery bypassing MFA.

### Federation

- state mismatch/replay;
- nonce mismatch;
- PKCE mismatch;
- code replay;
- wrong issuer;
- wrong audience;
- untrusted signing key;
- malicious return URL;
- account link collision.

## Authorization matrix coverage check

For every row in `docs/security/07-authorization-matrix.md`:

- identify enforcement location;
- link at least one positive test if action is expected to be usable;
- link at least one negative test;
- for tenant/ownership actions, link a boundary test;
- for high-risk action, link step-up/audit tests if policy requires them.

If a privileged matrix row has no negative test, Stage 07 is incomplete.

## Static-audit interpretation

The bundled static scanner is heuristic.

- `HIGH` finding: inspect manually before PASS. If confirmed and in Stage 07 scope, fix it. If false positive, record why.
- `MEDIUM` finding: inspect and either fix or record why it is safe/not applicable.
- `LOW/INFO`: use for hardening; may be deferred to Stage 08 if outside Stage 07.

Never downgrade a confirmed issue merely to satisfy the gate.

## Manual review checklist

Before PASS manually review:

- all auth middleware/guards;
- all admin/support routes;
- role/membership mutations;
- recovery/reset endpoints;
- token/session issuance and refresh;
- auth logs/error handling;
- client token storage;
- tenant-scoped repositories/queries;
- files/exports/realtime paths;
- OAuth callback/linking if present;
- MFA reset/disable if present;
- API key/service credential creation if present.

## Hard-fail findings

Any confirmed instance blocks PASS until resolved:

- authentication bypass;
- plaintext/reversible passwords;
- hard-coded/default reusable production credential;
- server-side protected action without authorization;
- vertical privilege escalation;
- horizontal ownership bypass;
- cross-tenant access;
- role/membership removal not enforced inside documented required window;
- reset/recovery replay enabling takeover;
- MFA bypass for mandatory high-risk flow;
- enabled OAuth/OIDC validation/account-linking defect enabling takeover/confusion;
- reusable auth secret/token exposed in source/log/URL against approved design;
- negative tests missing for privileged operations;
- tests fail on the implemented auth boundary.

## PASS algorithm

Follow this exact decision order:

1. Confirm Stage 06 precondition.
2. Confirm real implementation changes or verified existing implementation covers Stage 07 scope.
3. Confirm authorization matrix matches discovered protected actions.
4. Confirm all mandatory evidence-class IDs exist.
5. For each evidence class:
   - if applicable: must be `PASS`;
   - if not applicable: must be `N/A` with concrete architecture reason;
   - `FAIL` or `BLOCKED`: stage cannot PASS.
6. Confirm no hard-fail finding remains.
7. Confirm all High static-audit findings are dispositioned and confirmed defects fixed.
8. Confirm final auth-focused tests pass.
9. Confirm lint/typecheck/build/relevant regression results do not show a Stage 07 regression.
10. Confirm documentation reflects the verified code.
11. Update project state.
12. Only then emit `STAGE_07_STATUS: PASS`.

## BLOCKED algorithm

Use BLOCKED only after completing all work possible without the missing dependency.

Record:

- blocker ID;
- exact missing dependency/capability;
- why it cannot be safely inferred/mocked;
- completed work;
- evidence already passing;
- smallest action needed to unblock;
- files changed;
- tests already run.

Do not use BLOCKED to avoid fixing a difficult bug that is solvable inside the repository.
