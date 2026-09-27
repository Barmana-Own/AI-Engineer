# Data and Migration Review

## Safety classification first

Before any migration/setup action identify the target database/service.

Allowed by default:
- local disposable DB;
- test container/ephemeral DB;
- isolated staging only when project/user policy allows.

Not allowed without explicit authorization:
- production reset/drop/truncate;
- destructive migration rehearsal against production data;
- seed scripts that overwrite live records;
- schema experiments on a production-adjacent shared DB.

## Static migration review

Identify canonical mechanism and inspect:
- migration ordering/IDs;
- duplicate IDs/names;
- missing dependencies;
- up/down semantics if used;
- destructive operations;
- non-null additions without default/backfill strategy;
- unique constraints that can fail on existing data;
- type changes/truncation risk;
- foreign-key behavior;
- index creation on large tables where deployment impact matters;
- raw SQL safety;
- schema/model drift;
- migration code that depends on mutable application runtime behavior.

## Fresh setup verification

For a stateful project, prefer executable proof:
1. create empty isolated DB/schema;
2. apply all migrations from zero using documented command;
3. apply required deterministic seed/bootstrap if needed;
4. start application or run repository validation against resulting schema;
5. execute representative create/read/update flow;
6. capture command/runtime evidence;
7. tear down only the resources created for the test.

## Upgrade-path verification

When release risk warrants and a prior release schema is available:
1. restore or create a safe representative prior schema/data fixture;
2. apply current migration chain;
3. verify constraints/data transformations;
4. run smoke/integration tests;
5. compare expected critical counts/invariants where meaningful.

Do not fabricate prior production data.

## Data integrity checks

Verify important business invariants through DB constraints and/or transactional domain logic:
- uniqueness;
- ownership/tenant keys;
- referential integrity;
- required statuses/transitions;
- money/quantity precision;
- timestamps/timezones;
- soft-delete semantics;
- idempotency keys where used.

## Seed/bootstrap review

Ensure production does not silently create:
- default admin credentials;
- predictable privileged users;
- demo/test accounts;
- destructive sample data.

Development seeds should be clearly environment-scoped.

## Migration blockers

Block release when:
- fresh migration fails;
- application expects columns/tables not created by migration;
- migration can predictably corrupt required data with no safe procedure;
- critical uniqueness/ownership invariant is unenforced and causes a core/security defect;
- production startup requires undocumented manual schema edits;
- default seed creates insecure privileged access.
