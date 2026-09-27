# گزارش امنیت اجرای اسکریپت‌های مهارت — فاز ۱۰ج

| فیلد | مقدار |
| --- | --- |
| پروژه | AI-Engineer |
| فاز | ۱۰ج — سخت‌سازی اجرای اسکریپت‌های مهارت |
| زبان | فارسی |
| تاریخ میلادی | 2026-09-22 |
| تاریخ شمسی | 1405-06-31 |
| وضعیت | پیاده‌سازی‌شده با محدودیت اتصال به Runtime زنده |

## مدل امنیتی اجرای اسکریپت

`services/orchestrator/app/skill_script_gateway.py` مرز واحد سیاست‌گذاری برای helperهای مهارت‌های واردشده است. درخواست فقط زمانی پذیرفته می‌شود که skill/script دقیقاً در manifest ثبت شده باشد، زنجیرهٔ `agent_worker` → `tool_policy` → `local_agent` را اعلام کند، scope آن توسط Router تأیید شده باشد و اشتراک قابلیت‌ها معتبر باشد. Gateway خودش subprocess، socket یا نوشتن آزاد روی فایل را انجام نمی‌دهد.

فقط نام اسکریپت ثبت‌شده در manifest و داخل پوشهٔ `scripts/` همان مهارت resolve می‌شود. جداکنندهٔ مسیر، traversal، مسیر مهارت غیرقابل‌اعتماد و فایل مفقود رد می‌شوند. متادیتای `allow_implicit_invocation` خارجی مرجع تصمیم‌گیری نیست.

## سیاست اجرای فرمان

فرمان فقط وقتی پذیرفته می‌شود که کل tuple آرگومان با برنامهٔ فرمان ثبت‌شده در repository یکسان باشد. دستهٔ executable مورداعتماد، رد کاراکترهای shell/control و traversal، محدودیت مسیر به workspace/ریشه‌های مجاز، اشتراک مجوز role/task/global و سقف زمان و خروجی هم اعمال می‌شود. وجود command runner در skill بازبین، دسترسی shell آزاد یا مجوز نوشتن ایجاد نمی‌کند.

Adapter مربوط به Local Agent فقط پس از تصمیم policy طرح معتبر را دریافت می‌کند. فیلد legacy به نام `approved` صرفاً برای سازگاری ارسال می‌شود و منبع authorization نیست.

## سیاست شبکه

بررسی شبکه فقط با URL مطلق HTTP(S) و در صورت تطبیق با target اعلام‌شدهٔ پروژه یا deployment target صریحاً تأییدشده مجاز است. userinfo دارای credential و query پارامترهای حساس رد می‌شوند. hostهای metadata ابری و مقصدهای private/reserved اعلام‌نشده مسدود هستند. health check روی localhost/dev فقط با declaration صریح مجاز است. شواهد `url` و `response_url` بازگشت‌داده‌شده برای redirect خارج از target مجاز بررسی می‌شوند.

اگر helper خارجی URL نهایی redirect را گزارش نکند، Gateway امکان مشاهدهٔ آن را ندارد؛ این محدودیت برای adapterهای آینده ثبت شده است.

## سیاست workspace و artifact

مسیر resolve‌شده باید زیر ریشه‌های مجاز تنظیم‌شده باقی بماند؛ traversal پیش از normalize رد، symlink resolve و نوشتن artifact فقط به `docs/`، `artifacts/` یا `reports/` محدود است. `project-state.json` فقط از مسیر compatibility adapter مجاز است و database مرجع اصلی باقی می‌ماند. نتیجهٔ artifact محدود و قابل‌اعتماد serialize می‌شود.

## حذف محرمانه‌ها

header، evidence، stdout، stderr و mappingهای برگشتی پیش از persistence/return redact و محدود می‌شوند. Bearer/Basic، headerهای authorization/cookie، فیلدهای token/API-key/password/secret/private-key، بلوک private key و مقادیر شبیه `.env` حذف می‌شوند. این رفتار به‌صورت مستقل و در اجرای موفق از طریق Local Agent آزموده شده است.

## اتصال تأیید مالک

اسکریپت‌های پرریسک/بحرانی و بررسی‌های شبکه به `ApprovalVerifier` سمت سرور و hash دقیق action canonical نیاز دارند. `client_approved=true` نادیده گرفته می‌شود. نبودن approval یا approval منقضی، ردشده، مصرف‌شده یا نامطابق fail-closed است. Gateway قرارداد approval و hash تک‌عملیاتی را فراهم می‌کند؛ ذخیره‌سازی کامل ApprovalRequest و اتصال به Worker زنده خارج از این فاز است و پیش از فعال‌سازی autonomy در Production باید تکمیل شود.

## نتایج آزمون

| اعتبارسنجی | نتیجه |
| --- | --- |
| `test_skill_script_gateway.py` | PASS — ۲۰ موفق |
| مجموعهٔ Orchestrator | PASS — ۹۳ موفق و ۱۰ subtest موفق |
| مجموعهٔ Model Gateway | PASS — ۲۵ موفق |
| کامپایل Python مربوط به Local Agent | PASS — ۱۵ ماژول؛ مجموعهٔ pytest برای Local Agent وجود ندارد |
| کامپایل Python تغییرکرده | PASS |
| `git diff --check` | PASS — خطای whitespace ندارد؛ فقط هشدارهای line-ending موجود است |
| کامپایل موجودی helperهای مهارت (baseline فاز ۱۰الف) | PASS — ۳۶ اسکریپت بدون اجرا کامپایل شدند |
| buildهای Node | NOT_RUN — خارج از دامنهٔ فاز ۱۰ج و بدون تغییر فایل frontend |

## فایل‌ها و artifactها

- `services/orchestrator/app/skill_script_gateway.py`
- `services/orchestrator/app/skill_registry.py`
- `services/orchestrator/tests/test_skill_script_gateway.py`
- `skills/software-delivery/integration-policy.json`
- `docs/skills-routing.md`
- `skills/software-delivery/README.md`

پیش از ویرایش‌ها backupهای timestamped و verifyشده ساخته شد. آخرین backup پاک‌سازی Gateway در `F:\phase9work\backups\phase10c-gateway-cleanup-20260922-144748.zip` با SHA-256 برابر `4FA250CBF92F7B63BBA37210F7A7BB918BABD31F503885F9E531F810EAD06C51` است.

## محدودیت‌ها

Gateway سیاست‌گذاری و آزمون‌ها پیاده شده‌اند، اما repository هنوز Runtime اختصاصی و زنده‌ای ندارد که همهٔ helperهای واردشده را واقعاً از این مسیر اجرا کند. بنابراین Gateway زنجیرهٔ مورد انتظار را در API enforce می‌کند و adapterهای Local Agent و compatibility را ارائه می‌دهد؛ اتصال آن به Worker زنده هنوز لازم است. فیلد boolean قدیمی Local Agent برای سازگاری باقی مانده، اما از طریق این Gateway مجوز ایجاد نمی‌کند.
## مجوز برنامهٔ task

Command runner و test runner به `task_plan_authorized=true` از طرف Worker/برنامه‌ریز task نیاز دارند. مدل نمی‌تواند با ارسال `declared_commands` خودش مجوز بسازد؛ فرمان باید از تعریف مورداعتماد repository/skill یا task plan صریحاً تأییدشده بیاید.
به‌روزرسانی‌های پرریسک compatibility adapter نیز approval-gate دارند؛ تغییر critical در `project-state.json` نمی‌تواند verifier سمت سرور را دور بزند.