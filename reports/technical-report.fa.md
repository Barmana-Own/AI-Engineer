# گزارش فنی AI-Engineer

| فیلد | مقدار |
|---|---|
| نوع گزارش | تحویل و ممیزی فنی مهندسی |
| زبان | فارسی |
| تاریخ میلادی | 2026-09-18 |
| تاریخ جلالی | 1405-06-27 |
| بازبینی ریویژن | `dc436aa` |
| وضعیت تحویل | هسته سامانه تأیید شده انتشار مشروط |

## دامنه و معماری

این بازبینی فازهای  تا  را بدون افزودن قابلیت بزرگ جدید بررسی کرد. مرزهای Electron Desktop / React Control Center -> FastAPI Orchestrator -> Model Gateway / Local Agent حفظ شدهاند. Provider Router همچنان یک پل اختیاری برای ارائهدهندگان است. Orchestrator از SQLite با نسخه شمای  مهاجرتهای افزایشی قطعی WAL و پایگاهداده جداگانه برای تست استفاده میکند.

## معماری پیادهسازیشده

- ثبت مرکزی  نقش عامل همراه با قراردادها و نامهای سازگاری.
- گراف وظایف پایدار تحت مدیریت Supervisor با وابستگی و وضعیتهای صریح.
- گذرگاه پیام نوعدار و پروتکل handoff پایدار.
- قفل تراکنشی فضایکار و اجرای محدود کارهای فقطخواندنی موازی.
- حافظههای working episodic project lesson و failure با ارتقای مبتنی بر شواهد و حذف داده شبیه credential.
- چرخه خودبهبود مبتنی بر شواهد با checkpoint محلی دروازه تست/بازبینی محدودیتها و بدون push خودکار.
- بازیابی آغاز به کار lease اجرا heartbeat/انقضا رویدادهای recovery و ثبت خطای provider.
- فیکسچر قطعی end-to-end و API مسیر `GET /v1/coordination/runs/{run_id}/trace`.

## همگامسازی مستندات

فایلهای `docs/architecture.md` `docs/roadmap.md` `docs/multi-agent-coordination.md` `docs/engineering-memory.md` `docs/autonomous-backlog.md` `docs/implementation-plan-autonomous-multi-agent.md` و `README.md` اکنون Electron نسخه شمای  رفتار واقعی نقشها/گراف/پیام/حافظه/بازیابی و محدودیتها را بیان میکنند. متن قدیمی Tauri تاریخی علامتگذاری یا حذف شده است. ماژولهای placeholder همچنان صریحا placeholder هستند.

## شواهد اعتبارسنجی

| آزمون یا بررسی | نتیجه |
|---|---|
| تستهای Orchestrator | PASS   تست  مورد skip |
| فیکسچر E2E قطعی | PASS   تست تست مدل واقعی اختیاری skip |
| تست Model Gateway | PASS   تست |
| تست unittest Local Agent | PASS   تست |
| بررسی compile پایتون | PASS برای سه درخت سرویس |
| build کنترلسنتر | PASS (`tsc -b && vite build`) |
| سلامت سرویسها | PASS  پورتهای   و  پاسخ  |
| smoke API هماهنگی/بازیابی | PASS  roles برابر  trace ناموجود  مورد انتظار recovery status برابر  |
| build دسکتاپ | NOT_RUN/BLOCKED  وابستگی `vite` موجود نیست |
| تست Provider Router | NOT_RUN/BLOCKED  وابستگی `vitest` موجود نیست |

## یافتههای بازبینی

- **همزمانی:** یک مسیر batching زمانبندیکننده ممکن است در صورت مشاهده دیرتر writer تعارض reader/writer را از دست بدهد پیش از ادعای همزمانی production باید تحلیل مستقل از ترتیب اضافه شود.
- **اجرای worker:** هماهنگی و persistence Supervisor واقعی است اما فراخوانی نقشها هنوز در حلقه agent/autonomy موجود انجام میشود adapter مستقل worker تحویل نشده است.
- **بحث:** confidence فعلا advisory است و شمارش round بر اساس subject جدا نمیشود.
- **عملیات:** SQLite برای یک پردازش طراحی شده و صف/قفل توزیعشده وجود ندارد.
- **حافظه:** بازیابی lexical/ranked قطعی است و index معنایی/vector وجود ندارد.

