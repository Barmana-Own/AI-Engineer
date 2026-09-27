# Stage 01 Execution Playbook

## Table of Contents

1. Operating principle
2. Phase 0 - Workspace safety and recovery
3. Phase 1 - Source inventory and authority map
4. Phase 2 - Product framing
5. Phase 3 - Scope baseline and release intent
6. Phase 4 - Actor and stakeholder model
7. Phase 5 - Journey and lifecycle analysis
8. Phase 6 - Business rules and invariants
9. Phase 7 - Conceptual domain analysis
10. Phase 8 - Integration and dependency analysis
11. Phase 9 - Functional requirements engineering
12. Phase 10 - Non-functional requirements engineering
13. Phase 11 - Security, privacy, and abuse analysis
14. Phase 12 - Risk, assumptions, decisions, conflicts, and questions
15. Phase 13 - Conditional research
16. Phase 14 - Traceability closure
17. Phase 15 - Adversarial review
18. Phase 16 - Stage 02 handoff engineering
19. Phase 17 - Readiness review and repair loop
20. Phase 18 - State commit and completion
21. Stop conditions and anti-shortcuts

## 1. Operating principle

Execute Stage 01 as a professional discovery and requirements engagement. The goal is not to maximize document size. The goal is to remove ambiguity, expose uncertainty, create testable requirements, and protect downstream stages from rework.

For every phase:
1. inspect the current authoritative inputs;
2. produce or update the phase output;
3. check internal consistency;
4. record assumptions/decisions/risks/questions as needed;
5. do not advance if a critical defect from the current phase is still known and repairable.

## 2. Phase 0 - Workspace safety and recovery

### Objective

Understand what already exists and avoid destroying accepted work.

### Actions

1. Locate the workspace root and `project-state.json`.
2. Inventory Stage 01 files already present.
3. Inspect previous stage records, accepted decisions, assumptions, risks, questions, conflicts, and evidence.
4. Detect whether execution mode is DISCOVERY, SPECIFICATION, RESUME, or REPAIR.
5. Detect partial/inconsistent artifacts before writing anything.
6. When code execution is available, run the bootstrap script only for missing files.
7. Set Stage 01 status to `IN_PROGRESS` unless preserving a valid existing PASS during a read-only inspection.
8. Never overwrite user files or unrelated project files.

### Definition of Done

- execution mode is known;
- existing accepted work is identified;
- canonical Stage 01 artifacts are known;
- no existing artifact has been silently discarded;
- recovery/repair actions are clear.

## 3. Phase 1 - Source inventory and authority map

### Objective

Establish what information exists, how authoritative it is, and where conflicts or gaps exist.

### Actions

1. Enumerate relevant user messages, briefs, files, contracts, specifications, repo docs, diagrams, API docs, screenshots, and prior Stage 01 artifacts.
2. For each source, record:
   - source identifier/path;
   - source type;
   - owner/author when known;
   - authority level;
   - freshness/date when known;
   - scope covered;
   - notable limitations.
3. Build `docs/01-source-map.md`.
4. Extract explicit constraints before making assumptions.
5. Detect contradictions between sources and create CONFLICT-* records.
6. Mark stale or unverified external claims for research rather than treating them as current fact.

### Definition of Done

- every material source is represented in the source map;
- source precedence is explicit;
- contradictions are visible;
- missing authoritative inputs are distinguished from ordinary ambiguity.

## 4. Phase 2 - Product framing

### Objective

Define what the product is, why it exists, and what outcome it must create.

### Actions

1. Write a one-sentence product definition using concrete nouns and verbs.
2. Identify primary problem(s), affected users, and current friction.
3. Identify business/product objective(s).
4. Identify success signals only when supplied or safely framed as proposed measures.
5. Distinguish user goals from system features.
6. Identify the operating context: B2B/B2C/internal, regulated/unregulated, public/private, multi-tenant/single-tenant when supported.
7. Record unknown context as assumptions rather than facts.
8. Reject generic filler such as "modern", "powerful", or "user-friendly" unless converted into measurable implications later.

### Definition of Done

- a new team member can explain the product in one paragraph;
- the problem, users, and intended outcome are distinct;
- unsupported market claims are not presented as facts.

## 5. Phase 3 - Scope baseline and release intent

### Objective

Prevent silent scope expansion and give downstream stages a stable product boundary.

### Actions

1. Classify requested capabilities into:
   - IN SCOPE;
   - OUT OF SCOPE;
   - OPTIONAL/FUTURE.
2. For each major in-scope capability, identify the user/business outcome it supports.
3. Separate MVP/release-critical scope from later enhancements when the source supports release sequencing.
4. Do not infer "standard" features into MUST scope.
5. Record explicit exclusions even when they seem obvious.
6. Identify dependencies that could force scope sequencing.
7. Create DEC-* for material scope decisions.

