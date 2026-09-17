# گزارش فنی ممیزی AI-Engineer

| فیلد | مقدار |
|---|---|
| پروژه | AI-Engineer |
| نوع گزارش | تحویل فنی مهندسی |
| زبان | فارسی |
| تاریخ هجری شمسی | 1405-06-27 |
| تاریخ میلادی | 2026-09-18 |
| snapshot مخزن | شاخه main؛ در ممیزی commit بازیابی fd80c52 و یک commit محلی جلوتر از origin مشاهده شد |
| دامنه ممیزی | درخت منبع، تست‌ها، snapshot SQLite، اسکریپت‌های deployment و probe سرویس‌های محلی |

## دامنه و شواهد

این سند نتیجه ممیزی source-first از checkout فعلی است. خود ممیزی تغییر عمده‌ای در source برنامه ایجاد نکرد؛ برنامه پیاده‌سازی و گزارش‌های دوزبانه ممیزی ایجاد/به‌روزرسانی شدند. در زمان ممیزی supervisor در حال اجرا یک commit بازیابی ایجاد کرد که فقط README.md را تغییر داد؛ این commit برگردانده نشد.

## معماری فعلی

مرز تأییدشده فعلی:

UI/Desktop  Orchestrator  Local Agent (workspace، فایل، Git، terminal و process)
   Model Gateway (مسیریابی provider/model)

Orchestrator زمان‌بندی task، اجرای خودکار، نقش‌ها، memory، ذخیره handoff و routeهای health/developer را مدیریت می‌کند. Local Agent عملیات محافظت‌شده ماشین را ارائه می‌دهد. Model Gateway جلوی adapterهای provider و readiness check قرار دارد. React Control Center endpointهای تایپ‌شده Orchestrator را مصرف می‌کند. پیاده‌سازی Desktop در source، Electron است؛ درحالی‌که بخش‌هایی از مستندات هنوز معماری آینده Tauri/Rust را توصیف می‌کنند.

## workflow فعلی agentها

چرخه فعلی یک هدف را از backlog ثابت 14‌تایی انتخاب می‌کند، goal و فرمان validation محدود می‌سازد و فازهای specialist را اجرا می‌کند. specialistهای read-only در batchهای موازی محدود اجرا می‌شوند و roleهای نویسنده جدا و سریالی هستند. پس از موفقیت validation، mutation می‌تواند checkpoint شود. handoffها به‌صورت رکورد ساختاریافته ذخیره و memoryها از نتایج terminal فشرده می‌شوند. scheduler پنج‌دقیقه‌ای run فعال را رد و کار stale را reconcile می‌کند.

این چرخه برای automation محدود مفید است، اما workflow سطح پروژه برای Supervisor نیست: intake پایدار پروژه، baseline نیازمندی، DAG وابستگی‌محور، lease کار، دروازه پذیرش و تصمیم نهایی release وجود ندارد.

## نقش‌ها و قراردادهای موجود

registry شامل inspector، planner، implementer، verifier، reviewer، monitor/Supervisor Manager، requirements، architect، orchestrator، gateway، local-agent، UI، desktop، tests، security، docs، debugger و integration است و aliasهای scout/local-agent/test-verifier/manager را دارد. metadata نقش‌ها read-only یا writer/validation را مشخص می‌کند. قرارداد فعلی عمدتاً prompt و metadata handoff است و semantics اجباری inbox، سؤال، challenge، revision یا decision سازمانی ندارد.

## مدل persistence

SQLite با WAL، foreign key و busy timeout فعال است. جدول‌های فعلی projects، agent_tasks، agent_memories، autonomy_runs و subagent_handoffs هستند و indexهای status/project دارند. نتیجه task، فرمان validation، مسیرهای تغییرکرده، جزئیات محدود terminal، memory و handoff ذخیره می‌شود. primitiveهای مفقود شامل جدول message/event، dependency task، lease/lock، decision پایدار، evidence پذیرش و state قابل resume است.

snapshot فعلی شامل 1 پروژه، 1,110 task، 1,110 memory، 498 autonomy run و 1,110 handoff بود. نتیجه runها 335 تکمیل و 163 ناموفق؛ handoffها 947 تکمیل، 157 ناموفق و 6 در حال اجرا بودند. بازه داده مشاهده‌شده 2026-09-15T08:35:40Z تا 2026-09-17T20:57:43Z بود.

## بدهی فنی و ریسک اصلی

