# معماری اولیه AI Engineer

## 1. دامنه سند

این سند معماری سطح‌بالای پلتفرم را در ابتدای پروژه ثبت می‌کند. جزئیات فنی هر سرویس در مرحله مربوط به آن تکمیل می‌شود.

## 2. اهداف معماری

- اجرای Local-First روی Windows 11
- جداسازی رابط کاربری، Orchestration، Model Gateway و ابزارهای سیستمی
- جلوگیری از دسترسی مستقیم مدل هوش مصنوعی به سیستم‌عامل
- ثبت کامل Task، فرمان، تصمیم، خطا، تست و مصرف مدل
- قابلیت اجرای سبک روی سیستم کم‌منبع
- قابلیت جایگزینی Provider هوش مصنوعی
- امکان انتقال تدریجی از SQLite به PostgreSQL
- آمادگی برای Docker، VS Code، cPanel و مدل محلی در آینده

## 3. اجزای اصلی

### 3.1 Desktop Application

مسیر آینده:

```text
apps/desktop
```

فناوری هدف:

- Tauri
- Rust
- React
- TypeScript

مسئولیت‌ها:

- Window Management
- System Tray
- ارتباط کنترل‌شده با سرویس‌های Local
- نمایش درخواست‌های تأیید کاربر
- نگهداری امن تنظیمات محلی غیرمحرمانه

### 3.2 Web UI

مسیر آینده:

```text
apps/web-ui
```

مسئولیت‌ها:

- نمایش پروژه‌ها و Taskها
- نمایش Plan و وضعیت Agentها
- Terminal Output به‌صورت Read-Only یا کنترل‌شده
- نمایش Diff فایل‌ها
- تأیید یا رد عملیات حساس
- مشاهده Log، Test Result و Model Usage

### 3.3 VS Code Extension

مسیر آینده:

```text
apps/vscode-extension
```

مسئولیت‌ها:

- دریافت Context محدود از Workspace باز
- نمایش پیشنهاد تغییرات
- اعمال Patch فقط پس از تأیید
- ارسال Selection، فایل یا Diagnostic به Orchestrator
- نمایش وضعیت Task در VS Code

افزونه نباید API Key اصلی را نگهداری کند.

### 3.4 Orchestrator

مسیر آینده:

```text
services/orchestrator
```

فناوری هدف:

- Python
- FastAPI

مسئولیت‌ها:

- دریافت درخواست کاربر
- ساخت Task Graph
- اجرای Agent Workflow
- مدیریت State
- درخواست تأیید عملیات حساس
- توقف، ادامه و لغو Task
- ثبت checkpoint و نتیجه
- اجرای چرخه‌ی خودتکمیلِ محدود و قابل بازیابی
- انتخاب بهبود بعدی بر اساس وضعیت واقعی Workspace و حافظه‌ی پروژه
- جداکردن حالت `interactive` از حالت `autonomous`

### 3.5 Model Gateway

مسیر آینده:

```text
services/model-gateway
```

مسئولیت‌ها:

- نگهداری امن Provider Configuration
- دریافت و Cache فهرست مدل‌ها
- انتخاب مدل متناسب با Task
- Timeout، Retry، Backoff و Rate Limit
- Fallback بین مدل‌ها
- ثبت Token Usage، Latency، Error و Quality Signal
- مدیریت Context و جلوگیری از ارسال بی‌دلیل کل پروژه
- ارائه Interface ثابت به Agentها

هیچ Agentی نباید مستقیماً به API خارجی متصل شود.

### 3.6 Local Agent

مسیر آینده:

```text
services/local-agent
```

مسئولیت‌ها:

- File Read
- File Write با Policy
- Directory Listing
- Search
- Patch Application
- Process Execution
- Process Stop
- Timeout Enforcement
- Environment Detection
- Tool Detection
- Git Operations
- Workspace Isolation

Local Agent مرز اصلی اعتماد با سیستم‌عامل است.

### 3.7 Memory Service

