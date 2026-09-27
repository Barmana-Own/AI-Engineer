# گزارش فنی سئوی رخ‌پوش — فاز A2

| مشخصه | مقدار |
|---|---|
| پروژه | سئوی رخ‌پوش |
| نوع گزارش | گزارش فنی |
| زبان | فارسی |
| تاریخ شمسی | ۱۴۰۵-۰۷-۰۴ |
| تاریخ میلادی | ۲۰۲۶-۰۹-۲۶ |
| baseline | `3fa35322-4251-4ae9-8954-9ef143dd4220` |
| وضعیت | **BLOCKED — REPAIR_REQUIRED** |

## دامنهٔ بررسی

این checkpoint بررسی می‌کند که آیا مخزن می‌تواند یافته‌های تأییدشدهٔ A1 رخ‌پوش را از طریق runtime واقعی Agent Worker نقش‌محور اجرا کند یا خیر. این بررسی مجوز اصلاح source یا deployment نیست.

## baseline و تیم پیشنهادی

سایت اصلی هشت finding ثبت‌شده دارد (شش مورد مشاهده‌شده و دو مورد از کد منبع). تیم برنامه‌ریزی‌شده شامل `seo_manager`، `seo_specialist`، `frontend`، `devops`، `tester` و `reviewer` است و نقش‌های غیرمرتبط حذف شده‌اند. این برنامه در `reports/seo-projects/rookhposh-a1-team-plan.json` است و `execution_started` همچنان `false` است.

## ممیزی runtime

پیاده‌سازی worker موردنیاز در source قابل اثبات نیست:

- زیرپکیج `coordination/` یا ماژول‌های worker/pool/claim/context در `services/orchestrator/app/` وجود ندارد.
- جدول `agent_tasks` ستون‌های assignment نقش، dependency، claim اتمیک، lease یا heartbeat ندارد.
- `services/orchestrator/app/subagents.py` قرارداد نقش و helperهای خالص prompt/status/handoff را فراهم می‌کند و assignment را اجرا نمی‌کند.
- `services/orchestrator/app/routers/seo.py` مسیر قدیمی `run_agent_task(task_id)` را در background اجرا می‌کند.
- `services/orchestrator/app/agent_service.py` حلقهٔ قدیمی و یکپارچهٔ ابزار است و مرز callable موردنیاز برای worker نقش‌محور با lifecycle پایدار assignment را ندارد.

بنابراین استفاده از endpoint واگذاری فعلی، زنجیرهٔ خواسته‌شده را ثابت نمی‌کند و trace فاز A2 را گمراه‌کننده می‌سازد. هیچ taskی ایجاد نشد، هیچ وضعیت completion تزریق نشد و هیچ فایل source تغییر نکرد.

## gate پیاده‌سازی پیش‌نیاز

پیش از ادامهٔ A2 باید runtime فاز ۹الف/۹ب در مرزهای موجود task، پیام، handoff، Model Gateway، Local Agent و persistence پیاده‌سازی شود. این gate باید موارد زیر را نشان دهد:

۱. claim اتمیک task آماده و resolve نقش/پروفایل؛
۲. progression مبتنی بر dependency و recovery محدود lease؛
۳. context محدود و مجوز مؤثر نقش/ابزار؛
۴. فراخوانی واقعی Model Gateway و عملیات فقط از Local Agent؛
۵. ثبت نتیجهٔ ساختاریافته، پیام، handoff، retry و failure؛
۶. trace منشأ worker برای اتصال finding، task، agent، فایل، تست و re-audit.

## ماتریس اعتبارسنجی

| بررسی | وضعیت | شواهد |
|---|---|---|
| تست‌های متمرکز سئو | PASS | ۱۳ تست |
| `git diff --check` | PASS | خطای whitespace ندارد |
| `npm ci` در workspace رخ‌پوش | NOT_RUN | `node_modules` موجود نیست |
| `npm run typecheck` | NOT_RUN | remediation شروع نشده است |
| `npm run lint` | NOT_RUN | remediation شروع نشده است |
| `npm run build` | NOT_RUN | remediation شروع نشده است |
| اجرای worker واقعی | NOT_RUN | runtime موجود نیست |
| re-audit پس از اصلاح | NOT_RUN | source تغییر نکرده است |

## وضعیت trace

زنجیرهٔ `finding → engineering task → assigned worker → files changed → tests → deployment/review → SEO re-verification` عمداً برای A2 خالی است. رکورد machine-readable مانع در `reports/seo-projects/rookhposh-a2-blocker.json` قرار دارد.

## امنیت و یکپارچگی

در این checkpoint هیچ mutation در source یا database انجام نشد و تغییرات موجود کاربر حفظ شد. خطای DNS دامنهٔ blog و نبود دادهٔ Search Console همچنان شرایط خارجیِ صریحاً تأییدنشده هستند.