## فاز پیشنهادی بعدی

P0: نصب و pin کردن وابستگیهای Desktop و Provider Router و افزودن gate در CI اصلاح ترتیب تحلیل تعارض scheduler پیادهسازی و تست adapter Supervisor به Model Gateway. P1: فیکسچر ارتقای migration metrics/correlation و سیاست بحث محدود بر اساس subject. P2: بازیابی معنایی و templateهای دامنهای پس از پایدار شدن رفتار قطعی.

## درخت منبع

```text
services/orchestrator/app/{db.py,main.py,config.py,agent_service.py,autonomy.py,recovery.py,self_improvement.py}
services/orchestrator/app/coordination/{models.py,roles.py,store.py,scheduler.py,bus.py,context.py,supervisor.py,e2e.py}
services/orchestrator/app/memory/{models.py,store.py,sanitizer.py}
services/model-gateway/app/*
services/local-agent/app/*
services/provider-router/server/*
apps/control-center/*
apps/desktop/*
start-ai-engineer.ps1
```

هیچ secret واقعی به source یا گزارشها افزوده نشده است. push خودکار Git غیرفعال است.

## هسته سازمانی Phase 8A

### معماری سازمانی

لایه سازمانی پایدار بالای Supervisor هماهنگی موجود قرار گرفته است. Company Director
یک هماهنگ‌کننده اجرایی read-only است؛ محدوده را ارزیابی می‌کند، تیم می‌سازد، اعضای
blocked/stalled را پایش می‌کند و گزارش اجرایی می‌دهد. اجرای فنی همچنان به DAG وظایف و
نقش‌های تخصصی فعلی واگذار می‌شود.

### پروفایل کارکنان و دپارتمان‌ها

Migration شماره ۷ جدول‌های agent_profiles و project_team_members را اضافه و
ستون‌های رهبری، دپارتمان، phase، priority و team state را به projects اضافه می‌کند.
پروفایل شامل شناسه پایدار، role، نام نمایشی، دپارتمان، قابلیت، تخصص، ابزار مجاز،
مجوز نوشتن، model profile، وضعیت عملیاتی، پروژه فعال، وظایف جاری، خلاصه تجربه و
timestampها است. دپارتمان‌ها EXECUTIVE، PRODUCT، ENGINEERING، QUALITY، SECURITY،
RESEARCH، OPERATIONS و DOCUMENTATION هستند و امتیاز شخصیت یا هوش ذخیره نمی‌شود.

### مدل نقش و تشکیل تیم پویا

registry نقش موجود حفظ شده و نقش‌های company_director، project_manager،
engineering_manager و operations با aliasهای سازگار اضافه شده‌اند. TeamPlanner
بر اساس شواهد، سیاست کوچک (Engineering Manager، Implementer، Tester، Reviewer)،
متوسط (با Architect، Integration و Documentation) یا بزرگ (Project Manager،
Requirements، Engineering Manager، Architect، Backend، Frontend، Integration،
Tester، Security، Documentation و Release Verifier) را انتخاب می‌کند. ایجاد پروژه
تیم کوچک پیش‌فرض می‌سازد و برنامه‌ریزی صریح امکان تغییر اندازه دارد.

### API و آزمون

endpointهای سازمانی زیر /v1/organization برای دپارتمان، کارکنان، وضعیت، تشکیل تیم،
مشاهده تیم و گزارش اجرایی در دسترس هستند. آزمون‌های Phase 8A با SQLite ایزوله،
ماندگاری و restart پروفایل، Director، دپارتمان، سازگاری نقش، تیم کوچک و بزرگ،
ماندگاری پروژه/تیم، migration idempotence و inference محدود را پوشش می‌دهند. task،
message و memory جدیدی ساخته نشده و primitiveهای قبلی تنها منبع اجرا هستند.

### محدودیت‌ها

Company Director مستقیماً کد اجرا نمی‌کند، adapter مستقل workerها همچنان بدهی مستند
است و SQLite برای یک orchestrator طراحی شده است. کمبود وابستگی‌های JavaScript نیز
شرط انتشار قبلی باقی می‌ماند.

