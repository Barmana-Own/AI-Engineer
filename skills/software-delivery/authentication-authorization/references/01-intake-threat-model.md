# Intake and Authentication Threat Model

## Contents

- [Purpose](#purpose)
- [1. Repository intake](#1-repository-intake)
- [2. Identity inventory](#2-identity-inventory)
- [3. Asset inventory](#3-asset-inventory)
- [4. Trust boundaries](#4-trust-boundaries)
- [5. Attack-path catalog](#5-attack-path-catalog)
- [6. Threat-to-control mapping](#6-threat-to-control-mapping)
- [7. Risk ranking](#7-risk-ranking)
- [8. Completion condition](#8-completion-condition)


## Purpose

Use this reference before designing or changing auth. The goal is to discover the actual security boundaries in the repository and translate attack paths into implementation and test obligations.

## 1. Repository intake

Inspect, at minimum:

- application entrypoints;
- route/controller definitions;
- auth middleware/guards/decorators;
- service/repository/query layers;
- user/account/tenant/membership/role tables or models;
- migrations;
- environment/configuration loaders;
- session/token libraries;
- external IdP configuration;
- frontend auth provider/state/store;
- API client/interceptors;
- websocket/realtime authentication;
- file/object access paths;
- background jobs and queues;
- webhooks and machine credentials;
- test helpers/fixtures/factories;
- CI workflows that exercise auth/security tests.

Search for terms such as `auth`, `login`, `session`, `token`, `jwt`, `cookie`, `role`, `permission`, `scope`, `tenant`, `organization`, `owner`, `admin`, `impersonate`, `reset`, `verify`, `mfa`, `otp`, `oauth`, `oidc`, `sso`, `apiKey`, `authorization`, and framework-specific guard/middleware names.

## 2. Identity inventory

Build a table with these columns:

| Identity type | Authenticator | Source of truth | Allowed clients | Primary privileges | Lifecycle owner | Revocation path |
|---|---|---|---|---|---|---|

Include anonymous/public access as an identity context even when it has no account.

## 3. Asset inventory

Identify assets that auth controls protect:

- personal/private records;
- tenant/customer data;
- files and generated documents;
- financial actions;
- administrative configuration;
- billing/payment methods;
- API credentials/secrets;
- integrations/webhooks;
- exports/reports;
- moderation/support actions;
- audit logs;
- user security settings;
- role/membership management;
- infrastructure or deployment actions if exposed through the product.

Mark high-impact actions that can cause irreversible, financial, privacy, security, or availability consequences.

## 4. Trust boundaries

Draw or describe boundaries between:

- browser/mobile client and API;
- API gateway and internal services;
- services and database;
- application and external IdP;
- application and email/SMS provider;
- tenant A and tenant B;
- user and admin/support planes;
- application and queue/background worker;
- application and object storage/CDN;
- public webhooks and internal processors;
- application and third-party integrations.

For each boundary, identify how identity is propagated and re-verified.

## 5. Attack-path catalog

Evaluate these scenarios explicitly:

### Authentication bypass

- protected endpoint callable without credentials;
- alternate route/version bypasses middleware;
- HTTP method variant bypass;
- websocket/realtime connection lacks equivalent auth;
- internal/admin endpoint exposed through public routing;
- weak fallback/default credential;
- malformed token accepted because verification errors fail open.

### Credential/session attacks

- stolen token remains valid too long;
- logout does not invalidate a server-side session when invalidation is expected;
- refresh token replay succeeds after rotation;
- session identifier not rotated after authentication/privilege elevation;
- token accepted for wrong audience/client/service;
- disabled/suspended user retains access;
- password/MFA reset does not terminate sessions when policy requires it;
- token leaks through URL/log/storage.

### Authorization attacks

- regular user invokes admin endpoint;
- user changes role/permission field in request body;
- user changes object ID to access another user's record;
- tenant member substitutes another tenant ID;
- nested resource ownership is checked only on parent or only on child;
- bulk/export endpoint applies weaker filtering;
- file download uses guessable object path without permission re-check;
- websocket channel subscription lacks resource authorization;
- background job trusts caller-supplied tenant/owner data;
- cached authorization survives privilege revocation indefinitely.

### Recovery/verification attacks

- reset token can be reused;
- token remains valid after email/phone/account state changes;
- recovery response reveals account existence;
- attacker initiates reset to a user-controlled destination;
- verification flow binds the wrong account/identifier;
- password reset bypasses required MFA without explicit policy;
- recovery codes are stored or logged in plaintext without need.

### OAuth/OIDC/federation attacks

- callback lacks state/nonce/PKCE checks where required;
- redirect URI validation is loose;
- issuer/audience/signature validation is incomplete;
- login links external identity to an existing account based only on untrusted/mutable attributes;
- provider access token is mistaken for application authorization;
- open redirect after login leaks code/token or enables phishing.

### MFA/step-up attacks

- privileged endpoint only checks that user once enrolled in MFA, not that challenge is satisfied/recent;
- MFA disable endpoint is weaker than login;
- recovery flow silently disables MFA;
- backup code reuse;
- remembered-device token has excessive lifetime or weak binding;
- lower-assurance factor can always bypass higher-assurance policy.

## 6. Threat-to-control mapping

For every material threat create a mapping:

| Threat ID | Asset/action | Attack precondition | Security control | Enforcement point | Verification test | Residual risk |
|---|---|---|---|---|---|---|

Use stable IDs such as `AUTH-T01`, `AUTH-T02`.

A threat with no control or no test is unresolved.

## 7. Risk ranking

Use project risk context rather than arbitrary numeric precision. Classify each issue as:

- Critical: direct account takeover, broad auth bypass, cross-tenant compromise, privileged compromise, or equivalent catastrophic impact with realistic exploitability.
- High: meaningful privilege escalation, credential/session compromise, recovery bypass, or broad unauthorized data/action access.
- Medium: limited exposure, weaker exploitability, missing defense-in-depth with plausible security impact, or contained authorization inconsistency.
- Low: hygiene issue with limited direct impact.
- Informational: observation or hardening opportunity without a demonstrated security defect.

Critical and High Stage 07 defects block PASS until fixed or made genuinely unreachable by the implemented architecture.

## 8. Completion condition

Threat modeling is complete only when:

- identities, assets, and boundaries are enumerated;
- enabled auth mechanisms are known;
- privileged actions are identified;
- ownership/tenant boundaries are known;
- material attack paths have controls;
- every material control has a planned verification method.
