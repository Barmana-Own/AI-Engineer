# Performance and Reliability Smoke QA

## Table of contents

1. Scope
2. Baseline philosophy
3. Frontend performance smoke
4. API performance smoke
5. Database and query symptoms
6. Queue/job reliability
7. Retry and timeout behavior
8. Resource and lifecycle symptoms
9. Resilience scenarios
10. Non-goals
11. Exit criteria

## 1. Scope

Stage 10 performs release-oriented performance and reliability smoke testing. It should discover obvious regressions and unsafe failure behavior before deployment preparation. It does not replace a formal capacity, soak, stress, or load test unless the project explicitly includes those tests and the required environment exists.

## 2. Baseline philosophy

Prefer comparison with:

- project performance budgets;
- prior release evidence;
- existing CI/performance tests;
- documented SLA/SLO targets;
- architecture-specific expectations.

If no numeric baseline exists, report observations and obvious pathological behavior without inventing performance guarantees.

## 3. Frontend performance smoke

For critical pages inspect as tools permit:

- initial load completes without endless spinners;
- route transitions complete without repeated network storms;
- large bundles/assets are not accidentally multiplied;
- image/video behavior does not block essential interaction;
- infinite lists or tables do not render unbounded data when pagination/virtualization is expected;
- repeated renders do not create obvious UI freezes;
- polling intervals are bounded and stop when no longer needed;
- failed requests do not trigger infinite retry loops;
- skeleton/loading state transitions correctly to success/error.

Do not claim Core Web Vitals values unless actually measured.

## 4. API performance smoke

For high-traffic or critical endpoints look for:

- obvious multi-second delays in ordinary local/staging conditions;
- repeated duplicate calls for one user action;
- N+1-like request/query patterns where observable;
- unbounded list endpoints;
- expensive search without sensible limits;
- synchronous execution of obviously long background work when architecture expects jobs;
- timeouts shorter than normal operation or retries longer than user flow permits.

Quantify only when measurements are actually collected.

## 5. Database and query symptoms

Inspect critical flows for evidence of:

- unbounded scans caused by missing pagination/filters;
- repeated per-row queries;
- locks/deadlocks during ordinary concurrency;
- missing indexes only when query evidence supports the concern;
- large transactions holding resources excessively;
- connection leaks/pool exhaustion symptoms;
- slow queries exposed in logs/profilers where available.

Do not prescribe schema/index changes from intuition alone.

## 6. Queue/job reliability

For workers/jobs verify:

- jobs complete in expected test conditions;
- failure is observable;
- retry is bounded;
- retries are idempotent for irreversible side effects;
- permanently failing jobs do not create an infinite hot loop;
- duplicate delivery is safe;
- worker restart does not silently lose critical work if persistence semantics require durability.

## 7. Retry and timeout behavior

Review critical integration/client paths for:

- explicit timeout or platform-default behavior;
- bounded retry count;
- backoff/jitter when relevant;
- no retry of unsafe non-idempotent mutation unless protected;
- cancellation/cleanup after user navigation where important;
- clear UI behavior after terminal failure.

Retry logic must not amplify an outage into a request storm.

## 8. Resource and lifecycle symptoms

Where practical inspect for:

- runaway CPU;
- obvious memory growth during repeated critical flow;
- file/stream handles not closing;
- background timers continuing after component/page teardown;
- repeated event subscriptions;
- temporary files not cleaned up;
- browser console/server logs flooded continuously.

Only report resource leaks as confirmed when repeated evidence supports them.

## 9. Resilience scenarios

For critical dependencies, safely test or simulate:

- slow downstream response;
- downstream 5xx;
- connection refusal;
- timeout;
- queue unavailable;
- cache unavailable if system is expected to degrade;
- transient database failure only in disposable environments;
- user retry after ambiguous result.

Verify the system avoids false success and maintains safe state.

## 10. Non-goals

Do not:

- perform denial-of-service testing;
- run uncontrolled load against public/production systems;
- invent throughput/concurrency certification;
- infer production latency from a developer laptop;
- block release on arbitrary performance preferences when no user/business impact exists.

## 11. Exit criteria

Before PASS:

- no known P0/P1 reliability defect remains;
- no obvious retry storm/infinite polling/duplicate mutation behavior remains in critical paths;
- critical background work has safe failure/retry semantics to the extent executable;
- serious performance regressions that break core use are fixed;
- unmeasured production capacity is clearly left to the appropriate deployment/performance stage rather than claimed as proven.