## ?? ?? 埪? ?  ?

|  | 租 |
|---|---|
| ? ?韧? | 2026-09-18 |
| ? ? | 1405-06-27 |
|  | ?? ?? ?? ???  ?  ?? ????? |
| ? | ????  㢠? ? 埪 ? 䟪 묧  |

### ?? ?  埪 ?

?? ??  ? ??? ꥧ?? ???? ?? ??? ?? 묫?? ?? ? ?  ?? ꥧ    ????  ? ???  ? ???. ??? `app/coordination/collaboration.py`  `collaboration_store.py`  ? ? ???. ?? ?? ? `/v1/collaboration`  ?  ? ???   ??? ?? ????   ?颩 ??? ?? ꥧ    ??.

### ?? ??  埪 ?

? `app/coordination/project_management.py` ? ?? Project Manager   ???  ? Project Manager   Engineering Manager  ? ??. ?? ? ?    ????? ???? ?? ???   ?? ? ? ? ??. ?? ??   ?? : 骟 ? ??  ????  ? ?? `tests_passed`  `review_accepted` ? ???? 뢬 ???  ?? `security_review`    ? ???  ? ???  뢬 韪 .

?? ???     ?? .  ?? ? ???  ? ??  ? ? ?  ???  ??? ? ???? ?? ?  ??  ?? ? ? 㟩  ?? ?? 럠 ?럩 ? ??. ?? ?? ??  . `blackboard()` ?? ? ?  ? 㢠   ???? ? ? ???? ??? ??? ?? ? ???? ??  ? 뢬   ????    ?  ?.

### ?? ???

쟤 ? ??? ??? 묫?? ?? ?  婟 ??   ???. 쟤 ? ?? ? ?  ? ???? ?? ???  `agent_work_queue`   ???  租? 媟?? idempotent  ???. ?? ? ???? ?? ???? handoff  ?  ?. 뫦 ?  ? ? ?? ??  뫦 ? ??  ??.

###  㢠?

-  ? Orchestrator: **???  ? ?  skip **.
- ?? ?? ?? 埪 ?: **? **.
- ?? ?? 埪 ?: **? **.
- ?? Model Gateway: **?? **.
- ?? Local Agent: **? **.
- ? ??? : **?? ? ???  ** ?  ?? ??.
- ? ?  import: **??? ?**  **?? ? ??**  **?? ? ?? ??**? ? ?? health 租 `True` .
-  ??: ??? **????? ????  ????** ? HTTP 200 .

### ꥧ?  ??

??  ??? ? ꠢ?  ?    SQLite 쫢?  ?? ? ??? ? 맟????? ? ???  맟. ? ???   ? Supervisor  worker/model  ? ???? JavaScript ?  뢬 . ?? commit ? push ? 뤟 묧. 埪 ? 䟪 묧 .

### 韥  ?? 㢠?

? ?? **??? ? ?**? **?? ? ??**  **?? ? ?? ??**   ?. 㠟 ? ?? ? ?? ?? ?  ? 쩫 ? ?? ? ??  `docs/project-management.md`  .


---

## 埪 ?D - ?? ? ???? ?  ?뢩 ? 뫟?

**? ?韧?:** 2026-09-18  
**? ?:** 1405-06-27  
**:** ????  㢠? ? ?? ? 埪 ?D

### ? 

? ?: services/orchestrator/app/coordination/incidents.py.

? ?   ?? ???  ? detect? contain? diagnose? repair? verify? postmortem? learn  resolved   ???. ??? 㢠  ??  ? 埪 ? idempotent .  ? ??? ?? ?   ? ?   ꥧ  ???.

?   ???? ??   ??. 뢦      ?  埧 ???    ? ???? ???? ?  ?  ?? ???. 뢦 ? ? ??? ??   ? 뤟 ??     ? SQLite ? .

### ?? ?

 postmortems  ???? ?  ??  ? ?? ????? ??? ?????? ?? ?????  럫    ? ??. ?    ?    sanitizer  ?    埧 ???.    ? ? 矠? ? ??.

###  ?

?? ??  project_id ?   ??  ??.       ??  ??? ??? MemoryStore 뤟 ??. ?? ?  ??  ??? ???? ??.

