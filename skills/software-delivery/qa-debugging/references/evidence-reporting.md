# Evidence and Reporting Standard

## Table of contents

1. Evidence principles
2. Evidence hierarchy
3. Command evidence
4. Browser/UI evidence
5. API/data evidence
6. Defect evidence
7. Unavailable evidence
8. QA report structure
9. Known issues structure
10. Matrix consistency
11. Final summary language
12. Anti-patterns

## 1. Evidence principles

Stage 10 must be auditable. Another engineer should be able to understand what was tested, what failed, what changed, and why PASS/BLOCKED was declared.

Never convert assumptions into facts in the final report.

## 2. Evidence hierarchy

Prefer direct executed evidence in this order where appropriate:

1. reproducible end-to-end behavior;
2. automated integration/E2E result;
3. API request/response plus persisted state;
4. focused automated unit/service result;
5. logs/traces supporting the executed scenario;
6. code inspection supporting, but not replacing, runtime proof;
7. authoritative requirement/specification for expected behavior.

Different claims require different evidence. A code review cannot prove a browser layout works.

## 3. Command evidence

Record:

- exact command;
- working directory/package when ambiguous;
- outcome;
- key counts or summary;
- relevant failure identifiers;
- whether run before or after fixes.

Example:

```text
Command: npm run test:integration
Scope: apps/api
Result: PASS
Summary: 84 passed, 0 failed
Phase: final regression
```

Do not paste thousands of log lines into the report. Preserve concise evidence and point to log files when the project stores them.

## 4. Browser/UI evidence

For manual/browser execution record:

- route/screen;
- role;
- starting state;
- viewport class;
- action;
- expected;
- observed;
- result;
- defect ID if failed.

Use screenshots only when available and useful; text evidence is still required so the report remains understandable without the image.

## 5. API/data evidence

For important mutations record enough to demonstrate:

- request/action;
- response/status;
- resulting canonical state;
- relevant side effect;
- denial behavior for protected operations.

Redact secrets/tokens. Do not put real credentials in QA documents.

## 6. Defect evidence

Every P0/P1 defect must have:

- deterministic or well-characterized reproduction;
- impact rationale;
- root-cause evidence;
- fix evidence;
- regression evidence;
- closure status.

P2/P3 may use lighter evidence, but still need enough context for a future engineer to reproduce or understand them.

## 7. Unavailable evidence

Use explicit language:

- `NOT RUN - browser execution unavailable`
- `BLOCKED - payment sandbox credential unavailable`
- `PARTIALLY VERIFIED - local webhook contract exercised; provider delivery not executed`

Do not write `PASS` for an unexecuted surface.

## 8. QA report structure

Use `assets/10-qa-report.template.md`.

Required sections:

1. Executive status
2. Release candidate identity
3. Environment and constraints
4. Source artifacts used
5. Risk and coverage strategy
6. Automated baseline
7. QA matrix summary
8. Core journey results
9. Functional/exploratory results
10. Authorization/security regression
11. API/data integrity
12. UI/responsive/RTL/accessibility
13. Performance/reliability smoke
14. Defect log
15. Fix/regression summary
16. Flaky/pre-existing/external issues
17. Final suite verification
18. Open known issues
19. Quality gate
20. Stage 11 handoff

## 9. Known issues structure

`docs/10-known-issues.md` must list every unresolved issue intentionally carried forward.

For each issue record:

- ID;
- severity;
- affected area;
- user/business impact;
- workaround if safe;
- why it does not block Stage 11;
- recommended owner/action;
- evidence/reference.

If there are no known issues, say explicitly that no intentionally unresolved issues remain as of the tested release candidate. Do not omit the file.

## 10. Matrix consistency

Before closure cross-check:

- every FAIL row links to a defect;
- every fixed defect has updated PASS/regression evidence;
- every BLOCKED critical row appears in blockers;
- every known issue appears in the report;
- P0/P1 open count is zero for PASS;
- report command results match actual execution.

## 11. Final summary language

Use precise statements:

Good:

- "The three release-critical applicant submission scenarios passed in the local Docker environment."
- "Live payment-provider callback was not executed because sandbox credentials were unavailable; local signature and failure handling were verified."
- "QA10-004 was fixed in the authorization guard and reverified for owner/non-owner/admin roles."

Avoid:

- "Everything looks good."
- "Production ready" when deployment/production behavior has not been tested.
- "Security passed" when only a limited regression check ran.
- "No bugs" when the claim means "no bugs found in executed coverage."

## 12. Anti-patterns

Never:

- fabricate pass counts;
- hide failed first attempts;
- omit high-severity defects because they were fixed;
- mark an unavailable integration as passed;
- copy raw secrets into evidence;
- use screenshots without describing tested state;
- replace reproducible steps with vague prose;
- declare PASS before report/matrix/project state agree.
