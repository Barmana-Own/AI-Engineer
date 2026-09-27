# Controlled Self-Improvement Engine

> Gregorian date: 2026-09-18
> Jalali date: 1405-06-27


The self-improvement engine is an evidence-driven, resumable workflow for safe local engineering changes. It is deliberately separate from the model gateway, local-agent tool execution, and the existing autonomous task loop.

## Lifecycle

OBSERVE -> DIAGNOSE -> PROPOSE -> PLAN -> CHECKPOINT -> IMPLEMENT -> TEST -> REVIEW -> ACCEPT/REJECT -> LEARN.

Observations come from failed agent tasks, retries, failed autonomy runs, and bounded TODO/FIXME scans under the configured project root. Observations are grouped by a deterministic failure signature; the engine persists a candidate instead of inventing work.

## Safety policy

- Remote Git publication is disabled unconditionally for autonomous work.
- A cycle must persist its baseline commit, status, expected files, expected tests, and local checkpoint before implementation.
- Acceptance requires tests to pass, review to accept, acceptance criteria to be met, and no regressions.
- Rejected work creates a candidate lesson and records the assessment. Automatic rollback is disabled by default and requires explicit policy plus an explicit execution request.
- Limits cover changes per run, changed files, retries, runtime, allowed roots, and allowed commands.

## Persistence

Migration 5 adds improvement_candidates and improvement_cycles. Each cycle stores stage, checkpoint, test evidence, review result, regressions, assessment, lesson memory, confidence, and follow-up tasks. The existing experience-memory lifecycle is used for lessons: candidate -> validated -> trusted.

## API

The /v1/self-improvement API exposes observation, candidate listing, cycle start, checkpoint, test evidence, review, interrupt/resume, cycle listing, and limits. The scheduler observes every eligible project and only schedules candidate-driven work when the explicit improvement switch is enabled.

## Recovery

Interrupted cycles can resume from their planned or checkpointed state. Rollback is recorded by default; execution is blocked unless autonomous_rollback_enabled is true and the caller explicitly requests execution. All cycle state is persisted so a supervisor restart does not erase evidence.

## Operational notes

The engine uses bounded scans and bounded serialized evidence. It does not retrain models, push remotes, run arbitrary commands, or bypass existing workspace and approval controls.
