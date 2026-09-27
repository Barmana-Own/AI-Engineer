# API Contract Standards

## Contents
1. Contract principles
2. Resource and operation design
3. HTTP methods and status semantics
4. Request/response schema rules
5. Data representation
6. Validation
7. Lists, pagination, filtering, sorting, search
8. Bulk operations
9. Concurrency and conditional operations
10. Idempotency interaction
11. File transfer
12. Caching
13. Async operations and webhooks
14. Versioning and compatibility
15. OpenAPI quality checklist

## 1. Contract principles

Design contracts for stability, explicitness, and client usefulness.

A production API contract should be:
- deterministic;
- backward-conscious;
- machine-readable where practical;
- independent from database row shape;
- explicit about failure semantics;
- bounded against accidental unbounded work;
- consistent across related operations.

Preserve an existing coherent convention rather than imposing a new one endpoint-by-endpoint.

## 2. Resource and operation design

For REST-style HTTP APIs:
- use nouns for resources;
- use plural resource collections when repository convention does so;
- use nested paths only when ownership/context is real and depth remains manageable;
- use command/action endpoints for genuine domain transitions that do not map cleanly to CRUD;
- do not encode business verbs inconsistently across otherwise resource-oriented APIs.

Examples of reasonable domain actions:
- `POST /orders/{id}/cancel`
- `POST /invoices/{id}/issue`
- `POST /jobs/{id}/retry`

Do not create a generic `/doAction` endpoint when domain meaning can be explicit.

## 3. HTTP methods and status semantics

Use project conventions first. For conventional REST:
- `GET` - read, safe, no intended state mutation;
- `POST` - create or non-idempotent command unless idempotency is explicitly added;
- `PUT` - full replacement/upsert only when semantics are truly replacement-like;
- `PATCH` - partial update;
- `DELETE` - remove/cancel according to domain contract.

Typical success statuses:
- `200` for successful read/update with representation;
- `201` for creation, with resource identifier/location when appropriate;
- `202` for accepted asynchronous work when completion occurs later;
- `204` for success with intentionally empty body.

Typical client/problem statuses when repository conventions allow:
- `400` malformed request syntax/shape that cannot be interpreted;
- `401` unauthenticated when auth is enforced;
- `403` authenticated but forbidden when authz is enforced;
- `404` resource not found or intentionally concealed;
- `409` state conflict/duplicate incompatible operation;
- `412` failed precondition when conditional requests are used;
- `413` payload too large;
- `415` unsupported media type;
- `422` structurally valid request with semantic/field validation failure, when adopted consistently;
- `429` rate limited when relevant.

Do not alternate between 400 and 422 for identical validation classes without a documented convention.

## 4. Request/response schema rules

Separate transport DTOs from persistence entities when coupling would leak internals or destabilize clients.

For every field decide:
- required vs optional;
- nullable vs non-null;
- writable vs read-only;
- server-generated vs client-provided;
- default behavior when omitted;
- allowed enum/range/format;
- backward compatibility expectation.

Do not use `null`, missing, empty string, and empty collection interchangeably unless the domain explicitly defines them as equivalent.

Avoid returning sensitive/internal fields merely because they exist on a database model.

## 5. Data representation

### Identifiers
Treat IDs as opaque client values. Do not require clients to infer meaning from an ID format.

### Dates and times
Prefer ISO 8601/RFC 3339-style interoperable timestamp representations. Preserve timezone/offset semantics. Do not silently reinterpret local wall-clock values as UTC.

If domain data is date-only, model it as date-only rather than midnight timestamp.

### Money and decimals
Avoid binary floating-point semantics for monetary values. Follow established project convention such as decimal string, integer minor units, or explicit money object. Document currency and scale.

### Enums
Use stable machine values. UI labels belong in UI/localization layers unless the API contract explicitly includes display labels.

### Booleans
Do not overload booleans for multi-state workflows. Use explicit state enums when more than two meaningful states exist.

## 6. Validation

Validate at appropriate boundaries without duplicating contradictory rule sets.

Transport validation may enforce:
- type/shape;
- required fields;
- length/format;
- list limits;
- allowed media type;
- basic cross-field constraints.

Domain/application validation owns business invariants.

Return stable field identifiers for client-correctable validation errors when the frontend needs field mapping.

Do not echo sensitive submitted values in error payloads.

## 7. Lists, pagination, filtering, sorting, search