### Definition of Done

- each MUST capability is inside explicit scope;
- optional ideas are not mixed with required behavior;
- Stage 02 cannot accidentally reintroduce excluded scope.

## 6. Phase 4 - Actor and stakeholder model

### Objective

Identify who interacts with the system, who is affected by it, and whose permissions or responsibilities matter.

### Actions

1. Identify primary end-user actors.
2. Identify operational/admin actors.
3. Identify external/system actors where they initiate or receive behavior.
4. Identify auditors, support, finance, compliance, moderators, managers, or representatives only when relevant.
5. For each ROLE-* record:
   - name;
   - responsibility;
   - goals;
   - core actions;
   - data visibility/action intent;
   - interactions with other roles;
   - source/confidence.
6. Detect role collisions such as requester/approver conflict or admin/self-approval concerns.
7. Distinguish "role" from organizational job title when the system permission boundary differs.

### Definition of Done

- every major journey has an initiating actor or SYSTEM;
- no material role is known but absent;
- permission intent is explicit enough for Stage 02 information architecture.

## 7. Phase 5 - Journey and lifecycle analysis

### Objective

Model what actually happens end to end, including non-happy paths.

### Actions

For each JRN-* capture:
- trigger;
- initiating actor;
- prerequisites;
- normal path;
- alternate path(s);
- exception/failure path(s);
- resulting state/outcome;
- notifications or handoffs when relevant;
- related roles, rules, modules, integrations, and assumptions.

Review relevant lifecycle dimensions:
- create/draft/submit;
- validate/reject/request changes;
- approve/assign/process;
- cancel/expire/archive;
- retry/recover;
- refund/reverse when financial;
- reopen/escalate when workflow-based;
- delete/export/retain when privacy/data lifecycle matters.

Do not force all lifecycle dimensions into every product. Apply only those that are materially relevant.

### Definition of Done

- primary happy paths are modeled;
- material exception paths are modeled;
- important state transitions are understood conceptually;
- orphan actors and orphan journeys are identified and repaired.

## 8. Phase 6 - Business rules and invariants

### Objective

Convert policy and domain logic into enforceable statements.

### Actions

1. Extract eligibility, validation, calculation, sequencing, approval, ownership, timing, limit, uniqueness, and state-transition rules.
2. Write each BR-* as one clear rule.
3. Separate policy rules from implementation mechanisms.
4. Identify precedence when multiple rules can apply.
5. Identify rule exceptions explicitly.
6. Link rules to the journeys and requirements they constrain.
7. Record uncertain business policy as Q-* plus reversible ASM-* rather than inventing it.

### Definition of Done

- material process behavior is not hidden only in prose;
- contradictory rules are represented as CONFLICT-*;
- each rule is traceable to affected behavior.

## 9. Phase 7 - Conceptual domain analysis

### Objective

Establish a shared business vocabulary and lifecycle ownership without prematurely designing a database.

### Actions

1. Identify DOM-* business domains or entity groups.
2. For each domain, capture:
   - definition;
   - business owner/actor relationship;
   - lifecycle summary;
   - sensitive-data classification when relevant;
   - relationships to other domains in conceptual terms;
   - authoritative source/system when external.
3. Create `docs/01-domain-integration-map.md`.
4. Detect ambiguous terminology and normalize canonical names.
5. Record aliases from source material when useful.
6. Do not define table names, column types, indexes, migrations, or physical schemas.

### Definition of Done

- core nouns have one canonical meaning;
- downstream architecture can reason about domain boundaries without guessing;
- physical data design has not leaked into Stage 01.

## 10. Phase 8 - Integration and dependency analysis

### Objective

Identify external systems and operational dependencies early enough to affect requirements.

### Actions

For each INT-* capture:
- external party/system;
- business purpose;
- direction: inbound/outbound/bidirectional;
- trigger or interaction pattern;
- data exchanged at conceptual level;
- classification: CONFIRMED/ASSUMED/OPTIONAL;
- authentication/authorization dependency when known;
- availability and failure implications;
- retry/idempotency/synchronization concerns when applicable;
- version/vendor/jurisdiction constraints when applicable;
- evidence or assumption links.

Consider relevant dependency classes:
- identity/SSO;
- payment;
- email/SMS/push;
- storage/files;
- maps/geolocation;
- government/regulatory API;
- ERP/CRM/accounting;
- AI/model provider;
- analytics;
- webhooks/partner APIs;
- device/hardware.

### Definition of Done

- every confirmed integration affects at least one FR/NFR/constraint;
- assumed integrations are labeled;
- failure behavior is not ignored when business-critical.

## 11. Phase 9 - Functional requirements engineering

### Objective

Produce a testable behavioral contract.

### Derivation method

