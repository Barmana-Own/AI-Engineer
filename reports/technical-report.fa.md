# گزارش فنی — وضعیت و مسیر تکمیل AI Engineer

| فیلد | مقدار |
|---|---|
| پروژه | AI Engineer |
| نوع گزارش | گزارش فنی |
| زبان | فارسی |
| تاریخ شمسی | ۱۴۰۵/۰۷/۰۱ |
| تاریخ میلادی | ۲۳ سپتامبر ۲۰۲۶ |
| revision مخزن در زمان گزارش | `1e3839e` (working tree تغییرات commit نشده دارد) |
| وضعیت تحویل | قابل اجرای محلی، اما هنوز نسخهٔ نهایی و Production نیست |

**یادداشت محتوای تاریخی:** بخش‌های پیش از الحاقیه فعلی موتور سئو، گزارش‌ها و شمارش تست فازهای قبلی را حفظ می‌کنند. الحاقیه زیر وضعیت معتبر این تاریخ گزارش است.

## دامنه و مبنای بررسی

این گزارش بر اساس بررسی مستقیم سرور در ۱۶ سپتامبر ۲۰۲۶، اجرای سرویس‌ها، اجرای تست‌های موجود و بررسی تاریخچهٔ Git تهیه شده است. snapshot محلی قبلی در ۳۰ اوت جداگانه در همین گزارش حفظ شده است. در سرور، نسبت به commit قبل از بازهٔ ۲۴ساعته (`57c9b67`)، ۶۳ فایل با ۲۵۹۵ خط افزوده و ۲۸۷ خط حذف‌شده مشاهده شد. در مخزن `project-state.json` و `project-integrity-manifest.md` وجود ندارد؛ بنابراین وضعیت‌های رسمی دوازده‌مرحله‌ای هنوز به‌صورت قابل ردیابی ثبت نشده‌اند.

## شواهد مستقیم سرور Windows در ۲۴ ساعت اخیر

مسیر پیدا‌شده روی سرور `C:\\Services\\AI-Engineer\\current` است. زمان snapshot سرور ۱۵ سپتامبر ۲۰۲۶، ساعت ۲۳:۲۱:۱۵ با offset `-07:00` بود. task با نام `AI Engineer Server` پیدا شد، در وضعیت `Ready` بود، با حساب `aieng` اجرا می‌شود و آخرین نتیجهٔ ثبت‌شدهٔ آن `0` است؛ trigger آن startup است و NextRun خالی است.

در Git، ۱۷ commit در ۲۴ ساعت ثبت شده است (۱۶ recovery checkpoint و یک merge از `origin/main`). endpoint autonomy تعداد ۱۰۰ run اخیر را برگرداند: ۴۱ `completed`، ۵۸ `failed` و یک `running`، روی ۱۴ کلید backlog. قدیمی‌ترین run این snapshot در `2026-09-15T16:41:42Z` و جدیدترین در `2026-09-16T06:16:08Z` بود. آخرین وضعیت اکثر کلیدها failed است؛ فقط `control-center-observability`، `gateway-routing` و `local-agent-policy` آخرین وضعیت completed داشتند و `security-boundary` هنگام snapshot running بود.

پورت‌های ۸۰۱۰، ۸۰۱۱، ۸۰۱۲ و ۱۱۴۳۴ (Ollama) در وضعیت LISTEN بودند؛ ۸۰۲۰ (Provider Router) و ۵۱۷۵ (Control Center runtime) DOWN بودند. logهای Model Gateway تا حدود ۲۳:۲۰:۵۴ درخواست‌های `chat/completions` با پاسخ ۲۰۰ و logهای Local Agent درخواست‌های `POST /git/checkpoint` با پاسخ ۲۰۰ ثبت کرده‌اند. هیچ mutation، restart یا حذف فایلی در این بررسی انجام نشد.

## معماری موجود

