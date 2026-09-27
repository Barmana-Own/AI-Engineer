from pathlib import Path

root = Path(r"C:\Services\AI-Engineer\current\reports")

english_customer = r'''

## Corrective Phase 4 — Deployment Safety

| Field | Value |
|---|---|
| Gregorian date | 2026-09-20 |
| Jalali date | 1405-06-29 |
| Delivery status | Prepared; deployment not performed |
| Production readiness | NO |

### Executive summary

The repository now contains an authentication boundary for the Orchestrator control plane and Model Gateway, separate owner authorization for high-risk operations, safe autonomy defaults, authenticated server health checks, and sanitized release packaging. No deployment or remote Git push was performed.

### Verified work

- Control-plane routes require `X-AI-Engine-Token` or a Bearer token when production mode is enabled.
- File, terminal, process, Git, owner-control, recovery and self-improvement route families additionally require an owner token.
- Model Gateway runtime/model routes require a separate gateway token.
- Production launcher defaults autonomous execution and automatic remote push to disabled.
- Release packaging excludes dependencies, caches, runtime data, logs, credentials and local environment files while retaining `.env.example` templates.
- IIS responses preserve FastAPI authentication errors and add baseline security headers.

### Validation summary

247 Orchestrator tests passed with 1 optional test skipped; 27 Model Gateway tests passed; 2 Local Agent tests passed. The Control Center TypeScript/build pipeline passed. Desktop build was not run because its dependencies are not installed on the server. Loopback health checks returned HTTP 200 with the expected service identities.

### Deployment blockers

The current running server instance has not been restarted with the new authentication configuration. Required machine-level control-plane, owner and gateway tokens are not configured, and the authenticated public health check therefore cannot run. The existing runtime `.env` still explicitly enables autonomy and must be reviewed before a public restart. HTTPS/IIS authenticated proxy validation remains outstanding.

### Handover

Configure protected machine environment variables, set autonomy false unless explicitly approved, restart through the deployment script, run the authenticated health check, and retain the verified backup until smoke tests pass.
'''

persian_customer = r'''

## فاز اصلاحی ۴ — ایمنی استقرار

| مورد | مقدار |
|---|---|
| تاریخ میلادی | 2026-09-20 |
| تاریخ جلالی | 1405-06-29 |
| وضعیت تحویل | آماده‌سازی انجام شد؛ استقرار انجام نشد |
| آمادگی Production | خیر |

### خلاصه اجرایی

در مخزن، مرز احراز هویت برای کنترل‌پلین Orchestrator و Model Gateway، مجوز جداگانه مالک برای عملیات پرریسک، پیش‌فرض‌های امن خودکارسازی، health check احراز هویت‌شده و بسته‌بندی پاک‌سازی‌شده اضافه شد. هیچ استقرار یا push به Git از راه دور انجام نشد.

### موارد تأییدشده

- مسیرهای کنترلی در حالت Production به `X-AI-Engine-Token` یا Bearer token نیاز دارند.
- عملیات فایل، ترمینال، پردازش، Git، کنترل مالک، بازیابی و خودبهبود علاوه بر آن به توکن مالک نیاز دارند.
- مسیرهای runtime/model در Model Gateway به توکن جداگانه نیاز دارند.
- لانچر Production اجرای خودکار و push خودکار را به‌صورت پیش‌فرض غیرفعال می‌کند.
- بسته انتشار وابستگی‌ها، cache، داده runtime، لاگ، credential و فایل‌های محیط محلی را حذف می‌کند و `.env.example` را نگه می‌دارد.
- پاسخ‌های خطای احراز هویت FastAPI در IIS حفظ و headerهای پایه امنیتی اضافه شدند.

### خلاصه اعتبارسنجی

تعداد ۲۴۷ تست Orchestrator با یک تست اختیاری skip شده، ۲۷ تست Model Gateway و ۲ تست Local Agent موفق شدند. build و TypeScript Control Center موفق بود. build Desktop اجرا نشد چون dependencyهای آن روی سرور نصب نیست. health سرویس‌های loopback با HTTP 200 و هویت صحیح پاسخ داد.

### موانع استقرار

نمونه در حال اجرای سرور هنوز با تنظیمات احراز هویت جدید restart نشده است. توکن‌های machine-level مربوط به control-plane، مالک و gateway تنظیم نشده‌اند؛ بنابراین health check عمومی احراز هویت‌شده قابل اجرا نیست. فایل runtime `.env` فعلاً اجرای خودکار را صریحاً فعال کرده و پیش از restart عمومی باید بازبینی شود. اعتبارسنجی HTTPS و proxy احراز هویت‌شده IIS باقی مانده است.

### تحویل به اپراتور

توکن‌ها را به‌صورت protected machine environment variable تنظیم کنید، مگر با تأیید صریح autonomy را خاموش نگه دارید، سرویس‌ها را با لانچر restart کنید، health check احراز هویت‌شده را اجرا کنید و تا موفقیت smoke test نسخه پشتیبان را نگه دارید.
'''

