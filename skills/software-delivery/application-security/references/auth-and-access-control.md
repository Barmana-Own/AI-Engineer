# Authentication, Session, Authorization, and Tenant Isolation Review

## Table of contents

1. Identity inventory
2. Registration and account lifecycle
3. Password and credential handling
4. Login and anti-automation
5. Session/token lifecycle
6. Password reset and recovery
7. MFA and step-up controls
8. OAuth/OIDC and federated identity
9. Authorization model
10. Object/property/function authorization
11. Tenant isolation
12. Mass assignment and over-posting
13. Administrative boundaries
14. Testing matrix
15. Common failure patterns

## 1. Identity inventory

Identify every identity type:

- anonymous visitor;
- customer/user;
- tenant member;
- tenant administrator;
- platform operator/admin;
- support/impersonation role;
- API client/service account;
- worker/service identity;
- webhook/integration identity.

For each identity, determine credential type, creation path, revocation path, privilege source and intended data/action scope.

Do not assume UI visibility defines authorization.

## 2. Registration and account lifecycle

Review:

- duplicate identity rules;
- email/phone ownership verification where required by product risk;
- invite flows and invite expiry;
- activation/deactivation/suspension;
- account deletion and re-registration behavior;
- role assignment at creation;
- organization/tenant invitation acceptance;
- change of primary email/phone;
- handling of unverified accounts;
- stale invited/pending accounts.

Check whether client-supplied fields can select a privileged role, tenant, owner ID, approval status, credit/plan, or trust state.

## 3. Password and credential handling

When passwords exist:

- verify one-way adaptive password hashing using a suitable library and parameters;
- ensure plaintext passwords are never logged, stored, emailed or placed in analytics;
- ensure password comparison is performed through the hashing library;
- inspect password-change flow for current-session/identity verification appropriate to risk;
- check credential change invalidates or rotates relevant sessions/tokens according to policy;
- avoid custom password crypto.

Password policy should prioritize resistance to guessing and breached/common passwords where practical rather than arbitrary complexity theater. Do not invent policy that contradicts product requirements without documenting the change.

## 4. Login and anti-automation

Review:

- consistent generic errors where account enumeration matters;
- rate/abuse controls by account and source dimension as appropriate;
- lockout behavior that cannot be trivially weaponized to deny service;
- secure handling of login telemetry;
- remember-me behavior;
- brute-force resistance for privileged accounts;
- bot/abuse controls only when proportionate to actual exposure.

Rate limiting is not authorization and must not be used to compensate for broken identity controls.

## 5. Session/token lifecycle

Identify whether the application uses cookies, opaque sessions, JWTs, API keys, refresh tokens or a combination.

Verify:

- session/token creation occurs only after successful identity proof;
- tokens have appropriate audience/scope and are validated server-side;
- algorithms/keys are constrained rather than accepted from attacker-controlled metadata;
- expiry is enforced;
- refresh tokens are protected and rotated/revoked as architecture requires;
- logout meaningfully ends the session when the product promises logout;
- password reset/change, account suspension and privilege changes have defined session effects;
- stolen/replayed refresh tokens have bounded lifetime/rotation semantics where applicable;
- cookie sessions use appropriate `HttpOnly`, `Secure` and `SameSite` settings;
- session IDs are not accepted from URLs;
- session fixation is prevented;
- privileged actions can require recent authentication/step-up if product risk warrants it.

For JWTs specifically, inspect issuer, audience, signature verification, algorithm restrictions, time claims, key rotation assumptions, token type confusion and whether sensitive authorization state is trusted indefinitely from stale claims.

Do not treat decoding as verification.

## 6. Password reset and recovery

Trace the complete lifecycle:

1. request reset/recovery;
2. generate token/code;
3. deliver token/code;
4. verify token/code;
5. change credential;
6. invalidate token/code;
7. handle sessions after reset.

Verify tokens/codes are random enough, expire, are single-use where expected, are bound to the correct account/purpose, cannot be changed to target another user, and are not leaked through logs/referrers/URLs unnecessarily.

Check reset-request enumeration and abuse of email/SMS delivery.

## 7. MFA and step-up controls

When MFA exists:

- verify enrollment requires authenticated identity and appropriate re-authentication;
- protect secret/backup-code display;
- ensure recovery does not bypass MFA more weakly than intended;
- verify disable/reset operations are protected;
- rate-limit OTP verification appropriately;
- ensure trusted-device logic is bounded and revocable;
- verify admin/privileged MFA policy if required by project requirements.

