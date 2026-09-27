# OAuth, OpenID Connect, SSO, and Federation

## Contents

- [Purpose](#purpose)
- [Architecture inventory](#architecture-inventory)
- [Authorization Code flow](#authorization-code-flow)
- [Redirect URI handling](#redirect-uri-handling)
- [State and login CSRF](#state-and-login-csrf)
- [OIDC nonce](#oidc-nonce)
- [PKCE](#pkce)
- [Token validation](#token-validation)
- [Discovery and JWKS](#discovery-and-jwks)
- [Account mapping and linking](#account-mapping-and-linking)
- [Provider access tokens](#provider-access-tokens)
- [Enterprise SSO](#enterprise-sso)
- [Logout](#logout)
- [Required negative tests](#required-negative-tests)


## Purpose

Use this reference when the project integrates an external authorization server or identity provider. Apply the current provider documentation plus current OAuth/OIDC security best practice. RFC 9700 is the baseline OAuth 2.0 security BCP at the time this skill was authored; verify for newer guidance.

## Architecture inventory

Record:

- provider/issuer;
- client type (confidential/public);
- grant/flow;
- redirect URI(s);
- scopes;
- PKCE use;
- state use;
- nonce use for OIDC;
- client authentication method;
- discovery/JWKS source;
- token audience/resource server;
- where provider tokens are stored;
- application account-linking rule;
- logout/session coupling.

## Authorization Code flow

Prefer authorization code flows with current security protections rather than deprecated implicit-style token delivery.

For public/native/browser clients, use PKCE according to current protocol/provider requirements. For confidential clients, use strong client authentication appropriate to the provider and deployment.

## Redirect URI handling

- register explicit redirect URIs;
- enforce exact matching as required by current security guidance/provider behavior;
- do not implement an open redirector in the callback or post-login redirect path;
- validate local post-login return targets against an allowlist or safe relative-path rule;
- never accept arbitrary external `next`, `redirect`, `returnTo`, or equivalent targets without validation.

## State and login CSRF

Use `state` or an equivalent framework-managed transaction binding for redirect flows where required. Bind it to the initiating browser transaction and consume it once.

Reject:

- missing state when required;
- mismatched state;
- expired state;
- reused state;
- state belonging to another browser/session transaction.

Do not store sensitive return state directly in an unsigned, attacker-editable parameter.

## OIDC nonce

When using OIDC ID tokens in a flow requiring nonce:

- generate unpredictable nonce;
- bind it to the authentication transaction;
- verify returned nonce exactly;
- reject missing/mismatched/replayed nonce;
- consume transaction state after successful callback.

## PKCE

When PKCE is used:

- generate a cryptographically random verifier;
- derive challenge using the recommended method supported by current standards/provider;
- bind verifier to the transaction;
- never expose verifier through URL/logging;
- reject callbacks/token exchanges without the correct verifier.

## Token validation

For ID/access tokens validate the fields required by the protocol and architecture. Common checks include:

- signature;
- issuer;
- audience/client ID;
- expiration;
- not-before/issued-at within accepted clock behavior where required;
- nonce for OIDC flow;
- authorized party when applicable;
- token type/purpose;
- provider-specific required claims.

Use the provider/framework verifier rather than hand-rolling JWS validation.

Do not accept a token from Provider A merely because it uses a key format similar to Provider B.

## Discovery and JWKS

- pin issuer to configured trusted providers;
- do not accept arbitrary issuer/discovery URLs from end-user input;
- retrieve keys from the issuer's trusted metadata path;
- cache and rotate keys according to library/provider behavior;
- fail closed when a token cannot be verified;
- prevent token-controlled key URLs or arbitrary network fetches.

## Account mapping and linking

The hardest federation defect is often account confusion rather than cryptography.

Rules:

- map external identity by stable issuer + subject ID;
- do not rely only on display name or mutable username;
- treat email-based auto-linking as a security policy decision, not a convenience default;
- if auto-linking by verified email is permitted, document the provider trust assumptions and collisions/changes behavior;
- require trusted existing authentication plus provider verification for manual linking;
- prevent one external identity from linking to multiple local accounts unintentionally;
- audit linking/unlinking;
- test account takeover attempts through linking.

## Provider access tokens

An external provider access token is authorization to the provider/resource server, not automatically authorization to your application.

- store provider tokens only if the application needs provider APIs;
- protect refresh tokens as high-value secrets;
- request minimum scopes;
- revoke/disconnect when integration is removed where provider supports it;
- do not expose provider refresh tokens to browser code unless the architecture explicitly requires a public-client flow and follows provider security guidance.

## Enterprise SSO

For enterprise tenants define:

- tenant-to-issuer/domain configuration ownership;
- how an admin proves control before enabling SSO;
- whether local password login remains enabled;
- emergency/break-glass access policy;
- just-in-time provisioning rules;
- role/group mapping trust model;
- deprovisioning behavior;
- SSO enforcement and bypass protection;
- audit events for configuration changes.

Do not trust arbitrary group/role claims unless the issuer and mapping were configured by an authorized tenant administrator and the application constrains them to allowed roles.

## Logout

Clarify which logout is implemented:

- local application session logout;
- provider logout;
- federated single logout.

Do not claim provider/federated logout if only the local cookie/session is cleared. Conversely, local logout must still invalidate local session state even if provider logout is unavailable.

## Required negative tests

As applicable:

- callback without state;
- wrong/replayed state;
- wrong nonce;
- wrong issuer;
- wrong audience;
- expired token;
- token signed by untrusted key;
- code replay;
- PKCE verifier mismatch;
- unsafe external return URL;
- account-linking collision/takeover attempt;
- tenant configured for SSO cannot bypass enforced SSO unexpectedly;
- role/group claim cannot grant an unconfigured application role.
