# گزارش پیاده‌سازی مدیر سئو

| فیلد | مقدار |
|---|---|
| پروژه | AI-Engineer |
| نوع گزارش | تحویل نقش فنی |
| زبان | فارسی |
| تاریخ جلالی | ۱۴۰۵-۰۶-۲۸ (1405-06-28) |
| تاریخ میلادی | ۲۰۲۶-۰۹-۱۹ (2026-09-19) |
| وضعیت تحویل | پیاده‌سازی و راستی‌آزمایی شد |

## معماری مدیر سئو

نقش canonical با شناسه `seo_manager` یک نقش مدیریتی و فقط‌خواندنی است که روی Company Director، Project Manager، Engineering Manager، Task DAG، پیام‌رسان پایدار، handoff، تصمیم‌های فنی، صف کار، حافظه و بازیابی موجود ساخته شده است. چارچوب دوم برای agent/task/memory ایجاد نشده و این نقش مستقیماً سورس تولیدی را تغییر نمی‌دهد.

## قرارداد نقش

قرارداد registry حوزه‌های استراتژی سئو، audit فنی و on-page، استراتژی و نیت کلمات کلیدی، معماری سایت، indexability/crawlability، metadata، داده ساختاریافته، performance، سئوی بین‌المللی/محلی/فروشگاهی، پایش، تشخیص regression، واگذاری کار، quality gate و گزارش‌دهی را پوشش می‌دهد. ابزارها به بازرسی محدود، ساخت task/message/decision و اجرای تست امن محدود هستند. writable scope برابر `none` است و تغییر تولیدی به نقش‌های موجود واگذار می‌شود.

## جریان کاری سئو

۱. پروفایل سایت در محدوده پروژه ساخته می‌شود و داده‌های ناموجود با `DATA NOT AVAILABLE` علامت می‌خورند.
۲. شواهد مشاهده‌پذیر audit به finding دارای اثر، URL/فایل، نقش مسئول، اولویت، معیار پذیرش و روش راستی‌آزمایی تبدیل می‌شوند.
۳. clusterهای کلمه و نگاشت کلمه به صفحه ساخته می‌شود و cannibalization و صفحه هدف ناموجود علامت می‌خورد.
۴. findingها به taskهای واقعی DAG، صف کار و handoff پایدار تبدیل می‌شوند.
۵. تصمیم‌های سئو فقط با evidence ثبت و به‌صورت ساختاریافته منتشر می‌شوند.
۶. معیار پذیرش با وضعیت‌های `SEO_PENDING`، `SEO_IN_PROGRESS`، `SEO_REVIEW`، `SEO_VERIFIED` و `SEO_FAILED` بررسی می‌شود.
۷. فقط دانش پروژه‌ای evidence-gated در حافظه ذخیره و گزارش سئو تولید می‌شود.

## مدل audit

ماژول robots.txt، XML sitemap، indexability، canonical، کدهای HTTP، redirect، صفحات تکراری، URL، metadata، heading، لینک داخلی، صفحات orphan و لینک شکسته، تصویر، structured data، موبایل، performance، crawlability، rendering، pagination، hreflang، ساختار چندزبانه، صفحات thin، JavaScript SEO و معماری سایت را پشتیبانی می‌کند. نبود داده صریحاً گزارش می‌شود و هیچ traffic، ranking، search volume، Search Console یا Core Web Vitals ساختگی تولید نمی‌شود.

## مدل کلمه کلیدی و نگاشت

clusterها با message bus موجود و با project_id ذخیره می‌شوند و شامل کلمه‌ها، intent، زبان، منطقه، funnel، ارزش تجاری، صفحه هدف/فعلی/پیشنهادی، اولویت و وضعیت هستند. هدف صفحه تکراری به `cannibalization` و هدف ناموجود به `missing_target_page` تبدیل می‌شود.

## واگذاری و quality gate

findingهای سئو taskهای عادی `CoordinationTask` می‌سازند، employeeهای موجود را در صف قرار می‌دهند و `AgentHandoff` ثبت می‌کنند. مالکیت Frontend، Backend، DevOps، Research، Integration، Documentation، Test، Review و Architecture حفظ شده است. gate تأییدشده بدون شواهد معتبر نیست؛ نبود شواهد یا عدم تطابق observed/expected پیام blocker و `SEO_FAILED` تولید می‌کند.

## یکپارچگی حافظه

نقش از `MemoryStore` موجود با `MemoryType.PROJECT`، محدوده پروژه، role=`seo_manager` و task type=`seo` استفاده می‌کند. lifecycle و sanitization حافظه حفظ شده و retrieval بر اساس پروژه و نقش فیلتر می‌شود.

## تغییرات پایگاه داده و API

جدول یا migration جدیدی اضافه نشده است. task، message، handoff، decision، work queue، employee و memory موجود دوباره استفاده می‌شوند. endpoint موجود `/v1/coordination/roles` قرارداد canonical را بعد از reload سرویس ارائه می‌دهد و API جداگانه‌ای برای SEO ساخته نشده است.

## فایل‌های تغییرکرده

- `services/orchestrator/app/coordination/roles.py`
- `services/orchestrator/app/organization/__init__.py`
- `services/orchestrator/app/organization/seo_manager.py`
- `services/orchestrator/tests/test_seo_manager.py`

## نتایج تست

- تست‌های متمرکز SEO Manager: **۱۱ موفق**.
- تست‌های regression ارکستریتور: **۲۱۳ موفق، ۱ skip**.
- تست‌های pytest مربوط به Model Gateway: **۲۶ موفق**.
- تست‌های unittest مربوط به Local Agent: **۲ موفق**.
- compile نحوی فایل‌های تغییرکرده: **موفق**.
- health زنده پس از reload scheduled task: **HTTP 200** و وابستگی‌های Model Gateway و Local Agent سالم.
- بررسی registry زنده: نقش `seo_manager` با `read_only` و writable scope برابر `none` بارگذاری شد.

## محدودیت‌های شناخته‌شده

اتصال به Search Console، analytics، سرویس ranking، crawler یا منبع Core Web Vitals انجام نشده است و این داده‌ها باید از adapter مجاز تأمین شوند. SEO Manager هماهنگ‌کننده و verifier است و تغییرات تولیدی همچنان از مسیر agentهای مهندسی، review و release موجود عبور می‌کند.