| لایه | مؤلفه | وضعیت مشاهده‌شده |
|---|---|---|
| ارکستراسیون | `services/orchestrator` | API پروژه، task، memory و autonomy؛ workspace guard و checkpoint/backup دارد |
| عامل محلی | `services/local-agent` | اجرای عامل محلی و endpoint سلامت؛ compile موفق |
| درگاه مدل | `services/model-gateway` | درگاه مدل با provider پیکربندی‌شده؛ تست‌ها موفق |
| مسیریاب provider | `services/provider-router` | سرویس Node/SQLite و unified provider API؛ بخشی از تست‌های سخت‌سازی و فشرده‌سازی شکست دارد |
| رابط کنترل | `apps/control-center` | build تولیدی با Vite موفق؛ runtime عمداً راه‌اندازی نشده است |
| اپ دسکتاپ | `apps/desktop` | build تولیدی با Vite موفق |
| مدل محلی | Ollama | endpoint `/api/tags` پاسخ ۲۰۰ دارد و مدل محلی موجود است |

## تغییرات واقعی مشاهده‌شده

- چرخهٔ autonomy دارای backlog چرخشی ۱۴ کلید است و planner، implementer، verifier، checkpoint/push policy و single-writer barrier دارد.
- workspace guard مسیرهای مطلق و خروج از ریشهٔ workspace را رد می‌کند؛ نام مستعار `ai-engineer` برای خود مخزن تعریف شده است.
- عامل سرویس ابزارهای مجاز، ابزارهای approval، سقف ۳۰ گام و retry برای فراخوانی مدل دارد.
- کنترل‌های مربوط به محدودسازی طول آرگومان فرایندها، هم‌ترازی نسخهٔ health، پوشش recovery و قراردادهای نقش/نیازمندی در تاریخچهٔ اخیر دیده شد.
- مدارک قدیمی پیشرفت، هستهٔ local-first را فعال می‌دانند؛ همان مدارک تصریح می‌کنند که parity کامل با Codex و چرخهٔ عمومی پروژه هنوز تکمیل نشده است.

## شواهد اجرای autonomy — snapshot محلی ۳۰ اوت

در زمان بررسی، endpoint `/v1/agent/autonomy/runs?limit=100` تعداد ۱۰۰ اجرای اخیر را برگرداند: ۹۴ مورد `completed`، شش مورد `failed`، صفر مورد active و ۱۴ کلید backlog یکتا. آخرین بازهٔ مشاهده‌شده از ۲۶ تا ۳۰ اوت بود. آخرین وضعیت هر کلید نشان می‌دهد `control-center-observability`، `desktop-health`، `gateway-routing`، `local-agent-policy`، `memory-safety`، `operations-docs`، `role-contracts`، `supervisor-resume`، `task-observability` و `test-coverage` آخرین اجرای موفق داشتند؛ آخرین اجرای `integration-health`، `recovery-coverage`، `requirements-contract` و `security-boundary` ناموفق بود.

علت ثبت‌شدهٔ شکست‌های autonomy، ناتوانی مدل در تولید tool call معتبر پس از دو تلاش است (`Unsupported Agent tool: .`). این مورد شکست پروتکل اجرای مدل است و نباید به‌عنوان قبولی validation کد گزارش شود.

## ماتریس اعتبارسنجی اجراشده

| بررسی | فرمان/شاهد | نتیجه |
|---|---|---|
| تست ارکستریتور | `services/orchestrator/.venv/Scripts/python.exe -m unittest discover -s tests -q` | PASS — ۴۸ تست، ۱۶٫۶۳۷ ثانیه |
| تست Model Gateway | `services/model-gateway/.venv/Scripts/python.exe -m pytest -q` | PASS — خروجی pytest موفق؛ فقط warning وابستگی |
| compile عامل محلی | `services/local-agent/.venv/Scripts/python.exe -m compileall -q app` | PASS |
| build Control Center | `apps/control-center npm run build` | PASS — Vite 7.3.6 |
| build Desktop | `apps/desktop npm run build` | PASS — Vite 8.2.0 |
| تست Provider Router | `services/provider-router npm test` | FAIL — ۱۶۸/۱۷۰ فایل تست و ۱۷۵۰/۱۷۵۴ تست موفق؛ ۴ شکست |
| health مدل gateway | `GET http://127.0.0.1:8010/health` | PASS — HTTP 200 |
| health عامل محلی | `GET http://127.0.0.1:8011/health` | PASS — HTTP 200 |
| health ارکستریتور | `GET http://127.0.0.1:8012/health` | PASS — HTTP 200 |
| قابلیت‌های ارکستریتور | `GET http://127.0.0.1:8012/capabilities` | PASS — supervisor فعال، interval یک دقیقه، workspace guarded |
| سرویس Provider Router | `GET http://127.0.0.1:8020` | PASS — HTTP 200 |
| Ollama | `GET http://127.0.0.1:11434/api/tags` | PASS — HTTP 200 |
| runtime رابط کنترل | پورت `5175` | NOT_RUN — طبق دستور عدم تمرکز/بازکردن UI اجرا نشد |

