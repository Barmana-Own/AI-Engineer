# Authorization, RBAC, ABAC, and Privileged Operations

## Contents

- [Purpose](#purpose)
- [1. Build the authorization vocabulary](#1-build-the-authorization-vocabulary)
- [2. Authorization matrix](#2-authorization-matrix)
- [3. Deny-by-default](#3-deny-by-default)
- [4. Enforcement layers](#4-enforcement-layers)
- [5. RBAC](#5-rbac)
- [6. ABAC/contextual rules](#6-abaccontextual-rules)
- [7. Ownership](#7-ownership)
- [8. Tenant-scoped roles](#8-tenant-scoped-roles)
- [9. Privileged operations](#9-privileged-operations)
- [10. Role/permission assignment](#10-rolepermission-assignment)
- [11. Cached authorization](#11-cached-authorization)
- [12. Background jobs and async processing](#12-background-jobs-and-async-processing)
- [13. GraphQL/RPC/batch endpoints](#13-graphqlrpcbatch-endpoints)
- [14. File/object authorization](#14-fileobject-authorization)
- [15. Impersonation](#15-impersonation)
- [16. Required negative tests](#16-required-negative-tests)
- [Completion condition](#completion-condition)


## Purpose

Use this reference to turn business roles into enforceable server-side authorization policies. Authentication proves identity; authorization decides whether that identity may perform a specific action on a specific resource in a specific context.

## 1. Build the authorization vocabulary

Define separately:

- subjects/actors;
- roles;
- permissions/capabilities;
- actions;
- resources;
- scopes;
- attributes/conditions;
- tenant/ownership constraints;
- high-risk operations;
- system/service identities.

Do not use one overloaded `role` string when the product needs tenant-scoped membership, global platform roles, resource ownership, and contextual rules.

## 2. Authorization matrix

Create `docs/security/07-authorization-matrix.md` with a row for every protected action/resource combination.

Recommended columns:

| Action ID | Route/service action | Resource | Allowed actor/role | Required permission/policy | Scope/tenant rule | Additional condition | Enforcement point | Positive test | Negative test |
|---|---|---|---|---|---|---|---|---|---|

Use stable action IDs such as `AUTHZ-USER-READ`, `AUTHZ-TENANT-BILLING-UPDATE`, or project-specific equivalents.

The matrix must cover APIs, not merely pages.

## 3. Deny-by-default

Choose an implementation where protected actions are denied unless an explicit allow rule succeeds.

Avoid patterns such as:

- `if role == blocked then deny else allow`;
- route is protected only because the frontend hides it;
- any authenticated user may call a new endpoint until someone adds a deny check;
- missing permission data interpreted as allow;
- authorization service timeout/error interpreted as allow.

For an unknown role/permission/action, fail closed.

## 4. Enforcement layers

Use the minimum number of consistent enforcement layers necessary, commonly:

1. route/transport authentication;
2. coarse route/action authorization;
3. service/domain authorization for resource/context rules;
4. query/repository scoping for ownership/tenant isolation;
5. downstream service policy if trust boundaries require re-verification.

Route-level role checks are not enough when the action depends on which resource is being modified.

## 5. RBAC

Use RBAC when permissions map cleanly to roles.

Good model:

`User -> Membership/Role -> Permission -> Action`

Prefer stable permission names over scattering role-name comparisons throughout controllers.

Examples of permission semantics:

- `users.read`;
- `users.manage`;
- `billing.read`;
- `billing.manage`;
- `reports.export`;
- `roles.assign`;
- `api_keys.manage`.

Avoid granting a broad role simply because one endpoint needs one capability.

## 6. ABAC/contextual rules

Use attributes when role alone is insufficient, such as:

- tenant membership;
- resource owner;
- record status;
- region/business unit;
- assigned case/team;
- monetary threshold;
- time/risk state;
- step-up authentication freshness;
- feature/product entitlement.

Make ABAC conditions explicit and test both boundary sides.

Do not let attacker-controlled request fields become trusted attributes without server validation.

## 7. Ownership

Ownership is an authorization rule, not a filter convenience.

For a resource owned by user A:

- look up the resource by identifier plus trusted owner/tenant scope when practical;
- return a safe not-found/forbidden response according to product leakage policy;
- never fetch by ID, serialize sensitive fields, then decide ownership on the client;
- enforce ownership on update/delete/download/export as well as read;
- enforce on nested resources and attachments.

## 8. Tenant-scoped roles

Distinguish global platform roles from tenant roles.

Example:

- platform administrator: global operational capability;
- tenant owner/admin: capability only inside one tenant;
- tenant member: scoped permissions inside membership;
- support agent: explicit support capabilities, not equivalent to platform admin.

A user who is admin in tenant A must not become admin in tenant B because the token contains `role=admin` without tenant scope.

## 9. Privileged operations

Identify high-impact operations and require dedicated permissions, not merely generic `admin` status when practical.

Examples:

- role assignment;
- tenant ownership transfer;
- user disable/delete;
- MFA reset;
- API key creation/revocation;
- billing/payment changes;
- data export;
- impersonation;
- security configuration;
- audit-log access;
- destructive bulk actions.

For especially sensitive actions combine permission + recent authentication/step-up + audit event.

## 10. Role/permission assignment

Treat role assignment as an authorization problem itself.

Rules:

- caller must have a dedicated assignment capability;
- caller cannot assign roles above its allowed grant set;
- tenant administrator cannot assign global platform roles;
- request body cannot directly set arbitrary permissions without validation;
- protect against mass assignment of `role`, `isAdmin`, `permissions`, `tenantId`, `ownerId`, `verified`, or similar fields;
- audit old/new role and actor/target/tenant;
- test self-escalation attempts.

## 11. Cached authorization

If permissions/membership are cached or embedded in tokens:

- document maximum stale window;
- invalidate/update cache on privilege removal;
- ensure high-risk revocation can take effect inside required security window;
- do not cache negative/positive decisions across tenants/resources incorrectly;
- include tenant/resource/policy version in cache key when needed.

Test removal, not only grant.

## 12. Background jobs and async processing

Authorization can be lost when work moves to a queue.

For queued jobs:

- record trusted actor/tenant/resource context at enqueue time;
- validate that the action was authorized when enqueued;
- decide whether authorization must be re-checked at execution time for long delays/high-risk actions;
- never trust arbitrary actor/tenant IDs in a public queue message;
- preserve audit attribution.

## 13. GraphQL/RPC/batch endpoints

For GraphQL/RPC/batch:

- enforce at resolver/method/resource level;
- prevent one authorized parent query from exposing unauthorized nested objects;
- authorize each operation in a batch;
- constrain field-level sensitive data where required;
- test aliases/fragments/nested paths or method variants that may bypass coarse guards.

## 14. File/object authorization

Signed URLs or object paths do not replace authorization unless the signed URL is intentionally the authorization capability with a limited scope/lifetime.

For private files:

- authorize before issuance/download;
- bind signed URL to exact object and short lifetime;
- avoid predictable public buckets/paths;
- revoke/expire access as product risk requires;
- enforce tenant/owner scope.

## 15. Impersonation

Use a dedicated policy. Never implement as `set userId` from request.

Require:

- privileged permission;
- explicit target selection;
- optional step-up;
- real actor retained separately from effective subject;
- strong audit event;
- visible operator state;
- explicit end;
- optional restrictions on security/financial actions.

## 16. Required negative tests

For each privileged action include at least:

- anonymous caller;
- authenticated caller without permission;
- lower role attempting higher-role action;
- self-escalation or privileged-field mass assignment;
- wrong tenant;
- wrong owner;
- removed role/membership using a still-valid session/token;
- alternate HTTP method or endpoint variant where relevant;
- direct service invocation test if route guards could be bypassed internally;
- admin/support action without required step-up when applicable.

## Completion condition

Authorization design is complete only when every privileged operation in the discovered API/action inventory maps to an explicit policy and to positive/negative executable evidence.
