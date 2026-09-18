# گزارش وضعیت پروژه و نقشهراه / Project Status and Roadmap

| فیلد / Field | مقدار / Value |
|---|---|
| پروژه / Project | AI-Engineer |
| تاریخ جلالی / Jalali date | 1405-06-27 |
| تاریخ میلادی / Gregorian date | 2026-09-18 |
| ریویژن مشاهدهشده / Revision | `8130980` |
| وضعیت تحویل / Delivery | هسته مهندسی آماده انتشار Production مشروط |

## بخش فارسی

### . خلاصه وضعیت فعلی پروژه

هسته Orchestrator هماهنگی چندعاملی حافظه مهندسی خودبهبود کنترلشده و بازیابی پس از restart پیادهسازی و با تستهای قطعی بررسی شدهاند. معماری فعلی Electron Desktop و React Control Center را به FastAPI Orchestrator و سرویسهای جداگانه Model Gateway و Local Agent متصل میکند.

### . مواردی که واقعا پیادهسازی شدهاند

- نسخه  شمای SQLite با migrationهای افزایشی و deterministic.
- registry پانزده نقش Supervisor و گراف وظایف وابسته با وضعیتهای پایدار.
- پیامهای نوعدار handoff قفل فضایکار و trace قابل بازرسی.
- حافظههای working episodic project lesson و failure با lifecycle مبتنی بر شواهد و redaction.
- چرخه self-improvement از observe تا learn با checkpoint محلی و بدون push خودکار.
- lease heartbeat recovery event و ثبت خطاهای provider.
- تست E2E قطعی health سرویسها و build موفق Control Center.
- کشف قابلحمل ریشه پروژه با `AI_ENGINE_PROJECT_ROOT`/`PROJECT_ROOT`.

### . کارهای باقیمانده

**MUST-FIX پیش از انتشار:** نصب و pin وابستگیهای Desktop و Provider Router اصلاح تشخیص تعارض reader/writer مستقل از ترتیب adapter تستشده برای dispatch نقشها از Supervisor به Model Gateway.

**بهبودهای بعدی:** fixture ارتقای migrationهای قدیمی metrics/correlation بحث subject-scoped semantic retrieval و templateهای دامنهای.

### . موارد ناقص مسدود FAIL یا NOT_RUN

- Desktop build: **NOT_RUN/BLOCKED** چون `vite` در dependencyهای نصبشده موجود نیست.
- Provider Router tests: **NOT_RUN/BLOCKED** چون `vitest` موجود نیست.
- استقرار Production واقعی: **NOT_PERFORMED** اعتبار یا هدف استقرار ارائه نشده است.
- SQLite چندپردازشی worker مستقل برای هر نقش و vector memory: **NOT_READY**.

### . مشکلات یا ریسکهای فعلی پروژه

تعارض بالقوه reader/writer در یک مسیر scheduler به ترتیب iteration وابسته است. SQLite و recovery برای یک process طراحی شدهاند. confidence بحث فعلا advisory است و specialist workerها هنوز adapter مستقل ندارند. این موارد در گزارش فنی ثبت شدهاند.

### . پیشنهادهای مفید برای ادامه توسعه پروژه

. ابتدا gateهای build/test جاوااسکریپت و scheduler را سبز کنید. . سپس adapter نقشها و trace correlation را اضافه کنید. . بعد migration upgrade و تست چندفرآیندی را تثبیت کنید. . تنها پس از این شواهد semantic retrieval و templateهای جدید را بررسی کنید.

### . قابلیتها یا بهبودهای ارزشمند برای این نوع کسبوکار

- مسیر end-to-end قابلردیابی برای هر تغییر کد.
- evidence و review اجباری برای self-improvement.
- recovery امن پس از قطع مدل/worker/ماشین.
- metrics هزینه زمان retry و نرخ پذیرش review.
- catalog پروژه و conventions قابلبازیابی برای کوتاهکردن زمان تحویل.

### . اولویت پیشنهادی اقدامات بعدی