چهار شکست Provider Router دو دسته‌اند: دو assertion مربوط به mode فایل DB/WAL روی Windows که مقدار مورد انتظار صفر و مقدار دریافتی ۵۴ بود، و دو تست کارایی فشرده‌سازی که p50 برابر ۱۸٫۴۴۳ms در برابر سقف ۸ms و payload adversarial برابر ۶۲۲٫۸۶ms در برابر سقف ۲۵۰ms اندازه‌گیری شد.

## وضعیت رسمی دوازده مرحله

این جدول وضعیت gate رسمی را نشان می‌دهد، نه صرفاً وجود بخشی از کد:

| مرحله | وضعیت رسمی | توضیح کوتاه |
|---:|---|---|
| ۰۱ تحلیل و نیازمندی | NOT_RUN | artifact و `project-state.json` رسمی موجود نیست |
| ۰۲ طراحی سیستم و UI | NOT_RUN | مستندات کامل gate موجود نیست |
| ۰۳ معماری frontend | NOT_RUN | build موجود است، اما gate مرحله‌ای ثبت نشده |
| ۰۴ معماری backend | NOT_RUN | کد backend موجود است، artifact مرحله‌ای ثبت نشده |
| ۰۵ معماری database | NOT_RUN | persistence موجود است، gate مستقل ثبت نشده |
| ۰۶ API و integration | NOT_RUN | endpointها موجودند، contract gate کامل ثبت نشده |
| ۰۷ احراز هویت و مجوز | NOT_RUN | کنترل‌های موجود به معنای تکمیل gate نیستند |
| ۰۸ امنیت کاربرد | NOT_RUN | گزارش امنیت رسمی و gate مستقل موجود نیست |
| ۰۹ تست نرم‌افزار | NOT_RUN | بخشی از تست‌ها اجرا شده، اما ماتریس رسمی کامل نیست |
| ۱۰ QA و debugging | NOT_RUN | بررسی محصول‌محور کامل اجرا نشده |
| ۱۱ deployment و production | NOT_RUN | deployment واقعی انجام نشده و runbook کامل gate نشده |
| ۱۲ final review | NOT_RUN | بازبینی مستقل نهایی اجرا نشده |

## ریسک‌ها و blockerهای فعلی

1. چهار failure در تست Provider Router مانع اعلام سبز بودن کامل تست‌هاست.
2. چهار کلید autonomy آخرین اجرای ناموفق دارند و خطای tool-call مدل می‌تواند چرخهٔ خودکار را متوقف کند.
3. launcher اسکریپتی Provider Router در حالت نبودن process با دسترسی به `Count` روی مقدار null شکست می‌خورد؛ سرویس برای این بررسی با Node مستقیم بالا نگه داشته شد.
4. autonomy backlog چرخه‌ای است و شرط پایان نهایی ندارد؛ صرفاً روشن‌ماندن supervisor به‌تنهایی پروژه را به محصول نهایی تبدیل نمی‌کند.
5. Control Center runtime و سناریوهای end-to-end مرورگر در این بررسی اجرا نشدند.
6. فرایندهای فعلی محلی‌اند و تضمین ۲۴/۷ برای restart، watchdog، CI/CD، backup/restore و observability تولیدی هنوز اثبات نشده است.
7. نبود `project-state.json` و integrity baseline، ردیابی gateها و تشخیص regression را ناقص می‌کند.

## مسیر باقی‌مانده تا تکمیل نهایی

مسیر تکمیل «محصول قابل استفاده برای دریافت پروژهٔ دلخواه و تحویل نتیجهٔ تست‌شده» به این ترتیب است:

