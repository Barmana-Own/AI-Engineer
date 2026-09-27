# گزارش نهایی یکپارچه‌سازی موتور سئو

| مورد | مقدار |
|---|---|
| پروژه | AI-Engineer |
| نوع گزارش | گزارش نهایی یکپارچه‌سازی موتور سئو |
| زبان | فارسی |
| تاریخ شمسی | ۱۴۰۵-۰۷-۰۱ |
| تاریخ میلادی | ۲۰۲۶-۰۹-۲۳ |
| revision مخزن | `1e3839e` (working tree تغییرات commit نشده دارد) |
| وضعیت تحویل | قابلیت یکپارچه شده؛ دروازه‌های اجرای زنده هنوز باز هستند |

## ۱. ممیزی SEO Bot منبع

آرشیو TypeScript سئو پیش از پیاده‌سازی بررسی شد. بخش‌های قابل استفاده شامل قراردادها و قواعد مستقل از پلتفرم، نرمال‌سازی و خوشه‌بندی کیفی کلمات، ساختار بریف محتوا، مفاهیم لینک داخلی، رفتار draft-first وردپرس، برچسب‌های real/mock/no-data برای Search Console، رابط‌های Rank Math، الگوهای ایمنی provider و مفاهیم Playwright بود. زیرساخت‌های مستقل NestJS/Prisma/BullMQ، احراز هویت، تیم، صف و UI مدیریتی وارد runtime Orchestrator نشدند.

## ۲. معماری یکپارچه‌سازی

قابلیت در `services/orchestrator/app/seo_engine/` قرار گرفته و از مسیرهای FastAPI موجود فراخوانی می‌شود. SQLite منبع حقیقت پروژه و سئو است. نقش‌های SEO Manager/Specialist همان نقش‌های موجود هستند؛ findings تسک‌های موجود `agent_tasks` را می‌سازند و Skill Router فعلی استفاده می‌شود. تغییرات production باید از نقش مهندسی مجاز و مرز Local Agent عبور کنند.

## ۳. اجزای استفاده‌شده

| مفهوم منبع | مقصد در AI-Engineer |
|---|---|
| قراردادها و قواعد SEO | `seo_engine/models.py` و `audit.py` |
| نرمال‌سازی و خوشه‌بندی | `seo_engine/keywords.py` |
| WordPress draft-first | `seo_engine/providers.py` |
| برچسب real/mock/no-data | `seo_engine/providers.py` |
| ایمنی provider و اعتبارنامه | `seo_engine/security.py` و `providers.py` |
| تشخیص پلتفرم | `seo_engine/detector.py` |
| بررسی کد | `seo_engine/codebase.py` |
| واگذاری تسک | `db.py`، `agent_service.py` و `skill_routing.py` موجود |

## ۴. حذف یا غیرفعال‌سازی زیرساخت تکراری

احراز هویت، RBAC، شرکت/تیم، task/queue، پایگاه Prisma، API NestJS، UI React مدیریتی و stack مستقل AI آرشیو، جزء runtime فعال AI-Engineer نیستند. task، message، memory، project state یا stack مستقل LLM دوم ساخته نشده است.

## ۵. وضعیت پلتفرم‌ها

| پلتفرم | وضعیت | شواهد |
|---|---|---|
| WordPress | PARTIAL | آداپتر REST سمت سرور، draft/update، منع publish و تشخیص |
| React SPA | READY برای source audit | تشخیص قطعی منبع و یافته‌های metadata |
| Vite React | READY برای source audit | تشخیص Vite+React و یافته‌های منبع |
| Next.js | READY برای source audit | تشخیص dependency/config و markerهای HTML |
| Node/Express | READY برای source audit | تشخیص dependency/header و مسیر واگذاری |
| Static | READY برای source audit | تشخیص artifactهای ایستا |
| Generic Web | PARTIAL | خزنده محدود و شواهد HTML |

