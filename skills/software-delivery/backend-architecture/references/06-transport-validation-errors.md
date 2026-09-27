# Transport, Validation, and Error Contracts

## Table of contents

1. Thin transport boundary
2. Validation layering
3. Normalization rules
4. Error taxonomy
5. Public error envelope
6. HTTP mapping guidance
7. Sensitive failure handling
8. Contract tests

## 1. Thin transport boundary

A transport handler should normally:

1. parse request inputs;
2. validate transport-level shape;
3. establish request context (identity, tenant, correlation, locale where needed);
4. invoke authorization/use case;
5. map application result/error to transport response;
6. avoid business-rule branching that belongs in application/domain code.

The same application use case should remain usable from another transport (job, CLI, message consumer) when that is realistic for the product.

## 2. Validation layering

### Transport/trust-boundary validation

Validate:

- required fields;
- primitive types/formats;
- length/range bounds that protect the boundary;
- enum membership;
- pagination limits;
- file metadata limits when relevant;
- malformed identifiers;
- unknown fields when accepting them would be unsafe/ambiguous.

### Domain/application validation

Validate:

- state transitions;
- business eligibility;
- cross-field business rules;
- ownership/permission conditions;
- uniqueness semantics (with Stage 05 backing where needed);
- time-window rules;
- money/business constraints;
- dependency-derived rules.

Do not duplicate business rules in controller schemas and domain code with divergent semantics.

## 3. Normalization rules

Normalize deliberately, not invisibly.

Document semantics for:

- trimming/case sensitivity;
- Unicode handling when identifiers/names are affected;
- timestamps and timezone conversion;
- locale-sensitive numbers;
- phone/email canonicalization when used for identity/uniqueness;
- currency amounts;
- optional/empty/null distinctions.

Do not normalize security-sensitive identifiers in a way that creates equivalence bugs.

## 4. Error taxonomy

Use a stable internal taxonomy such as:

- `ValidationError`
- `UnauthorizedError` (identity missing/invalid when applicable)
- `ForbiddenError`
- `NotFoundError`
- `ConflictError`
- `PreconditionError`
- `RateLimitError` when relevant
- `DependencyUnavailableError`
- `DependencyRejectedError`
- `InternalError`

Add domain-specific error codes where clients or orchestration need stable semantics.

Every application-facing error should define at least:

- stable code;
- safe message or message key;
- category;
- retryability where meaningful;
- optional safe details/field errors;
- original internal cause retained only for diagnostics.

## 5. Public error envelope

Prefer a stable shape equivalent to:

```json
{
  "error": {
    "code": "ORDER_STATE_CONFLICT",
    "message": "The order cannot be changed in its current state.",
    "details": null,
    "fieldErrors": null,
    "correlationId": "...",
    "retryable": false
  }
}
```

Adapt casing/naming to existing project conventions. Never expose raw exception objects.

## 6. HTTP mapping guidance

Use semantics consistently rather than mechanically:

- malformed/invalid request: 400 or 422 according to established API convention;
- missing/invalid authentication: 401;
- authenticated but not allowed: 403;
- absent resource where disclosure is allowed: 404;
- state/uniqueness/idempotency conflict: 409;
- rate limit: 429;
- temporary upstream failure: 502/503/504 depending on semantics;
- unexpected server failure: 500 with generic public message.

Preserve existing API conventions unless they are unsafe or inconsistent enough to require documented correction.

## 7. Sensitive failure handling

Never expose in public errors or logs:

- passwords;
- bearer/session tokens;
- API keys;
- cryptographic secrets;
- full payment credentials;
- raw database connection strings;
- full sensitive documents;
- stack traces to untrusted clients;
- SQL/ORM internals;
- private provider credentials.

Use structured redaction rather than relying on developers to remember every log call.

## 8. Contract tests

For critical routes/handlers, test at least:

- invalid input mapping;
- authorization failure mapping when the boundary exists;
- domain conflict mapping;
- unexpected error sanitization;
- correlation identifier presence/propagation when implemented.