1. **P0 — تثبیت اجرا:** رفع failureهای Provider Router، اصلاح launcher، و رفع خطای invalid tool call یا افزودن fallback/abort شفاف برای آن.
2. **P0 — intake واقعی پروژه:** تعریف ورودی پروژهٔ خارجی، تشخیص stack و محیط، ایجاد workspace ایزوله، snapshot/backup و policy مجوز.
3. **P0 — چرخهٔ کامل تحویل:** plan → patch → targeted test → full test → debug/retry → approval در موارد پرریسک → گزارش و rollback.
4. **P1 — validation و resilience:** جمع‌آوری نتیجهٔ همهٔ سرویس‌ها، resume پس از restart، جلوگیری از duplicate run، timeout/retry محدود و telemetry قابل جست‌وجو.
5. **P1 — تجربهٔ استفاده:** اتصال واقعی Control Center و Desktop، نمایش task/run/log/approval، خطا و پیشرفت؛ سپس اجرای E2E و accessibility.
6. **P1 — امنیت و عملیات:** احراز هویت/مجوز چندکاربره، tenant/ownership isolation، مدیریت secret، audit، rate limit، CI/CD، container، health/readiness و backup/restore آزموده‌شده.
7. **P2 — پوشش محصول:** متخصص‌های عمیق‌تر (debugger، test/fix، security review، release)، contractهای رسمی و sample-project smoke tests.
8. **P2 — gate نهایی:** ایجاد artifacts دوازده مرحله، `project-state.json` و integrity manifest، اجرای full review مستقل و بسته‌بندی release.

برآورد زمانی قابل اتکا بدون اجرای این گام‌ها ممکن نیست؛ چون backlog فعلی زمان‌محور و چرخشی است، نه برنامهٔ دارای شرط اتمام. بنابراین «چند ساعت روشن‌بودن» یا «تعداد اجرای supervisor» معیار تکمیل نهایی نیست.

## وضعیت آمادگی Production

**NOT_READY.** هستهٔ سرویس‌ها در محیط محلی قابل اجراست و چندین validation سبز است، اما failureهای تستی، نبود gate رسمی، نبود intake/چرخهٔ کامل پروژه، نبود اثبات عملیات ۲۴/۷ و اجرا نشدن review نهایی، انتشار Production را توجیه نمی‌کند.

## جمع‌بندی فنی

تا این نقطه یک هستهٔ local-first با ارکستراسیون، عامل محلی، gateway مدل، provider router، UI buildشدنی و supervisor خودکار ساخته شده و شواهد اجرایی واقعی دارد. برای رسیدن به چیزی که بتوان پروژهٔ دلخواه را بگیرد و نتیجهٔ نهایی تست‌شده تحویل دهد، هنوز یک مسیر چندبخشی P0/P1 شامل تثبیت failureها، intake ایزوله، چرخهٔ کامل تغییر و تست، امنیت، UI عملیاتی و gate نهایی باقی است.

## الحاقیه فاز ۱۰A — واردسازی مهارت‌های مهندسی نرم‌افزار

**تاریخ‌ها:** میلادی 2026-09-22؛ شمسی 1405-06-31

۱۲ Playbook مهندسی با حفظ فایل‌های اصلی در `skills/software-delivery/` قرار گرفتند و Manifest، سیاست فعال‌سازی فقط از طریق Router، متادیتای سازگاری و آزمون‌های قطعی رجیستری اضافه شد. متادیتای فعال‌سازی ضمنی بسته خارجی معتبر نیست. هر ۳۶ اسکریپت Python بدون اجرا با موفقیت کامپایل شدند. اعتبارسنجی Orchestrator پس از واردسازی: **۵۷ موفق**. در این فاز هیچ اتصال به عامل‌های زنده یا اجبار خط لوله ترتیبی مراحل ایجاد نشد.
### جزئیات اعتبارسنجی فاز ۱۰A

