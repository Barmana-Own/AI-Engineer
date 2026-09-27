# Authentication, Authorization, and Security Regression Testing

## Purpose

Ensure Stage 08 security work remains enforced and critical denial paths cannot regress silently.

## Table of contents

1. Import Stage 08 findings
2. Authentication matrix
3. Session/token lifecycle
4. Authorization/RBAC/ABAC
5. Ownership and IDOR/BOLA
6. Tenant isolation
7. Input and output security regressions
8. File upload regressions
9. Rate limiting and abuse controls
10. CSRF/CORS/cookie behavior
11. Sensitive data and logging
12. Security test evidence

## 1. Import Stage 08 findings

For every Stage 08 finding marked fixed:
1. preserve the finding ID;
2. identify the exploit precondition;
3. add a regression test reproducing the previously unsafe request when repository-level testing can represent it;
4. assert the safe outcome;
5. assert forbidden side effects did not occur;
6. link the test ID back to the finding.

A security fix without a reproducible automated regression test must be documented with the technical reason and compensating automated evidence if available.

## 2. Authentication matrix

For protected endpoint families, test relevant states:
- no credentials;
- valid credentials;
- malformed credential;
- invalid signature/secret where safely testable;
- expired credential;
- revoked/invalidated credential when revocation is supported;
- disabled/deleted user;
- user whose role changed after token/session issuance when policy specifies behavior.

Do not accept only "happy-path login works" as authentication coverage.

## 3. Session/token lifecycle

Where applicable test:
- login success/failure;
- logout invalidation semantics;
- refresh rotation/reuse detection;
- expiry;
- revocation;
- session fixation prevention behavior exposed by the implementation;
- concurrent sessions policy;
- cookie flags/config through application tests when the framework supports them.

If logout is stateless by design and cannot revoke access tokens, test the documented contract instead of inventing revocation semantics.

## 4. Authorization/RBAC/ABAC

Build a role-action matrix for P0/P1 actions.

Test at minimum:
- allowed role can act;
- lower/unrelated role cannot act;
- role cannot escalate itself unless explicitly allowed;
- read permission does not imply write permission;
- scoped admin cannot access broader scope;
- hidden UI control is not the only enforcement—backend denial must be tested.

Test the enforcement point actually protecting the operation.

## 5. Ownership and IDOR/BOLA

For object-level operations:
1. create Actor A and Actor B;
2. create resource owned/scoped to A;
3. authenticate as B;
4. attempt read/update/delete/action using A's identifier;
5. assert denial/not-found according to contract;
6. assert A's resource remains unchanged;
7. repeat for nested resources where scope can be bypassed.

Test predictable and alternate identifiers if the API accepts multiple addressing forms.

Do not treat unguessable UUIDs as authorization.

## 6. Tenant isolation

For multi-tenant systems, create at least two tenants and test:
- cross-tenant read;
- cross-tenant update/delete;
- cross-tenant search/filter;
- cross-tenant nested resource access;
- cached data separation;
- background job tenant scoping;
- export/report tenant scoping;
- admin scope boundaries.

Cross-tenant exposure is P0 by default.

## 7. Input and output security regressions

Automated tests should cover implementation-specific controls introduced in Stage 08, such as:
- server-side validation cannot be bypassed by direct API call;
- mass-assignment/protected fields cannot be overwritten;
- dangerous HTML/script is escaped/sanitized according to contract;
- SQL/ORM query parameters remain parameterized via behavior tests where practical;
- path traversal is rejected;
- redirect targets are constrained when open-redirect risk exists;
- response does not expose sensitive fields;
- error response does not leak stack/secret details in production-like config.

Do not build offensive payload libraries beyond what is necessary to reproduce the known defensive requirement.

## 8. File upload regressions

If uploads exist, test relevant Stage 08 controls:
- authentication/authorization;
- allowed extension/MIME/content policy;
- size limit;
- filename/path handling;
- metadata ownership;
- rejected file cleanup;
- download authorization;
- content-disposition/security headers if part of application behavior;
- image/document processing failure safety.

Use benign test files that exercise validation. Do not introduce real malware.

## 9. Rate limiting and abuse controls

When Stage 08 defines rate limits or lockouts, test behavior without destabilizing shared infrastructure.

Verify:
- threshold behavior;
- response/status/error contract;
- reset/window behavior when deterministic clock support exists;
- scope key (IP/user/token) as designed;
- privileged bypass only if explicitly specified;
- limits do not leak between unrelated tenants/users unexpectedly.

Avoid high-volume load testing in Stage 09 unless specifically required and safe.

## 10. CSRF, CORS, and cookie behavior

For cookie-authenticated state-changing flows, test CSRF enforcement if the architecture requires it.

For CORS, test application configuration only where the framework exposes deterministic test hooks. Verify allowed and denied origins according to the documented policy.

For auth cookies where observable in tests, check required attributes such as secure/HTTP-only/same-site according to Stage 08 decisions and environment behavior.

Do not blindly require CSRF tokens for bearer-token APIs that are not cookie-authenticated.

## 11. Sensitive data and logging

Verify important response/logging behavior when testable:
- password hashes/secrets are not returned;
- tokens are not emitted in normal API responses unless contract requires;
- sensitive fields are redacted from audit/log structures where Stage 08 implemented redaction;
- test evidence itself redacts credentials and PII.

Do not copy real secrets into snapshots or result documents.

## 12. Security test evidence

In `docs/09-test-plan.md`, include a security traceability table:

| Security source/finding | Priority | Control | Regression test | Result |
|---|---|---|---|---|

In `docs/09-test-results.md`, report:
- auth tests passed/failed;
- authorization denial tests passed/failed;
- cross-owner/tenant tests passed/failed;
- Stage 08 regression tests passed/failed/not-run;
- unresolved security-related defects.

PASS requires zero unresolved failed P0/P1 security regressions.
