# Requirements Traceability

## Table of contents

1. Goal
2. Requirement inventory
3. Traceability dimensions
4. Coverage states
5. Critical requirement rules
6. Suggested matrix
7. Handoff relationship

## 1. Goal

Prove that the backend architecture covers validated product behavior. Architectural elegance does not compensate for lost requirements.

## 2. Requirement inventory

Collect every backend-relevant item from earlier stages, including:

- actor capabilities and permissions;
- business rules and invariants;
- commands/mutations;
- queries/read behaviors;
- workflows and state transitions;
- uploads/downloads;
- notifications;
- external integrations;
- money/payment behaviors;
- audit/evidence needs;
- lifecycle/retention/deletion rules;
- multi-tenant/account boundaries;
- performance, availability, latency, throughput, and reliability constraints;
- frontend data expectations and error/empty/loading assumptions that imply backend contracts.

If upstream requirements do not have IDs, assign local trace IDs such as `S04-RQ-001` while preserving the original wording/source.

## 3. Traceability dimensions

For each requirement, capture:

- source artifact/reference;
- requirement ID;
- short statement;
- criticality: critical/high/normal;
- owning backend module;
- use case(s);
- domain rule/invariant if applicable;
- authorization policy;
- transport/API surface if known;
- repository/external ports needed;
- transaction/consistency need;
- validation/error behavior;
- test evidence;
- Stage 05 persistence need;
- status;
- assumption/risk/defer reason.

## 4. Coverage states

Use only:

- `COVERED`: implemented or explicitly represented in Stage 04 architecture with evidence.
- `DEFERRED_WITH_REASON`: belongs to a later stage and Stage 04 has defined the seam/constraint needed to defer safely.
- `BLOCKED`: cannot be implemented safely because of a true blocker.

Never use vague states such as `mostly done` for the final gate.

## 5. Critical requirement rules

A critical requirement cannot be `DEFERRED_WITH_REASON` if deferral would cause any of the following:

- incorrect authorization or tenant boundary;
- irreversible data loss;
- incorrect money movement or financial calculation;
- inability to enforce a core business invariant;
- architectural lock-in that makes the known requirement expensive to implement later;
- inability to audit a regulated or legally significant action when required.

A critical requirement without a safe Stage 04 representation blocks PASS.

## 6. Suggested matrix

Include a concise matrix in `docs/04-backend-architecture.md` or a generated appendix:

| Requirement | Module | Use case | AuthZ | Ports | Tx/Consistency | Test evidence | Status |
|---|---|---|---|---|---|---|---|

Do not make the matrix a substitute for actual implementation.

## 7. Handoff relationship

Every requirement that needs persistence must feed `docs/04-stage05-handoff.json`. Stage 05 should be able to derive storage concerns from business needs without reverse-engineering controllers.
