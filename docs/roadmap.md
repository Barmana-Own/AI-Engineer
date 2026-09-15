# نقشه راه AI Engineer

## قانون تکمیل هر مرحله

هر مرحله فقط زمانی کامل است که:

1. فایل‌های لازم ایجاد شده باشند.
2. Build موفق باشد.
3. اجرای واقعی انجام شده باشد.
4. تست‌های تعریف‌شده موفق باشند.
5. Log و خطا قابل مشاهده باشند.
6. مستندات به‌روزرسانی شده باشند.
7. عملیات حساس بدون تأیید اجرا نشده باشند.

---

## مرحله صفر — بررسی سیستم و آماده‌سازی Workspace

### هدف

ساخت یک پایه امن، مستند و Version-Controlled بدون نصب Framework سنگین.

### خروجی‌ها

- گزارش سخت‌افزار و ابزارهای نصب‌شده
- ساختار پوشه‌ها
- `README.md`
- `.gitignore`
- `docs/architecture.md`
- `docs/roadmap.md`
- Git Repository محلی

### معیار خروج

- مسیر `F:\AI-Engineer` وجود داشته باشد.
- تمام پوشه‌های اصلی ساخته شده باشند.
- چهار فایل اصلی قابل خواندن باشند.
- `git status` بدون خطای Repository اجرا شود.
- هیچ Framework جدیدی نصب نشده باشد.

---

## مرحله یک — Model Gateway و اتصال API

### هدف

ایجاد Interface مستقل برای Provider هوش مصنوعی.

### قابلیت‌ها

- تنظیم Base URL و Authentication
- Secret Storage محلی
- دریافت فهرست مدل‌ها
- درخواست آزمایشی مدل
- Timeout و Retry
- Fallback اولیه
- ثبت Token Usage و Latency
- عدم ذخیره API Key در Git

### معیار خروج

- Health Check موفق
- دریافت یا ثبت فهرست مدل‌ها
- یک Request آزمایشی موفق
- تست Timeout و خطای Authentication
- بررسی Git برای عدم وجود Secret

---

## مرحله دو — Local Agent برای فایل و Terminal

### هدف

ایجاد دسترسی محدود، ثبت‌شده و قابل توقف به File System و Processها.

### قابلیت‌ها

- Read، Write و Patch محدود به Workspace
- Command Allowlist و Policy
- Timeout
- Stop Process
- ثبت stdout و stderr
- جلوگیری از دسترسی خارج Workspace
- Approval Gate برای عملیات حساس

### معیار خروج

- تست خواندن و نوشتن فایل
- تست جلوگیری از Path Traversal
- تست Timeout
- تست Stop
- تست ثبت کامل فرمان

---

## مرحله سه — Orchestrator و سیستم Task

### هدف

مدیریت Workflow، State و چرخه عمر Task.

### قابلیت‌ها

- Project و Task
- Task State Machine
- Agent Invocation
- Cancellation
- Retry
- Approval Request
- Event Log

### معیار خروج

- Task از ابتدا تا پایان اجرا شود.
- توقف و ادامه Task تست شود.
- Task شکست‌خورده قابل بازیابی باشد.

---

## مرحله چهار — React UI و Tauri Desktop

### هدف

ایجاد رابط کاربری Local برای مدیریت پروژه و Agentها.

### قابلیت‌ها

- Project Dashboard
- Task View
- Diff View
- Log View
- Approval Dialog
- Settings
- Tauri Desktop Shell

### معیار خروج

- Build React موفق
- Build Tauri موفق
- اتصال UI به Orchestrator
- نمایش Live Task Status

---

## مرحله پنج — حافظه پروژه

### هدف

ذخیره پایدار Context و تاریخچه پروژه.

### قابلیت‌ها

- Requirement
- Decision
- Task
- Error
- Test Result
- Feedback
- Model Usage
- Checkpoint

### معیار خروج

- بازیابی Context پس از Restart
- Query بر اساس Project و Task
- Migration و Backup آزمایشی

---

## مرحله شش — Agentهای Coding، Review، Test و Debug

