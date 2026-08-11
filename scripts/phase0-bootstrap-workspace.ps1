#requires -Version 5.1
<#
.SYNOPSIS
  Creates the AI-Engineer Phase 0 workspace on Windows 11.

.DESCRIPTION
  Safe and idempotent bootstrap script for:
    F:\AI-Engineer

  Actions:
  - Verifies the target drive.
  - Creates the approved directory structure.
  - Creates README.md, .gitignore, docs\architecture.md, and docs\roadmap.md.
  - Initializes a local Git repository.
  - Does NOT install software or frameworks.
  - Does NOT require Administrator access.
  - Does NOT modify Windows settings.
  - Does NOT overwrite existing files unless -Force is explicitly supplied.

.PARAMETER ProjectDrive
  Target drive letter. Default: F

.PARAMETER Force
  Explicitly allows overwriting the four generated documentation/config files.
  Existing overwritten files are backed up under backups\phase0-file-backup-<timestamp>.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass `
    -File .\phase0-bootstrap-workspace.ps1 `
    -ProjectDrive F
#>

[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z]$')]
    [string]$ProjectDrive = 'F',

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section {
    param([Parameter(Mandatory)][string]$Title)
    Write-Host ''
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Write-Utf8FileSafely {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content,
        [Parameter(Mandatory)][string]$BackupDirectory,
        [switch]$AllowOverwrite
    )

    if (Test-Path -LiteralPath $Path) {
        if (-not $AllowOverwrite) {
            Write-Host "SKIP existing file: $Path" -ForegroundColor Yellow
            return 'skipped'
        }

        if (-not (Test-Path -LiteralPath $BackupDirectory)) {
            New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
        }

        $backupPath = Join-Path $BackupDirectory ([System.IO.Path]::GetFileName($Path))
        Copy-Item -LiteralPath $Path -Destination $backupPath -Force
        Write-Host "BACKUP: $Path -> $backupPath" -ForegroundColor DarkYellow
    }

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
    Write-Host "WRITE: $Path" -ForegroundColor Green
    return 'written'
}

$driveLetter = $ProjectDrive.ToUpperInvariant()
$driveRoot = "${driveLetter}:\"
$projectRoot = Join-Path $driveRoot 'AI-Engineer'
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDirectory = Join-Path $projectRoot "backups\phase0-file-backup-$timestamp"

Write-Section 'Preflight checks'

if (-not (Test-Path -LiteralPath $driveRoot)) {
    throw "Target drive does not exist or is not mounted: $driveRoot"
}

$drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='${driveLetter}:'" -ErrorAction Stop
$freeGB = [math]::Round(([double]$drive.FreeSpace / 1GB), 2)

if ($freeGB -lt 10) {
    throw "Insufficient free space on ${driveLetter}: drive. At least 10 GB is required for Phase 0. Available: $freeGB GB"
}

Write-Host "Target: $projectRoot"
Write-Host "Filesystem: $($drive.FileSystem)"
Write-Host "Free space: $freeGB GB"
Write-Host "Overwrite mode: $($Force.IsPresent)"

$directories = @(
    'apps',
    'apps\desktop',
    'apps\web-ui',
    'apps\vscode-extension',

    'services',
    'services\orchestrator',
    'services\model-gateway',
    'services\local-agent',
    'services\memory-service',

    'packages',
    'packages\shared-types',
    'packages\agent-sdk',
    'packages\tool-sdk',

    'workspaces',
    'data',
    'logs',
    'backups',
    'models',
    'docs',
    'scripts'
)

Write-Section 'Creating directories'

if (-not (Test-Path -LiteralPath $projectRoot)) {
    New-Item -ItemType Directory -Path $projectRoot -Force | Out-Null
    Write-Host "CREATE: $projectRoot" -ForegroundColor Green
} else {
    Write-Host "EXISTS: $projectRoot" -ForegroundColor Yellow
}