| بررسی | نتیجه |
| --- | --- |
| آزمون‌های Orchestrator | PASS — تعداد ۵۷ موفق؛ ۱۰ زیرآزمون موفق |
| آزمون‌های رجیستری مهارت | PASS — تعداد ۹ موفق (در ۵۷ آزمون Orchestrator) |
| آزمون‌های Model Gateway | PASS — تعداد ۲۵ موفق |
| کامپایل ایستای Local Agent | PASS — تعداد ۱۵ ماژول Python؛ مجموعه آزمون پروژه وجود ندارد |
| کامپایل اسکریپت‌های مهارت | PASS — تعداد ۳۶ اسکریپت بدون اجرا یا تولید bytecode |
| حفظ بسته‌ها | PASS — موجودی هر ۱۲ بسته با منبع برابر است؛ ۲۲۴ فایل منبع حفظ و چهار فایل رجیستری/گزارش اضافه شد |
| بررسی الگوی محرمانه | PASS — مقدار credential یافت نشد؛ فقط عبارت عمومی اسکنر تطبیق داشت |
## فاز ۱۰ب — مسیریابی نقش به مهارت (۲۰۲۶-۰۹-۲۲ / ۱۴۰۵-۰۶-۳۱)

فایل `skills/software-delivery/role-skill-map.json` و لایهٔ `services/orchestrator/app/skill_routing.py` به‌عنوان مسیریابی مرجع روی `SkillRegistry` فاز ۱۰الف اضافه شد. انتخاب شرطی نقش، وابستگی مرحله‌ای متناسب با پروژه، بارگذاری lazy و محدود context، evidence ساختاریافته، gateهای عینی و اشتراک مجوز حداقلی پیاده‌سازی شد. ستون‌های migration‌شوندهٔ `agent_tasks.skill_selections_json` و `agent_tasks.skill_trace_json`، persistence task، ورودی‌های اختیاری API و فیلدهای پاسخ نیز اضافه شدند.

اعتبارسنجی: `py -3.11 -m pytest -q tests/test_skill_routing.py` — ۱۶ موفق؛ کل Orchestrator — ۷۳ موفق و ۱۰ subtest موفق؛ رگرسیون رجیستری/state فاز ۱۰الف — ۹ موفق؛ compile ماژول‌های Python تغییرکرده موفق است. فعال‌سازی Worker واقعی و اجبار stage سراسری اضافه نشده است.
## الحاقیه فاز ۱۰ج — سخت‌سازی امنیت اسکریپت‌ها

**تاریخ‌ها:** میلادی 2026-09-22؛ شمسی 1405-06-31

### دامنه و پیاده‌سازی

- افزودن `app/skill_script_gateway.py` به‌عنوان مرز واحد policy برای اجرا.
- افزودن lookup محدود به manifest در `SkillRegistry`.
- enforce زنجیرهٔ Worker → Tool Policy → Local Agent و اشتراک capabilityهای role/task/global.
- enforce برنامهٔ دقیق فرمان ثبت‌شده در repository، executableهای مورداعتماد، بررسی workspace/path، سقف timeout/output و ریشه‌های مجاز artifact.
- بررسی target شبکه، مسدودسازی metadata/private، رد URL حساس و redirect خارج از target اعلام‌شده.
- مسیر compatibility-adapter-only برای viewهای `project-state.json`.
- hook تأیید سمت سرور و action hash؛ metadata به‌نام `approved` از client معتبر نیست.
- redact بازگشتی evidence/header/stdout/stderr.
- تست‌های قطعی برای مرزهای امنیتی خواسته‌شده.

### اعتبارسنجی

| فرمان/بررسی | نتیجه |
| --- | --- |
| `py -3.11 -m pytest -q tests/test_skill_script_gateway.py` | PASS — ۲۰ موفق |
| `py -3.11 -m pytest -q` (Orchestrator) | PASS — ۹۳ موفق و ۱۰ subtest موفق |
| `py -3.11 -m pytest -q -rA` (Model Gateway) | PASS — ۲۵ موفق |
| `py_compile` برای Local Agent | PASS — ۱۵ ماژول |
| `py_compile` برای Pythonهای تغییرکرده | PASS |
| `git diff --check` | PASS — خطای whitespace ندارد |

### وضعیت امنیت و اتصال

