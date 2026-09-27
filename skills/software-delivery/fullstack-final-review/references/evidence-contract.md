# Evidence Contract

Final review claims must be backed by reproducible evidence.

## Evidence classes

1. **Execution evidence** — command actually executed with argv, cwd, exit status and output log.
2. **Source evidence** — specific file/path/symbol/config inspected in the current workspace.
3. **Runtime evidence** — HTTP/API/UI/health/database behavior observed in a running environment.
4. **Artifact evidence** — generated build, migration output, archive, manifest or report verified to exist.
5. **External evidence** — authoritative current documentation needed to interpret framework/API/security behavior.
6. **Decision evidence** — approved scope exclusions, risk acceptance, or external authorization from the user/project artifacts.

## Evidence quality rules

- Prefer direct execution/runtime evidence over narrative claims.
- Preserve exact command and working directory for command checks.
- Capture both stdout and stderr.
- Store exit code; zero alone is not enough if output indicates skipped/no tests where tests were expected.
- A test command that executes zero relevant tests is not evidence of behavior coverage unless zero tests are intentionally expected and documented.
- Do not cite generated documentation as proof of runtime behavior unless it is itself the thing being verified.
- Do not reuse evidence from another branch, commit, build artifact, database schema, or materially changed source state without revalidation.

## Freshness and invalidation

Evidence becomes stale when a change can affect the property it proved.

Minimum invalidation examples:
- source change → affected lint/typecheck/unit/integration/build evidence stale;
- API contract change → API/client/contract/E2E/docs evidence stale;
- auth change → auth/security/integration/E2E evidence stale;
- schema/migration change → migration/integration/E2E/runtime/docs evidence stale;
- dependency change → audit/build/test/runtime evidence stale;
- deployment config change → build/runtime/health/ops/docs evidence stale.

A stale check returns to `PENDING` or is recorded as invalidated. It cannot contribute to final PASS until re-run.

## Command evidence schema

`run_check.py` records entries similar to:

```json
{
  "id": "lint-root",
  "category": "static-quality",
  "status": "PASS",
  "command": ["npm", "run", "lint"],
  "cwd": "/workspace/project",
  "exit_code": 0,
  "duration_seconds": 4.28,
  "log_path": ".final-review/logs/lint-root.log",
  "log_sha256": "...",
  "reason": null
}
```

## Manual evidence

When no deterministic script can collect evidence, record:
- what was inspected;
- exact path/symbol/endpoint;
- result;
- why the inspection proves the gate property;
- any uncertainty.

Do not write vague evidence such as "code looks good".

## `NOT_RUN` evidence

Every `NOT_RUN` must contain:
- check attempted/planned;
- exact blocker;
- whether the blocker is local, external, credential-related, legal/business approval, or unavailable service;
- whether a substitute check was performed;
- release impact;
- owner for resolution when known.

## Evidence retention

Keep detailed command logs under `.final-review/logs/` during review. Do not include them in the release archive by default because logs can contain local paths, test data, tokens or service output. Summarize only safe evidence in `docs/12-final-review.md` and `release-manifest.json`.
