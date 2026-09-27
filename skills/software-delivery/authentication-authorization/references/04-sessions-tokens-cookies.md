# Sessions, Tokens, Cookies, and Revocation

## Contents

- [Purpose](#purpose)
- [Start with a credential inventory](#start-with-a-credential-inventory)
- [Server-side cookie sessions](#server-side-cookie-sessions)
- [CSRF for cookie-authenticated requests](#csrf-for-cookie-authenticated-requests)
- [Bearer access tokens](#bearer-access-tokens)
- [JWT verification](#jwt-verification)
- [Refresh tokens](#refresh-tokens)
- [Opaque tokens](#opaque-tokens)
- [Revocation model](#revocation-model)
- [Browser storage](#browser-storage)
- [Mobile/native clients](#mobilenative-clients)
- [Websocket/realtime](#websocketrealtime)
- [Service-to-service credentials](#service-to-service-credentials)
- [Required tests](#required-tests)


## Purpose

Use this reference to define and verify the entire credential lifecycle after authentication. Do not treat token issuance as the end of authentication security.

## Start with a credential inventory

For every credential/session type record:

| Credential | Holder | Issuer | Verifier | Transport | Storage | Lifetime | Renewal | Revocation | Audience |
|---|---|---|---|---|---|---|---|---|---|

Include browser session cookies, access tokens, refresh tokens, API keys, websocket credentials, device tokens, remembered-device cookies, temporary step-up state, reset/recovery transactions, and service credentials.

## Server-side cookie sessions

Prefer a mature session framework. Verify:

- session identifiers are generated with a cryptographically secure primitive;
- unknown/attacker-chosen session IDs are not accepted as valid server sessions;
- rotate the session identifier after successful login and privilege elevation when the framework does not already do so;
- cookie uses `HttpOnly` when client JavaScript does not need the secret;
- cookie uses `Secure` in TLS environments;
- `SameSite` is selected deliberately for the actual cross-site flow requirements;
- cookie domain/path are no broader than required;
- persistent expiration is used only when product behavior requires it;
- session data store has explicit expiry/cleanup;
- logout invalidates the server session, not merely the browser copy;
- session state is invalidated on account suspension/disablement and security events according to policy.

Do not infer CSRF safety from `SameSite` alone when the application's threat model requires explicit CSRF defense.

## CSRF for cookie-authenticated requests

For state-changing browser requests authenticated by automatically attached cookies:

- use the framework's maintained CSRF protection or a proven synchronizer-token/double-submit design appropriate to the architecture;
- validate token on state-changing methods/actions;
- do not expose CSRF token to third-party origins;
- combine with origin/referer validation when appropriate as defense in depth;
- protect login and other security-sensitive flows when login CSRF/session swapping is plausible;
- ensure CORS settings do not accidentally allow credentialed cross-origin requests from untrusted origins.

Document why a route is exempt if it is deliberately exempt.

## Bearer access tokens

Bearer tokens are credentials: possession is sufficient unless an additional sender-constraining mechanism is used.

Requirements:

- transmit only over TLS outside local development;
- keep lifetime as short as practical for the product and client type;
- scope to intended audience/resource server;
- reject malformed, expired, not-yet-valid, wrong-issuer, wrong-audience, or unverifiable tokens;
- do not put tokens in query strings;
- avoid writing them to logs or analytics;
- do not use access tokens as database authorization truth when server-side state can change independently without a freshness strategy.

## JWT verification

If JWT/JWS is used:

- verify signature using the expected key source;
- use an explicit allowed algorithm set supported by the chosen architecture;
- never accept `none` or attacker-selected algorithms;
- validate issuer when an issuer exists;
- validate audience for the resource/client boundary;
- validate expiration and not-before/time claims as applicable;
- validate subject and token type/purpose where relevant;
- distinguish access, ID, refresh, reset, and email-verification token purposes so one cannot be substituted for another;
- validate key identifiers safely; do not let an untrusted token select arbitrary filesystem/URL key material;
- cache JWKS/discovery data safely and define rotation behavior for external issuers;
- avoid embedding secrets or sensitive personal data in JWT payloads merely because tokens are signed; ordinary JWT payloads are readable by holders.

Do not use a decode-only API as verification.

## Refresh tokens

If refresh tokens are used:

- bind each token to a session/device/client record when architecture permits;
- store a verifier/hash rather than raw token when the server only needs to compare presented values;
- set an absolute lifetime and appropriate inactivity policy;
- rotate on successful use for public/browser/mobile clients when the chosen design relies on rotation;
- detect reuse of a rotated token where practical and revoke the affected token family/session;
- make refresh atomic so concurrent redemption cannot create multiple valid descendants unexpectedly;
- revoke on logout when logout semantics promise server invalidation;
- revoke on account disablement, password/MFA reset, tenant removal, or compromise according to policy;
- ensure a stolen refresh token cannot mint access for an unintended audience/client.

If refresh tokens are intentionally non-rotating, document the compensating controls and why the risk is acceptable.

## Opaque tokens

Opaque tokens still require:

- cryptographically strong generation;
- secure storage/verifier handling;
- expiry;
- scope/audience association;
- revocation;
- safe lookup that does not expose token values;
- operational cleanup.

Opaque tokens simplify immediate revocation when resource servers introspect authoritative state, but the actual architecture determines tradeoffs.

## Revocation model

Define events and effects explicitly:

| Event | Access token | Refresh/session | API key | MFA remembered state | Authorization cache |
|---|---|---|---|---|---|
| Logout | project-specific | revoke expected session | usually unchanged | project-specific | refresh if needed |
| Password reset | short-lived token may age out or be revoked | revoke per compromise policy | project-specific | often revoke | invalidate |
| Account suspension | deny even if token valid | revoke/deny | revoke/deny | revoke | invalidate |
| Role removal | must stop privilege within bound | refresh/revoke as needed | scope re-evaluate | unchanged | invalidate |
| Tenant removal | deny tenant access | refresh/revoke tenant context | revoke tenant key | unchanged | invalidate |
| MFA reset | risk-based | often revoke privileged sessions | project-specific | revoke | invalidate |
| Suspected compromise | revoke/deny | revoke | rotate/revoke | revoke | invalidate |

The exact matrix belongs in project documentation. The key requirement is deterministic behavior with a tested maximum stale-privilege window.

## Browser storage

Preferred order depends on architecture, but treat persistent JavaScript-readable storage as higher risk for bearer credentials because XSS can read it.

- Prefer secure HttpOnly cookies for browser session credentials when compatible with architecture.
- If JavaScript must hold a short-lived token, keep persistence minimal and document XSS exposure.
- Do not place long-lived refresh credentials in `localStorage` merely for convenience without explicit architecture/risk approval.
- Clear client-side auth state on logout/revocation signals, but do not rely on clearing the client as the only revocation mechanism.

## Mobile/native clients

Use platform secure credential storage where available. Do not store long-lived secrets in ordinary preferences/files. Treat app reinstall, device backup, rooted/jailbroken environments, and deep-link callback handling according to platform threat model.

## Websocket/realtime

Authenticate the connection and authorize each channel/resource subscription. Do not assume an authenticated socket may subscribe to any identifier it requests. Define expiry/re-authentication behavior for long-lived connections.

## Service-to-service credentials

- scope to service/audience;
- avoid sharing one static secret across many services;
- support rotation with overlap when needed;
- use workload identity/mTLS/platform identity where the deployment platform provides a stronger managed primitive;
- log credential identifier, not secret;
- verify downstream authorization separately from transport identity.

## Required tests

As applicable:

- session fixation defense;
- cookie attributes in runtime response;
- CSRF rejection and valid request acceptance;
- expired token rejected;
- wrong issuer/audience rejected;
- decode-without-signature attack rejected;
- token-purpose substitution rejected;
- logout invalidates session/refresh as designed;
- rotated refresh token reuse rejected/detected;
- suspension blocks an otherwise syntactically valid token;
- role/tenant removal stops access within documented window;
- websocket subscription cannot cross authorization boundary.
