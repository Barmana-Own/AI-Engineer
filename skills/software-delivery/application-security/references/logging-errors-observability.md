# Security Logging, Error Handling, and Observability Review

## Table of contents

1. Security-event inventory
2. Required context
3. Redaction
4. Error responses
5. Audit integrity and authorization
6. Detection-oriented events
7. Noise and abuse
8. Tests

## 1. Security-event inventory

Identify security-relevant events that the project should be able to investigate. Depending on product scope:

- login success/failure;
- password/MFA/recovery changes;
- session/token revocation;
- role/permission changes;
- membership/tenant changes;
- privileged/admin actions;
- access denied to sensitive resources;
- webhook verification failure/replay;
- payment/state-transition failures;
- export/download of sensitive bulk data;
- security configuration changes;
- destructive operations.

Do not log every request body merely for auditability.

## 2. Required context

For material events, prefer structured context such as:

- timestamp;
- event type;
- actor ID and actor role;
- tenant/organization ID where relevant;
- target object/type/ID;
- outcome;
- request/correlation ID;
- source/service context;
- reason category for denial/failure when safe.

Use stable IDs rather than sensitive display data where possible.

## 3. Redaction

Never log:

- passwords;
- OTPs/reset tokens;
- full session/refresh/access/API tokens;
- Authorization/Cookie headers;
- private keys;
- full sensitive payment data;
- raw high-sensitivity documents;
- secrets from environment/config.

Apply centralized redaction where possible. Check exception logging, HTTP client debug logs, ORM query logs and third-party telemetry separately.

A token masked in normal logs may still leak in exception context.

## 4. Error responses

Production-facing errors should not expose stack traces, filesystem paths, SQL queries, secret-bearing configuration, internal hostnames or verbose vendor errors unnecessarily.

Keep client errors actionable while storing richer diagnostic context safely server-side. Map validation/auth errors intentionally; avoid returning raw exception messages by default.

Authentication errors should not unnecessarily enumerate accounts or secret state.

## 5. Audit integrity and authorization

Audit/log viewing endpoints themselves require authorization and tenant scoping. Users should not be able to edit/delete audit records unless the product explicitly defines a controlled retention mechanism.

If logs are stored in the main database, ensure generic update/delete APIs cannot modify them.

## 6. Detection-oriented events

Where applicable, ensure repeated/high-risk events can be surfaced operationally:

- repeated login/recovery failures;
- repeated authorization denials;
- webhook signature failures;
- unexpected admin operations;
- bulk export;
- secret/config validation failures;
- unusual duplicate/replay events.

Stage 08 need not build a full SIEM. Verify the application emits sufficient structured signals for the project's monitoring stage/operations.

## 7. Noise and abuse

Avoid attacker-controlled unbounded log amplification. Truncate/normalize large fields and avoid logging whole request bodies on failures. Protect against log injection by using structured logging rather than attacker-controlled line formatting.

Logging itself must not become a denial-of-wallet vector through high-volume expensive sinks where the architecture exposes that risk.

## 8. Tests

Useful tests:

- sensitive headers/fields are redacted;
- production error response omits stack trace while logs retain a correlation ID;
- authorization-denied event includes actor/target but no secret;
- audit endpoint enforces role/tenant boundary;
- webhook invalid-signature event is logged without payload secret;
- malicious newline/control characters do not corrupt structured log format.