Do not add MFA as a substitute for fixing broken authorization.

## 8. OAuth/OIDC and federated identity

When present, review:

- exact redirect URI handling;
- `state`/nonce/PKCE as applicable;
- issuer and audience validation;
- authorization-code exchange only on trusted backend when architecture requires it;
- token type and scope validation;
- account-linking rules;
- email/domain claims not being trusted beyond provider guarantees;
- logout/session semantics;
- provider token storage and redaction.

Use provider/standard documentation for protocol-specific details; do not test the identity provider itself.

## 9. Authorization model

Document the authorization decision inputs:

- identity/role;
- tenant/organization;
- object ownership;
- object state;
- action/function;
- relationship/membership;
- plan/entitlement;
- geographic/legal constraints if explicitly part of project requirements.

Identify the authoritative server-side enforcement point. Client-side route guards, hidden buttons and frontend role checks are UX, not security boundaries.

Prefer deny-by-default and centralized policy/middleware/domain service checks where compatible with architecture.

## 10. Object/property/function authorization

For each material endpoint/action, test:

### Object level (BOLA/IDOR)

Can changing an ID, slug, UUID, filename, storage key, nested resource ID or query selector reach another actor's object?

### Property level

Can the client read or write fields that should be hidden/protected, such as role, owner, price, approval state, internal notes, balance, tenant ID or moderation flags?

### Function level

Can a lower role call an admin/operator endpoint directly despite UI restrictions?

### Relationship level

Can a user attach/detach objects to another tenant/user, assign themselves to a privileged group, or reference inaccessible foreign keys?

Authorization must be evaluated after resolving the actual object/relationship, not solely from client-provided ownership/tenant fields.

## 11. Tenant isolation

For multi-tenant applications, identify the tenant boundary at every storage/query layer.

Review:

- tenant selection source;
- server-side tenant membership;
- queries missing tenant predicates;
- joins/subqueries that can cross tenant boundaries;
- cache keys lacking tenant namespace;
- object-storage prefixes/buckets and signed URLs;
- background jobs carrying tenant context;
- exports/search/indexes/analytics;
- global unique IDs that do not themselves enforce tenant ownership;
- admin/support cross-tenant capabilities and audit logging.

Test at least two tenants where local fixtures are available. Cross-tenant denial is a mandatory negative test for high-value resources.

## 12. Mass assignment and over-posting

Inspect request-to-model binding. Reject or ignore client-controlled protected fields by explicit allowlist/schema. Pay special attention to:

- role/permissions;
- owner/user/tenant IDs;
- status/state;
- price/discount/balance/credit;
- verification/approval flags;
- createdBy/updatedBy;
- internal/audit fields;
- storage paths;
- feature flags/plan entitlements.

ORM/model-level "hidden" serialization fields do not necessarily prevent write-time mass assignment.

## 13. Administrative boundaries

Review:

- admin routes and APIs independently from normal user routes;
- privilege assignment/revocation;
- support impersonation/delegation;
- destructive/bulk operations;
- export endpoints;
- audit visibility;
- privileged session timeout/step-up where required;
- whether one admin can affect another super-admin if product rules forbid it.

Privileged actions should have auditable actor, target and outcome context.

## 14. Testing matrix

Create negative tests for representative protected resources:

- anonymous -> authenticated-only action;
- User A -> User B object;
- same-tenant member -> restricted object/property;
- tenant A -> tenant B object;
- normal role -> privileged function;
- stale/revoked/suspended identity -> protected action;
- client-supplied protected field -> ignored/rejected;
- old token after security-sensitive lifecycle event -> expected denial/behavior.

Where a centralized authorization layer exists, test both the policy unit and representative endpoint integration so middleware wiring errors are caught.

## 15. Common failure patterns

Treat these as review prompts, not automatic findings:

- `isAuthenticated` used where ownership/role is required;
- frontend-only role checks;
- loading by ID before/without tenant predicate;
- trusting `userId`/`tenantId` from request body;
- decoding JWT without verifying signature/claims;
- logout endpoint returning success but leaving token/session valid contrary to product semantics;
- password reset token reusable after success;
- role embedded in a long-lived token and never revalidated after privilege change;
- admin endpoints mounted before authorization middleware;
- wildcard GraphQL/RPC resolvers with inconsistent policy checks;
- cached private response reused across users/tenants.
