# AI Engineer

## Autonomous development

This repository is maintained by a bounded five-minute supervisor with checkpointed sub-agent inspection, implementation, and verification.

- Last bounded cycle checkpoint: c173cad2

This repository is maintained by a bounded, interval-configured supervisor with checkpointed sub-agent inspection, implementation, and verification.

- The latest bounded cycle is recorded as a Git checkpoint; inspect `git log -1 --oneline` for the current commit.

پلتفرم مهندسی نرم‌افزار هوشمند شخصی، Local-First و قابل اجرا روی Windows 11.

## وضعیت فعلی

- مرحله فعال: **هسته Orchestrator و حلقه خودتکمیل کنترل‌شده**
- مسیر پروژه: `F:\AI-Engineer`
- Model Gateway، Local Agent و Desktop اولیه موجود هستند.
- Orchestrator اکنون دو حالت `interactive` و `autonomous` دارد.
- وضعیت زنده‌ی سرویس‌ها و cadence supervisor از `GET /health` و `GET /capabilities` قابل مشاهده است.
- هر چرخه خودتکمیل قبل از تغییر Read و Git Checkpoint انجام می‌دهد، Validation اجرا می‌کند و نتیجه را در حافظه پروژه ثبت می‌کند.
- مخزن Git محلی در ریشه پروژه نگهداری می‌شود.
- API Key، رمزها و فایل‌های محرمانه نباید وارد Git شوند.

## هدف محصول

این سیستم در نسخه نهایی باید بتواند:

1. نیازمندی را از Prompt، Word یا PDF دریافت کند.
2. معماری، برنامه اجرای کار و کد پروژه را تولید کند.
3. فایل‌ها و Workspace پروژه را مدیریت کند.
4. فرمان‌های محدود و ثبت‌شده را در PowerShell، CMD یا محیط کنترل‌شده اجرا کند.
5. محیط پروژه را از روی فایل‌هایی مانند `package.json`، `Dockerfile` و `pyproject.toml` تشخیص دهد.
6. Build، Test، Debug، Review و Rollback انجام دهد.
7. از چند Agent تخصصی و یک Model Gateway مستقل استفاده کند.
8. حافظه دائمی پروژه، Task، تصمیم‌ها، خطاها و بازخورد کاربر داشته باشد.

## اصول پایه

- **Local-First:** داده‌ها و سرویس‌ها فعلاً روی لپ‌تاپ اجرا می‌شوند.
- **Least Privilege:** اجرای Administrator فقط با تأیید صریح کاربر.
- **Human Approval:** حذف، نصب، انتشار، تغییر تنظیمات سیستم و عملیات مخرب نیازمند تأیید است.
- **Git Checkpoint:** پیش از تغییر مهم، checkpoint ساخته می‌شود.
- **Observability:** فرمان‌ها، Taskها، خطاها، مصرف مدل و نتایج تست ثبت می‌شوند.
- **Replaceable Model Provider:** وابستگی مستقیم Agentها به API یک شرکت مجاز نیست.
- **Controlled Execution:** فرمان‌ها باید Timeout، توقف، ثبت خروجی و محدودیت دسترسی داشته باشند.

## پروفایل منابع

### Standard — سیستم فعلی

- RAM: حدود 16 GB
- CPU: Intel Core i7-8750H، شش هسته و دوازده Thread
- GPU: NVIDIA GTX 1050 با 4 GB VRAM
- سیاست اولیه: حداکثر دو Task پردازشی هم‌زمان
- Docker و سرویس‌های سنگین فقط هنگام نیاز اجرا شوند.

### Lite — سیستم احتمالی آینده

- RAM: 4 GB
- CPU: Core i3
- سیاست اولیه: یک Task هم‌زمان
- SQLite به‌جای PostgreSQL برای اجرای سبک
- Docker به‌صورت پیش‌فرض خاموش
- سرویس‌ها به‌صورت On-Demand اجرا شوند.
- مدل محلی سنگین غیرفعال باشد.

## ساختار Workspace

```text
F:\AI-Engineer\
├── apps\
│   ├── desktop\
│   ├── web-ui\
│   └── vscode-extension\
├── services\
│   ├── orchestrator\
│   ├── model-gateway\
│   ├── local-agent\
│   └── memory-service\
├── packages\
│   ├── shared-types\
│   ├── agent-sdk\
│   └── tool-sdk\
├── workspaces\
├── data\
├── logs\
├── backups\
├── models\
├── docs\
└── scripts\
```

## وضعیت ابزارهای سیستم در مرحله صفر

در بررسی اولیه این ابزارها نصب تشخیص داده شدند:

- VS Code
- Git
- Python 3.11
- Node.js و npm
- Docker Desktop
- WSL
- XAMPP

XAMPP در `D:\xampp` قرار دارد. فرمان‌های `php`، `composer` و `mysql` در PATH فعلی ویندوز تشخیص داده نشدند. در این مرحله PATH تغییر داده نمی‌شود.

## محدودیت فضای پروژه

درایو `F:` حدود 97 GB فضا دارد. بودجه اولیه پروژه **حداکثر 50 GB** در نظر گرفته می‌شود. در مراحل بعد برای `logs`، `backups`، `models` و Docker سیاست پاک‌سازی و سقف مصرف تعریف خواهد شد.

## ادامه کار

برای شروع یک چرخه خودتکمیل محدود، پس از اجرای Orchestrator یک درخواست به این endpoint ارسال می‌شود:

```http
POST /v1/agent/projects/{project_id}/self-improve
Content-Type: application/json

{"goal":"Complete the highest-value safe improvement","cycles":1}
```

وضعیت چرخه و حافظه از این مسیرها قابل مشاهده است:

```text
GET /v1/agent/autonomy/runs/{run_id}
GET /v1/agent/projects/{project_id}/memory
GET /capabilities
```

حالت خودکار فقط برای تغییرات فایلِ خوانده‌شده و پس از checkpoint فعال است؛ هر task می‌تواند `validation_command` مشخص داشته باشد تا در پایان همان پروژه اجرا شود. حذف، نصب، rollback، انتشار و تغییرات سیستم‌عامل همچنان نیازمند Policy/Approval هستند.

برای اینکه Supervisor خودش به‌صورت دوره‌ای بیدار شود، مقادیر نمونه‌ی
`services/orchestrator/.env.example` را در `.env` کپی و
`AUTONOMOUS_MODE_ENABLED=true` را فعال کنید. این حالت به‌صورت پیش‌فرض خاموش است.

ادامه توسعه شامل حافظه مستقل، Task Graph چندAgent، Cancellation/Resume و Browser Validation است. اطلاعات موردنیاز برای اتصال Provider خارجی:

- API Base URL
- روش احراز هویت و نام Header
- نمونه `curl` بدون کلید واقعی
- Endpoint فهرست مدل‌ها
- Endpoint درخواست Chat یا Completion
