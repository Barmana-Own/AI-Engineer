# Auth Abuse Controls, Audit Events, and Observability

## Contents

- [Purpose](#purpose)
- [Abuse surfaces](#abuse-surfaces)
- [Layered throttling](#layered-throttling)
- [Enumeration resistance](#enumeration-resistance)
- [Rate-limit correctness](#rate-limit-correctness)
- [Lockout/backoff](#lockoutbackoff)
- [CAPTCHA/challenges](#captchachallenges)
- [Audit event design](#audit-event-design)
- [Required event families](#required-event-families)
- [Never log](#never-log)
- [Operational response](#operational-response)
- [Alerts](#alerts)
- [Tests](#tests)


## Purpose

Use this reference to resist automated auth abuse and to make identity/access events investigable without leaking credentials.

## Abuse surfaces

Inventory at least:

- login;
- registration;
- username/email availability checks;
- password reset request;
- reset token validation;
- verification resend;
- email/phone verification attempts;
- OTP/MFA challenge;
- recovery code;
- magic link request/redemption;
- token refresh;
- invitation creation/acceptance;
- API key creation;
- SSO discovery/domain lookup;
- account linking;
- MFA reset;
- impersonation start;
- admin login;
- support tools.

## Layered throttling

Use controls appropriate to attack shape. Potential dimensions:

- source IP/network;
- account/subject identifier;
- device/session/client;
- tenant;
- endpoint/action;
- provider/phone/email destination;
- global system budget.

Avoid a single naive account lockout that allows an attacker to permanently deny service to arbitrary users.

Prefer escalating delay/backoff, bounded temporary lock, challenge/risk controls, and layered limits according to product requirements.

## Enumeration resistance

Where account existence is sensitive:

- normalize public success/error messages;
- avoid materially different status codes/body fields for unknown account vs wrong credential unless product intentionally accepts enumeration risk;
- reduce large timing differences where feasible;
- normalize password reset and verification resend responses;
- keep internal telemetry specific so operations can diagnose attacks.

Document deliberate exceptions, such as enterprise user directories where account existence is already public.

## Rate-limit correctness

Verify rate limits cannot be trivially bypassed by:

- alternate endpoint/version;
- changing identifier case/format;
- spoofable proxy headers when proxy trust is misconfigured;
- IPv6 address variation if architecture needs aggregation;
- distributed attempts against one account;
- one source attacking many accounts;
- refresh/login endpoint separation;
- tenant alias/domain variants.

Do not trust `X-Forwarded-For` unless the framework/proxy chain is explicitly configured to trust only known proxies.

## Lockout/backoff

If account lockout exists:

- set bounded behavior;
- provide safe recovery;
- avoid revealing exact account existence to unauthenticated attackers;
- audit trigger/release;
- test successful authentication after the lock/backoff expires or is cleared;
- protect admin/support unlock operations.

## CAPTCHA/challenges

Treat CAPTCHA as an abuse-friction control, not primary authentication. Do not rely on it to compensate for missing rate limiting or weak credentials.

## Audit event design

Create structured security events for relevant actions.

Recommended fields:

- event name/version;
- timestamp;
- outcome;
- actor subject ID;
- effective subject ID for impersonation;
- target subject/resource ID;
- tenant/organization ID;
- role/permission/action;
- authentication method/assurance when relevant;
- request/correlation ID;
- session/credential identifier or safe prefix/hash, never full secret;
- source IP or coarse network data where lawful/appropriate;
- user agent/device metadata when useful;
- reason code;
- application/service name.

## Required event families

As applicable log:

- login success/failure;
- logout;
- session/refresh revocation;
- password change/reset request/reset success;
- email/phone change/verification;
- MFA enrollment/challenge/reset/disable/recovery-code use;
- OAuth/SSO link/unlink/failure;
- account state change;
- role/permission grant/revoke;
- tenant membership add/remove/change;
- API key/service credential create/revoke/rotate;
- impersonation start/end;
- sensitive admin/security-setting changes;
- repeated authorization denial or cross-tenant attempt when useful for detection.

## Never log

Do not record:

- plaintext passwords;
- password hashes unless an explicit secure migration tool requires controlled handling;
- full session IDs;
- full access or refresh tokens;
- OAuth authorization codes;
- reset/verification/magic-link tokens;
- TOTP seeds;
- full recovery codes;
- API key secrets;
- client secrets;
- private keys;
- cookies containing auth credentials.

Sanitize request/response logging middleware so auth endpoints do not leak these fields automatically.

## Operational response

Document operator actions for:

- suspicious login spike;
- credential stuffing;
- compromised account;
- stolen refresh token/session;
- leaked API key;
- malicious tenant admin;
- cross-tenant access alert;
- support/admin account compromise.

Actions may include session revocation, account suspension, credential rotation, forced re-authentication, MFA reset with identity proofing, tenant containment, alert escalation, and evidence preservation.

## Alerts

High-value systems should consider alerts for:

- repeated failed MFA/recovery;
- successful login after unusual failure burst;
- new admin/privileged role grant;
- MFA disabled/reset;
- API key created;
- mass session revocation;
- unusual cross-tenant denials;
- impersonation;
- SSO configuration changes.

Avoid alerting on every normal auth failure without aggregation; noisy telemetry is not useful security monitoring.

## Tests

Where testable:

- rate limit triggers at expected boundary;
- legitimate recovery after limit window works;
- account enumeration response is normalized;
- spoofed forwarding headers do not bypass source identity under configured proxy trust;
- secrets are redacted from application logs;
- privileged change emits an audit event with actor/target/tenant;
- impersonation records real and effective actor;
- authorization denial does not log sensitive request secrets.
