# Final Review Gate Matrix

All gates start as `PENDING`. A gate becomes `PASS`, `FAIL`, or `NOT_RUN`. `STALE` is an internal transient state after a repair and must be resolved before final validation.

| Gate | Domain | Required evidence | Blocking rule | `NOT_RUN` policy |
|---|---|---|---|---|
| G00 | Stage 11 precondition | current Stage 11 PASS proof + state consistency | Any unresolved Stage 11 failure/conflict blocks | Not allowed |
| G01 | Repository integrity | source-tree review + release-relevant markers/findings | Broken/missing runtime modules, unresolved conflicts, production mock/bypass block | Not allowed when source is available |
| G02 | Requirement traceability | traceability map for every core requirement | Missing/broken core requirement blocks | Not allowed |
| G03 | Architecture/topology coherence | implemented component/runtime map | Contradictory topology that breaks build/runtime/security blocks | Only if architecture artifacts unavailable but runtime still fully discoverable; document impact |
| G04 | Frontend critical journeys | route/screen/client-call review + runnable smoke/E2E when available | Unusable or incorrectly wired core journey blocks | Runtime smoke may be NOT_RUN only if environment unavailable; static integration review remains required |
| G05 | Backend/business rules | module/validation/error/business-rule review + tests | Missing core server-side rule or broken handler blocks | Static review not waivable; runtime may be NOT_RUN with reason |
| G06 | API contract/integration | representative request/response/spec/client comparison | Contract drift breaking critical clients blocks | Not allowed for static contract review |
| G07 | Data model/migrations | migration/schema/model consistency | Broken schema path, destructive unsafe default, missing critical constraint blocks | Not allowed for static review |
| G08 | Authentication/authorization | negative-path code/runtime evidence | Auth bypass, privilege escalation, tenant/ownership failure blocks | Runtime negative tests may be NOT_RUN only with strong static evidence; High uncertainty blocks production-ready verdict |
| G09 | Security review | security checklist + finding ledger | Open Critical/High or P0/P1 security issue blocks | Essential security review not waivable |
| G10 | Dependencies/supply chain | lockfiles + available audit results + risky dependency review | Known exploitable Critical/High in reachable release path blocks unless mitigated and documented | Tool-based audit may be NOT_RUN if unavailable; manifest/lock review remains required |
| G11 | Static quality | repo-defined lint/typecheck/compile/format checks | Failed required check blocks | Required repo-defined checks cannot be silently waived; missing executable may produce NOT_RUN and block when CI requires it |
| G12 | Automated tests | unit/integration/contract/E2E/security regression results as applicable | Any required suite failure blocks; test bypass used to pass blocks | A non-applicable tier may be marked N/A in notes, but applicable essential suite NOT_RUN can block |
| G13 | Clean setup/migrations | isolated fresh setup/migration evidence | Persistence project with unproven/broken fresh setup blocks production-ready verdict | Essential for stateful production release; NOT_RUN blocks unless product has no persistence |
| G14 | Production build | real production build/package result | Failed production build blocks | Not allowed when build is technically executable |
| G15 | Runtime/health/smoke | production-mode start/container + health/smoke where supported | Cannot start or critical smoke fails blocks | May be NOT_RUN only for unavailable external infra; record release impact |
| G16 | Operations/observability | deployment, rollback, health, logging/metrics/runbook review | Missing core startup/deploy/rollback path for intended production model blocks | Static ops review not waivable |
| G17 | Documentation | README/runbook commands verified against repo | Missing/stale core setup/build/migrate/deploy docs blocks handoff | Not allowed |
| G18 | Release hygiene | hygiene scan + manual disposition | Real secret/private production data/bypass in release blocks | Not allowed |
| G19 | Manifest/package integrity | final manifest + archive inventory when packaging requested | Manifest contradicts evidence or archive includes forbidden content blocks | Package may be N/A only if no archive capability/request; manifest remains required |

## Gate evidence minimums

### G01 Repository integrity
Must inspect at least:
- conflict markers;
- TODO/FIXME/HACK with release relevance;
- mock/dev/test adapters reachable from production configuration;
- duplicate entrypoints/abandoned implementations that can be invoked;
- missing imports/modules/config references;
- debug flags and accidental generated junk.

### G02 Requirement traceability
For every `core=true` requirement:
- approved source identifier;
- at least one implementation location unless explicitly excluded;
- verification/test evidence appropriate to risk;
- status not `UNKNOWN`, `MISSING`, or `BROKEN`.

### G04/G05/G06 Integration
At least one representative critical journey must be followed end to end through:
UI/consumer → client request → API/router/controller → auth/validation/business logic → persistence/integration → response/state update.

### G08/G09 Security
Negative-path verification should prioritize:
- unauthenticated access;
- wrong role;
- wrong tenant/object owner;
- expired/revoked session/token;
- tampered identifiers/input;
- privileged mutation;
- upload/download authorization;
- bypass/debug flags.

### G11/G12/G14 Command gates
Evidence must include:
- exact command/argv;
- working directory;
- exit code;
- captured output/log path;
- timestamp if reliable;
- status and reason when `NOT_RUN`.

### G13 Clean setup
For persistence projects, evidence should demonstrate a new empty schema can reach the expected current schema without manual undocumented edits.

### G18 Hygiene
A regex hit alone is a candidate finding, not always a true vulnerability. However, a verified real secret or private production dataset is blocking until removed/rotated as appropriate.

## Essential `NOT_RUN` decision rule

When a required check cannot execute:

1. Determine whether the gate is marked essential above.
2. Record the exact missing prerequisite (tool, service, credential, contract, environment).
3. Determine whether a lower-risk static substitute materially proves the same property.
4. If not, leave the gate `NOT_RUN` and block production-ready PASS.
5. Never downgrade a required check merely because fixing the environment is inconvenient.

## Dependency between gates

Repairs can invalidate multiple gates. Examples:
- changing auth middleware invalidates G05, G06, G08, G09, G12, G15;
- changing DB schema/migration invalidates G05, G06, G07, G12, G13, G15, G17;
- changing frontend API client invalidates G04, G06, G12, G14, G15;
- changing dependencies invalidates G10, G11, G12, G14, and security/runtime gates affected by the package;
- changing environment/container config invalidates G14, G15, G16, G17, G18.
