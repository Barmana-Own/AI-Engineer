# SELF-IMPROVEMENT PIPELINE

> Gregorian date: 2026-09-18
> Jalali date: 1405-06-27


## SAFETY GATES
The controlled lifecycle is OBSERVE -> DIAGNOSE -> PROPOSE -> PLAN -> SANDBOX/CHECKPOINT -> IMPLEMENT -> TEST -> REVIEW -> ACCEPT or REJECT -> LEARN. Remote push is hard-disabled; acceptance requires tests, review, acceptance criteria, and no regressions. Runtime, retry, file, change, root, and command limits are enforced.

## ROLLBACK DESIGN
Every cycle stores baseline commit/status and a local checkpoint reference. Interrupted work is resumable. Rollback is explicit and disabled by default; no destructive reset occurs without policy and an explicit execution request.

## SCHEDULER
The scheduler performs bounded evidence collection for failed tasks, retries, failed runs, and TODO/FIXME hotspots. It persists and prioritizes candidates; candidate-driven scheduling is opt-in through autonomous_improvement_enabled.

## DATABASE CHANGES
Migration 5 adds improvement_candidates and improvement_cycles, with indexed status/priority/signatures and links to projects, runs, and trusted experience lessons.

## TEST RESULTS
The deterministic self-improvement test suite covers observation/prioritization, repeated-cycle avoidance, checkpoint creation, rejection, acceptance and lesson promotion, interruption/resume, limits, and no-remote-push safety.

## EXAMPLE IMPROVEMENT RUN
A failed SQLite task is observed, grouped into a candidate, checkpointed locally, validated with before/after tests, reviewed, accepted only when all gates pass, and promoted into trusted engineering memory. A failing review is persisted as rejected with a reusable lesson.

## KNOWN LIMITATIONS
The scheduler does not execute arbitrary shell commands on behalf of an improvement candidate; implementation and verification continue through the existing agent/task policy. Automatic rollback remains opt-in and external CI/deployment systems are not invoked.
