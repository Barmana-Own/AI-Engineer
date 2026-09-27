# Stage 05 Preflight

Use this checklist before designing or editing persistence.

## 1. Repository discovery

Identify:
- project root and monorepo/package boundaries;
- backend package/service locations;
- existing database/ORM/query-builder packages;
- migration directories and naming conventions;
- `.env.example` or configuration contracts without exposing secrets;
- Docker/Compose/devcontainer database services;
- test database setup and CI database jobs;
- seed/bootstrap scripts;
- existing schema documentation.

Do not infer the active ORM from a dependency alone. Confirm imports/config/usage.

## 2. Stage 04 evidence

Read the Stage 04 architecture document/state plus the actual interfaces it references. Build a table with:
- repository/port name;
- method/operation;
- input/output domain types;
- expected cardinality;
- transaction expectation;
- error semantics;
- tenant/ownership scope;
- source file.

Any Stage 04 port without a persistence implementation plan becomes a gap-register item.

## 3. Business-rule extraction

Search requirements, domain types, services, tests, and Stage 04 docs for words/behaviors that imply data invariants:
- unique, only one, cannot, must, required, immutable;
- active/current/default/primary;
- total/balance/quota/capacity;
- status/state/transition;
- owner/tenant/account/organization;
- expires/valid from/valid until;
- ordered/sequence/version;
- deleted/archived/retained/audited.

Translate each into a concrete enforcement candidate.

## 4. Existing database classification

Classify the project as:
- greenfield/no schema;
- schema exists but not deployed;
- deployed with migrations and compatibility obligations;
- legacy database/database-first integration.

The migration strategy depends on this classification. Never apply greenfield assumptions to a deployed schema.

## 5. Environment safety

Before running database commands, determine the target host/database and environment. Refuse destructive operations against a database that cannot be confidently identified as disposable/local/test.

Use read-only inspection when environment identity is uncertain.

## 6. Preflight output

Record:
- detected stack and versions;
- Stage 04 PASS evidence;
- authoritative input artifacts;
- existing persistence artifacts;
- database classification;
- gap register;
- critical ambiguities/blockers;
- safe assumptions.
