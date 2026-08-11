# AI Engineer Model Gateway v0.2.1

Model Gateway محلی برای ارتباط کنترل‌شده Agentها با Barmana API.

## قابلیت‌های فعلی

- FastAPI روی `127.0.0.1:8010`
- دریافت ۱۱۶ مدل از `/models`
- Chat Completion محلی در `/v1/chat/completions`
- Provider Endpoint در `/chat/completions`
- مدل پیش‌فرض `mistral-small-latest`
- Fallback خودکار در Timeout، Rate Limit، خطای موقت و خطای `No such model`
- Timeout، Retry و Backoff
- ثبت مدل انتخاب‌شده و مدل‌های امتحان‌شده
- ثبت Token Usage، Latency، Agent، Task و Project در SQLite
- Cache فهرست مدل‌ها
- Health Check و Swagger
- عدم ذخیره API Key در سورس، Cache، SQLite یا Git

## مسیرهای محلی

```text
GET  /health
GET  /health/ready
GET  /v1/models
POST /v1/chat/completions
GET  /v1/usage/summary
GET  /docs
```

## دیتابیس مصرف

```text
F:\AI-Engineer\data\model-gateway\usage.sqlite3
```

این دیتابیس شامل API Key یا متن کامل Prompt و Response نیست. فقط Metadata، مدل، Token، زمان و نتیجه درخواست ثبت می‌شود.

## نصب یا به‌روزرسانی

```powershell
Set-Location "F:\AI-Engineer\services\model-gateway"

powershell -NoProfile -ExecutionPolicy Bypass `
  -File ".\scripts\setup.ps1"
```

## اجرا

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File ".\scripts\start.ps1"
```

API Key به‌صورت مخفی دریافت می‌شود و فقط در Process جاری باقی می‌ماند.

## تست واقعی

در PowerShell دوم:

```powershell
Set-Location "F:\AI-Engineer\services\model-gateway"

powershell -NoProfile -ExecutionPolicy Bypass `
  -File ".\scripts\smoke-test.ps1"
```

## نمونه درخواست محلی

```json
{
  "model": "auto",
  "messages": [
    {
      "role": "user",
      "content": "Reply only with OK"
    }
  ],
  "temperature": 0,
  "max_tokens": 16,
  "project_id": "example-project",
  "task_id": "task-1",
  "agent_id": "coding-agent"
}
```

## محدودیت این نسخه

- Streaming هنوز فعال نیست.
- Context Trimming پیشرفته در بخش بعدی اضافه می‌شود.
- کیفیت مدل‌ها هنوز فقط از روی موفقیت، خطا و Latency ارزیابی می‌شود.


## اصلاح v0.2.1

Provider در یک تست، مدل `auto` را به شناسه‌ای نامعتبر در Cloudflare نگاشت کرد و خطای
`No such model` برگرداند. این نسخه:

- مدل `mistral-small-latest` را پیش‌فرض می‌کند.
- خطای `No such model` را قابل Fallback تشخیص می‌دهد.
- سپس `mistral-medium-latest`، `auto` و `codestral-latest` را به‌ترتیب امتحان می‌کند.
