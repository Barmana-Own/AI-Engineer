# API Security and Business-Logic Abuse Review

## Table of contents

1. API inventory
2. Resource and function controls
3. Property exposure and mass assignment
4. Business-flow abuse
5. State machines
6. Replay and idempotency
7. Concurrency and race conditions
8. Resource consumption and denial-of-wallet
9. Enumeration and bulk operations
10. Payments/credits/quotas
11. Async jobs and queues
12. Unsafe third-party API consumption
13. Versioning and shadow endpoints
14. Test design

## 1. API inventory

Inventory all API surfaces, including internal/admin/mobile/versioned routes, GraphQL/RPC, server actions, WebSockets, workers and webhook-triggered actions. Compare code routes with published API specs if both exist. Identify undocumented/deprecated routes that remain reachable.

For each material operation record:

- caller identity;
- object/resource;
- authorization policy;
- state transition;
- input schema;
- side effects;
- external calls;
- cost/resource impact;
- idempotency expectations.

## 2. Resource and function controls

Apply object/property/function authorization from `auth-and-access-control.md` to every API, not only CRUD routes. Check nested resource routes, search endpoints, exports, attachments, history/audit views and action endpoints.

A UUID is not an authorization control.

## 3. Property exposure and mass assignment

Review both request and response schemas. Check whether serializers expose internal fields, secrets, moderation data, internal IDs or cross-tenant references. Check whether update/create schemas accept protected fields.

Prefer explicit DTO/schema allowlists for both read and write shapes.

## 4. Business-flow abuse

Model security-sensitive business flows as ordered invariants rather than individual endpoints.

Examples:

- draft -> submitted -> reviewed -> approved -> fulfilled;
- cart -> quote -> payment initiation -> provider callback -> paid -> shipment;
- invite -> accept -> membership;
- upload -> scan -> approve -> publish;
- request -> expert assignment -> completion -> payout;
- password reset -> token use -> invalidation.

Ask:

- Can a caller skip a required state?
- Can they move backward to regain value?
- Can they invoke the final action directly?
- Can client-controlled state replace authoritative server state?
- Can one flow's token/reference be reused in another flow?
- Can a denied/expired/cancelled object be revived?
- Can a user repeat a one-time benefit?
- Can approval be self-granted through a generic update endpoint?

## 5. State machines

Represent important states/transitions explicitly in the report or tests. Validate transition source state, actor permission, invariant and atomicity server-side.

Do not rely solely on the UI to disable invalid actions.

For generic PATCH/update endpoints, ensure status fields cannot bypass domain transition rules.

## 6. Replay and idempotency

Review operations that must not execute twice:

- payments/refunds;
- order creation;
- balance/credit changes;
- email/SMS notifications;
- webhook processing;
- provisioning;
- coupon/redemption;
- export jobs;
- invite acceptance;
- destructive actions.

Use stable idempotency keys, unique constraints, transaction semantics or durable processed-event IDs as appropriate. Verify retries after timeouts do not duplicate side effects.

For signed callbacks, signature verification alone does not prevent replay if an old valid event can be processed repeatedly.

## 7. Concurrency and race conditions

Identify read-check-write sequences involving scarce/financial/privileged state. Examples:

- check balance then debit;
- check stock then reserve;
- check coupon unused then redeem;
- check role/state then mutate;
- check upload quota then store;
- approve only once;
- create unique membership/invite.

Use transactions, atomic updates, row/record locks, unique constraints or compare-and-set semantics appropriate to the data store. A pre-check without an atomic enforcement mechanism may race.

Test safe concurrent behavior locally when feasible without load generation. A small deterministic concurrency test is preferred over stress testing.

## 8. Resource consumption and denial-of-wallet

Review endpoints that trigger:

- AI/model calls;
- image/video/PDF processing;
- large database queries;
- bulk exports;
- email/SMS/OTP;
- object storage transfer;
- third-party paid APIs;
- queue fan-out;
- report generation;
- unbounded pagination/search;
- regex/parser-heavy work.

Check authentication, quotas, size/page limits, timeouts, cancellation, concurrency caps, caching and cost attribution where appropriate.

Do not perform denial-of-service testing. Validate controls from code and small safe test cases.

## 9. Enumeration and bulk operations

Check whether sequential IDs, search/autocomplete, password reset, invite, account lookup, order tracking or validation endpoints leak existence/sensitive metadata.

Bulk endpoints must enforce authorization per item or at an equivalent trusted set boundary. One authorized object in a list must not authorize the whole list.

Exports must apply the same tenant/role/filter policy as interactive views.

## 10. Payments, credits, quotas and economic state

When present, verify authoritative values come from trusted server/provider state, not client input. Review:

- amount/currency/product price;
- discount/coupon eligibility;
- credit/balance mutation;
- payment status transition;
- provider callback signature and event identity;
- duplicate callback handling;
- refund ownership/limits;
- order-to-payment binding;
- stale quote reuse;
- negative/overflow/precision edge cases;
- quota reset/consumption.

Never test a real payment provider by attempting unauthorized free purchases. Use local/provider sandbox fixtures if authorized.

## 11. Async jobs and queues

Treat queued messages as untrusted unless integrity/authenticity is guaranteed. Validate message schema and authoritative IDs again at the worker boundary. Check:

- tenant/user context propagation;
- privilege of worker credentials;
- poison-message retry loops;
- duplicate delivery;
- idempotency;
- dead-letter handling;
- serialized object trust;
- whether a user can enqueue an internal-only action indirectly.

## 12. Unsafe third-party API consumption

Do not assume vendor responses are safe because the vendor is trusted. Validate required fields/types/limits. Bound redirects/timeouts/response sizes. Avoid directly reflecting vendor error/detail data to users. Treat vendor HTML/URLs/files as untrusted content according to sink.

## 13. Versioning and shadow endpoints

Search for:

- `/v1`, `/v2`, legacy routers;
- disabled UI features whose API remains mounted;
- old admin/debug endpoints;
- test routes;
- alternate HTTP methods;
- duplicate route registration;
- deprecated GraphQL fields/resolvers.

Older versions often miss newer authorization/validation middleware.

## 14. Test design

For high-value flows, write negative tests for:

- skipped state;
- repeated one-time action;
- stale/cancelled resource;
- modified object/tenant identifier;
- protected-field over-posting;
- duplicate callback/event;
- wrong order/payment binding;
- unauthorized bulk item;
- excessive but bounded page/size value;
- concurrent double-action using a small deterministic test where needed.

Assert both response behavior and persisted side effects. A request returning 403 is insufficient if the database side effect already occurred.