Derive FRs from:
1. actor goals;
2. journey steps and exception paths;
3. business rules;
4. domain lifecycles;
5. integration behaviors;
6. security/privacy behavior that is functionally observable;
7. explicit user/client constraints.

### Requirement writing rules

Each FR must:
- express one primary behavior;
- name the actor or SYSTEM;
- use MUST/SHOULD/COULD intentionally;
- be implementation-neutral unless an implementation constraint is explicit;
- contain observable acceptance criteria;
- reference at least a journey or module;
- reference relevant BR/INT/ASM/EVD IDs;
- state source and confidence.

Split a requirement when it contains independent behaviors that could pass/fail separately.

Avoid vague terms unless quantified or defined:
- fast;
- secure;
- intuitive;
- seamless;
- flexible;
- robust;
- easy;
- real-time (unless latency expectations are stated or explicitly assumed).

### Acceptance criteria review

Acceptance criteria must describe externally verifiable outcomes. Include relevant:
- success condition;
- validation failure;
- unauthorized/forbidden behavior;
- duplicate/retry behavior;
- state transition;
- notification/handoff;
- integration failure behavior.

Do not mechanically add all categories to every FR.

### Definition of Done

- each material journey step maps to requirements;
- each FR is atomic and testable;
- no critical behavior exists only in narrative prose;
- no MUST requirement is unsupported by source, decision, or explicit assumption.

## 12. Phase 10 - Non-functional requirements engineering

### Objective

Define relevant quality constraints in measurable terms.

### Actions

1. Review all quality attributes in the quality catalog.
2. Mark each attribute as APPLICABLE, NOT_APPLICABLE, or DEFERRED with rationale in the readiness review when material.
3. Write NFRs only for applicable attributes.
4. Give each NFR:
   - category;
   - priority;
   - measurable target or validation target;
   - verification method;
   - related scope;
   - source/confidence;
   - assumption/evidence links.
5. Avoid fabricated numeric targets.
6. Where a number is needed for downstream design but not supplied, create ASM-* and make it easy to change.

### Definition of Done

- relevant quality attributes were consciously considered;
- every NFR is verifiable;
- inferred targets are visibly assumptions.

## 13. Phase 11 - Security, privacy, and abuse analysis

### Objective

Expose material product-level security/privacy risks before design begins.

### Actions

Review relevant questions:
- What identities exist and how trusted are they?
- What actions are privileged or irreversible?
- What data is confidential, personal, financial, legal, health-related, location-related, credential-like, or otherwise sensitive?
- What cross-role visibility would be harmful?
- What workflows are vulnerable to fraud, impersonation, replay, duplicate submission, privilege abuse, or approval conflicts?
- What events require audit history?
- What data lifecycle or deletion/export questions exist?
- What third parties receive sensitive data?
- What abuse/rate-limit concerns exist at product level?

Translate material findings into FR/NFR/RSK/Q records. Do not prescribe detailed cryptographic, network, IAM, or infrastructure implementation unless already fixed by an authoritative constraint.

### Definition of Done

- high-impact trust boundaries are identified;
- sensitive data classes are visible;
- material abuse cases have a requirement, risk, or question;
- later security stages are not forced to rediscover obvious product risks.

## 14. Phase 12 - Risk, assumptions, decisions, conflicts, and questions

### Objective

Make uncertainty explicit and manageable.

### Actions

1. Create/update `docs/01-risk-register.md`.
2. Record ASM-* for inferred facts that affect behavior or quality.
3. Record DEC-* for material choices that downstream stages must preserve.
4. Record RSK-* with category, likelihood, impact, mitigation, owner/stage, trigger, and affected IDs when known.
5. Record Q-* for unresolved questions.
6. Mark each question blocking true/false.
7. For a non-blocking question, link a temporary assumption when behavior depends on the answer.
8. Record CONFLICT-* when sources disagree; include the competing positions and resolution/status.
9. Do not use a risk register as a dumping ground for trivial observations.

### Definition of Done

- no material uncertainty is hidden;
- every blocking question is genuinely blocking;
- high-impact risks have mitigation direction and ownership.

## 15. Phase 13 - Conditional research

### Objective

Resolve external facts that materially affect the product contract.

### Research triggers

Research when requirements depend on current:
- law/regulation;
- official API/vendor behavior;
- platform/browser/device constraints;
- standards;
- authentication/payment/provider rules;
- framework/runtime capabilities when the user has fixed a technology and the fact affects scope;
- externally maintained compatibility constraints.

Do not research merely to make the document look comprehensive.

### Actions

1. Form a narrow research question.
2. Prefer primary/official sources.
3. Record EVD-* using the evidence contract.
4. Link evidence to affected IDs.
5. Separate source claim from analyst interpretation.
6. Revisit requirements changed by the evidence.
7. Record a DEC-* when evidence changes a material prior assumption.

