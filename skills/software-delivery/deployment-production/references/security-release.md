# Release Security and Supply-Chain Controls

## Table of contents

1. Purpose
2. Threat model
3. Secret handling
4. Dependency integrity
5. CI/CD trust boundaries
6. Container/runtime hardening
7. SBOM and provenance
8. Vulnerability triage
9. Client build exposure
10. Network and TLS controls
11. Release evidence
12. Failure conditions

## 1. Purpose

Use this reference to prevent a release pipeline from becoming the path that introduces credentials, vulnerable dependencies, mutable artifacts, excessive privileges, or unverifiable binaries into production.

Apply project-specific judgment. Do not force a tool solely because it is listed here; implement the strongest practical equivalent for the actual ecosystem and target.

## 2. Threat model

Consider at least these release-path threats:

- leaked source or deployment credentials;
- compromised dependency/package;
- dependency confusion or unintended registry use;
- compromised CI action/plugin/build image;
- attacker-controlled pull request gaining production secrets;
- artifact rebuilt from different source after testing;
- malicious or stale base image;
- accidental inclusion of `.env`, SSH keys, cloud configs, database dumps, or tokens in artifacts;
- excessive runtime privileges;
- public exposure of internal admin/metrics/debug services;
- client-side exposure of server secrets;
- unsigned/unverifiable artifacts where provenance is required;
- vulnerable package accepted without impact analysis.

## 3. Secret handling

### Repository checks

Inspect tracked and untracked release-relevant files for credential material using trustworthy secret-scanning tooling when available. Also manually inspect high-risk locations:

- `.env`, `.env.*`;
- CI workflow files;
- Dockerfiles and Compose manifests;
- infrastructure manifests;
- application config;
- shell scripts;
- test fixtures;
- exported database/config dumps;
- private keys/cert bundles;
- npm/pip/maven/nuget registry configs;
- cloud CLI config files.

Do not print discovered secret values into logs/evidence. Record file/line/category in redacted form.

### If a real secret is found

Treat deletion from the current file as insufficient. Determine whether it was committed, built into an artifact, logged, uploaded, or deployed. Rotate/revoke when authorized and record the exposure boundary. If rotation requires external access not available, classify that as a blocker when the credential could be live and release-significant.

### Build-time secrets

Never pass long-lived secrets via Docker `ARG` or other mechanisms that can persist in image history/layers. Use build secret mounts or target-native protected secret mechanisms when a private dependency registry requires credentials.

### Runtime secrets

Prefer target secret stores or protected environment injection. Define:

- owner;
- scope;
- rotation expectation;
- restart/reload requirement;
- revocation path;
- environment separation.

Avoid sharing production credentials with non-production environments.

## 4. Dependency integrity

For every ecosystem:

1. Identify authoritative manifest and lockfile.
2. Use frozen/immutable install mode when supported.
3. Confirm package registry sources are expected.
4. Investigate unexpected git/path/file dependencies.
5. Remove unused production dependencies when practical.
6. Run ecosystem vulnerability audit/scanner.
7. Record tool version and database timestamp if available.
8. Triage findings based on actual runtime reachability/exposure, not CVSS alone.

Do not blindly upgrade major versions during Stage 11 unless necessary for a release blocker and validated against regression tests.

### Registry integrity

For private registries, verify scope mapping prevents unintended fallback to public packages for private names when the ecosystem is susceptible to dependency-confusion patterns.

## 5. CI/CD trust boundaries

Review:

- trigger events;
- branch/tag restrictions;
- pull-request behavior;
- fork behavior;
- environment protections;
- token permissions;
- OIDC/cloud federation scope;
- secret availability;
- artifact download/upload trust;
- reusable workflow trust;
- third-party actions/plugins;
- manual inputs interpolated into shell commands.

Production deploy secrets must not become available to arbitrary untrusted pull-request code.

Prefer short-lived federated credentials over long-lived static cloud keys when the platform supports it and project scope permits.

