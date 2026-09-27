# Error and Reliability Standards

## Contents
1. Error contract goals
2. Recommended error envelope
3. Error taxonomy
4. Mapping rules
5. Sensitive information rules
6. Correlation and observability
7. Timeouts
8. Retries
9. Idempotency
10. Dependency failure normalization
11. Webhook/callback duplicate safety
12. Client recovery guidance

## 1. Error contract goals

Use one predictable machine-readable error shape per API family. A client must be able to distinguish validation, not-found, conflict, transient dependency failure, and unexpected server failure without parsing human prose.

Human-readable messages may help the UI, but stable machine codes are the primary contract.

## 2. Recommended error envelope

Use the repository's established model if coherent. Otherwise use a structure equivalent to:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "fields": {
      "email": ["INVALID_EMAIL"]
    },
    "requestId": "req_opaque"
  }
}
```

`fields` is optional and intended only for client-correctable field errors.

An RFC 9457 Problem Details style is also acceptable when adopted consistently.

## 3. Error taxonomy

Define stable codes for domain-relevant classes. Example families:
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `CONFLICT`
- `PRECONDITION_FAILED`
- `DUPLICATE_REQUEST`
- `PAYLOAD_TOO_LARGE`
- `UNSUPPORTED_MEDIA_TYPE`
- `DEPENDENCY_TIMEOUT`
- `DEPENDENCY_UNAVAILABLE`
- `DEPENDENCY_REJECTED`
- `INTERNAL_ERROR`

Use domain-specific codes where clients need distinct recovery, for example `ORDER_ALREADY_CANCELLED` rather than forcing every conflict into an indistinguishable generic code.

Do not create hundreds of codes that clients cannot reasonably use.

## 4. Mapping rules

Map exceptions/results centrally when architecture allows. Avoid each controller inventing its own error payload.

For every important application/domain error define:
- HTTP status;
- machine code;
- safe user-facing message strategy;
- field errors if any;
- retryable yes/no;
- telemetry/log level according to existing project conventions.

Do not expose raw database constraint names as client contracts.

## 5. Sensitive information rules

Never return or document:
- stack traces;
- SQL statements;
- database hosts/table internals unless intentionally public;
- environment variables;
- filesystem paths;
- secret/token values;
- private keys;
- raw upstream credentials;
- internal exception dumps.

Logs should also redact sensitive values according to existing logging/security conventions.

## 6. Correlation and observability

If the project already has request/correlation IDs, propagate them through Stage 06 paths and include a safe request identifier in unexpected error responses when useful.

Do not invent a distributed tracing platform in Stage 06 unless the project already uses one or earlier requirements demand it.

## 7. Timeouts

Every external network dependency should have bounded time behavior.

Identify:
- connect timeout where configurable;
- request/read timeout;
- long-running operation strategy;
- user-facing timeout classification.

Do not allow indefinite waits because a library default happens to be unbounded.

## 8. Retries

Retry only operations that are safe to retry or protected by idempotency.

Define:
- retry owner (frontend, backend, worker, proxy);
- maximum attempts;
- backoff strategy when implemented here;
- retryable statuses/errors;
- non-retryable validation/auth/domain failures;
- interaction with timeouts and user cancellation.

Avoid retry amplification where frontend, backend, SDK, and proxy all retry the same request independently.

Respect provider `Retry-After` or equivalent semantics where applicable.

## 9. Idempotency

Use idempotency for retry-prone business mutations where duplicate side effects are unacceptable.

Define:
- key source and format;
- scope (tenant/user/operation/resource as appropriate);
- request fingerprint/hash to detect key reuse with a different payload;
- storage location;
- lifecycle/TTL;
- state while original request is in progress;
- replayed response behavior;
- behavior after original failure;
- concurrent duplicate behavior.

A robust pattern:
1. Client sends an opaque idempotency key.
2. Server scopes and stores key with request fingerprint.
3. First request acquires/creates the idempotency record.
4. Same key + same fingerprint returns/replays the established result or a documented in-progress response.
5. Same key + different fingerprint returns conflict.
6. Side effect and idempotency state are coordinated transactionally when feasible.

Do not call a random frontend debounce an idempotency guarantee.

## 10. Dependency failure normalization

For each external dependency distinguish:
- timeout;
- DNS/network/unavailable;
- provider 4xx/business rejection;
- provider 5xx;
- malformed/unexpected provider response;
- quota/rate limit.

Normalize these into the API error contract rather than forwarding arbitrary provider payloads directly to the frontend.

Preserve provider details in safe internal logs when permitted, not in public responses.

## 11. Webhook/callback duplicate safety

Incoming providers often retry callbacks. Process provider event IDs or equivalent deduplication keys where available.

Webhook handling should avoid duplicate side effects by design. Record duplicate detection semantics and persistence.

Security verification/signature enforcement may be completed in Stage 07, but Stage 06 must leave explicit hook points and must not destroy existing verification.

## 12. Client recovery guidance

Frontend mapping should distinguish:
- field correction required;
- resource no longer exists;
- state changed/conflict - refresh/reconcile;
- transient dependency issue - retry when safe;
- duplicate accepted/replayed - show established result;
- unexpected system failure - generic recovery path with request ID when available.

Do not show raw backend/internal messages directly to end users unless the contract explicitly marks them safe for display.
