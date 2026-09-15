# AI Engineer Provider Router

این پوشه یک Snapshot کامل و محلی از FreeLLMAPI است که داخل پروژه AI Engineer
نگهداری می‌شود.

## استقلال سورس

فایل اصلی نسخه دانلودشده در این مسیر نگهداری می‌شود:

```text
F:\AI-Engineer\vendor\freellmapi\v0.6.6\
```

سورس کامل اجراشونده در این مسیر است:

```text
F:\AI-Engineer\services\provider-router\
```

پس از نصب موفق، اجرای عادی برنامه Source را از GitHub دانلود نمی‌کند.

## چیزی که محلی شده

- تمام Source Code
- Provider Adapterها
- Router و Fallback Engine
- Dashboard
- Static Model Catalog همراه نسخه
- package-lock.json
- Dependencies نصب‌شده در node_modules
- LICENSE اصلی
- SHA256 آرشیو اصلی
- SQLite و تنظیمات محلی AI Engineer

## چیزی که قابل کپی‌کردن نیست

خود سرورهای Google، Groq، Mistral، OpenRouter، Cloudflare و سایر Providerها
روی اینترنت قرار دارند. کلید، سهمیه رایگان و دسترسی آن‌ها باید متعلق به حساب
خود کاربر باشد و ممکن است توسط خود Provider تغییر کند.

برای استقلال واقعی از اینترنت، در مرحله مدل محلی باید Ollama یا LM Studio و
یک مدل مناسب سخت‌افزار اضافه شود.

## اجرا

```powershell
Set-Location "F:\AI-Engineer\services\provider-router"

powershell -NoProfile -ExecutionPolicy Bypass `
  -File ".\ai-engineer\start.ps1"
```

در حالت Development:

- Dashboard: `http://127.0.0.1:5173`
- API Server: `http://127.0.0.1:8020`

## داده

```text
F:\AI-Engineer\data\provider-router\freellmapi.db
```

فایل `.env` و دیتابیس نباید وارد Git شوند.