### هدف

ساخت حلقه مهندسی نرم‌افزار چندمرحله‌ای.

### قابلیت‌ها

- تولید Plan
- تولید Patch
- Review
- اجرای Test
- تحلیل Failure
- اصلاح محدود
- توقف در Loop بی‌نتیجه

### معیار خروج

- تکمیل یک پروژه نمونه کوچک
- ثبت تمام تصمیم‌ها و Patchها
- محدودیت تعداد چرخه اصلاح

---

## مرحله هفت — اتصال VS Code

### هدف

ارائه تجربه توسعه داخل Editor.

### قابلیت‌ها

- ارسال Context انتخاب‌شده
- نمایش Patch
- Apply پس از تأیید
- Diagnostic Integration
- Task Status

### معیار خروج

- نصب Extension محلی
- ارتباط موفق با Orchestrator
- اعمال یک Patch تأییدشده

---

## مرحله هشت — تشخیص و اجرای محیط توسعه

### هدف

تشخیص و اجرای کنترل‌شده پروژه‌های مختلف.

### محیط‌ها

- Docker
- Node.js
- Python
- PHP
- Laravel
- XAMPP
- MySQL
- WSL

### معیار خروج

- تشخیص صحیح پروژه‌های نمونه
- اجرای Development Server
- توقف تمیز Processها
- گزارش Port Conflict

---

## مرحله نه — مرورگر، تست رابط و حلقه اصلاح

### هدف

تست UI و اصلاح کنترل‌شده خطاهای رابط.

### قابلیت‌ها

- Browser Automation
- Screenshot
- Console Error Capture
- Network Failure Capture
- UI Test
- محدودیت Loop

### معیار خروج

- اجرای تست رابط نمونه
- ثبت Screenshot و Failure
- اصلاح یک خطای واقعی

---

## مرحله ده — امنیت کنترل‌شده و گزارش کیفیت

### هدف

اعتبارسنجی امنیتی فقط روی دارایی مجاز و محیط کنترل‌شده.

### قابلیت‌ها

- Dependency Audit
- Secret Scan
- Static Analysis
- Configuration Review
- Local Test Environment
- گزارش ریسک و اولویت

### محدودیت

تست مخرب، DDoS، ایجاد اختلال و اسکن دارایی بدون مجوز ممنوع است.

### معیار خروج

- گزارش امنیتی نمونه
- ثبت Scope و مجوز
- عدم خروج تست از محیط تعریف‌شده

---

## مرحله یازده — cPanel و Deployment

### هدف

Backup، Deploy، Update و Rollback کنترل‌شده.

### روش‌ها

- API
- SSH
- SFTP
- Git Deployment

### معیار خروج

- اتصال آزمایشی
- Backup
- Deploy به محیط تست
- Rollback موفق
- تأیید صریح پیش از Production

---

## مرحله دوازده — مدل محلی و حالت آفلاین

### هدف

اجرای Taskهای منتخب بدون API خارجی.

### قابلیت‌ها

- Local Model Adapter
- Hardware Profile
- Quantized Model
- Fallback Offline
- Context محدود

### معیار خروج

- اجرای مدل مناسب سخت‌افزار
- یک Task کدنویسی کوچک آفلاین
- اندازه‌گیری RAM، VRAM و سرعت

---

## مرحله سیزده — امکانات فریلنسری

### هدف

یافتن و رتبه‌بندی پروژه‌های مناسب بدون اقدام خودکار حساس.

### قابلیت‌ها

- بررسی منبع مجاز
- Match پروژه با مهارت‌ها
- تخمین زمان و ریسک
- تهیه Draft Proposal
- ثبت فرصت‌ها

### محدودیت

ارسال پیشنهاد، قبول پروژه، قیمت‌گذاری نهایی و تعهد قراردادی فقط با تأیید کاربر انجام می‌شود.

### معیار خروج

- جمع‌آوری فرصت نمونه
- رتبه‌بندی قابل توضیح
- Draft Proposal
- عدم ارسال خودکار
