# API Performance and Operability Standards

## Contents
1. Scope
2. Bounded work
3. Database/query behavior
4. Payload and serialization sanity
5. External dependency fan-out
6. Transaction boundaries
7. Logging and correlation
8. Metrics/tracing compatibility
9. Health and readiness compatibility
10. Validation checklist

## 1. Scope

Stage 06 is not a full performance-optimization stage, but integration must not introduce obvious production hazards. Apply these checks proportionally to the product and existing architecture.

Do not invent arbitrary latency SLOs. Use existing requirements/SLOs when available; otherwise record qualitative sanity checks and obvious bottlenecks.

## 2. Bounded work

Every request path must have bounded work where data can grow.

Check for:
- unbounded list queries;
- unbounded request arrays;
- unbounded file sizes/counts;
- uncontrolled recursive expansion;
- endpoints that load an entire large table to filter in application memory;
- synchronous loops that call an external service once per unbounded item.

Apply hard limits at the server boundary or persistence query as appropriate.

## 3. Database/query behavior

Inspect core API flows for obvious persistence inefficiencies:
- N+1 query patterns;
- missing pagination at query level;
- repeated reads of the same entity in one request without reason;
- loading full records when only small projections are needed in hot list paths;
- transaction scope that remains open during slow external network calls;
- missing deterministic ordering in paginated reads.

Do not add speculative indexes in Stage 06 without evidence or earlier data-model justification, but record a concrete index risk when the API access pattern clearly requires Stage 05 follow-up.

## 4. Payload and serialization sanity

Avoid accidental oversized responses such as:
- embedding large child collections in every list row;
- returning file bytes inside normal JSON when streaming/object-storage indirection is expected;
- returning internal audit/history blobs by default;
- serializing cyclic object graphs;
- duplicate nested data that the client does not consume.

Use compact DTOs appropriate to the journey. Add dedicated detail operations when list and detail needs differ materially.

## 5. External dependency fan-out

For API paths that call external systems:
- bound concurrency;
- avoid request-per-row fan-out on unbounded lists;
- use batch/provider bulk operations when established and beneficial;
- use bounded timeouts;
- define partial failure semantics for bulk/fan-out operations;
- avoid retry storms.

If fan-out is inherently long-running, consider an asynchronous job pattern rather than keeping a user request open indefinitely.

## 6. Transaction boundaries

Keep transactions as short as correctness allows.

Avoid holding database transactions open while waiting for unrelated slow network calls unless atomicity design specifically requires a coordination pattern.

For side effects that span database and external systems, preserve the architecture's established reliability pattern (outbox, job, saga, compensating action, etc.) when present. Do not invent distributed transactions casually.

## 7. Logging and correlation

Preserve existing structured logging conventions.

For core failures, logs should be sufficient to diagnose:
- operation/route;
- safe request/correlation ID;
- error class/code;
- dependency name when relevant;
- duration/status when existing instrumentation supports it.

Never log secrets, passwords, auth tokens, private keys, full payment details, or sensitive upload contents.

Do not log complete request/response bodies by default merely for debugging.

## 8. Metrics/tracing compatibility

If the project already has metrics or tracing, ensure new Stage 06 routes use the established middleware/instrumentation path.

Useful existing metrics may include:
- request count;
- latency;
- status/error class;
- dependency latency/failure;
- queue/job outcomes.

Do not introduce a new observability platform solely in Stage 06 unless requirements demand it.

## 9. Health and readiness compatibility

If health/readiness endpoints already exist, new required dependencies should be reflected according to existing conventions.

Do not mark an optional third-party service as a hard readiness dependency without architectural justification.

Do not expose detailed internal health data publicly if existing security conventions restrict it.

## 10. Validation checklist

For core Stage 06 flows, inspect and record applicable results:
- list/query work is bounded;
- pagination occurs in persistence, not only in UI;
- no obvious N+1 in core list/detail flows;
- payload size/shape is reasonable for the journey;
- file transfer is streamed/indirected where necessary;
- dependency fan-out is bounded;
- timeouts are finite;
- retries are controlled;
- transaction boundaries are reasonable;
- existing logging/metrics/tracing middleware is preserved;
- no sensitive values are introduced into logs.