- agent_service.py با 3,270 خط policy ابزار، ایمنی mutation، action مدل، اجرا، recovery و orchestration را مخلوط کرده است.
- autonomy.py با 944 خط backlog، scheduling، retry، reconciliation و checkpoint push را در خود دارد.
- Orchestrator middleware احراز هویت یا مدل authorization ندارد.
- CORS برای originهای loopback تمام method/headerها را مجاز می‌کند و extraهای schema task پذیرفته می‌شوند.
- deployment مقدار AUTONOMOUS_AUTO_PUSH=true دارد و مسیر push به origin main commit/push می‌کند.
- electron/main.cjs مسیر F:\AI-Engineer را hard-code کرده است.
- درخت وابستگی Provider Router و Desktop در checkout موجود نیست و بررسی runnable آن‌ها کامل نمی‌شود.
- مستندات و گزارش‌های تاریخی ادعاهای قدیمی درباره stage/status و Tauri دارند.
- رکورد خطاها شامل timeoutهای 360 ثانیه‌ای، اتمام max-step، reconciliation پس از restart و actionهای نامعتبر model-tool است.

## شکاف ارتباطی

handoff فعلی summary ساختاریافته‌ای با evidence، changed files، validation، blocker، confidence و previous handoff ID است. entity پیام/inbox، سؤال خطاب‌شده، challenge/rebuttal، تصمیم Supervisor، درخواست revision، acknowledgement یا event stream پایدار وجود ندارد. فازهای موازی محدودند، اما جلوگیری از تداخل writer عمدتاً با جداسازی فاز انجام می‌شود، نه lease در سطح task.

## baseline تست و probe سرویس

| بررسی | نتیجه |
|---|---|
| unittest Orchestrator | PASS  62 |
| unittest Local Agent | PASS  2 |
| pytest Model Gateway | PASS  26 |
| compileall پایتون | PASS  هر سه سرویس |
| npm build کنترل‌سنتر | PASS |
| npm build Desktop | NOT_RUN/مسدود  Vite/dependencies موجود نیست |
| npm test Provider Router | NOT_RUN/مسدود  Vitest/dependencies موجود نیست |
| health/capabilities در 8012 | PASS |
| health در 8011 | PASS |
| health/readiness در 8010 | PASS |
| Provider Router در 8020 | NOT_RUN  اتصال رد شد |
| lint/type/security audit کامل و browser E2E | NOT_RUN |

گزارش‌های تاریخی با تعداد تست یا موفقیت Desktop متفاوت، به‌عنوان شواهد فعلی استفاده نشدند.

## معماری هدف پیشنهادی

مرز سرویس‌های فعلی حفظ می‌شود و قابلیت‌های ماژولار به Orchestrator افزوده می‌گردد:

1. intake پروژه و baseline نیازمندی.
2. control plane Supervisor با role assignment، policy، decision log و acceptance gate.
3. task DAG پایدار با dependency، priority، retry، lease و checkpoint قابل resume.
4. subsystem پیام/event برای assignment، question، challenge، evidence، revision، acknowledgement و تصمیم Supervisor.
5. adapter اجرای specialist که همچنان از public interfaceهای Local Agent و Model Gateway استفاده کند.
6. pipeline integration/review/release با evidence اجباری تست، امنیت، مستندات و verification.
7. API احراز هویت‌شده و مجاز با observability عملیاتی.
8. سیاست امن Git با commit محلی checkpoint به‌صورت پیش‌فرض و مجوز صریح برای push release.

## فازهای پیشنهادی اجرا

| فاز | خروجی اصلی |
|---|---|
| 0 | baseline، integrity manifest و flagهای ایمنی؛ خاموش‌کردن auto-push پیش‌فرض |
| 1 | تفکیک agent service به policy/tool/execution/recovery بدون تغییر قرارداد |
| 2 | DAG پایدار task، dependency، lease، idempotency و resume |
| 3 | mailbox بین agentها، سؤال/challenge، evidence، revision و تصمیم Supervisor |
| 4 | intake پروژه، تخصیص role، زمان‌بندی و acceptance gate توسط Supervisor |
| 5 | authentication، authorization، audit event و regression امنیتی |
| 6 | observability در frontend/desktop و حذف path hard-coded و drift پیکربندی |
| 7 | integration، release verification، hardening deployment، مستندات و QA کامل |

فهرست دقیق فایل‌های پیشنهادی در docs/implementation-plan-autonomous-multi-agent.md ثبت شده و شامل افزودنی‌های متمرکز در services/orchestrator/app (workflow، messaging، supervisor، policy، lease، acceptance و auth)، تغییر schema/migration، استخراج agent_service، پیکربندی deployment و تست‌هاست.

## ارزیابی validation و release

سرویس‌های اصلی Python و build کنترل‌سنتر قابل‌تأیید هستند. بررسی Desktop و Provider Router به‌علت نبود dependency مسدود است؛ lint، security audit کامل و browser E2E اجرا نشدند. دروازه release production تا زمان پیاده‌سازی و اعتبارسنجی authentication/authorization، سیاست auto-push، معیار تکمیل workflow، نصب dependency و primitiveهای ارتباطی Supervisor قابل عبور نیست.