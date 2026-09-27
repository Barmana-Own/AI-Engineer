# API Contract and Compatibility

## Table of contents

1. Contract ownership
2. Stage 03 compatibility
3. DTO boundaries
4. Pagination/filtering/sorting
5. Versioning and breaking changes
6. Upload/download contracts
7. Webhooks/callbacks
8. Generated specifications

## 1. Contract ownership

Stage 04 owns backend transport semantics that are necessary to implement validated use cases, while later integration stages may complete full frontend-backend wiring.

Do not let route shape become accidental. Record the public or internal API contract that implemented handlers expose.

For each critical endpoint/operation define:

- method/operation name;
- path/topic when applicable;
- request input contract;
- response contract;
- actor/authorization requirement;
- stable error codes;
- idempotency semantics if applicable;
- pagination/filter/sort semantics for collections;
- compatibility/deprecation considerations.

## 2. Stage 03 compatibility

Treat Stage 03 frontend expectations as evidence, not absolute truth when they conflict with validated product/security requirements.

Compare frontend assumptions against backend semantics for:

- field names/types;
- nullable/optional behavior;
- loading/empty/error states;
- pagination;
- optimistic UI assumptions;
- status/state names;
- date/time format and timezone;
- money/currency representation;
- error codes;
- authorization-sensitive fields;
- upload/download behavior.

When Stage 04 must change an expectation:

1. document the mismatch;
2. preserve compatibility if safe and low-cost;
3. otherwise record the required Stage 06/frontend integration change explicitly.

Do not silently return extra sensitive fields because the frontend mock included them.

## 3. DTO boundaries

Use transport DTOs/contracts at the trust boundary.

Do not expose:

- ORM entities;
- internal aggregate objects with private fields;
- vendor SDK models;
- raw exception structures.

Map only fields required by the contract.

Distinguish absent, null, empty, and default values intentionally.

## 4. Pagination, filtering, and sorting

For collection endpoints define:

- pagination model (offset/page or cursor) based on product/query needs;
- default and maximum page size;
- stable ordering;
- allowed filter fields/operators;
- allowed sort fields/directions;
- tenant/authorization filters that cannot be overridden by the client.

Record Stage 05 query/index implications without selecting final indexes now.

Do not expose arbitrary ORM query/filter syntax to clients.

## 5. Versioning and breaking changes

Preserve existing public contracts unless a change is required for correctness/security.

Classify changes as:

- additive/backward-compatible;
- behavior correction with compatibility risk;
- breaking.

For breaking changes, record:

- affected consumers;
- migration/deprecation path;
- why compatibility cannot be preserved safely;
- later-stage integration work.

Do not add versioning machinery preemptively when the product has no compatibility need.

## 6. Upload/download contracts

When files are involved, define:

- accepted size/type constraints;
- metadata contract;
- ownership/access rules;
- upload flow (direct, presigned, multipart, server-mediated) as an architectural requirement only when known;
- download authorization;
- range/streaming needs if relevant;
- Stage 05 metadata persistence needs;
- storage-provider abstraction when applicable.

Do not trust filename extension or client content type as proof of file content.

## 7. Webhooks and callbacks

For inbound webhooks/callbacks define:

- provider/source identity;
- verification/signature requirement;
- replay protection/idempotency;
- event ID uniqueness scope;
- acknowledgement semantics;
- retry behavior expected from provider;
- asynchronous processing need;
- safe logging/redaction.

For outbound webhooks define delivery, signing, retry, ordering, and idempotency expectations.

## 8. Generated specifications

If OpenAPI, GraphQL schema, protobuf, or another source contract exists:

- change the source specification rather than generated output where project conventions require generation;
- run generation/contract validation commands when available;
- keep generated client/server artifacts synchronized;
- record breaking changes;
- never edit generated artifacts manually without a repository-specific reason.