english_technical = r'''

# Corrective Phase 4 Technical Report — Deployment Safety and Release Cleanup

| Field | Value |
|---|---|
| Gregorian date | 2026-09-20 |
| Jalali date | 1405-06-29 |
| Scope | IIS exposure, control-plane authentication, gateway protection, autonomy/configuration safety, release packaging |
| Deployment performed | NO |
| Remote push performed | NO |

## Authentication boundary

`services/orchestrator/app/security.py` adds `ControlPlaneAuthMiddleware`. Health, readiness and documentation endpoints remain liveness-public. Other routes require `X-AI-Engine-Token` or `Authorization: Bearer`. High-risk route families (`/v1/developer`, `/v1/self-improvement`, `/v1/owner`, recovery run controls and agent project controls) additionally require `X-AI-Engine-Owner-Token`. Tokens are loaded through `SecretStr` settings and compared with `hmac.compare_digest`.

`services/model-gateway/app/security.py` adds `GatewayAuthMiddleware`; only liveness/documentation paths are public when `GATEWAY_AUTH_REQUIRED=true`. Orchestrator downstream requests propagate `MODEL_GATEWAY_TOKEN` only to the configured gateway URL.

## Privileged endpoint protection

The boundary is server-side and does not trust request fields such as `approved=true`. IIS remains a reverse proxy; `httpErrors existingResponse="PassThrough"` preserves 401/403 responses. The static frontend is not given privileged tokens. Production startup fails closed when required tokens are absent.

## Autonomy safety

Settings, `.env.example` and the Windows launcher default `AUTONOMOUS_MODE_ENABLED=false` and `AUTONOMOUS_AUTO_PUSH=false`. Explicit protected machine variables (`AI_ENGINE_AUTONOMOUS_MODE_ENABLED`, `AI_ENGINE_AUTONOMOUS_AUTO_PUSH`) are required to opt in. The current server `.env` is an existing opt-in runtime configuration (`AUTONOMOUS_MODE_ENABLED=true`, auto-push false) and is a pre-restart review blocker, not a source default.

## Configuration and documentation

Updated service environment examples, schema-version references (13), Electron architecture references, deployment instructions, authentication requirements, and the deployment rollback runbook. The server launcher resolves the project root from environment or script location and uses loopback service ports 8010/8011/8012.

## Release cleanup

`deploy/windows-server/package-release.ps1` creates a sanitized ZIP without `.git`, virtual environments, `node_modules`, caches, logs, runtime data, workspaces, backups, database copies, credentials, private keys or local `.env` files. Safe `.env.example` templates are retained. A server packaging smoke run produced a 6,781,876-byte archive; forbidden-entry scan returned no matches and four safe `.env.example` files were present.

## Deployment health checks

The health script validates service identity/status for Ollama, Gateway, Local Agent and Orchestrator, Control Center reachability, authenticated gateway/orchestrator proxy paths and optional model chat. With no configured tokens it fails closed with a required-token error. Live loopback checks passed: all three services returned HTTP 200 and expected identities. The current public proxy returned HTTP 200 for the existing unauthenticated gateway route because the running processes have not been restarted with the new boundary; this is an explicit release blocker.

## Rollback plan

Run the complete test/build gate, create and checksum a timestamped backup, configure protected tokens, restart, run authenticated health and smoke checks, and retain the backup. On failure stop the new instance, restore the verified checkout/data backup, restart the previous version and rerun health checks. No irreversible deployment was performed.

## Exact validation results

| Check | Result |
|---|---|
| Orchestrator full unittest discovery | PASS — 247 passed, 1 skipped, 0 failed |
| Orchestrator deployment security tests | PASS — 4 passed |
| Model Gateway full pytest suite | PASS — 27 passed, 0 failed |
| Model Gateway security test | PASS — 1 passed |
| Local Agent unittest discovery | PASS — 2 passed, 0 failed |
| SEO/company integration subset | PASS — 33 passed, 0 failed (included in Orchestrator total) |
| Python compileall | PASS |
| `git diff --check` | PASS (line-ending warnings only) |
| Control Center `npm run build` | PASS (tsc + Vite) |
| Desktop build/typecheck | NOT_RUN — dependencies absent |
| Sanitized package smoke test | PASS — 6,781,876 bytes; no forbidden entries |
| Loopback health identity checks | PASS — Gateway, Local Agent, Orchestrator HTTP 200 |
| Authenticated public health check | NOT_RUN — required machine tokens absent |

## Remaining server blockers

`READY_FOR_DEPLOYMENT = NO`. Exact blockers: (1) configure protected machine control-plane, owner and gateway tokens; (2) restart services so the new middleware is active; (3) change/review the existing runtime autonomy opt-in before public restart; (4) configure and verify HTTPS/IIS authenticated proxy behavior; (5) install Desktop dependencies if a Desktop build is a release requirement; (6) rerun authenticated health and smoke checks after restart.
'''