READY در این جدول به معنی قابلیت audit محدود است، نه تکمیل تعمیر زنده.

## ۶. قابلیت‌های سئو

پروفایل مستقل سایت؛ جداسازی پروژه/سایت؛ خزیدن محدود و هم‌دامنه؛ hash خام و رندرشده؛ استخراج title، description، robots، canonical، hreflang، heading، link، تصویر، JSON-LD و word count؛ یافته‌های HTTP/metadata/indexability/internal-link؛ بررسی robots/sitemap؛ نرمال‌سازی، intent، clustering، نقشه keyword-page، تشخیص cannibalization و بریف محتوا؛ بررسی read-only کد؛ آداپتر WordPress draft-first؛ برچسب Search Console؛ snapshot baseline/re-audit و verification صریح پیاده شده‌اند.

Playwright، Rank Math، OAuth و query واقعی Search Console، داده میدانی performance و آداپتر بریف هوشمند متصل به Model Gateway هنوز اجرای زنده ندارند.

## ۷. جریان عامل‌های AI-Engineer

جریان هدف: Company Director/Supervisor → `seo_manager` برای strategy و اولویت → `seo_specialist` برای audit → finding ذخیره‌شده → تسک و Skill Router موجود → Frontend/Backend/DevOps/Tester در صورت نیاز → re-verification سئو. در مخزن فعلی runtime اثبات‌شده Agent Worker → Model Gateway → Local Agent وجود ندارد؛ بنابراین واگذاری فقط task را ذخیره و runner قدیمی را فراخوانی می‌کند.

## ۸. مدل داده و مهاجرت

`db.py` رکورد idempotent `schema_migrations` با نسخه `1.0` و جدول‌های `seo_sites`، `seo_audit_snapshots`، `seo_pages`، `seo_findings`، `seo_keyword_clusters` و `seo_keyword_maps` را همراه foreign key و index اضافه می‌کند. شواهد صفحه و finding با snapshot مرتبط ذخیره می‌شوند. داده قبلی حفظ می‌شود و `project-state.json` منبع مستقل حقیقت نیست.

## ۹. مرزهای امنیتی

اعتبارسنجی URL، credential/fragment، scheme نامعتبر، مقصد خصوصی یا loopback مگر با اجازه، host خارج از allowlist و redirect بین‌دامنه‌ای را رد می‌کند. crawl تعداد صفحه، عمق، timeout و بایت پاسخ را محدود می‌کند. workspace فقط زیر ریشه‌های تنظیم‌شده مجاز است. credential وردپرس سمت سرور باقی می‌ماند و در prompt/report ذخیره نمی‌شود. status وردپرس allowlist شده و publish مستقیم ممنوع است. شکاف‌های احراز هویت/approval کنترل‌پلین موجود خارج از این slice هستند و مانع exposure عمومی production می‌شوند.

## ۱۰. قرارداد API و ابزار

مسیرهای `/v1/seo`: ثبت/فهرست/دریافت سایت؛ تشخیص پلتفرم؛ ایجاد/فهرست audit؛ فهرست finding snapshot؛ برنامه keyword؛ فهرست finding؛ واگذاری finding به task موجود؛ و verify finding. مدل‌های Pydantic ورودی‌ها و طول اعضای فهرست را محدود می‌کنند. routeهای SEO subprocess یا script بدون محدودیت ارائه نمی‌کنند.

## ۱۱. نتایج تست

| بررسی | نتیجه |
|---|---|
| تست‌های Orchestrator | PASS — ۱۱۰ موفق، صفر شکست، صفر skip |
| تست‌های متمرکز SEO | PASS — ۱۳ موفق |
| تست‌های Model Gateway | PASS — ۲۵ موفق |
| compile/compileall پایتون SEO | PASS |
| compile Local Agent | PASS |
| تست Local Agent | NOT_RUN — فایل تست نیست و pytest در venv موجود نیست |
| build Control Center | PASS |
| build Desktop | PASS |
| `git diff --check` | PASS |
| خواندن UTF-8 گزارش/مستندات | PASS |

