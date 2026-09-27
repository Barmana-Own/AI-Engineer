# Observability and Operational Readiness

## Table of contents

1. Goals
2. Health model
3. Logging
4. Correlation and tracing
5. Metrics
6. SLI/SLO design
7. Alerting
8. Dashboards
9. Dependency visibility
10. Queue/worker visibility
11. Security/privacy in telemetry
12. Production-like validation
13. Runbook expectations
14. Failure conditions

## 1. Goals

Observability must let an operator determine whether users are affected, identify the failing component, correlate the failure to a release or dependency, and choose a safe next action.

Do not treat "logs exist" as equivalent to observability.

## 2. Health model

Separate these concepts when the runtime supports them:

### Startup

Use for processes that legitimately need initialization time. A startup probe/check should answer whether initialization has completed or the process is stuck. It can protect the application from premature liveness failures during warmup.

### Liveness

Answer: "Is this process fundamentally alive, or is restart likely to help?"

Do not make liveness fail merely because every external dependency is temporarily unavailable. Otherwise a database outage can create restart storms and worsen recovery.

### Readiness

Answer: "Can this instance safely receive the traffic/work assigned to it?"

Readiness may depend on critical local initialization and critical dependencies required to serve the intended request path. Keep it fast and bounded.

### Public health endpoints

Return minimal non-sensitive status. Do not expose:

- database credentials/DSNs;
- secret values;
- stack traces;
- internal hostnames unnecessarily;
- detailed dependency topology useful to attackers;
- build environment secrets.

Detailed diagnostics can live behind authenticated/internal telemetry channels.

## 3. Logging

Prefer structured machine-parseable logs in production.

Include where useful:

- timestamp;
- severity;
- service/component;
- environment;
- release/version/commit identifier;
- request ID/correlation ID;
- trace/span identifiers when tracing exists;
- route/template rather than raw sensitive URL where possible;
- status/result;
- duration;
- error code/class;
- job/message ID in background processing;
- tenant/account identifiers only when privacy policy allows and values are appropriately minimized/pseudonymized.

Avoid logging:

- passwords;
- access/refresh/session tokens;
- authorization headers;
- raw cookies;
- private keys;
- full connection strings containing credentials;
- payment card data;
- OTP/security codes;
- unnecessary request/response bodies;
- sensitive PII not needed for operations.

Define log retention/access outside the app when the platform owns it.

## 4. Correlation and tracing

For multi-service systems, propagate a correlation/request ID through ingress, application calls, queues/jobs, and outgoing requests when practical.

Use distributed tracing when diagnosis materially benefits from it. Ensure:

- trace context propagates across HTTP/RPC and asynchronous boundaries where supported;
- sampling is intentional;
- high-cardinality sensitive attributes are not captured blindly;
- release/environment/service attributes exist;
- tracing failures do not break user traffic.

## 5. Metrics

Cover the four major service perspectives:

### Traffic

- request rate;
- active users/sessions only when safe/useful;
- job enqueue/dequeue rates;
- message throughput.

### Errors

- HTTP 5xx/4xx by route category;
- exception count/rate;
- failed jobs;
- dead-letter count;
- external dependency failures;
- authentication/authorization failure trends where operationally useful.

### Latency

- request duration percentiles;
- database/query latency;
- external API latency;
- job wait and processing time;
- queue age.

### Saturation/resources

- CPU;
- memory;
- event-loop/thread pool saturation where relevant;
- connection pool usage;
- disk/storage;
- file descriptors;
- queue depth;
- rate-limit exhaustion.

Avoid unbounded metric labels such as raw user IDs, URLs, error strings, or arbitrary object IDs.

## 6. SLI/SLO design

For each critical user journey or service capability, define at least a measurable indicator. Mature projects should define SLOs; smaller projects may define explicit release/operational thresholds if formal SLOs are absent.

Examples:

- availability: successful eligible requests / total eligible requests;
- latency: percentage of successful requests below threshold;
- job freshness: percentage of jobs completed within expected delay;
- correctness proxy: successful transaction completion rate.

Do not invent business SLO targets. Derive them from existing requirements or document them as proposed assumptions requiring owner confirmation.

## 7. Alerting

Alert on symptoms that require action, not every log line.

Good candidates:

- sustained elevated error rate;
- sustained latency breach;
- service unavailable/readiness capacity below safe threshold;
- queue age/backlog breach;
- repeated job failures/DLQ growth;
- storage exhaustion;
- certificate expiry risk;
- backup failure;
- critical dependency outage;
- anomalous restart/crash loop;
- database connection/pool exhaustion.

Each alert should define:

- condition/window;
- severity;
- owner/on-call destination;
- first diagnostic link/check;
- likely impact;
- runbook action;
- suppression/deduplication behavior where relevant.

Avoid alerts that fire continuously during known normal deployment behavior unless they are automatically muted by a controlled release process.

## 8. Dashboards

A production operations dashboard should answer, at minimum:

- current release/version;
- service availability/readiness;
- request/error rate;
- latency;
- resource saturation;
- dependency health;
- queue/job health;
- deployment markers;
- recent alerts/incidents.

For multi-service systems, provide both system-level and service-level views when practical.

## 9. Dependency visibility

For critical external dependencies, capture:

- request count;
- failure/timeout count;
- latency;
- circuit-breaker/open state if used;
- rate-limit responses;
- retry count;
- dependency identity/category.

Do not log full sensitive request/response payloads by default.

## 10. Queue/worker visibility

Track:

- queue depth;
- oldest-message age;
- enqueue/dequeue rate;
- processing duration;
- success/failure;
- retry count;
- dead-letter count;
- worker concurrency;
- stuck/in-progress jobs when detectable.

A worker can be "running" while the queue is failing. Monitor work outcomes, not just process existence.

## 11. Security/privacy in telemetry

Treat telemetry as production data. Verify:

- access control;
- retention;
- redaction;
- transport encryption;
- tenant isolation where needed;
- sensitive field filtering;
- error-reporting payload controls;
- session replay privacy controls if used.

Do not send secrets or regulated/sensitive data to third-party telemetry by accident.

## 12. Production-like validation

During smoke testing, intentionally produce at least:

- one successful request;
- one safe expected client error when useful;
- one background job flow if applicable;
- one dependency interaction if applicable.

Confirm corresponding logs/metrics/traces appear with the expected release and correlation metadata.

Validate readiness transitions on startup and graceful shutdown where feasible.

## 13. Runbook expectations

For each major operational failure, the runbook should tell the operator:

1. user/system symptom;
2. alert/indicator;
3. first checks;
4. how to identify the affected release/service;
5. safe mitigation;
6. rollback/roll-forward decision point;
7. data-integrity concerns;
8. escalation/owner;
9. evidence to preserve for incident review.

At minimum cover:

- service unavailable/high error rate;
- high latency/resource saturation;
- database connectivity/exhaustion;
- failed migration;
- queue backlog/job failures;
- external dependency outage;
- storage failure;
- secret compromise;
- failed deployment.

## 14. Failure conditions

Fail `G09_OBSERVABILITY` when applicable and unresolved:

- operators cannot tell whether the service is healthy;
- health checks expose sensitive detail;
- logs routinely contain secrets/tokens;
- critical distributed work has no failure/backlog visibility;
- deployment changes cannot be correlated to runtime behavior;
- no actionable monitoring/alert ownership exists for critical production paths in a system that requires ongoing operation.