### ???? ?

?? agent_performance   ?  埧 ??. ? 뢦 ???  ? ???? ?? ?  멦 ? / . collaboration_quality ?韢 ?? ??    ??        ꥧ  ???.

### ?뢩 ?

? ?: services/orchestrator/app/coordination/owner_control.py.

租 㟧? ?    ? ? ? ??  ??. 租 start_project? pause_project? resume_project? cancel_project? change_priority? request_report? approve_major_decision? reject_major_decision  request_review ??? ??. ? ???  ? ? 뫟?  ? pending_approval ??. ?? ???  requires_explicit_external_operator   ???  ?? 穟? 뢬? ? ??? 㢠?? ? ?   ???.

?? ?  human_owner  ??  payload ???? ??.  ? 穟 ? ?   HTTP    ? 埪 identity provider ??  묧 .

### 뢪 ? ?? ?

owner_control.py ?韫?? ProjectOpportunity? ClientMessage? ProjectProposal? ClientRequirement  ClientApproval  ? ???.  project_opportunities ? 럫 ? ??? ? 韭? ???  ?  ? ??. ?   adapter     ?  묧 .

### ?? ??? 

Migration 10 媟??  idempotent    incidents? incident_events? incident_team_members? postmortems? collaboration_quality? owner_control_actions  project_opportunities   ?? ?? ꥧ? ??  index?  ??. 뫦 schema  10 .

### ?? API

 ? services/orchestrator/app/routers/incident_control.py  app.main    endpoint? v1 ? ? ?? ??/?   ? ?? ??? ??? 租 ?  婭?  ???. API? ?  묧?.

### 뢟? 

-   埪 ?D: ** - ? **
- unittest ? Orchestrator: ** - ??? ? ?  ??**
- Model Gateway  pytest: ** - ?? **
- Local Agent  unittest: ** - ? **
- compile ??? ???: ****
- import  FastAPI: ** - ??? route?  ? route **
- push/deploy ?  ? ?: **  묧**

### ꥧ??? 럦?

?뢩 HTTP    ? 穟 ?  . ?? SQLite  ???? ?? ??? 쫢. ?? ?  worker ? ?맟? ???. adapter? 婭 ?? 穟 ?? 뢬     ?  ? ? ?.

## ÙØ§Ø² Û¸E â€” Ø§Ø¹ØªØ¨Ø§Ø±Ø³Ù†Ø¬ÛŒ ÛŒÚ©Ù¾Ø§Ø±Ú†Ù‡ Ø´Ø±Ú©Øª Ù†Ø±Ù…â€ŒØ§ÙØ²Ø§Ø±ÛŒ Ù‡ÙˆØ´ Ù…ØµÙ†ÙˆØ¹ÛŒ (2026-09-18 / 1405-06-27)

### Ø¯Ø§Ù…Ù†Ù‡ Ùˆ Ù†ØªÛŒØ¬Ù‡

Ø¯Ø± ÙØ§Ø² Û¸E Ø³Ø§Ù…Ø§Ù†Ù‡Ù” Ø¯ÙˆÙ… Ø¨Ø±Ø§ÛŒ ØªØ³Ú©ØŒ Ù¾ÛŒØ§Ù… ÛŒØ§ Ø­Ø§ÙØ¸Ù‡ Ø³Ø§Ø®ØªÙ‡ Ù†Ø´Ø¯. ØªÙ†Ù‡Ø§ Ø¯ÙØªØ± Ø±ÙˆÛŒØ¯Ø§Ø¯ Ù¾Ø§ÛŒØ¯Ø§Ø± `company_events` Ùˆ Ù„Ø§ÛŒÙ‡Ù” `coordination/company_trace.py` Ø±ÙˆÛŒ Ø³ÛŒØ³ØªÙ…â€ŒÙ‡Ø§ÛŒ Ù…ÙˆØ¬ÙˆØ¯ Ø³Ø§Ø²Ù…Ø§Ù†ØŒ DAG ØªØ³Ú©ØŒ Ù‡Ù…Ú©Ø§Ø±ÛŒØŒ ØªØ­ÙˆÛŒÙ„ Ú©Ø§Ø±ØŒ Ø±Ø®Ø¯Ø§Ø¯ØŒ Ø­Ø§ÙØ¸Ù‡ØŒ Ù…Ø¯ÛŒØ±ÛŒØª Ù¾Ø±ÙˆÚ˜Ù‡ØŒ Ø¨Ø§Ø²ÛŒØ§Ø¨ÛŒ Ùˆ Ø¯Ù…ÙˆÛŒ Ù…Ù‡Ù†Ø¯Ø³ÛŒ Ø§ÙØ²ÙˆØ¯Ù‡ Ø´Ø¯. Ø´Ø¨ÛŒÙ‡â€ŒØ³Ø§Ø²ÛŒ Ù‚Ø·Ø¹ÛŒ Ø´Ø±Ú©Øª Ø¨Ø±Ø§ÛŒ Ù‡Ø¯Ù ÙÙˆÙ„â€ŒØ§Ø³ØªÚ© Ù…ÙˆØ±Ø¯Ù†Ø¸Ø± Ø¨Ø§ Ù…ÙˆÙÙ‚ÛŒØª Ø§Ø¬Ø±Ø§ Ùˆ Ø±Ø¯Ù¾Ø§ÛŒ JSON/Markdown ØªÙˆÙ„ÛŒØ¯ Ø´Ø¯.