Gateway در نبود زنجیرهٔ policy، مسیر اسکریپت غیرقابل‌اعتماد، mismatch فرمان، خروج از scope، مقصد شبکهٔ دلخواه، redirect نامعتبر، approval ناموجود/نامطابق و نقض timeout/output fail-closed می‌کند. Gateway خودش subprocess یا network call اجرا نمی‌کند. Runtime اختصاصی Worker زنده در source فعلی وجود ندارد؛ بنابراین اتصال Gateway به Worker واقعی و ApprovalRequest دائمی هنوز برای Production لازم است. boolean قدیمی Local Agent در این مرز منبع مجوز نیست.
### مجوز برنامهٔ task

برای command/test runner اکنون `task_plan_authorized` الزامی است؛ صرفاً اعلام command توسط caller مجوز اجرا ایجاد نمی‌کند.
## فاز ۱۰د — اعتبارسنجی اجرای مبتنی بر مهارت

| فیلد | مقدار |
| --- | --- |
| تاریخ جلالی | ۱۴۰۵-۰۶-۳۱ |
| تاریخ میلادی | ۲۳ سپتامبر ۲۰۲۶ |
| دامنه | مسیریابی زمینه‌ای، بارگذاری تنبل، اشتراک مجوزها، دروازه شواهد و ردپای پایدار |
| artifact | `reports/phase10d-skill-execution-trace.json` |
| نتیجه | قرارداد اعتبارسنجی شد؛ اتصال Worker زنده آماده نیست |

مجموعه سناریوهای قطعی جدید از `SkillRouter`، `SkillContextLoader`، مجوزهای مؤثر، دروازه‌های کیفیت و ماندگاری ردپای وظیفه در SQLite استفاده می‌کند. پنج نوع پروژه و ۲۵ رکورد وظیفه پوشش داده شد. شواهد رگرسیون: Orchestrator برابر ۹۷ تست و ۱۰ subtest موفق، Model Gateway برابر ۲۵ تست موفق، کامپایل ۱۵ ماژول Python برای Local Agent و Build موفق کنترل‌سنتر و دسکتاپ. ماژول Agent Worker تولیدی برای فراخوانی Model Gateway یا Local Agent وجود ندارد؛ بنابراین اجرای زنده `NOT_RUN` و `SKILL_INTEGRATION_READY` برابر NO است.
مجموعه متمرکز رگرسیون مهارت‌های واردشده (Registry، Routing، State، Script Gateway و سناریوها): **۴۹ موفق**.

---
# الحاقیه فنی یکپارچه‌سازی موتور سئو

| مورد | مقدار |
|---|---|
| تاریخ گزارش | ۱۴۰۵-۰۷-۰۱ (هجری شمسی) / ۲۰۲۶-۰۹-۲۳ (میلادی) |
| مخزن | F:\AI-Engineer |
| دامنه | یکپارچه‌سازی SEO Content Automation Phase 10 |
| وضعیت تحویل | قابلیت پیاده‌سازی شده؛ دروازه‌های اجرای زنده هنوز باز هستند |

## سطح پیاده‌سازی‌شده

- پوشه `services/orchestrator/app/seo_engine/` مدل‌ها، ایمنی URL و SSRF، استخراج شواهد HTML، تشخیص پلتفرم، خزنده محدود، بررسی کد، برنامه کلمات کلیدی و قصد جست‌وجو، آداپترهای provider، persistence و facade موتور را دارد.
- فایل `services/orchestrator/app/routers/seo.py` ثبت سایت، تشخیص پلتفرم، audit، یافته‌ها، برنامه کلمات کلیدی، واگذاری و راستی‌آزمایی را در مسیر `/v1/seo` ارائه می‌کند.
- قراردادهای درخواست و پاسخ در `seo_schemas.py` تعریف شده‌اند.
- `db.py` جدول‌های سئو و رکورد `schema_migrations` را به‌صورت idempotent اضافه می‌کند و داده‌های قبلی را حفظ می‌کند.
- نقش‌های `seo_manager` و `seo_specialist` از زیرساخت نقش و پروفایل موجود استفاده می‌کنند.
- نگاشت نقش‌های سئو در `skills/software-delivery/role-skill-map.json` به Skill Router موجود متصل است.

## مدل داده