Never expose unbounded production collection reads for potentially growing data.

Choose one pagination style per API family:
- offset/page for simple/admin/reporting cases where stable offset semantics are acceptable;
- cursor for high-change/high-scale datasets where stable continuation matters.

Document:
- default limit/page size;
- maximum limit/page size;
- cursor encoding treated as opaque;
- deterministic default sort;
- tie-breaker field for stable ordering;
- behavior for invalid/expired cursor;
- total count availability and cost.

Filtering:
- whitelist filterable fields/operators;
- reject or ignore unknown filters consistently;
- bound list filters;
- avoid passing raw filter fragments into persistence queries.

Sorting:
- whitelist sortable fields;
- define direction syntax;
- define deterministic fallback order.

Search:
- distinguish free-text search from exact filters;
- bound query length;
- document normalization if relevant.

Field selection/projection should be added only when it materially helps the product and can be implemented safely.

## 8. Bulk operations

For bulk mutation define:
- maximum batch size;
- atomic vs partial-success behavior;
- per-item error reporting;
- idempotency behavior;
- ordering guarantees;
- asynchronous threshold for large work.

Do not leave partial-success behavior implicit.

## 9. Concurrency and conditional operations

For race-sensitive updates decide whether the system uses:
- version fields;
- updated-at comparison;
- ETag/If-Match;
- database optimistic locking;
- domain conflict detection.

Return a clear conflict/precondition error when stale clients attempt unsafe updates.

Do not silently overwrite state when lost updates would harm correctness.

## 10. Idempotency interaction

Use `error-reliability-standards.md` for full rules.

At contract level define:
- whether an idempotency key is required/optional;
- header/field name;
- key scope;
- duplicate replay behavior;
- behavior when same key is reused with a different payload;
- retention/TTL expectations if externally visible.

## 11. File transfer

For uploads define:
- accepted media types using content validation, not extension alone;
- maximum file size;
- maximum file count;
- multipart/direct-upload/presigned strategy;
- metadata fields;
- checksum when needed;
- quarantine/scanning hook point when security architecture requires it;
- storage indirection rather than exposing local paths;
- error semantics for rejected files.

For downloads define:
- stable resource identifier;
- content type;
- content disposition when relevant;
- authorization hook point;
- range/streaming support if large files need it;
- expiry semantics for signed URLs if used.

Never expose a server filesystem path as an API contract.

## 12. Caching

Add caching semantics only when useful.

When applicable define:
- Cache-Control behavior;
- ETag/Last-Modified semantics;
- invalidation ownership;
- private vs public cacheability;
- no-store handling for sensitive responses.

Do not cache personalized/sensitive data through shared caches by accident.

## 13. Async operations and webhooks

For asynchronous commands consider:
- `202 Accepted` with operation/job resource;
- status polling endpoint;
- terminal states;
- failure result shape;
- cancellation if supported.

For incoming webhooks/callbacks define:
- stable endpoint;
- provider event identifier;
- duplicate handling;
- payload validation/signature hook point for Stage 07/security stage;
- retry-safe processing;
- response timing;
- dead-letter/manual recovery expectations if architecture supports them.

For outgoing webhooks define event versioning, retries, signing/security handoff, and delivery observability according to project scope.

## 14. Versioning and compatibility

Do not add complex versioning to a pre-launch internal API without need. Do not ignore compatibility for already-consumed/public APIs.

Possible strategies:
- path versioning;
- header/media-type versioning;
- additive unversioned evolution for private early-stage APIs.

Record the chosen strategy and rationale.

Backward-compatible changes commonly include additive optional fields. Breaking changes may include:
- removing/renaming fields;
- changing field type or meaning;
- tightening requiredness without migration;
- changing status/error semantics clients depend on;
- changing default sort/pagination in a way that breaks continuation.

## 15. OpenAPI quality checklist

For every production operation verify:
- unique operationId where project convention uses it;
- summary/description sufficient to identify purpose;
- tags grouping related operations;
- path/query/header parameters;
- request schema/media type;
- success responses;
- expected client error responses;
- common server/dependency error shape;
- pagination schema;
- upload/download content types;
- idempotency/precondition headers when applicable;
- examples only when they add clarity and contain no secrets/sensitive data;
- schemas reuse components where useful;
- documented required/nullable/readOnly/writeOnly behavior matches implementation.