مسیر آینده:

```text
services/memory-service
```

داده‌های هدف:

- Project
- Requirement
- Task
- Architectural Decision
- User Feedback
- File Snapshot Metadata
- Error
- Test Result
- Model Request Metadata
- Model Response Metadata
- Token Usage
- Approval
- Git Checkpoint

در MVP، ذخیره‌سازی حافظه داخل SQLite Orchestrator انجام می‌شود تا سیستم بدون
سرویس سنگین قابل اجرا باشد. قرارداد آن طوری طراحی شده است که بعداً به
`services/memory-service` یا PostgreSQL منتقل شود.

حافظه‌ی عملیاتی سه نوع داده را نگه می‌دارد:

1. **Episodic Memory** — نتیجه‌ی هر Task، فایل‌های تغییرکرده، فرمان‌های اعتبارسنجی و خطاها.
2. **Project Context** — واقعیت‌های کشف‌شده درباره‌ی Stack، ساختار و قراردادهای پروژه.
3. **Failure Memory** — خطاهایی که نباید در چرخه‌ی بعدی تکرار شوند.

### 3.8 Shared Packages

```text
packages/shared-types
packages/agent-sdk
packages/tool-sdk
```

کاربرد:

- Type Contract مشترک
- Schemaهای Versioned
- تعریف Agent Interface
- تعریف Tool Interface
- جلوگیری از Coupling بین سرویس‌ها

## 4. Agentهای هدف

- Requirement Agent
- Architect Agent
- Planner Agent
- Coding Agent
- Review Agent
- Test Agent
- Debug Agent
- Security Validation Agent
- Deployment Agent

Agentها باید Stateless یا Recoverable طراحی شوند. State معتبر باید در Orchestrator و Memory Service ثبت شود.

## 5. جریان اصلی داده

```text
User
  ↓
React / Tauri / VS Code
  ↓
Orchestrator
  ├── Memory Service
  ├── Model Gateway ── External or Local Models
  └── Local Agent ── Files / Git / Terminal / Docker / XAMPP
```

مدل هوش مصنوعی هیچ‌گاه مستقیماً به File System، Terminal یا API Key دسترسی ندارد.

## 5.1 حلقه‌ی خودتکمیل و یادگیری

```text
Autonomy Supervisor
  ↓
Observe Workspace + Git + Tests
  ↓
Retrieve Project Memory
  ↓
Model selects one bounded improvement
  ↓
Read target → Checkpoint → Patch
  ↓
Validate / Diagnose / Repair once
  ↓
Persist outcome and failure memory
  ↺ next bounded cycle
```

این حلقه به معنی تغییر آزاد و بی‌نهایت نیست. هر چرخه:

- فقط یک بهبود منسجم را دنبال می‌کند؛
- فقط فایل‌هایی را تغییر می‌دهد که همان چرخه واقعاً خوانده شده‌اند؛
- پیش از Mutation checkpoint می‌سازد؛
- حذف، نصب Dependency، Rollback، انتشار و تغییر سیستم‌عامل را خودکار نمی‌کند؛
- سقف چرخه و سقف Step دارد و با شکست غیرقابل‌حل متوقف می‌شود؛
- نتیجه و خطا را برای چرخه‌های بعدی در حافظه ثبت می‌کند.

حالت‌های اجرا:

| حالت | رفتار |
| --- | --- |
| `interactive` | تغییرات حساس در صف تأیید کاربر قرار می‌گیرند. |
| `autonomous` | فقط Mutation فایل پس از Read و Checkpoint خودکار تأیید می‌شود؛ Terminal و عملیات حساس همچنان Policy دارند. |

شروع چرخه از API زیر انجام می‌شود و می‌تواند برای چند چرخه‌ی محدود در پس‌زمینه
ادامه پیدا کند:

```text
POST /v1/agent/projects/{project_id}/self-improve
GET  /v1/agent/autonomy/runs/{run_id}
GET  /v1/agent/projects/{project_id}/memory
```