### Ø§Ø¹ØªØ¨Ø§Ø±Ø³Ù†Ø¬ÛŒ

- Orchestrator: **Û±Û²Û° Ù…ÙˆÙÙ‚ØŒ Û± Ù…ÙˆØ±Ø¯ Ø±Ø¯Ø´Ø¯Ù‡ Ø¨Ù‡â€ŒØ¯Ù„ÛŒÙ„ Ø§Ø®ØªÛŒØ§Ø±ÛŒ Ø¨ÙˆØ¯Ù† ØªØ³Øª Ù…Ø¯Ù„ ÙˆØ§Ù‚Ø¹ÛŒ**.
- Model Gateway: **Û²Û¶ Ù…ÙˆÙÙ‚**.
- Local Agent: **Û² Ù…ÙˆÙÙ‚**.
- Ú©Ø§Ù…Ù¾Ø§ÛŒÙ„ Ù…Ø§Ú˜ÙˆÙ„â€ŒÙ‡Ø§ÛŒ Ù¾Ø§ÛŒØªÙˆÙ† ØªØºÛŒÛŒØ±Ú©Ø±Ø¯Ù‡ Ù…ÙˆÙÙ‚ Ø¨ÙˆØ¯.
- Ù…Ø³ÛŒØ±Ù‡Ø§ÛŒ Ø±Ø¯Ù¾Ø§ÛŒ Ø´Ø±Ú©Øª Ø«Ø¨Øª Ø´Ø¯Ù†Ø¯: `/v1/company/events`ØŒ `/v1/company/projects/{project_id}/trace` Ùˆ `/v1/company/projects/{project_id}/trace/markdown`.

### Ø´ÙˆØ§Ù‡Ø¯ Ùˆ Ù…Ø­Ø¯ÙˆØ¯ÛŒØªâ€ŒÙ‡Ø§

