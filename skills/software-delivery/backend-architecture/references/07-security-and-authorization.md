# Security and Authorization Architecture

## Table of contents

1. Scope
2. Identity versus authorization
3. Use-case authorization
4. Multi-tenant isolation
5. Sensitive data classification
6. Files, URLs, and external input
7. Secrets and configuration
8. Auditability
9. Deferred hardening boundary

## 1. Scope

Stage 04 is not the final security-hardening stage, but security decisions that shape backend architecture must be correct now. Do not defer a control if adding it later would require changing module ownership, use-case contracts, tenant boundaries, persistence semantics, or integration contracts.

## 2. Identity versus authorization

Treat authentication as evidence of identity/context. Treat authorization as the decision whether that identity may perform a business action.

Application code should consume a normalized request/actor context rather than provider-specific token objects.

Typical context fields may include:

- actor/user ID;
- tenant/account/organization ID;
- roles/permissions/scopes;
- authentication strength/session metadata only when business policy needs it;
- correlation ID.

Do not let provider token claims leak everywhere through the application.

## 3. Use-case authorization

For each sensitive use case, answer:

- who may call it;
- under which tenant/account;
- whether ownership is required;
- whether role/permission is sufficient;
- whether current resource state changes authorization;
- whether separation-of-duties applies;
- whether elevated/step-up authentication will be required later;
- whether audit evidence is required.

Enforce authorization before sensitive state mutation or disclosure.

Use deny-by-default behavior where absence of an allow rule should not grant access.

Do not rely solely on route middleware for resource-level authorization.

## 4. Multi-tenant isolation

When the product is multi-tenant, define tenant scoping at every relevant layer:

- request context;
- use-case input/authorization;
- repository port contracts;
- query/list semantics;
- idempotency-key scope;
- uniqueness scope;
- cache keys if caching exists;
- job/event envelope;
- audit records;
- Stage 05 persistence constraints.

Never trust a client-supplied tenant ID without reconciling it with authenticated context/policy.

Cross-tenant admin workflows must be explicit and auditable.

## 5. Sensitive data classification

At minimum classify data as:

- public;
- internal;
- confidential;
- highly sensitive/regulated when applicable.

Use the classification to drive:

- log redaction;
- response filtering;
- audit requirements;
- retention/deletion handoff;
- encryption requirements for later stages;
- access policy.

Record actual categories relevant to the product rather than blindly using all four.

## 6. Files, URLs, and external input

When the backend accepts uploads or external URLs, define architecture-level controls needed later:

- size/type constraints;
- filename/path normalization;
- content-type trust boundaries;
- malware/scanning seam if required;
- object storage ownership/access model;
- signed URL semantics;
- SSRF-safe fetching boundary if server-side URL fetch is required;
- metadata stripping/processing when sensitive.

Do not implement unsafe arbitrary URL fetching inside business code.

## 7. Secrets and configuration

Secrets must come from runtime configuration/secret management, never source literals.

Do not copy actual secrets into docs, tests, fixtures, or evidence JSON.

Environment examples must contain placeholders only.

## 8. Auditability

For privileged, financial, legal, approval, identity, or security-significant operations, determine whether an audit event is required.

An audit event contract should identify:

- actor;
- tenant/context;
- action;
- target/resource;
- timestamp source;
- outcome;
- correlation ID;
- safe before/after metadata if required;
- reason/approval reference when business rules require it.

Do not log secrets as audit evidence.

## 9. Deferred hardening boundary

May be deferred when assigned later and not architecture-shaping:

- production WAF/CDN rules;
- full penetration testing;
- infrastructure network policies;
- secret-manager provisioning;
- production SIEM routing;
- final auth-provider tenant configuration;
- operational security runbooks.

Still document the seams/requirements Stage 04 establishes for them.
