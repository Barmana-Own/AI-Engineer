# Data Lifecycle, Audit, Retention, and Privacy

## Separate concerns

Do not treat these as interchangeable:
- `created_at`/`updated_at`: operational timestamps;
- soft delete: application visibility/lifecycle state;
- audit history: evidence of changes/actions;
- archive: lower-frequency retained data;
- retention: how long data may/must remain;
- anonymization: removing link to a person/entity;
- legal hold: suspension of normal deletion.

## Deletion decision

For each important data class decide:
- who may request deletion;
- whether dependent rows may be deleted;
- whether records are evidence/accounting/legal records;
- whether anonymization is preferable to deletion;
- what foreign-key behavior preserves consistency;
- how uniqueness behaves for soft-deleted rows.

## Soft delete

Use soft delete only when business recovery/history/visibility requires it. If used:
- define default query scope;
- define admin/audit visibility;
- define restore behavior;
- test uniqueness with deleted rows;
- prevent accidental joins to deleted parents where inappropriate.

## Audit

If actor-level traceability is required, define:
- actor identity/service identity;
- action/event type;
- target entity and identifier;
- before/after or changed fields where appropriate;
- timestamp;
- correlation/request identifier;
- immutability/tamper expectations.

Avoid placing secrets or unnecessary sensitive values in audit payloads.

## Sensitive data

Minimize stored sensitive data. Identify fields requiring encryption/tokenization/masking according to project requirements. Keep credentials/secrets out of database fixtures and application logs.

## Retention source

Never invent a legal retention period. If Stage 01-04 or authoritative policy specifies one, implement it. Otherwise record the unresolved retention source and choose only a reversible technical structure unless the missing decision is blocking.
