# Multi-Tenancy, Ownership, and Isolation

## Contents

- [Purpose](#purpose)
- [Core rule](#core-rule)
- [Tenant context](#tenant-context)
- [Query scoping](#query-scoping)
- [Direct object reference testing](#direct-object-reference-testing)
- [Nested resources](#nested-resources)
- [Creation](#creation)
- [Update and mass assignment](#update-and-mass-assignment)
- [Delete/archive](#deletearchive)
- [Bulk operations](#bulk-operations)
- [Search/list/filter](#searchlistfilter)
- [Files and object storage](#files-and-object-storage)
- [Caches](#caches)
- [Background jobs](#background-jobs)
- [Realtime/WebSocket](#realtimewebsocket)
- [Exports/reports/analytics](#exportsreportsanalytics)
- [Tenant administration](#tenant-administration)
- [Cross-tenant test matrix](#cross-tenant-test-matrix)
- [Completion condition](#completion-condition)


## Purpose

Use this reference whenever records, files, actions, or credentials are owned by a user, organization, workspace, customer, account, project, store, department, or other isolation boundary.

## Core rule

A client-provided tenant/owner/resource identifier identifies what the client wants to access; it does not prove the client is allowed to access it.

Derive or verify authorization against trusted server-side membership/ownership state on every protected operation.

## Tenant context

Define the authoritative tenant context source:

- server session membership;
- token claim plus server freshness policy;
- URL/path tenant identifier verified against membership;
- subdomain/domain mapping verified against tenant;
- API key bound to tenant;
- service identity bound to tenant scope.

If several are present, define consistency checks. Reject conflicting tenant context rather than selecting whichever is most permissive.

## Query scoping

Prefer query patterns that make cross-tenant fetches structurally difficult.

Examples:

- query by `resource_id AND tenant_id`;
- repository method requires tenant scope parameter;
- ORM global/query scope when safe and testable;
- row-level security when appropriate and correctly configured;
- tenant-specific database/schema boundary if architecture uses it.

Do not fetch globally by ID and rely on frontend filtering.

## Direct object reference testing

For every resource family test:

- another user's ID in same tenant;
- another tenant's ID;
- parent from authorized tenant + child from unauthorized tenant;
- child from authorized tenant + parent from unauthorized tenant;
- sequential/guessable identifiers;
- UUIDs copied from another account (unguessable is not authorization);
- archived/deleted/disabled records;
- alternate endpoint/version for the same object.

## Nested resources

Validate parent-child-tenant consistency.

Example: `/tenants/A/projects/P/documents/D`

Verify:

- caller belongs to tenant A with required permission;
- project P belongs to A;
- document D belongs to P/A;
- caller has action permission for D;
- request cannot substitute D from tenant B while keeping path A/P.

Do not trust nested IDs independently.

## Creation

On create:

- derive owner/tenant from trusted context when possible;
- ignore/reject unauthorized `ownerId`, `tenantId`, `createdBy`, `role`, or privileged fields;
- verify referenced foreign keys belong to the same tenant/allowed scope;
- prevent cross-tenant relation injection.

## Update and mass assignment

Use explicit writable-field allowlists or schema validation. Prevent changes to ownership, tenant, creator, role, security status, verification status, or other protected fields unless a dedicated authorized operation exists.

Test JSON body over-posting/mass assignment.

## Delete/archive

Deletion is an authorization action. Verify tenant/owner scope and any stronger permission. Ensure soft-deleted records do not become accessible through an alternate endpoint or export.

## Bulk operations

Bulk endpoints frequently bypass per-resource checks.

For bulk update/delete/export:

- scope the candidate set by tenant and permission first;
- reject or safely handle IDs outside scope;
- avoid partial unauthorized disclosure through per-ID error differences when harmful;
- audit high-impact bulk actions;
- test mixed authorized/unauthorized ID batches.

## Search/list/filter

- apply tenant/owner scope before pagination/counting where possible;
- avoid exposing cross-tenant existence through total counts or filters;
- secure full-text/search indexes with equivalent tenant filters;
- test sort/filter combinations and admin-only fields.

## Files and object storage

For private objects:

- store tenant/owner metadata authoritatively;
- authorize metadata and download separately if paths differ;
- signed URLs must be generated only after authorization;
- short-lived signed URLs should reference exactly one allowed object/action;
- upload destinations must be tenant-scoped;
- prevent object-key substitution;
- secure thumbnails/previews/derived assets equivalently.

## Caches

Cache keys must include the isolation dimensions that affect authorization.

Avoid:

- `cache[resourceId]` if same IDs or policies can differ by tenant;
- caching an authorized serialized response and serving it to another user;
- CDN caching private authenticated responses without correct variation/private controls.

Test authorization after role/membership changes and cross-tenant requests with warm caches.

## Background jobs

Jobs must carry trusted tenant/resource context. Do not let a user-controlled queue payload select another tenant. Re-check authorization at execution time when the delay/risk requires it.

## Realtime/WebSocket

Authorize channel/topic subscription by tenant/resource. Re-check membership when long-lived connection state becomes stale according to the revocation model.

Never authorize `subscribe tenant:<id>` merely because the socket is authenticated.

## Exports/reports/analytics

Exports can bypass row-level application checks.

Verify:

- query scope;
- report parameter tenant binding;
- generated file access;
- async export job tenant context;
- notification/download link scope;
- expiration and deletion of generated artifacts.

## Tenant administration

For membership/role management:

- tenant admin can manage only its tenant;
- tenant admin cannot grant platform-global roles;
- role grant set is constrained;
- ownership transfer has stronger policy;
- last-owner removal is handled safely;
- tenant deletion/suspension invalidates access deterministically.

## Cross-tenant test matrix

For every high-value resource/action include:

| Case | Expected |
|---|---|
| Same tenant + allowed permission | Allow |
| Same tenant + missing permission | Deny |
| Different tenant + same role name | Deny |
| Different tenant + known resource ID | Deny |
| Removed membership + valid session | Deny within documented window |
| Mixed-tenant bulk IDs | Deny/filter according to explicit safe policy |
| Cross-tenant nested child ID | Deny |
| Cross-tenant file/object ID | Deny |

## Completion condition

Isolation is complete only when the protected data path, files, async work, caches, realtime channels, and administrative operations preserve the same tenant/ownership boundary and have executable negative tests.
