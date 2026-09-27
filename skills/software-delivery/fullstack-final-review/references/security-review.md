# Security Review Procedure

## Contents

- Attack surface
- Authentication
- Authorization
- Input and injection
- Browser/session protections
- File handling
- Abuse/rate controls
- Secrets/configuration
- Dependencies/supply chain
- Logging/privacy
- Prior-finding revalidation
- Blocking security conditions

Use risk-based review appropriate to the application's exposure and data sensitivity. This is a final engineering gate, not a claim of formal penetration-test certification.

## 1. Attack surface inventory

Identify:
- public HTTP/API endpoints;
- authenticated endpoints;
- admin/privileged endpoints;
- background workers/queues;
- webhooks/callbacks;
- file upload/download paths;
- WebSocket/realtime interfaces;
- external integrations;
- database/cache/object storage;
- management/debug/metrics endpoints;
- client-side secrets/config;
- deployment/admin interfaces included in the repo.

## 2. Authentication

Verify as applicable:
- login failure behavior does not leak excessive account information;
- credential verification uses safe library/framework mechanisms;
- reset/recovery tokens are scoped, time-limited and single-use where required;
- MFA enforcement matches approved requirements;
- session/token expiration is enforced;
- logout/revocation semantics are understood and tested;
- refresh token rotation/reuse handling is appropriate when implemented;
- disabled/deleted users lose access according to requirements;
- default/test credentials are not production-valid;
- debug auth bypasses are unreachable in production.

## 3. Authorization

Test negative paths, not only positive role checks:
- unauthenticated access;
- wrong role;
- lower privilege calling admin route directly;
- horizontal object access by changing IDs;
- cross-tenant access;
- ownership changes after object transfer/state change;
- nested resource authorization;
- file/download authorization;
- bulk/export/report endpoints;
- background/admin actions.

Backend authorization is authoritative. Hidden buttons are not security controls.

## 4. Input and injection

Assess stack-relevant classes:
- SQL/ORM injection;
- command/shell injection;
- template injection;
- path traversal;
- SSRF;
- unsafe deserialization;
- XML/entity hazards when XML exists;
- LDAP/NoSQL injection where relevant;
- XSS for HTML/markdown/rich text;
- open redirect;
- header injection.

Prefer framework-native parameterization/escaping. Test meaningful high-risk inputs safely in local/test environments.

## 5. Browser/session protections

As applicable verify:
- secure/HttpOnly/SameSite cookies;
- CSRF protections for cookie-authenticated state changes;
- CORS allowlist and credential semantics;
- security headers appropriate to deployment;
- CSP where relevant to application risk;
- no sensitive tokens in URLs/local logs unnecessarily;
- no server stack traces/secrets exposed to clients.

## 6. File handling

Verify:
- allowed types/extensions and actual content validation appropriate to use;
- size/count limits;
- randomized/non-user-controlled storage names when needed;
- path traversal protection;
- authorization on retrieval/deletion;
- malware scanning/quarantine when required by risk model;
- untrusted active content is not served with dangerous execution context;
- object storage is not accidentally public.

## 7. Abuse and rate controls

Review sensitive operations:
- login/reset/OTP;
- signup/invite;
- expensive generation/search;
- payment/order mutation;
- webhook processing;
- uploads;
- admin bulk actions.

Absence of rate limiting is not automatically High; assess realistic abuse impact.

## 8. Secrets and configuration

Run hygiene scan, then inspect candidates.

Block on confirmed:
- private keys/tokens/passwords committed for real environments;
- live payment/API secrets;
- production DB credentials;
- cloud credentials;
- hardcoded auth bypass keys.

Placeholders and test-only fake values should be documented and must not become production defaults.

## 9. Dependencies and supply chain

1. Identify lockfiles and package managers.
2. Run repository-supported audit/security tooling when available.
3. Do not automatically upgrade broad dependency ranges during final review without assessing compatibility.
4. For a Critical/High advisory, determine:
   - package/version;
   - direct vs transitive;
   - reachable/exploitable path;
   - fixed version or mitigation;
   - impact of upgrade.
5. Repair with the narrowest safe version change and re-run build/tests/security checks.

## 10. Logging/privacy

Check that production logs do not intentionally expose:
- passwords;
- full auth tokens/session IDs;
- private keys;
- sensitive payment data;
- unnecessary personal/private payloads.

Error logs should remain diagnostically useful without leaking secrets to clients.

## 11. Security finding revalidation

For prior findings:
- locate the original issue;
- verify current code path;
- re-run regression if possible;
- confirm the fix is not bypassable through alternate route/config;
- reopen if evidence is stale or contradictory.

## Blocking security conditions

Do not PASS with:
- open Critical/High confirmed issue;
- authn/authz bypass;
- cross-tenant/ownership breach with meaningful data/action impact;
- live secret intended for release;
- production debug/test bypass;
- known exploitable Critical/High dependency on a reachable path without effective mitigation;
- unsafe default that predictably exposes privileged capability.
