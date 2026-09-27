# Security Baseline and Source Hierarchy

## Purpose

Use this reference to anchor Stage 07 decisions in current, authoritative identity and access-control guidance without freezing the skill to obsolete implementation details.

## Source hierarchy

When guidance conflicts or a control is time-sensitive, prefer sources in this order:

1. The current specification or protocol standard that defines the behavior being implemented.
2. Current security best-current-practice documents for that protocol.
3. Current framework/library security documentation for the exact version in the project.
4. OWASP verification standards and cheat sheets.
5. NIST digital identity guidance when relevant to authentication, authenticators, recovery, or federation.
6. Project-specific requirements and risk decisions, provided they do not weaken a mandatory security boundary.

Do not rely on a blog post when a maintained specification, official framework document, or security standard is available.

## Current baseline references

At the time this skill was authored, use these as baseline references and verify for newer stable revisions when web research is available:

- OWASP Application Security Verification Standard (ASVS) 5.0.0, stable release: https://owasp.org/www-project-application-security-verification-standard/
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
- NIST SP 800-63-4 Digital Identity Guidelines: https://csrc.nist.gov/pubs/sp/800/63/4/final
- NIST SP 800-63B-4 Authentication and Authenticator Management: https://csrc.nist.gov/pubs/sp/800/63/b/4/final
- RFC 9700, Best Current Practice for OAuth 2.0 Security: https://www.rfc-editor.org/rfc/rfc9700

Relevant OWASP cheat sheets commonly include Authorization, Authentication, Session Management, Password Storage, Forgot Password, Multifactor Authentication, OAuth2, JSON Web Token, and Cross-Site Request Forgery guidance. Verify the current page before relying on a numeric parameter or browser behavior.

## Baseline design principles

Treat the following as default requirements:

- Minimize custom authentication and cryptographic code.
- Prefer opaque server-side state when it materially simplifies revocation and trust management.
- Use signed tokens only when the architecture benefits from distributed verification and the team can correctly operate key rotation, claim validation, revocation/expiry strategy, and audience boundaries.
- Keep authorization data authoritative on the server. Token claims can carry authorization context only with a defined freshness and revocation model.
- Use stable immutable subject identifiers internally. Treat email, phone, username, display name, and tenant slug as mutable attributes unless the product explicitly guarantees immutability.
- Separate authentication assurance from application authorization.
- Separate human identities, service identities, API credentials, and webhook credentials.
- Scope credentials to the minimum client, audience, tenant, resource, and permission set needed.
- Make security-sensitive state transitions explicit and testable.
- Protect recovery and authenticator management at least as strongly as the authentication mechanism they can replace.
- Require recent authentication or step-up for security-critical account changes when the risk justifies it.
- Make logout, suspension, password reset, MFA reset, role change, tenant removal, and credential compromise behavior deterministic.
- Avoid security controls that depend on a frontend not making a request.
- Avoid user-controlled role, permission, owner, subject, or tenant assignment fields unless an authorized administrative policy explicitly permits them.
- Use generic error behavior where distinguishing account existence would enable enumeration.
- Log enough to investigate security events, but never log reusable secrets.

## Risk escalation triggers

Apply stricter controls when any of these are present:

- administrator or support impersonation capabilities;
- money movement, billing, payouts, purchases, refunds, or financial approvals;
- regulated, highly sensitive, or bulk-exportable user data;
- multi-tenant B2B isolation requirements;
- organization ownership transfer;
- production infrastructure administration;
- security configuration, secrets, API credentials, or integration management;
- privileged developer/operator access;
- healthcare, identity, legal, financial, or government workflows;
- public APIs with delegated authorization;
- high-value accounts likely to be targeted;
- machine-to-machine credentials with broad data access.

For these cases, consider stronger MFA, step-up authentication, phishing-resistant authenticators, shorter privilege freshness windows, stricter session management, dual control/approval, dedicated audit events, and more aggressive negative testing.

## Version-sensitive decisions

Before choosing or validating any of the following, check current official guidance if web access exists:

- password hashing algorithm parameters;
- password length and composition policy;
- browser cookie and SameSite behavior;
- OAuth/OIDC flow recommendations;
- passkey/WebAuthn platform behavior;
- JWT/JWS library defaults and supported algorithms;
- framework auth middleware defaults;
- CSRF recommendations for the exact client/server architecture;
- token storage recommendations for browser/mobile clients.

Record the source consulted when a version-sensitive decision materially affects the design.

## Evidence policy

A design statement is not implementation evidence. Acceptable evidence includes:

- a code location tied to a control;
- a passing automated test exercising the real boundary;
- a migration/schema constraint;
- a runtime configuration value verified in the active environment;
- a command result from the current code;
- a request/response test against the application in a controlled environment;
- a deterministic static-audit result reviewed and dispositioned.

Never use screenshots of UI role visibility as proof of server authorization.
