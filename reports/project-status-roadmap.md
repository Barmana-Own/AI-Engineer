# وضعیت پروژه و نقشه راه — Project Status and Roadmap

| فیلد / Field | مقدار / Value |
|---|---|
| پروژه / Project | AI-Engineer |
| تاریخ جلالی / Jalali date | 1405-06-28 |
| تاریخ میلادی / Gregorian date | 2026-09-19 |
| فاز / Phase | Corrective Phase 3 |

## بخش فارسی

### ۱. خلاصه وضعیت فعلی پروژه

اتصال Sales و SEO به زیرساخت موجود شرکت AI تکمیل و روی سرور راه‌دور اعتبارسنجی شده است. فرصت فروش اکنون می‌تواند از qualification تا پروژه عادی و اجرای Supervisor پیش برود.

### ۲. مواردی که واقعاً پیاده‌سازی شده‌اند

- lifecycle پایدار فرصت با گیت مالک انسانی.
- سرویس واحد intake از Sales تا Requirements، Director، team plan و Supervisor.
- تبدیل فرصت به پروژه و اجرای idempotent در دیتابیس ایزوله.
- routing پویای SEO برای keyword-only و technical SEO.
- handoff و verification برای یافته‌های SEO.
- migration 13 و APIهای lifecycle فرصت.

### ۳. کارهای باقی‌مانده

- اتصال اختیاری به منابع معتبر Search Console/Analytics/ranking در صورت فراهم شدن credential و policy.
- اتصال خارجی CRM، پرداخت و قرارداد؛ این موارد خارج از این فاز هستند.
- اجرای build frontend در فازی که سورس frontend تغییر کند.

### ۴. موارد ناقص، مسدود، FAIL یا NOT_RUN

- FAIL: موردی در تست‌های الزامی باقی نماند.
- NOT_RUN: TypeScript/frontend checks، چون فایل frontend تغییر نکرد؛ smoke مدل واقعی، چون تست‌های deterministic انتخاب شدند.

### ۵. مشکلات و ریسک‌های فعلی

- داده‌های SEO بدون منبع معتبر قابل ادعا نیستند.
- تصمیم‌های تجاری مهم همچنان نیازمند Human Owner هستند.
- اعتبارسنجی external platformها در این فاز انجام نشده است.

### ۶. پیشنهادهای ادامه توسعه

- P0: نگه‌داشتن owner gate و جلوگیری از تعهد خودکار.
- P1: افزودن connectorهای مجاز برای داده SEO با ثبت منبع و تاریخ داده.
- P1: افزودن تست contract برای مصرف‌کننده API فرصت در Control Center.
- P2: افزودن گزارش مدیریتی دوره‌ای برای فرصت‌ها و پروژه‌های تبدیل‌شده.

### ۷. قابلیت‌های ارزشمند برای این کسب‌وکار

ردیابی منبع داده SEO، تیم‌بندی مبتنی بر outcomeهای اندازه‌گیری‌شده، و گزارش‌های قابل ممیزی بیشترین ارزش عملی را دارند؛ این موارد باید روی همین persistence و message/handoff موجود ساخته شوند.

### ۸. اولویت پیشنهادی

ابتدا گیت‌های مالک و جداسازی پروژه را حفظ کنید؛ سپس داده SEO معتبر و contractهای API را اضافه کنید؛ در پایان automationهای بیرونی را با approval صریح توسعه دهید.

### ۹. آمادگی Production

هسته Orchestrator برای این فاز با تست‌های کامل و health زنده آماده بازبینی است. یکپارچه‌سازی خارجی و frontend build برای این تغییرات جزء scope نبود و باید جداگانه اعتبارسنجی شود.

### ۱۰. جمع‌بندی مدیریتی کوتاه

مسیر Sales تا پروژه و مسیر SEO تا اجرای مهندسی واقعی شده است؛ اجرای بعدی باید evidence و approval را حفظ کند و از ایجاد معماری موازی پرهیز کند.

## English section

### 1. Current project status

Sales and SEO are connected to the existing AI-company infrastructure and were validated on the remote server. A sales opportunity can now move from qualification to a normal project and Supervisor execution.

### 2. Implemented items

- Durable opportunity lifecycle with a Human Owner gate.
- One intake service covering Sales, Requirements, Director, team planning, and Supervisor.
- Opportunity-to-project conversion with isolated-database idempotency.
- Dynamic SEO routing for keyword-only and technical SEO work.
- SEO finding handoff and verification/revision flow.
- Migration 13 and opportunity lifecycle APIs.