برای بیدارشدن خودکار Supervisor، گزینه‌های `AUTONOMOUS_MODE_ENABLED`،
`AUTONOMOUS_INTERVAL_MINUTES` و `AUTONOMOUS_CYCLES_PER_RUN` در فایل
`services/orchestrator/.env` فعال می‌شوند. این گزینه به‌صورت پیش‌فرض خاموش است
تا اجرای خودکار ناخواسته روی Workspace اتفاق نیفتد.

## 6. مدل امنیتی اولیه

### عملیات کم‌خطر

- خواندن فایل داخل Workspace مجاز
- فهرست‌کردن پوشه‌های مجاز
- اجرای تست‌های Read-Only
- بررسی نسخه ابزارها
- مشاهده Git Status

### عملیات نیازمند Policy و ثبت

- نوشتن یا اصلاح فایل
- اجرای Build
- اجرای Development Server
- ایجاد Branch یا Commit
- نصب Dependency داخل پروژه

### عملیات نیازمند تأیید صریح کاربر

- حذف فایل یا پوشه
- نصب نرم‌افزار سیستم
- اجرای Administrator
- تغییر Registry یا تنظیمات Windows
- حذف Database
- Reset یا Clean مخرب Git
- انتشار Production
- اتصال SSH یا cPanel
- اجرای تست امنیتی فعال

## 7. اجرای فرمان

هر فرمان باید شامل این Metadata باشد:

- `commandId`
- `taskId`
- `projectId`
- `workingDirectory`
- `shell`
- `arguments`
- `timeoutSeconds`
- `requestedBy`
- `approvalState`
- `startedAt`
- `finishedAt`
- `exitCode`
- `stdoutPath`
- `stderrPath`

فرمان Shell به‌صورت String آزاد و بدون Policy نباید اجرا شود.

## 8. تشخیص محیط پروژه

اولویت اولیه:

1. `docker-compose.yml`، `compose.yml` یا `Dockerfile` → Docker
2. `package.json` → Node.js
3. `composer.json` → PHP یا Laravel
4. `requirements.txt` یا `pyproject.toml` → Python
5. فایل‌های PHP ساده → XAMPP یا Docker
6. در نبود سیگنال کافی → درخواست تصمیم از کاربر

تشخیص Environment فقط پیشنهاد می‌دهد و عملیات حساس را خودکار تأیید نمی‌کند.

## 9. داده و پایگاه داده

### MVP سبک

- SQLite
- مناسب برای سیستم 4 GB
- یک Process Writer اصلی

### حالت استاندارد

- PostgreSQL
- Migration Versioned
- Backup محلی
- قابلیت انتقال از SQLite

Redis و Queue در مرحله بعد از تثبیت Task Model اضافه می‌شوند.

## 10. Git و Rollback

پیش از تغییر مهم:

1. بررسی Working Tree
2. ثبت Diff موجود
3. ساخت checkpoint
4. اجرای تغییر
5. Build و Test
6. در صورت شکست، ارائه Rollback Plan

فرمان‌های مخرب مانند `git reset --hard` بدون تأیید صریح ممنوع‌اند.

## 11. پروفایل اجرا

### Standard

- دو Task هم‌زمان
- PostgreSQL مجاز
- Docker On-Demand
- سرویس‌های غیرفعال به‌صورت Lazy Start

### Lite

- یک Task هم‌زمان
- SQLite
- Docker غیرفعال به‌صورت پیش‌فرض
- Log Retention کوتاه‌تر
- Context کوچک‌تر
- مدل محلی سنگین غیرفعال

## 12. تصمیم‌های باز

این موارد در مراحل بعد نهایی می‌شوند:

- پروتکل ارتباط بین سرویس‌ها
- روش نگهداری Secret در Windows
- ساختار دقیق Task Graph
- Schema حافظه
- سیاست Model Routing
- Isolation سطح Process یا Container
- روش Streaming خروجی Terminal
- روش Patch و Conflict Resolution