- **P0:** وابستگیهای build تعارض scheduler adapter واقعی Supervisor/Model Gateway.
- **P1:** migration fixtures observability policy بحث و تست چندپردازشی.
- **P2:** semantic memory و task templateهای تخصصی.

### . وضعیت آمادگی برای Production

**مشروط / Core-engine ready.** هسته محلی و APIهای اصلی آماده بررسی عملیاتی هستند اما به علت gateهای JavaScript اجرا نشده محدودیت single-process و بدهی worker مستقل release عمومی Production هنوز تأیید نمیشود.

### . جمعبندی مدیریتی کوتاه

سامانه از چند سرویس و چند prompt پراکنده به یک هسته قابلردیابی و قابلبازیابی برای مهندسی خودکار ارتقا یافته است. مسیر بعدی باید روی اثبات عملیاتی و حذف سه مانع P0 متمرکز باشد نه افزودن نقشهای نمایشی جدید.

## English section

### 1. Current Project Status

The Orchestrator core, multi-agent coordination, engineering memory, controlled self-improvement and restart recovery are implemented and covered by deterministic tests. The current architecture connects Electron Desktop and React Control Center to a FastAPI Orchestrator with separate Model Gateway and Local Agent services.

### 2. Implemented Items

- SQLite schema version 6 with deterministic additive migrations.
- Fifteen-role registry, Supervisor and dependency-aware persisted task graph.
- Typed messages, handoffs, workspace locks and inspectable run trace.
- Working, episodic, project, lesson and failure memories with evidence lifecycle and redaction.
- Self-improvement from observe through learn with local checkpoint and no automatic push.
- Leases, heartbeats, recovery events and provider-failure records.
- Deterministic E2E tests, service health checks and successful Control Center build.
- Portable root discovery through `AI_ENGINE_PROJECT_ROOT`/`PROJECT_ROOT`.

### 3. Remaining Work

**MUST-FIX before release:** install and pin Desktop/Provider Router dependencies; make reader/writer conflict detection order-independent; deliver a tested Supervisor-to-Model-Gateway role dispatch adapter.

**Later improvements:** migration-upgrade fixtures, metrics/correlation, subject-scoped discussion, semantic retrieval and domain templates.

### 4. Incomplete, Blocked, FAIL, or NOT_RUN Items

- Desktop build: **NOT_RUN/BLOCKED** because `vite` is absent from installed dependencies.
- Provider Router tests: **NOT_RUN/BLOCKED** because `vitest` is absent.
- Real production deployment: **NOT_PERFORMED**; no authorized deployment target was supplied.
- Multi-process SQLite, independent role workers and vector memory: **NOT_READY**.

### 5. Current Risks / Problems

One scheduler batching path depends on iteration order for reader/writer conflict detection. SQLite and recovery are single-process oriented. Discussion confidence is advisory and specialist workers do not yet have an independent dispatch adapter. These are documented in the technical review.

### 6. Recommended Next Improvements

First close the JavaScript build/test and scheduler gates. Next add role dispatch and trace correlation. Then stabilize migration upgrades and multi-process tests. Only after that evaluate semantic retrieval and new domain templates.

### 7. Valuable Product / Engineering Enhancements

- Traceable end-to-end evidence for every code change.
- Mandatory evidence and review gates for self-improvement.
- Safe recovery after model, worker or machine interruption.
- Cost, duration, retry and review-acceptance metrics.
- Reusable project conventions to reduce delivery time.

### 8. Recommended Priority Order

- **P0:** build dependencies, scheduler conflict safety, real Supervisor/Model Gateway adapter.
- **P1:** migration fixtures, observability, discussion policy and multi-process tests.
- **P2:** semantic memory and specialized task templates.

### 9. Production Readiness

**Conditional / Core-engine ready.** The local core and primary APIs are ready for operational review, but public production release is not approved until the unrun JavaScript gates, single-process constraint and independent worker debt are addressed.

### 10. Short Management Summary

The system has progressed from isolated prompts to a traceable, durable and recoverable autonomous-engineering core. The next phase should prove operations and remove the three P0 blockers rather than add more nominal roles.
