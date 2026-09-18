# گزارش فنی AI-Engineer

| فیلد | مقدار |
|---|---|
| نوع گزارش | تحویل و ممیزی فنی مهندسی |
| زبان | فارسی |
| تاریخ میلادی | 2026-09-18 |
| تاریخ جلالی | 1405-06-27 |
| بازبینی ریویژن | `8130980` |
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