foreach ($relativePath in $directories) {
    $fullPath = Join-Path $projectRoot $relativePath

    if (-not (Test-Path -LiteralPath $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "CREATE: $fullPath" -ForegroundColor Green
    } else {
        Write-Host "EXISTS: $fullPath" -ForegroundColor DarkYellow
    }
}

$readme = @'
# AI Engineer

پلتفرم مهندسی نرم‌افزار هوشمند شخصی، Local-First و قابل اجرا روی Windows 11.

## وضعیت فعلی

- مرحله فعال: **مرحله صفر — آماده‌سازی Workspace**
- مسیر پروژه: `F:\AI-Engineer`
- هنوز هیچ Framework یا Dependency سنگینی نصب نشده است.
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

پس از تأیید مرحله صفر، مرحله یک با ساخت Model Gateway و اتصال کنترل‌شده به API آغاز می‌شود. اطلاعات موردنیاز مرحله یک:

- API Base URL
- روش احراز هویت و نام Header
- نمونه `curl` بدون کلید واقعی
- Endpoint فهرست مدل‌ها
- Endpoint درخواست Chat یا Completion
'@

$gitignore = @'
# Secrets and environment variables
.env
.env.*
!.env.example
*.pem
*.key
*.pfx
*.p12
secrets/
credentials/
**/secrets/
**/credentials/

# AI provider credentials and local configuration
data/credentials/
data/provider-config.local.*
config.local.*
*.local.json
*.local.yaml
*.local.yml

# Dependencies
node_modules/
.pnpm-store/
.yarn/
vendor/
.venv/
venv/
env/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Build artifacts
dist/
build/
out/
target/
coverage/
htmlcov/
*.tsbuildinfo

# Framework/runtime artifacts
.next/
.nuxt/
.svelte-kit/
.vite/
.tauri/
Cargo.lock

# Keep Cargo.lock for applications when Rust/Tauri is added.
# The rule above must be reviewed in Phase 4.

# Logs and runtime output
logs/*
!logs/.gitkeep
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# Local data and databases
data/*
!data/.gitkeep
*.db
*.db-shm
*.db-wal
*.sqlite
*.sqlite3
*.dump
*.sql.gz

# User workspaces
workspaces/*
!workspaces/.gitkeep

# Backups
backups/*
!backups/.gitkeep
*.bak
*.backup
*.zip
*.7z
*.tar
*.tar.gz

# Local AI models
models/*
!models/.gitkeep
*.gguf
*.safetensors
*.onnx
*.bin

# Docker local state
.docker/
docker-data/
postgres-data/
redis-data/
mysql-data/

# IDE and OS
.vscode/*
!.vscode/extensions.json
!.vscode/settings.example.json
.idea/
*.code-workspace
.DS_Store
Thumbs.db
desktop.ini

# Windows temporary files
$RECYCLE.BIN/
System Volume Information/
*.tmp
*.temp

# Test and cache output
.cache/
tmp/
temp/
playwright-report/
test-results/
.nyc_output/

# Phase 0 audit reports
phase0-system-report-*.json
phase0-system-report-*.txt
'@

$architecture = @'
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
'@

$roadmap = @'
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
'@

Write-Section 'Creating files'

$fileResults = [ordered]@{}
$fileResults['README.md'] = Write-Utf8FileSafely `
    -Path (Join-Path $projectRoot 'README.md') `
    -Content $readme `
    -BackupDirectory $backupDirectory `
    -AllowOverwrite:$Force

$fileResults['.gitignore'] = Write-Utf8FileSafely `
    -Path (Join-Path $projectRoot '.gitignore') `
    -Content $gitignore `
    -BackupDirectory $backupDirectory `
    -AllowOverwrite:$Force

$fileResults['docs\architecture.md'] = Write-Utf8FileSafely `
    -Path (Join-Path $projectRoot 'docs\architecture.md') `
    -Content $architecture `
    -BackupDirectory $backupDirectory `
    -AllowOverwrite:$Force

$fileResults['docs\roadmap.md'] = Write-Utf8FileSafely `
    -Path (Join-Path $projectRoot 'docs\roadmap.md') `
    -Content $roadmap `
    -BackupDirectory $backupDirectory `
    -AllowOverwrite:$Force

Write-Section 'Creating tracked placeholders for runtime directories'

$placeholderDirectories = @('workspaces', 'data', 'logs', 'backups', 'models')
foreach ($relativePath in $placeholderDirectories) {
    $placeholderPath = Join-Path $projectRoot "$relativePath\.gitkeep"
    if (-not (Test-Path -LiteralPath $placeholderPath)) {
        New-Item -ItemType File -Path $placeholderPath -Force | Out-Null
        Write-Host "CREATE: $placeholderPath" -ForegroundColor Green
    } else {
        Write-Host "EXISTS: $placeholderPath" -ForegroundColor DarkYellow
    }
}

Write-Section 'Initializing Git repository'

$git = Get-Command 'git' -ErrorAction SilentlyContinue
if (-not $git) {
    throw 'Git is not available in PATH. Phase 0 cannot initialize the repository.'
}

Push-Location $projectRoot
try {
    if (Test-Path -LiteralPath (Join-Path $projectRoot '.git')) {
        Write-Host 'EXISTS: Git repository already initialized.' -ForegroundColor Yellow
    } else {
        & git init --initial-branch=main
        if ($LASTEXITCODE -ne 0) {
            throw "git init failed with exit code $LASTEXITCODE"
        }
    }

    & git status --short
    if ($LASTEXITCODE -ne 0) {
        throw "git status failed with exit code $LASTEXITCODE"
    }

    $branch = (& git branch --show-current 2>$null | Out-String).Trim()
    $gitRoot = (& git rev-parse --show-toplevel 2>$null | Out-String).Trim()
}
finally {
    Pop-Location
}

Write-Section 'Validation'

$requiredDirectories = $directories | ForEach-Object { Join-Path $projectRoot $_ }
$requiredFiles = @(
    (Join-Path $projectRoot 'README.md'),
    (Join-Path $projectRoot '.gitignore'),
    (Join-Path $projectRoot 'docs\architecture.md'),
    (Join-Path $projectRoot 'docs\roadmap.md')
)

$missingDirectories = @($requiredDirectories | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Container) })
$missingFiles = @($requiredFiles | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })

if ($missingDirectories.Count -gt 0) {
    throw "Validation failed. Missing directories: $($missingDirectories -join ', ')"
}

if ($missingFiles.Count -gt 0) {
    throw "Validation failed. Missing files: $($missingFiles -join ', ')"
}

$normalizedGitRoot = [System.IO.Path]::GetFullPath(($gitRoot -replace '/', '\\')).TrimEnd('\\')
$normalizedProjectRoot = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\\')

if (-not [string]::Equals(
    $normalizedGitRoot,
    $normalizedProjectRoot,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Validation failed. Unexpected Git root: $gitRoot"
}

Write-Host ''
Write-Host 'Phase 0 workspace bootstrap completed successfully.' -ForegroundColor Green
Write-Host "Project root: $projectRoot"
Write-Host "Git branch: $branch"
Write-Host "Git root: $gitRoot"
Write-Host "Free space after bootstrap: $freeGB GB"
Write-Host ''
Write-Host 'No framework, package, service, or Windows setting was installed or changed.' -ForegroundColor Green
Write-Host ''
Write-Host 'Next manual checks:'
Write-Host "  Set-Location '$projectRoot'"
Write-Host '  Get-ChildItem -Recurse -Depth 2'
Write-Host '  git status'