## ۱۲. نتیجه React + Node end-to-end

NOT RUN / NOT READY. تشخیص source می‌تواند workspace React/Vite و dependency Express را پیدا کند و audit محدود URL شواهد بسازد. اما زنجیره لازم شامل finding تا تغییر واقعی توسط worker، اصلاح fixture از مسیر Local Agent، build/test، re-audit و verification خودکار به‌دلیل نبود runtime اثبات‌شده Agent Worker قابل اثبات نیست. موفقیت مبتنی بر mock ادعا نشده است.

## ۱۳. نتیجه regression وردپرس

PARTIAL PASS. ایجاد/به‌روزرسانی draft و منع publish مستقیم در تست قطعی موفق است. مرز URL/credential و allowlist status پیاده شده‌اند. اجرای مجاز و زنده WordPress، Rank Math، taxonomy، media یا Search Console انجام نشده است؛ بنابراین آمادگی production وردپرس ادعا نمی‌شود.

## ۱۴. فایل‌های افزوده/تغییرکرده

افزوده‌های اصلی: `services/orchestrator/app/seo_engine/*.py`، `seo_schemas.py`، `routers/seo.py`، تست‌های `test_seo_engine.py` و `test_seo_router.py`، بخش مهاجرت SEO در `app/db.py`، نقش‌های سئو در `app/subagents.py`، نگاشت role-skill، مستندات `docs/seo-engine*.md` و گزارش‌های دوزبانه. تغییرات کاری نامرتبط موجود حفظ شده‌اند.

## ۱۵. محدودیت‌های شناخته‌شده

Agent Worker واقعی وجود ندارد؛ repair/re-audit خودکار تکمیل نشده؛ browser rendering نداریم؛ Search Console زنده نداریم؛ Rank Math اجرا نشده؛ Core Web Vitals میدانی نداریم؛ clustering فقط کیفی است؛ endpoint مستقل internal-link پیشنهادها اضافه نشده؛ routeهای SEO به وضعیت امنیت کنترل‌پلین موجود وابسته‌اند و به‌تنهایی مرز auth عمومی نیستند.

## ۱۶. موانع باقی‌مانده

۱. runtime واقعی Agent Worker → Model Gateway → Local Agent را پیاده و راستی‌آزمایی کنید.
۲. workflow fixture React+Node را با transition واقعی و evidence اجرا کنید.
۳. تست‌های مجاز rendering، Search Console و WordPress/Rank Math را اضافه کنید.
۴. پس از وجود evidence worker، quality gate سئو را به completion وصل کنید.
۵. تست Local Agent را اضافه یا ابزار تست آن را در محیط کنترل‌شده نصب کنید.

## ۱۷. پرچم‌های نهایی

```text
SEO_ENGINE_INTEGRATED = YES
REACT_NODE_SEO_READY = NO
WORDPRESS_SEO_READY = NO
READY_FOR_REAL_SEO_PROJECT = NO
```

سخت‌سازی نهایی شامل hydrate شدن سایت ذخیره‌شده پس از restart، محدودیت طول اعضای ورودی API و stream/cap کردن پاسخ HTTP راستی‌آزمایی شد. در این فاز هیچ استقرار راه دور یا push گیت انجام نشد.
### APIهای شواهد افزوده‌شده

API اکنون `GET /v1/seo/audits/{audit_id}/pages` را برای شواهد صفحه ذخیره‌شده و `GET /v1/seo/sites/{site_id}/audits/compare?baseline_id=...&current_id=...` را برای مقایسه baseline/re-audit بر اساس شواهد ارائه می‌کند. هر دو مسیر مالکیت site/snapshot را از رکوردهای SQLite موجود کنترل می‌کنند.