### Definition of Done

- researched facts have evidence records;
- stale or low-authority evidence is not treated as confirmed high-confidence truth;
- research changes are traceable.

## 16. Phase 14 - Traceability closure

### Objective

Prove that the product definition is internally connected rather than a collection of unrelated lists.

### Actions

Create/update `docs/01-traceability-matrix.md` with at least:
- Actor -> Journey;
- Journey -> FR;
- BR -> FR;
- Module -> FR/NFR;
- Integration -> FR/NFR;
- Assumption -> affected IDs;
- Risk -> affected IDs;
- Evidence -> affected IDs;
- Requirement -> source/confidence.

Check for:
- orphan roles;
- orphan journeys;
- rules with no enforcing behavior;
- confirmed integrations with no requirements;
- requirements pointing to unknown IDs;
- assumptions that affect behavior but are unreferenced;
- research-derived claims without evidence.

### Definition of Done

- all MUST FRs are traceable;
- all major journeys have coverage;
- all confirmed integrations have coverage;
- no dangling IDs remain.

## 17. Phase 15 - Adversarial review

### Objective

Find defects the authoring passes missed.

### Review lenses

Perform an independent challenge for:
1. missing actor;
2. missing journey/exception path;
3. inconsistent terminology;
4. over-scoping;
5. under-specification;
6. ambiguous acceptance criteria;
7. unsupported MUST requirements;
8. missing permissions intent;
9. missing lifecycle states;
10. missing integration failure behavior;
11. missing security/privacy concern;
12. fabricated NFR target;
13. conflicting rule;
14. dangling traceability;
15. Stage-boundary leakage.

Record findings in the readiness review as `FINDING-*` with severity CRITICAL/HIGH/MEDIUM/LOW and status OPEN/RESOLVED.

Repair all CRITICAL/HIGH findings before PASS. Repair MEDIUM findings when they affect Stage 02 readiness; otherwise explicitly defer with rationale and owner.

### Definition of Done

- zero open CRITICAL/HIGH findings;
- no known repairable Stage 01 defect is being ignored;
- deferred findings have explicit rationale and owner.

## 18. Phase 16 - Stage 02 handoff engineering

### Objective

Translate Stage 01 into a compact, directive prompt for the design stage.

### Actions

1. Reference canonical artifacts rather than duplicating them.
2. Summarize product definition and scope guardrails.
3. List high-confidence/immutable decisions.
4. Map roles to journeys needing UI coverage.
5. State permission intent that affects information architecture.
6. State localization/accessibility/device constraints.
7. List design-affecting FR/NFR/BR/INT IDs.
8. List non-blocking questions Stage 02 must keep reversible.
9. State exactly what Stage 02 should do.
10. State exactly what Stage 02 must not change.

### Definition of Done

- handoff is actionable without re-reading the whole conversation;
- it does not redefine product scope;
- it does not create wireframes, design systems, or screen layouts itself.

## 19. Phase 17 - Readiness review and repair loop

### Objective

Make PASS a quality decision, not a formatting decision.

### Actions

1. Complete `docs/01-readiness-review.md` using the quality rubric.
2. Run machine validation when code execution is available.
3. Review semantic gates manually.
4. If any gate fails, identify root cause and repair the canonical artifact.
5. Rerun traceability and validation after every material repair.
6. Repeat until:
   - structural validator passes;
   - quality score meets threshold;
   - zero open CRITICAL/HIGH findings;
   - zero blocking questions;
   - Stage 02 handoff is ready.

Do not lower the quality score or suppress findings just to obtain PASS.

## 20. Phase 18 - State commit and completion

### Objective

Commit a trustworthy Stage 01 state.

### Actions

1. Ensure `project-state.json` reflects current decisions, assumptions, risks, questions, conflicts, and evidence.
2. Run normal validation.
3. Commit state to PASS only after semantic readiness is confirmed.
4. Run strict-pass validation after the commit.
5. If strict-pass fails, revert to IN_PROGRESS, repair, and rerun.
6. Add all required Stage 01 artifacts to the state artifact list.
7. Emit completion markers only after strict validation succeeds.

## 21. Stop conditions and anti-shortcuts

Never:
- mark PASS because files merely exist;
- copy the user brief into requirements without analysis;
- make all features MUST;
- ask the user about every small ambiguity;
- hide assumptions in narrative text;
- invent legal/compliance/vendor facts;
- invent SLA/RTO/RPO/retention/throughput targets as confirmed facts;
- skip exception paths for convenience;
- treat a validator score as a substitute for semantic review;
- let Stage 01 design UI, database schemas, APIs, infrastructure, or production code;
- silently discard an accepted decision;
- silently change stable IDs;
- leave known CRITICAL/HIGH findings open and still pass.