### 3. Remaining work

- Optional authorized Search Console/Analytics/ranking connectors when credentials and policy are available.
- External CRM, payment, and contract integrations; these were outside this phase.
- Frontend build execution in a phase that changes frontend source.

### 4. Incomplete, blocked, FAIL, or NOT_RUN items

- FAIL: no required test failures remain.
- NOT_RUN: TypeScript/frontend checks because frontend source was unchanged; real-model smoke because deterministic tests were selected.

### 5. Current risks / problems

- SEO data must not be asserted without an authoritative source.
- Important commercial decisions still require the Human Owner.
- External platform validation was not part of this phase.

### 6. Recommended next improvements

- P0: preserve owner gates and prevent automatic commitments.
- P1: add authorized SEO data connectors with source and timestamp metadata.
- P1: add Control Center contract tests for opportunity APIs.
- P2: add periodic management reporting for opportunities and converted projects.

### 7. Valuable product / engineering enhancements

SEO data provenance, outcome-based team selection, and auditable reports provide the most practical value. They should extend the current persistence and message/handoff systems.

### 8. Recommended priority order

Preserve owner gates and project isolation first; add authoritative SEO data and API contracts next; only then add external automation with explicit approval.

### 9. Production readiness

The Orchestrator core for this phase is ready for review with the complete test baseline and live health validation. External integrations and frontend build checks were outside this change scope and require separate validation.

### 10. Short management summary

The Sales-to-project path and SEO-to-engineering path are now real; further work should preserve evidence and approval gates and avoid parallel architecture.

## وضعیت پروژه پس از Corrective Phase 4 — 2026-09-20 / 1405-06-29

### فارسی

**وضعیت فعلی:** آماده‌سازی امنیت deployment انجام شده اما استقرار عمومی هنوز مجاز نیست.

**پیاده‌سازی واقعی:** middleware احراز هویت control-plane و gateway، توکن جداگانه مالک برای عملیات پرریسک، پیش‌فرض امن autonomy، health check احراز هویت‌شده، package sanitized، مستندات و rollback runbook.

**باقی‌مانده:** تنظیم توکن‌های machine، restart امن، تأیید HTTPS/IIS، اجرای health و smoke احراز هویت‌شده و در صورت نیاز نصب dependencyهای Desktop.

**FAIL/NOT_RUN:** health عمومی احراز هویت‌شده NOT_RUN به علت نبود توکن؛ Desktop build NOT_RUN به علت نبود dependency؛ proxy فعلی تا restart هنوز anonymous است.

**ریسک‌ها:** exposure فعلی نمونه در حال اجرا، autonomy opt-in موجود در `.env`، و نبود مسیر احراز هویت operator در frontend استاتیک.

**اولویت‌ها:** P0 تنظیم توکن و restart؛ P0 تأیید HTTPS و proxy؛ P1 اجرای smoke احراز هویت‌شده؛ P1 تصمیم operator برای autonomy؛ P2 نصب و build Desktop.

**آمادگی Production:** خیر.

**جمع‌بندی مدیریتی:** کد و بسته release آماده gate نهایی هستند، اما بدون تنظیمات امن سرور و restart کنترل‌شده نباید public شوند.

### English

**Current status:** deployment security preparation is complete, but public deployment is not authorized yet.

**Implemented:** control-plane and gateway authentication middleware, a separate owner token for high-risk operations, safe autonomy defaults, authenticated health checks, sanitized packaging, documentation and rollback runbook.

**Remaining:** configure machine tokens, perform a controlled restart, verify HTTPS/IIS, run authenticated health and smoke checks, and install Desktop dependencies if that build is required.

**FAIL/NOT_RUN:** authenticated public health is NOT_RUN because tokens are absent; Desktop build is NOT_RUN because dependencies are absent; the current running proxy remains anonymous until restart.

**Risks:** current live instance exposure, an existing autonomy opt-in in `.env`, no operator-authentication channel in the static frontend, and an HTTPS probe that currently fails during connection setup.

**Priority order:** P0 configure tokens and restart; P0 verify HTTPS and proxy; P1 run authenticated smoke checks; P1 obtain an owner decision on autonomy; P2 install and build Desktop.

**Production readiness:** NO.

**Management summary:** source and release packaging are ready for the final gate, but the public server must not be exposed until secure configuration and a controlled restart are completed.

