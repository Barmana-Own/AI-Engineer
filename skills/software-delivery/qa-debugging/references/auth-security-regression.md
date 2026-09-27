# Authentication, Authorization, and Security Regression QA

## Table of contents

1. Scope and safety
2. Authentication
3. Session and token behavior
4. Authorization and object ownership
5. Input and output handling
6. CSRF and browser request context
7. File upload/download
8. Sensitive data and secrets
9. Logging and error exposure
10. Security headers and transport assumptions
11. Rate/abuse controls
12. Integration trust boundaries
13. Regression after fixes
14. Severity guidance
15. Exit criteria

## 1. Scope and safety

Stage 10 performs safe release-oriented security regression. It is not a full penetration test and must not perform destructive exploitation against production systems.

Use local/staging test identities and benign payloads. Prefer proving that a control exists and is enforced over aggressive exploitation.

## 2. Authentication

Check applicable flows:

- registration constraints;
- login success/failure;
- invalid credential messaging without excessive account disclosure;
- disabled/pending/locked account behavior;
- password reset or OTP flow if present;
- token/verification expiry;
- repeated/duplicate verification attempts;
- MFA flow when present;
- logout behavior;
- authenticated route protection after refresh/deep link.

If exact brute-force/lockout thresholds are requirements, verify them safely without creating service disruption.

## 3. Session and token behavior

Verify as applicable:

- expired session/token is rejected;
- malformed token is rejected;
- logout/revocation behavior matches the intended architecture;
- privilege changes do not leave stale privileged sessions beyond documented behavior;
- refresh token rotation/reuse behavior if used;
- session cookies use appropriate security attributes according to deployment model;
- sensitive tokens are not exposed in URLs/logs where avoidable.

Do not label every stateless JWT logout model a vulnerability; compare behavior to the approved session design and risk requirements.

## 4. Authorization and object ownership

This is a mandatory Stage 10 area for multi-role systems.

For every release-critical protected action:

- allowed role succeeds;
- forbidden role fails server-side;
- anonymous access fails when required;
- owner access succeeds when ownership is intended;
- non-owner access fails;
- object identifier substitution does not bypass access controls;
- list/search results do not leak unauthorized objects;
- bulk endpoints enforce the same boundaries;
- export/download endpoints enforce access control;
- admin-only fields cannot be changed by normal users through direct API requests.

Treat UI-only hiding as insufficient.

## 5. Input and output handling

Use benign test strings to verify defensive behavior around:

- SQL/ORM query construction;
- HTML/script rendering;
- command/path-like inputs when such sinks exist;
- template rendering;
- redirect URLs;
- JSON/object mass assignment;
- server-side URL fetching if present;
- filename/path handling.

Do not execute destructive commands or weaponized payloads. The objective is to verify validation, encoding, parameterization, allowlisting, and safe error handling.

## 6. CSRF and browser request context

For cookie-authenticated state-changing applications, verify the project has an appropriate CSRF strategy or same-site/origin design. Test safely whether cross-origin-like or missing-token requests are rejected according to that design.

For bearer-token APIs not vulnerable to ambient-cookie CSRF in the same way, do not mechanically require CSRF tokens; evaluate the actual auth model.

## 7. File upload/download

Verify:

- server-side type/size validation;
- extension/MIME mismatch handling;
- storage path isolation;
- unsafe filename handling;
- authorization for download/view;
- object URLs are not unintentionally public when files are private;
- failed upload does not leave orphaned sensitive objects;
- active content is not served in an unsafe context when the product design forbids it.

Use benign representative files.

## 8. Sensitive data and secrets

Inspect critical responses/UI/logs for accidental exposure of:

- passwords/password hashes;
- access/refresh tokens;
- API keys;
- private credentials;
- unnecessary PII;
- full financial identifiers beyond requirements;
- internal stack/configuration secrets.

Verify normal users cannot retrieve privileged fields merely by changing API parameters or calling alternate endpoints.

## 9. Logging and error exposure

Check that:

- auth failures are diagnosable without logging secrets;
- privileged actions are logged/audited when project requirements demand it;
- stack traces/internal SQL are not exposed to end users in production-like mode;
- correlation/request IDs are available when architecture provides them;
- sensitive body/header values are redacted according to project conventions.

## 10. Security headers and transport assumptions

When deployment-like response headers are available, inspect applicable controls such as CSP, frame restrictions, MIME sniffing protection, referrer policy, HSTS only in appropriate HTTPS contexts, and cookie attributes.

Do not block Stage 10 merely because a header belongs to Stage 11 infrastructure if application code does not own it. Record the ownership boundary clearly.

## 11. Rate and abuse controls

For high-risk public endpoints such as login, OTP, password reset, upload, expensive search, or public form submission, verify configured rate/abuse controls when the project requires them.

Use small safe test volumes. Do not perform denial-of-service testing.

## 12. Integration trust boundaries

Check:

- inbound webhook authentication/signatures when required;
- external callback parameters are validated;
- outbound secrets stay server-side;
- external errors do not leak secrets;
- replay behavior is safe;
- redirect/callback destinations are constrained where required.

## 13. Regression after fixes

For any security-related fix:

1. preserve a minimal safe reproduction;
2. add automated regression coverage where feasible;
3. verify the original bypass no longer works;
4. verify the legitimate flow still works;
5. test adjacent roles/objects/endpoints sharing the same guard/middleware;
6. inspect whether the patch created a new privilege or data-flow inconsistency.

## 14. Severity guidance

Security context alone does not define severity.

Consider:

- attacker prerequisites;
- authentication required or not;
- cross-tenant/privilege impact;
- sensitive data exposure scope;
- ability to alter/delete critical data;
- exploit reliability;
- affected user population;
- compensating controls;
- safe workaround.

Examples likely P0/P1 include trivially exploitable admin takeover, broad cross-tenant sensitive-data access, severe unauthenticated critical mutation, or corrupting authorization bypass. Minor missing hardening with no practical sensitive impact may be P2/P3 depending on context.

## 15. Exit criteria

Before Stage 10 PASS:

- no known serious authentication/authorization bypass remains;
- no known P0/P1 sensitive-data exposure remains;
- protected release-critical operations have server-side denial coverage;
- security regressions introduced by fixes are closed;
- any unverified external/security control is documented with ownership and release impact;
- dedicated security audit requirements are not falsely represented as completed by this stage.
