# Observability, Auditability, and Runtime Diagnostics QA

## Table of contents

1. Scope
2. Application error visibility
3. Browser/client diagnostics
4. Server logs
5. Audit trails
6. Correlation and traceability
7. Sensitive-data controls
8. Async diagnostics
9. Health and readiness signals
10. Exit criteria

## 1. Scope

Stage 10 verifies that critical runtime failures and security/business events are diagnosable enough for safe release preparation. Stage 11 owns production monitoring/infrastructure configuration, but Stage 10 must not hand over an application that silently fails or cannot explain critical state changes.

## 2. Application error visibility

During critical flows inspect for:

- unhandled exceptions;
- repeated error loops;
- swallowed failures that still show success;
- generic user error with no server-side diagnostic context;
- stack traces exposed to end users;
- fatal errors hidden behind endless loading states.

A user-safe message and an engineer-diagnosable log are separate requirements.

## 3. Browser/client diagnostics

For critical UI journeys, inspect when tooling permits:

- console errors;
- unhandled promise rejections;
- failed network requests;
- repeated duplicate network requests;
- hydration/runtime warnings that affect behavior;
- CSP/mixed-content errors in deployment-like environments;
- source-map or debug information exposure only when relevant to the release setup.

Do not block release on harmless development warnings unless evidence shows user or operational impact.

## 4. Server logs

Check critical operations for logs that are:

- sufficient to identify failure class;
- associated with route/job/action context;
- not flooded by uncontrolled repeated messages;
- free of plaintext secrets/tokens/passwords;
- appropriately leveled when project logging conventions exist.

Avoid changing the entire logging architecture during Stage 10 unless lack of diagnostics is itself a release blocker.

## 5. Audit trails

Where requirements call for auditability, verify material actions create correct audit evidence, such as:

- actor identity;
- action type;
- target entity;
- timestamp;
- before/after or meaningful change context where required;
- success/failure outcome;
- source/correlation metadata according to project conventions.

High-value examples include approval/rejection, permission changes, sensitive exports, financial changes, account-security changes, and administrative overrides.

Verify forbidden attempts are logged only when requirements demand it and without leaking sensitive request content.

## 6. Correlation and traceability

Where the architecture supports request/job correlation, verify a critical action can be followed across relevant boundaries:

- frontend/API request;
- service operation;
- queue/job;
- integration call;
- resulting state.

Do not invent a correlation-ID requirement if earlier architecture did not include one; flag diagnosability risk only when material.

## 7. Sensitive-data controls

Review representative logs and diagnostics for accidental inclusion of:

- access/refresh tokens;
- API keys;
- passwords/OTP values;
- secret headers;
- full sensitive personal/financial payloads beyond justified requirements;
- raw file contents.

Redact evidence included in QA reports.

## 8. Async diagnostics

For workers/jobs/webhooks verify:

- success and terminal failure are distinguishable;
- retry attempt is observable if the project logs it;
- dead-letter/failure storage is visible when architecture provides it;
- correlation with originating entity/request is possible enough to debug failures;
- duplicate processing is diagnosable.

## 9. Health and readiness signals

When the application provides health/readiness endpoints or equivalent signals, verify they reflect meaningful dependency state according to project design.

A health endpoint returning `200` while a required database is unavailable may be acceptable only if it is intentionally a liveness signal rather than readiness. Interpret according to the documented contract.

## 10. Exit criteria

Before PASS:

- no critical flow silently fails while reporting success;
- critical runtime errors are diagnosable in the available environment;
- required audit events are generated correctly;
- logs do not expose known P0/P1 sensitive secrets/data;
- Stage 11 receives any monitoring/infrastructure gaps without needing to repair core application diagnostics.
