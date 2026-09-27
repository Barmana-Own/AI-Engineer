# Dependency and Software Supply-Chain Review

## Table of contents

1. Inventory
2. Native advisory tooling
3. Reachability and project impact
4. Update discipline
5. Lockfiles and reproducibility
6. Install/build scripts
7. CI/CD and provenance
8. Package-name and source risks
9. Containers/base images
10. SBOM/provenance artifacts
11. Reporting rules

## 1. Inventory

Identify all package/ecosystem manifests and lockfiles, including nested workspaces/services. Examples include npm/pnpm/yarn, Python, Go, Rust, Java, .NET, PHP and container images.

Record package-manager/runtime versions when they materially affect audit output.

## 2. Native advisory tooling

Use existing/native project tooling where available. Examples may include package-manager audit commands or already-configured SCA scanners. Do not install a new invasive tool merely to satisfy the checklist unless it is appropriate and does not destabilize the project.

Capture command, exit status and concise result. If tooling cannot run due to network/registry/environment limits, mark `NOT_RUN` with reason and perform manual manifest/lockfile review.

## 3. Reachability and project impact

An advisory's package severity is not automatically the application's finding severity. Determine:

- direct vs transitive dependency;
- production vs development/build-only;
- affected version range;
- whether the vulnerable feature/code path is used;
- whether attacker-controlled input reaches it;
- deployment exposure;
- compensating controls;
- available fixed version.

Report both advisory severity and project-specific risk when useful.

## 4. Update discipline

Prefer the smallest compatible upgrade that fixes the issue. Follow the project's package manager and lockfile.

Never use force-major automated remediation (`audit fix --force` or equivalent) merely to reduce the advisory count. Major upgrades require compatibility review and tests.

After an upgrade:

- inspect manifest/lockfile diff;
- run affected tests/build;
- retest the security condition if reachable;
- check for new peer/deprecation/runtime issues.

If no safe fix exists, document exposure and mitigation rather than hiding the advisory.

## 5. Lockfiles and reproducibility

Review whether production dependencies are locked/reproducible as intended. Check accidental deletion/ignore of lockfiles, multiple conflicting lockfiles and CI using a different package manager than development.

Do not regenerate a lockfile with a different package manager.

## 6. Install/build scripts

Review high-risk lifecycle/install scripts when relevant, especially newly added/unfamiliar packages. Consider whether packages execute native downloads/scripts during install/build.

Do not execute arbitrary scripts from unknown packages solely for investigation.

## 7. CI/CD and provenance

Inspect repository CI workflow for supply-chain-sensitive behaviors:

- unpinned third-party actions/tools where pinning is expected;
- secrets exposed to untrusted fork/PR contexts;
- build artifacts from untrusted input being promoted to release;
- overly broad CI tokens/permissions;
- publishing credentials in unsafe job contexts;
- downloading executables without integrity/source controls;
- branch/tag protections if represented in repo configuration.

Review actual repository configuration only; do not claim organization-level settings that are not visible.

## 8. Package-name and source risks

Check dependencies sourced from:

- Git URLs/branches;
- local paths;
- tarball URLs;
- private registries;
- similarly named internal/public packages.

Identify dependency-confusion/typosquatting exposure only when repository configuration makes it plausible. Do not label a normal private package as vulnerable without evidence.

## 9. Containers and base images

Review base image tags/digests and whether the image includes unnecessary build/runtime tools. Use available container scanners if already available/appropriate. Distinguish OS-package advisory noise from reachable application risk while still patching meaningful high-risk base-image issues.

Avoid `latest` when reproducibility matters. A digest can improve immutability but requires an update process; choose according to project deployment conventions.

## 10. SBOM and provenance artifacts

If the project already generates an SBOM/provenance record, verify it remains accurate after Stage 08 changes. If supply-chain requirements explicitly demand one and generation tooling exists, update it. Do not make SBOM generation a universal PASS requirement unless required by the project/workflow.

## 11. Reporting rules

Report:

- manifests/lockfiles reviewed;
- audit/SCA commands and results;
- material advisories with project context;
- packages upgraded and verification performed;
- unresolved dependency risks;
- tooling limitations.

Do not copy huge audit outputs into the report. Summarize and point to machine output if the project stores it.
