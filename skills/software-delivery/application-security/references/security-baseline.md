# Security Baseline and Standards Mapping

## Purpose

Use standards to improve coverage and consistency, not to manufacture a compliance claim. This Stage 08 skill performs project security engineering and verification; it does not by itself certify the application against any external standard.

## Baseline hierarchy

1. Project-specific security requirements and architecture decisions.
2. Current stable OWASP Application Security Verification Standard (ASVS) as the primary application-control verification catalog.
3. Current OWASP API Security Top 10 for API-specific abuse and access-control themes.
4. Latest final NIST Secure Software Development Framework (SSDF) for secure-development process context.
5. CISA Secure by Design principles for ownership of security outcomes, secure defaults, transparency and systemic prevention.
6. CWE categories for root-cause classification when useful.

## Version posture as of skill authoring

- OWASP ASVS 5.0.0 is the stable ASVS release available at the time this skill was authored.
- OWASP API Security Top 10 2023 is the current published API Top 10 edition at the time this skill was authored.
- NIST SP 800-218 SSDF 1.1 is the current final SSDF baseline; later drafts must not be treated as final unless they have become final when the stage is executed.

When internet access is available and the exact version matters, verify these versions from authoritative OWASP/NIST/CISA sources before citing them in the project report.

## How to use the standards

- Map a finding to a standard only when the mapping is direct and helpful.
- Prefer root-cause wording over a generic label such as "OWASP issue".
- Do not claim "ASVS compliant" unless the project explicitly requests a formal requirement-by-requirement verification and all required controls were assessed with evidence.
- Do not downgrade a project-specific critical risk because a top-ten list does not mention it.
- Include business-logic, abuse, tenant-isolation and workflow risks even when no neat OWASP Top 10 category exists.

## Minimum security domains

Every project must explicitly assess or mark N/A with rationale:

- attack surface and trust boundaries;
- authentication and account lifecycle;
- authorization, ownership and tenant isolation;
- input handling and injection;
- browser/output security;
- CSRF/CORS as applicable to auth architecture;
- API resource and business-flow abuse;
- SSRF/outbound request safety;
- file/path/parser safety;
- secrets, sensitive data and cryptography;
- dependencies and supply chain;
- runtime/container/deployment configuration;
- logging, error handling and auditability;
- integrations, callbacks and webhooks;
- regression tests for material security controls.