persian_technical = r'''

# گزارش فنی فاز اصلاحی ۴ — ایمنی استقرار و پاک‌سازی Release

| مورد | مقدار |
|---|---|
| تاریخ میلادی | 2026-09-20 |
| تاریخ جلالی | 1405-06-29 |
| دامنه | exposure در IIS، احراز هویت control-plane، حفاظت gateway، ایمنی autonomy/config، بسته‌بندی release |
| استقرار | انجام نشد |
| push از راه دور | انجام نشد |

## مرز احراز هویت

فایل `services/orchestrator/app/security.py`، `ControlPlaneAuthMiddleware` را اضافه می‌کند. health، readiness و مستندات برای liveness عمومی باقی می‌مانند و سایر مسیرها به `X-AI-Engine-Token` یا `Authorization: Bearer` نیاز دارند. خانواده مسیرهای پرریسک (`/v1/developer`، `/v1/self-improvement`، `/v1/owner`، کنترل recovery و کنترل پروژه agent) علاوه بر آن به `X-AI-Engine-Owner-Token` نیاز دارند. توکن‌ها با `SecretStr` بارگذاری و با `hmac.compare_digest` مقایسه می‌شوند.

فایل `services/model-gateway/app/security.py`، `GatewayAuthMiddleware` را اضافه می‌کند؛ در حالت `GATEWAY_AUTH_REQUIRED=true` فقط مسیرهای liveness و مستندات عمومی هستند. درخواست‌های داخلی Orchestrator فقط به URL gateway تنظیم‌شده، `MODEL_GATEWAY_TOKEN` را منتقل می‌کنند.

## حفاظت مسیرهای privileged

مرز احراز هویت در سمت سرور است و به فیلدهایی مانند `approved=true` اعتماد نمی‌کند. IIS صرفاً reverse proxy است و `httpErrors existingResponse="PassThrough"` پاسخ‌های 401/403 را حفظ می‌کند. توکن privileged در frontend استاتیک قرار نمی‌گیرد. startup در نبود توکن‌های لازم fail-closed می‌شود.

## ایمنی autonomy

Settings، فایل‌های `.env.example` و لانچر Windows، `AUTONOMOUS_MODE_ENABLED=false` و `AUTONOMOUS_AUTO_PUSH=false` را به‌عنوان پیش‌فرض دارند. فعال‌سازی فقط با متغیرهای machine محافظت‌شده `AI_ENGINE_AUTONOMOUS_MODE_ENABLED` و `AI_ENGINE_AUTONOMOUS_AUTO_PUSH` انجام می‌شود. فایل `.env` فعلی سرور یک تنظیم runtime موجود و opt-in است (`AUTONOMOUS_MODE_ENABLED=true` و auto-push=false) و پیش از restart، blocker بررسی است نه پیش‌فرض source.

## پیکربندی و مستندات

نمونه‌های محیط سرویس، مرجع schema version (13)، معماری Electron، الزامات احراز هویت، دستورهای deployment و runbook rollback به‌روزرسانی شدند. لانچر ریشه پروژه را از محیط یا مسیر اسکریپت پیدا می‌کند و پورت‌های loopback برابر 8010/8011/8012 هستند.

## پاک‌سازی release

`deploy/windows-server/package-release.ps1` یک ZIP پاک‌سازی‌شده می‌سازد و `.git`، virtual environment، `node_modules`، cache، لاگ، داده runtime، workspace، backup، کپی پایگاه‌داده، credential، private key و فایل‌های `.env` محلی را حذف می‌کند. templateهای امن `.env.example` نگه داشته می‌شوند. اجرای smoke روی سرور archive با اندازه ۶٬۷۸۱٬۸۷۶ بایت ساخت؛ اسکن موارد ممنوع نتیجه‌ای نداشت و چهار `.env.example` امن وجود داشت.

## health check استقرار

اسکریپت health هویت و status مربوط به Ollama، Gateway، Local Agent و Orchestrator، دسترسی Control Center، مسیرهای proxy احراز هویت‌شده و در صورت درخواست chat مدل را بررسی می‌کند. در نبود توکن با خطای required-token متوقف می‌شود. بررسی loopback موفق بود: هر سه سرویس HTTP 200 و هویت صحیح داشتند. proxy عمومی فعلی برای مسیر gateway بدون احراز هویت HTTP 200 برگرداند، چون پردازش‌های در حال اجرا هنوز با middleware جدید restart نشده‌اند؛ این یک blocker صریح release است.

## برنامه rollback

ابتدا gate کامل تست/build، سپس backup timestamped و checksum، تنظیم توکن‌های محافظت‌شده، restart، health و smoke احراز هویت‌شده اجرا شود. در شکست، نمونه جدید متوقف، backup تأییدشده checkout/data بازیابی، نسخه قبلی restart و health دوباره اجرا شود. هیچ deployment برگشت‌ناپذیری انجام نشد.

## نتایج دقیق اعتبارسنجی

| بررسی | نتیجه |
|---|---|
| unittest کامل Orchestrator | PASS — ۲۴۷ موفق، ۱ skip، صفر شکست |
| تست امنیت deployment در Orchestrator | PASS — ۴ موفق |
| pytest کامل Model Gateway | PASS — ۲۷ موفق، صفر شکست |
| تست امنیت Model Gateway | PASS — ۱ موفق |
| unittest کامل Local Agent | PASS — ۲ موفق، صفر شکست |
| زیرمجموعه SEO/company integration | PASS — ۳۳ موفق، صفر شکست (در مجموع Orchestrator محاسبه شده) |
| Python compileall | PASS |
| `git diff --check` | PASS (فقط هشدار line ending) |
| `npm run build` در Control Center | PASS (tsc و Vite) |
| build/typecheck Desktop | NOT_RUN — dependency نصب نیست |
| smoke بسته sanitized | PASS — ۶٬۷۸۱٬۸۷۶ بایت و بدون مورد ممنوع |
| health هویت loopback | PASS — هر سه سرویس HTTP 200 |
| health عمومی احراز هویت‌شده | NOT_RUN — توکن machine وجود ندارد |

## موانع باقی‌مانده سرور

`READY_FOR_DEPLOYMENT = NO`. موانع دقیق: (۱) تنظیم توکن‌های machine برای control-plane، مالک و gateway؛ (۲) restart سرویس‌ها برای فعال شدن middleware؛ (۳) تغییر یا بازبینی autonomy فعلی قبل از restart عمومی؛ (۴) تنظیم و تأیید HTTPS و proxy احراز هویت‌شده IIS؛ (۵) نصب dependencyهای Desktop اگر build آن جزو release است؛ (۶) اجرای مجدد health و smoke احراز هویت‌شده پس از restart.
'''

roadmap = r'''

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

**Risks:** current live instance exposure, an existing autonomy opt-in in `.env`, and no operator-authentication channel in the static frontend.

**Priority order:** P0 configure tokens and restart; P0 verify HTTPS and proxy; P1 run authenticated smoke checks; P1 obtain an owner decision on autonomy; P2 install and build Desktop.

**Production readiness:** NO.

**Management summary:** source and release packaging are ready for the final gate, but the public server must not be exposed until secure configuration and a controlled restart are completed.
'''

updates = {
    "customer-report.en.md": english_customer,
    "customer-report.fa.md": persian_customer,
    "technical-report.en.md": english_technical,
    "technical-report.fa.md": persian_technical,
    "project-status-roadmap.md": roadmap,
}

for name, addition in updates.items():
    path = root / name
    path.write_text(path.read_text(encoding="utf-8").rstrip() + addition + "\n", encoding="utf-8", newline="")

print("updated Phase 4 report files")