مهاجرت فعلی جدول‌های `seo_sites`، `seo_audit_snapshots`، `seo_pages`، `seo_findings`، `seo_keyword_clusters` و `seo_keyword_maps` و ایندکس‌های مربوط را ایجاد می‌کند. همه داده‌ها با `project_id` و/یا `site_id` جدا می‌شوند و SQLite منبع حقیقت باقی می‌ماند. هر finding شدت، منشأ، شواهد، معیار پذیرش، روش راستی‌آزمایی و وضعیت دارد. verified شدن نیازمند درخواست راستی‌آزمایی است و ادعای مدل به‌تنهایی کافی نیست.

## ایمنی و providerها

`SafeHttpClient` اعتبارنامه و fragment، پروتکل‌های نامعتبر، مقصدهای خصوصی/loopback مگر با اجازه صریح، redirect بین دامنه‌ای و پاسخ‌های بزرگ را رد می‌کند. `BoundedCrawler` تعداد صفحه و عمق را محدود می‌کند، فقط لینک‌های هم‌دامنه را دنبال می‌کند، status و hash محتوا را ثبت می‌کند و robots/sitemap را بررسی می‌کند. اعتبارنامه WordPress فقط در سمت سرور تزریق می‌شود، statusها allowlist شده‌اند، ایجاد و به‌روزرسانی draft انجام می‌شود و publish مستقیم همیشه خطا می‌دهد. آداپترهای Search Console حالت real/mock/no-data را آشکار می‌کنند و metric ساختگی تولید نمی‌شود. Rank Math و اتصال زنده Search Console هنوز اجرا نشده‌اند.

## اتصال به گردش‌کار شرکت

یافته‌های سئو می‌توانند تسک‌های موجود `agent_tasks` را بسازند و از Skill Router استفاده کنند. سیستم دوم برای task، message یا memory ساخته نشده است. با این حال runtime واقعی Agent Worker که در فازهای قبلی درخواست شده بود هنوز در مخزن قابل اثبات نیست؛ بنابراین delegation فعلی ذخیره‌سازی و فراخوانی مسیر legacy است، نه شواهد اجرای واقعی worker تخصصی، تغییر کد، تست و re-audit.

## ماتریس اعتبارسنجی

| بررسی | نتیجه | شواهد |
|---|---|---|
| کامپایل پایتون تغییرات | PASS | اجرای `python -m py_compile` روی همه ماژول‌های تغییرکرده |
| مجموعه تست Orchestrator | PASS | ۱۱۰ موفق، صفر شکست، صفر skip با `unittest` |
| مجموعه تست Model Gateway | PASS | ۲۵ موفق، صفر شکست با `pytest` |
| کامپایل Local Agent | PASS | اجرای `python -m compileall -q app` |
| تست Local Agent | NOT_RUN | فایل تستی وجود ندارد و pytest در venv نصب نیست |
| build Control Center | PASS | اجرای `npm run build` |
| build Desktop | PASS | اجرای `npm run build` |
| بررسی فاصله و خطاهای diff | PASS | اجرای `git diff --check` |
| WordPress/Search Console زنده | NOT_RUN | اعتبارنامه و مقصد خارجی مجاز ارائه نشده است |
| تعمیر واقعی با worker | NOT_RUN | runtime Agent Worker → Local Agent در دسترس نیست |

## پرچم‌های نهایی

- `SEO_ENGINE_INTEGRATED = YES`
- `REACT_NODE_SEO_READY = NO`
- `WORDPRESS_SEO_READY = NO`
- `READY_FOR_REAL_SEO_PROJECT = NO`

## کار فنی باقی‌مانده

۱. runtime واقعی Agent Worker را پیاده و با fixture قطعی React/Node راستی‌آزمایی کنید.
۲. دریافت HTML رندرشده را از مسیر Local Agent اضافه کنید و مقایسه raw/rendered را حفظ کنید.
۳. تست‌های مجاز و زنده Search Console و WordPress/Rank Math را با secret redaction و سیاست draft-only اضافه کنید.
۴. پس از وجود شواهد worker و re-audit، quality gate سئو را به completion پروژه متصل کنید.
۵. تست Local Agent را اضافه کنید یا ابزار تست آن را در محیط توسعه کنترل‌شده نصب کنید.

در این فاز هیچ استقرار راه دور یا push گیت انجام نشد.
