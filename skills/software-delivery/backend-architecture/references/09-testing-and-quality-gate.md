# Testing and Stage 04 Quality Gate

## Table of contents

1. Evidence hierarchy
2. Required test layers
3. Architecture checks
4. Command execution
5. Negative checks
6. PASS gate
7. BLOCKED gate
8. Evidence recording

## 1. Evidence hierarchy

Prefer evidence in this order:

1. executable tests/checks that pass;
2. static analysis or architecture rules;
3. inspected implementation with exact file references;
4. documented design for intentionally deferred later-stage work.

Prose alone is weak evidence for implemented claims.

## 2. Required test layers

### Domain tests

Cover business invariants, value semantics, state transitions, money/time rules, and domain behavior that can run without infrastructure.

### Application/use-case tests

Use fakes/stubs for ports to cover:

- happy path;
- authorization decision where implemented at use-case boundary;
- validation/precondition failure;
- not-found/conflict paths;
- dependency error mapping;
- transaction/idempotency/concurrency behavior where the use case owns it.

### Transport/contract tests

For critical routes/handlers, cover parsing, validation, error mapping, and public contract semantics without requiring final Stage 05 persistence when practical.

### Architecture/boundary tests

Use ecosystem-native dependency/architecture tests where available. Otherwise run targeted import/search checks and document the inspected boundaries.

## 3. Architecture checks

Verify at least:

- transport does not contain material business rules;
- domain/application do not import concrete ORM/database clients;
- domain/application do not import vendor HTTP/queue/cloud SDKs except documented localized exceptions;
- no new circular module dependency is introduced;
- repository ports express semantic operations and tenant scope where required;
- authorization is represented at use-case/resource level for sensitive operations;
- secrets are not hard-coded in changed Stage 04 files;
- logs do not intentionally emit known sensitive fields;
- Stage 05 persistence requirements are complete enough to implement.

## 4. Command execution

Discover commands from the repository rather than guessing.

Run all applicable checks the environment can support, typically:

- formatting/check mode;
- lint;
- typecheck/static compile;
- unit tests;
- relevant contract/integration tests that do not require unavailable external infrastructure;
- build/package compile;
- Stage 04 validator.

If a command cannot run:

1. set its status to `NOT_RUN`;
2. record the exact reason;
3. determine whether the missing evidence blocks PASS.

A missing optional check may not block PASS. A missing critical compile/test check normally blocks PASS when no equivalent evidence exists.

Do not weaken configuration or delete tests to obtain a green result.

## 5. Negative checks

Before PASS, actively search for:

- `TODO`, `FIXME`, `HACK`, placeholder exceptions, unimplemented methods in Stage 04 critical paths;
- hard-coded credentials/tokens/secrets in changed files;
- controllers/routes performing direct SQL/ORM calls newly introduced by Stage 04;
- domain/application importing infrastructure SDKs;
- duplicated backend roots created accidentally;
- generic catch blocks swallowing errors without mapping/logging;
- unbounded external calls without timeout semantics;
- unsafe retries of non-idempotent operations;
- tenant ID accepted from client without policy reconciliation in multi-tenant flows;
- Stage 05 work accidentally finalized (new final migrations/schema) unless preserving pre-existing code.

Classify findings as gate failures or documented later-stage risks.

## 6. PASS gate

Declare PASS only when all are true:

1. Stage 03 precondition is verified.
2. Repository was inspected and the actual backend root/stack is documented.
3. All backend-relevant requirements have coverage status; no critical requirement is silently missing.
4. Module ownership and dependency direction are explicit and coherent.
5. Critical domain invariants are implemented/tested or safely represented for this stage.
6. Required application use cases exist with explicit authorization, errors, transaction, idempotency/concurrency semantics where applicable.
7. Persistence and external dependencies are behind appropriate ports/seams.
8. Transport validation and stable error handling exist for implemented critical surfaces.
9. Architecture-level security and tenant constraints are represented.
10. Configuration/secrets handling is safe for Stage 04.
11. Logging/correlation and reliability contracts are established to the level required by the runtime.
12. Applicable domain/application tests pass.
13. Applicable lint/typecheck/build checks pass.
14. No unresolved Stage 04 critical TODO or architecture violation remains.
15. `docs/04-backend-architecture.md` reflects the real implementation.
16. `docs/04-backend-architecture.evidence.json` contains current command evidence.
17. `docs/04-stage05-handoff.json` is complete and parseable.
18. `project-state.json` is updated without destroying unknown keys.
19. `scripts/validate_stage04.py <project-root>` exits successfully.
20. Residual risks are explicit and genuinely belong to later stages.

## 7. BLOCKED gate

Use BLOCKED only if a true external dependency prevents satisfying a mandatory gate and no safe abstraction/assumption can allow progress.

Do not mark Stage 04 completed in `completed_stages` with PASS when blocked.

Record blocker code, evidence, affected requirements, partial artifacts, and the minimum unblocking action.

## 8. Evidence recording

For each command record:

- command string (redact secrets);
- working directory;
- start/end time or timestamp when available;
- exit code;
- status: `PASS`, `FAIL`, `NOT_RUN`;
- concise output summary;
- failure reason/remediation if relevant.

Do not paste huge logs into evidence JSON. Store concise summaries and file/report paths when needed.

## 9. Adversarial architecture review

Before final PASS, challenge the implementation as if reviewing another senior engineer's work. Answer with evidence, not intuition:

1. Can any transport handler mutate sensitive state without the intended use-case authorization path?
2. In a multi-tenant product, can a client-controlled tenant/account identifier cause cross-tenant read or write access?
3. Can retry, double-click, webhook redelivery, or job retry execute a harmful mutation twice?
4. Can two concurrent requests violate a business invariant before Stage 05 adds the required constraint/versioning?
5. Can an upstream dependency hang the request/job indefinitely because timeout semantics are missing?
6. Can a transient retry accidentally repeat a non-idempotent provider operation?
7. Can domain/application code be tested without a real database or remote provider?
8. Does any controller/handler still contain material business rules or direct database coupling introduced in this stage?
9. Can one module import another module's internals and bypass its public application boundary?
10. Are vendor SDK types or ORM entities leaking into domain/application/public response contracts?
11. Could logs/errors disclose credentials, tokens, personal data, documents, or internal stack/SQL details?
12. Can Stage 05 implement persistence correctly without guessing atomicity, uniqueness, query, tenant, retention, or concurrency requirements?
13. Is any microservice, queue, cache, event bus, generic abstraction, or pattern present without a requirement-driven reason?
14. Is there any critical upstream requirement that is represented only in documentation but absent from the implementation/testing expected in Stage 04?
15. Would a new engineer be able to locate the backend root, module boundaries, commands, and handoff artifacts without reverse engineering the entire repository?

Any critical unanswered item is a gate failure or must be recorded as a true external blocker.
