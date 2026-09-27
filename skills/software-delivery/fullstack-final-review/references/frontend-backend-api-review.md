# Frontend, Backend and API Integration Review

Review the system as connected behavior, not isolated folders.

## Frontend review

For every critical actor and journey:

1. Enumerate production routes and navigation entry points.
2. Confirm route guards correspond to backend authorization, not only visibility logic.
3. Verify loading, empty, validation, authorization, server-error and success states.
4. Inspect form serialization for field names, types, dates, IDs, files and optional/null semantics.
5. Confirm API base URL/service discovery is correct for production builds.
6. Search for mock APIs, fixtures, hardcoded localhost URLs and dev fallbacks reachable in production.
7. Confirm token/cookie/session handling follows the backend's actual auth model.
8. Confirm logout clears client state and does not imply server-side revocation if the server does not provide it; document expected semantics.
9. Inspect client-side role checks for UX only; backend must independently enforce permission.
10. Verify critical responsive/accessibility behavior sufficient to complete the journey.
11. Verify error handling does not expose raw stack traces/secrets and does not mask failed mutations as success.
12. Verify optimistic UI has rollback/error handling when used.
13. Verify file uploads show actual failure/success state and enforce compatible client/server limits.

## Backend review

For representative critical modules:

1. Trace route → middleware → validation → controller → service/domain → repository/integration.
2. Ensure validation occurs before unsafe operations.
3. Ensure business invariants are server-side.
4. Ensure authorization occurs at the object/action boundary, not only at route grouping.
5. Verify error translation is deterministic and avoids sensitive internal leakage.
6. Verify transactions cover multi-step mutations requiring atomicity.
7. Verify concurrency/idempotency protections where duplicate submission can cause harm.
8. Verify background jobs have failure/retry/dead-letter semantics appropriate to importance.
9. Verify external integrations have timeout and error handling; avoid infinite retries or swallowed failures.
10. Verify configuration failures fail clearly rather than silently selecting insecure/mock defaults.
11. Verify health/readiness endpoints do not report healthy when essential dependencies are unavailable unless by explicit design.

## API contract review

Compare four sources when available:
- server implementation;
- OpenAPI/GraphQL/schema documentation;
- frontend/client usage;
- tests/examples.

Check:
- method/path;
- auth requirement;
- required headers;
- path/query/body field names;
- type/nullability/format;
- pagination/filter/sort semantics;
- success status/body;
- validation errors;
- authn/authz errors;
- not-found/conflict semantics;
- upload/download content types and limits;
- idempotency/retry contract;
- versioning/deprecation behavior.

Contract drift that breaks a core consumer is release-blocking.

## Cross-layer critical journey procedure

For each selected journey:
1. start from the user-visible action;
2. identify the exact frontend handler;
3. record the exact API request;
4. identify backend route and middleware;
5. verify identity/authorization context;
6. inspect business logic and persistence/integration;
7. observe response mapping;
8. verify resulting UI/application state;
9. test at least one meaningful negative path.

Example negative paths:
- missing authentication;
- wrong role;
- wrong owner/tenant;
- invalid field or malformed payload;
- nonexistent object;
- duplicate/conflicting mutation;
- downstream service error;
- expired session.

## Integration findings that normally block

- production frontend points to mock or nonexistent API;
- API field mismatch breaks critical form/flow;
- client-only authorization protects a privileged action;
- backend accepts forbidden state transitions;
- persistence writes partial state without required transaction safety;
- critical background job silently drops failed work;
- production config falls back to insecure/dev adapter;
- runtime startup cannot resolve required dependency/config.