Set CI job token permissions explicitly and minimally where the CI provider supports permission scoping.

Pin third-party actions/plugins to an immutable commit/digest where supply-chain policy warrants it. If using a version tag for maintainability, document the trade-off.

## 6. Container/runtime hardening

Inspect production images for:

- root execution;
- package managers/compilers/debuggers left in runtime image unnecessarily;
- shell utilities not required by the app;
- world-writable sensitive paths;
- setuid/setgid binaries where not needed;
- private keys or credentials;
- development dependencies;
- exposed debug/admin ports;
- stale/vulnerable base images;
- mutable `latest` base/image references in critical release paths.

Where target supports it, prefer:

- non-root UID/GID;
- read-only root filesystem if compatible;
- dropped Linux capabilities;
- no privilege escalation;
- seccomp/AppArmor/default sandboxing;
- bounded memory/CPU/PID resources;
- isolated service accounts;
- private network access to stateful services.

Do not enable a hardening control that breaks legitimate application behavior without understanding and documenting the required exception.

## 7. SBOM and provenance

Generate an SBOM for production artifacts when tooling is available or policy requires it. Use standard formats supported by the toolchain, commonly SPDX or CycloneDX.

The SBOM should correspond to the actual release artifact, not merely the source repository.

Capture:

- release source commit;
- build workflow identity;
- artifact digest;
- image digest if applicable;
- SBOM path/digest;
- signing/provenance reference if used.

Use artifact signing/attestation when supported by the deployment ecosystem or required by organizational policy. Do not claim SLSA/provenance level or compliance that has not been verified.

## 8. Vulnerability triage

For each significant finding, record:

- component/version;
- severity;
- affected artifact/service;
- runtime reachable?;
- exploit preconditions;
- fixed version/mitigation;
- remediation performed;
- residual risk;
- decision/owner when accepted.

Release-block by default for confirmed exploitable critical vulnerabilities in an exposed production path. High findings require project-specific analysis; do not silently ignore them.

A scanner finding in a dev-only dependency excluded from production may be non-blocking, but prove the production exclusion.

A scanner returning an error, rate limit, stale DB, or partial scan is not equivalent to zero findings.

## 9. Client build exposure

For browser/mobile/public client bundles, assume bundled values are public. Inspect:

- generated JS/source maps;
- public environment variables;
- API keys that grant privileged access;
- internal base URLs;
- debug endpoints;
- source maps exposing sensitive source where policy forbids it.

A public identifier may be acceptable; a server credential or signing secret is not.

## 10. Network and TLS controls

Require production public traffic to use TLS unless the architecture is strictly internal and another trusted encrypted boundary is documented.

Verify:

- TLS termination ownership;
- HTTP-to-HTTPS redirect if applicable;
- HSTS only when domain/subdomain implications are understood;
- certificate renewal ownership;
- trusted proxy list/network;
- secure cookies behind proxy;
- real client IP handling;
- internal services not directly public;
- metrics/admin endpoints protected;
- database/broker/cache exposure restricted.

Do not disable certificate verification for convenience. If a development certificate is needed in local production-like testing, scope the exception to that environment and never copy it into production settings.

## 11. Release evidence

Record evidence such as:

- secret scan command/result summary;
- dependency audit command/result summary;
- container scan result;
- SBOM path/hash;
- artifact/image digest;
- CI permissions review;
- runtime privilege review;
- accepted-risk records;
- confirmation that example/config artifacts contain placeholders only.

Never store secret values in the evidence ledger.

## 12. Failure conditions

Fail `G08_SUPPLY_CHAIN_SECURITY` when any of these remain unresolved and applicable:

- known live secret embedded in source/artifact;
- production artifact cannot be tied to reviewed source;
- untrusted CI path can access production credentials;
- confirmed critical exploitable dependency/image vulnerability without mitigation/approved exception;
- client bundle contains privileged server secret;
- runtime requires unjustified privileged access that materially expands risk;
- scanner results are fabricated or incomplete but represented as clean.
