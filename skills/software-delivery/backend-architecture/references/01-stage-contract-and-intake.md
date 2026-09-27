# Stage 04 Contract and Intake

## Table of contents

1. Purpose
2. Precondition evidence
3. Artifact discovery order
4. Ambiguity classification
5. Blocker criteria
6. Resume behavior
7. Intake checklist

## 1. Purpose

Use this procedure before making architectural or code changes. Stage 04 must be grounded in already-validated product and frontend work, not reconstructed from guesses.

## 2. Precondition evidence

Treat Stage 03 as passed only when at least one trustworthy project artifact states that status, preferably `project-state.json` or the Stage 03 completion artifact. Do not infer PASS merely because frontend files exist.

Accept equivalent legacy naming when the project predates this workflow, but record the mapping in the Stage 04 architecture document.

If the status is explicitly FAILED, BLOCKED, IN_PROGRESS, or absent while the workflow requires a strict stage gate, block Stage 04.

## 3. Artifact discovery order

Inspect in this order:

1. `project-state.json` and other workflow state files.
2. Stage 01 product/requirement artifacts.
3. Stage 02 UX/UI or system-flow artifacts relevant to backend behavior.
4. Stage 03 frontend implementation and its API/data expectations.
5. Existing backend architecture and code.
6. Repository documentation, ADRs, README files, environment examples, CI, and deployment manifests.
7. Tests, fixtures, mocks, generated clients, API schemas, and integration stubs.

Build a source-of-truth table containing artifact, version/date if available, authority, extracted decisions, and conflicts.

## 4. Ambiguity classification

Classify missing information before deciding to block:

### A. Safe engineering assumption

Use when a reasonable default is reversible and does not materially change product meaning, legal/compliance posture, money movement, identity, or destructive behavior.

Action: choose the safest conventional option, record the assumption, continue.

Examples:

- internal folder naming;
- logger library selection when the stack already constrains the choice;
- whether a pure query use case is named `GetOrder` or `GetOrderDetails`.

### B. Upstream inconsistency

Use when Stage 01-03 artifacts contradict each other.

Action:

1. Prefer the later artifact only when it clearly supersedes the earlier decision.
2. Otherwise prefer the artifact that owns the decision domain.
3. If the conflict affects security, money, legal rights, destructive behavior, or required scope, treat as critical until resolved or choose the more restrictive behavior when safe.
4. Record the conflict and resolution.

### C. Critical external dependency

Block only when implementation truly requires information that cannot be safely inferred, such as:

- unavailable private API contract whose request/response semantics determine implementation;
- credentials required to execute a mandatory verification that cannot be replaced with a local fake/contract;
- legal/compliance approval that changes permitted data processing;
- business decision about money, irreversible deletion, entitlement, regulated identity, or contractual obligation;
- cryptographic material or secrets that must never be fabricated.

Do not block for missing cosmetic preferences or details that can be isolated behind a port.

## 5. Blocker criteria

A valid blocker must include:

- blocker code;
- exact missing fact/dependency;
- evidence showing why it is required now;
- affected modules/use cases;
- why a safe assumption or abstraction cannot resolve it;
- minimal action needed to unblock;
- work completed safely despite the blocker.

Do not use `BLOCKED` to avoid difficult implementation or testing.

## 6. Resume behavior

When Stage 04 artifacts already exist:

1. Read them before modifying code.
2. Verify they match current repository state.
3. Reuse still-valid decisions.
4. Re-run relevant quality checks; do not trust stale PASS evidence blindly.
5. Append/replace evidence with the current run rather than duplicating modules or creating a second backend tree.
6. Preserve unknown keys in `project-state.json`.

## 7. Intake checklist

Before Phase 2, know or explicitly record as unknown:

- Stage 03 status and evidence source;
- active repository root;
- backend runtime and entry point, if one exists;
- package manager/build system;
- Stage 01 modules and critical business rules;
- actor/role model;
- frontend data/API expectations from Stage 03;
- non-functional requirements that affect backend architecture;
- integrations and private API dependencies;
- existing DB/persistence code and migration state;
- current auth/authz approach;
- test/lint/typecheck/build commands;
- CI constraints;
- known risks and unresolved upstream decisions.
