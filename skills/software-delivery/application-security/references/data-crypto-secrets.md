# Sensitive Data, Cryptography, Secrets, and Privacy-Security Review

## Table of contents

1. Data inventory and classification
2. Data minimization and exposure paths
3. Password hashing
4. Tokens and randomness
5. Encryption and key use
6. Transport security assumptions
7. Secret storage and source control
8. Frontend/build leakage
9. Logs, analytics and telemetry
10. Backups, exports and temporary data
11. Database access and least privilege
12. Tests and evidence

## 1. Data inventory and classification

Identify security-sensitive data handled by the project. Examples:

- passwords/credential material;
- session/refresh/API tokens;
- identity/contact data;
- financial/payment-related identifiers;
- private documents/media;
- legal/medical or other specially protected data when explicitly present;
- internal administrative notes;
- audit/security events;
- integration secrets;
- encryption/signing keys;
- customer/tenant business records.

Classify each as public, internal, confidential or secret enough to drive practical controls. Do not invent regulatory classifications without evidence.

## 2. Data minimization and exposure paths

Trace sensitive data through:

- API responses;
- browser state/HTML;
- logs;
- analytics/error monitoring;
- queues;
- cache;
- database;
- object storage;
- exports/backups;
- emails/SMS/notifications;
- URLs/query strings;
- third-party integrations.

Check whether the application returns whole database models when a narrow response DTO is intended. Avoid storing or transmitting data not required for the feature.

## 3. Password hashing

Use a purpose-built adaptive password hashing library/algorithm suitable for the runtime. Verify:

- no reversible encryption/plain hashing for passwords;
- parameters are not trivially weak;
- unique salts are library-managed;
- comparison uses the library's verification function;
- password hashes are not exposed via APIs/logs/backups unnecessarily.

Do not write custom password hashing.

## 4. Tokens and randomness

Security tokens, reset codes, invite tokens, API keys, CSRF tokens and identifiers intended to be unpredictable must use a cryptographically secure random generator with sufficient entropy for the threat model.

Do not use timestamps, counters, `Math.random()` or predictable UUID variants as secret authenticators.

If tokens are stored server-side, consider storing a one-way digest for high-value bearer tokens so database disclosure does not immediately reveal usable values.

## 5. Encryption and key use

Before adding encryption, identify the exact threat it addresses. Prefer well-maintained high-level cryptographic libraries and authenticated encryption modes.

Review:

- key source/storage;
- key separation by purpose when needed;
- nonce/IV generation requirements;
- authentication/integrity, not confidentiality alone;
- key rotation/versioning assumptions;
- encrypted-data migration/recovery path;
- accidental hardcoded keys;
- custom crypto constructions.

Do not invent cryptographic algorithms or hand-roll primitives.

Hashing is not encryption. Encoding is not encryption. Encryption at rest does not replace authorization.

## 6. Transport security assumptions

Identify where TLS terminates. Application code behind a reverse proxy may need correct trusted-proxy configuration to recognize secure requests and generate secure cookies/redirects.

Do not disable TLS certificate verification for convenience. A local development exception must be clearly isolated and never become a production default.

## 7. Secret storage and source control

Search for likely secrets without printing their values. Review:

- `.env` and environment-specific files;
- config files;
- CI workflow variables/examples;
- Dockerfiles/compose build args;
- frontend environment prefixes;
- test fixtures;
- sample credentials;
- PEM/private key files;
- cloud/provider tokens;
- connection strings.

Use `.env.example` with placeholders. Real secrets should be injected through the deployment secret mechanism appropriate to the environment.

If a live credential was committed, removing it from the current file is not enough. Recommend rotation/revocation. History rewriting is a separate disruptive action and must not be performed automatically.

## 8. Frontend and build leakage

Anything shipped to browser/mobile/public static assets must be considered public. Review framework conventions such as public environment prefixes and build-time replacement.

Do not place server credentials, database URLs with secrets, signing secrets or private API keys in frontend variables. "Obfuscated" client secrets are still exposed.

Inspect source maps/config manifests when deployment could expose sensitive internals.

## 9. Logs, analytics and telemetry

Apply redaction to:

- Authorization headers;
- cookies/session IDs;
- passwords/OTP/reset tokens;
- API keys;
- full payment credentials;
- private keys;
- sensitive request/response bodies.

Structured logs should include identifiers needed for security investigation without duplicating sensitive content.

Third-party error/analytics services are external data recipients; check what payloads are sent.

## 10. Backups, exports and temporary data

Review generated exports, temporary files and backups for:

- authorization;
- predictable/public locations;
- retention/cleanup;
- inclusion of secrets/hidden fields;
- encryption where project requirements demand it;
- access to old/deleted data;
- temporary conversion artifacts.

A protected main database does not protect an accidentally public CSV export.

## 11. Database access and least privilege

Review application database credentials/configuration. Production application accounts should not normally require schema-admin/global privileges. Migration/admin credentials should be separated when architecture supports it.

Check whether error responses expose raw database messages, queries or connection details.

## 12. Tests and evidence

Useful targeted tests include:

- response serializer excludes password hash/internal secret fields;
- frontend build cannot reference server-only secret module/variable;
- logs redact authorization/token fields;
- reset/invite token invalidates after use;
- predictable-token construction is replaced by secure random generation;
- private export requires current authorization;
- debug error response does not expose stack/config in production mode.

When a secret is discovered, evidence should say `path:line`, secret type and whether it appears live/placeholder; never write the full value into the report.