Ø±Ø¯Ù¾Ø§ Ø´Ø§Ù…Ù„ Ø³Ø§Ø®Øª Ø³Ø§Ø²Ù…Ø§Ù†/ØªÛŒÙ…ØŒ ØªØ®ØµÛŒØµâ€ŒÙ‡Ø§ØŒ DAG ØªØ³Ú©ØŒ Ù¾ÛŒØ§Ù…â€ŒÙ‡Ø§ Ùˆ Ú†Ø§Ù„Ø´/Ø­Ù„ Ø§Ø®ØªÙ„Ø§ÙØŒ ØªØµÙ…ÛŒÙ…â€ŒÙ‡Ø§ØŒ Ø¬Ù„Ø³Ù‡ Ùˆ Ø§Ù‚Ø¯Ø§Ù…ØŒ Ø¯Ø±Ø®ÙˆØ§Ø³Øª/Ù¾Ø§Ø³Ø® Ù‚Ø±Ø§Ø±Ø¯Ø§Ø¯ APIØŒ handoffØŒ Ø±Ø®Ø¯Ø§Ø¯/Ù¾Ø³Ø§Ù…Ø±Ú¯/Ø¯Ø±Ø³â€ŒØ¢Ù…ÙˆØ®ØªÙ‡ØŒ Ø¨Ø§Ø²ÛŒØ§Ø¨ÛŒ Ù¾Ø³ Ø§Ø² restartØŒ Ø´ÙˆØ§Ù‡Ø¯ ØªØ³Øª Ùˆ Ø¨Ø§Ø²Ø¨ÛŒÙ†ÛŒ Ùˆ Ø±ÙˆÛŒØ¯Ø§Ø¯Ù‡Ø§ÛŒ Ø¢Ù…Ø§Ø¯Ù‡â€ŒØ³Ø§Ø²ÛŒ Ø§Ù†ØªØ´Ø§Ø± Ùˆ ØªÚ©Ù…ÛŒÙ„ Ø§Ø³Øª. Ø¯Ø±Ø¬ Ø±ÙˆÛŒØ¯Ø§Ø¯ Ø¨Ø§ Ø´Ù†Ø§Ø³Ù‡Ù” Ø±ÙˆÛŒØ¯Ø§Ø¯ idempotent Ø§Ø³Øª Ùˆ Ù¾Ø±Ø³â€ŒÙˆØ¬ÙˆÙ‡Ø§ Ø¨Ù‡ Ù¾Ø±ÙˆÚ˜Ù‡ Ù…Ø­Ø¯ÙˆØ¯ Ù…ÛŒâ€ŒÙ…Ø§Ù†Ù†Ø¯. Ø´Ø¨ÛŒÙ‡â€ŒØ³Ø§Ø²ÛŒ Ù‚Ø·Ø¹ÛŒ Ø§Ø³Øª Ùˆ Ù…Ù†Ø·Ù‚ ÙˆØ§Ù‚Ø¹ÛŒ persistence Ùˆ orchestration Ø±Ø§ Ø§Ø¬Ø±Ø§ Ù…ÛŒâ€ŒÚ©Ù†Ø¯Ø› Ø§Ø¯Ø¹Ø§ÛŒ ÙØ±Ø§Ø®ÙˆØ§Ù†ÛŒ Ù…Ø¯Ù„ Ø®Ø§Ø±Ø¬ÛŒØŒ push ÛŒØ§ Ø§Ø³ØªÙ‚Ø±Ø§Ø± Production Ù†Ø¯Ø§Ø±Ø¯.

### Ù¾Ø§ÛŒÚ¯Ø§Ù‡ Ø¯Ø§Ø¯Ù‡

Migration 11 Ø¬Ø¯ÙˆÙ„ `company_events` Ø±Ø§ Ø¨Ø§ Ø§Ø±Ø¬Ø§Ø¹ Ù¾Ø±ÙˆÚ˜Ù‡/Ø§Ø¬Ø±Ø§/ØªØ³Ú©ØŒ Ø§Ø·Ù„Ø§Ø¹Ø§Øª actorØŒ payload JSON Ù¾Ø§Ù„Ø§ÛŒØ´â€ŒØ´Ø¯Ù‡ØŒ timestamp Ùˆ Ø§ÛŒÙ†Ø¯Ú©Ø³â€ŒÙ‡Ø§ÛŒ Ù¾Ø±ÙˆÚ˜Ù‡/Ø§Ø¬Ø±Ø§/Ù†ÙˆØ¹ Ø§ÛŒØ¬Ø§Ø¯ Ù…ÛŒâ€ŒÚ©Ù†Ø¯. Ù…Ù‚Ø¯Ø§Ø±Ø¯Ù‡ÛŒ migration Ù‡Ù…Ú†Ù†Ø§Ù† Ø§ÙØ²Ø§ÛŒØ´ÛŒ Ùˆ idempotent Ø§Ø³Øª.


## ØªØ­ÙˆÛŒÙ„ SEO Manager â€” Û²Û°Û²Û¶-Û°Û¹-Û±Û¹ / Û±Û´Û°Ûµ-Û°Û¶-Û²Û¸

Ù†Ù‚Ø´ ÛŒÚ©Ù¾Ø§Ø±Ú†Ù‡ `seo_manager` Ø¨Ù‡â€ŒØ¹Ù†ÙˆØ§Ù† Ù…Ø¯ÛŒØ± ÙÙ‚Ø·â€ŒØ®ÙˆØ§Ù†Ø¯Ù†ÛŒ Ø±ÙˆÛŒ Ø²ÛŒØ±Ø³Ø§Ø®Øª ÙØ¹Ù„ÛŒ Ø´Ø±Ú©Øª AI Ù¾ÛŒØ§Ø¯Ù‡â€ŒØ³Ø§Ø²ÛŒ Ø´Ø¯. Ø§ÛŒÙ† Ù†Ù‚Ø´ Ù¾Ø±ÙˆÙØ§ÛŒÙ„ Ù¾Ø±ÙˆÚ˜Ù‡â€ŒÙ…Ø­ÙˆØ± Ø³Ø§ÛŒØªØŒ audit Ù…Ø¨ØªÙ†ÛŒ Ø¨Ø± evidenceØŒ Ù†Ú¯Ø§Ø´Øª Ú©Ù„Ù…Ù‡ Ø¨Ù‡ ØµÙØ­Ù‡ØŒ taskÙ‡Ø§ÛŒ DAGØŒ handoffØŒ ØªØµÙ…ÛŒÙ…â€ŒÙ‡Ø§ØŒ quality gateØŒ Ø­Ø§ÙØ¸Ù‡ Ù…Ø¹ØªØ¨Ø± Ùˆ Ú¯Ø²Ø§Ø±Ø´ Ø³Ø¦Ùˆ Ø±Ø§ Ø§ÛŒØ¬Ø§Ø¯ Ù…ÛŒâ€ŒÚ©Ù†Ø¯. Ú†Ø§Ø±Ú†ÙˆØ¨ Ø¯ÙˆÙ… Ø¨Ø±Ø§ÛŒ agent/task/memory Ùˆ Ø¬Ø¯ÙˆÙ„ Ø§Ø®ØªØµØ§ØµÛŒ Ø³Ø¦Ùˆ Ø§Ø¶Ø§ÙÙ‡ Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.

Ø§Ø¹ØªØ¨Ø§Ø±Ø³Ù†Ø¬ÛŒ: Û±Û± ØªØ³Øª Ù…ØªÙ…Ø±Ú©Ø² Ø³Ø¦Ùˆ Ù…ÙˆÙÙ‚Ø› Û²Û±Û³ ØªØ³Øª Ø§Ø±Ú©Ø³ØªØ±ÛŒØªÙˆØ± Ø¨Ø§ Û± skip Ù…ÙˆÙÙ‚Ø› Û²Û¶ ØªØ³Øª pytest Ù…Ø¯Ù„â€ŒÚ¯ÛŒØªâ€ŒÙˆÛŒ Ù…ÙˆÙÙ‚Ø› Û² ØªØ³Øª Local Agent Ù…ÙˆÙÙ‚Ø› compile Ùˆ health/role Ø²Ù†Ø¯Ù‡ Ù…ÙˆÙÙ‚. Ù…Ù†Ø¨Ø¹ analyticsØŒ ranking Ùˆ Core Web Vitals Ù…ØªØµÙ„ Ù†ÛŒØ³Øª Ùˆ Ø¯Ø§Ø¯Ù‡ Ø³Ø§Ø®ØªÚ¯ÛŒ ØªÙˆÙ„ÛŒØ¯ Ù†Ù…ÛŒâ€ŒØ´ÙˆØ¯.

## به‌روزرسانی متخصص سئو (2026-09-19 / 1405-06-28)

کارمند فقط‌خواندنی seo_specialist برای تحلیل مستند Technical و On-Page SEO، خوشه‌بندی و نگاشت کلمات کلیدی، شکاف و brief محتوا، پیشنهاد لینک داخلی، handoff پیاده‌سازی، راستی‌آزمایی مستقل و ارتقای حافظه پروژه اضافه شد. ۱۰ آزمون قطعی اضافه شد و کل آزمون‌های Orchestrator با یک آزمون skip‌شده قبلی موفق شد. ادعاهای رتبه، ترافیک، analytics، Search Console، حجم جست‌وجو و Core Web Vitals بدون منبع مجاز در دسترس نیستند.