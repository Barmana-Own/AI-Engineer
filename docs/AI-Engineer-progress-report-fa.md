# گزارش پیشرفت پروژه AI Engineer

**تاریخ گزارش:** ۱۶ اوت ۲۰۲۶  
**مسیر پروژه:** F:\AI-Engineer

## خلاصهٔ اجرایی

AI Engineer از یک مجموعه سرویس اولیه به یک سکوی محلی برای توسعهٔ خودکار نرم‌افزار تبدیل شده است. اکنون هستهٔ آن می‌تواند:

- هدف بعدی را از backlog انتخاب کند؛
- برای هر بخش، specialist/domain agent و نقش‌های planner، implementer و verifier را مدیریت کند؛
- تحلیل‌های خواندنی را محدود و موازی اجرا کند؛
- فقط یک writer را هم‌زمان وارد workspace کند؛
- قبل از تغییر checkpoint و backup داشته باشد؛
- تغییرات، validation، handoff و memory را در SQLite ثبت کند؛
- در صورت نبودن تغییر معتبر، verifier تکراری را حذف و سریعاً سراغ هدف بعدی برود؛
- با Ollama کاملاً محلی و بدون اینترنت به کار ادامه دهد.

هستهٔ خودتوسعه اکنون فعال و پایدار است؛ اما محصول هنوز در مرحلهٔ تکمیل قابلیت‌ها و نزدیک‌شدن به تجربهٔ Codex است، نه یک محصول نهایی هم‌سطح Codex.

## مسیر پیشرفت از صفر تا امروز

### مرحلهٔ ۱ — اسکلت چندسرویسی

ساختار اولیه به چند مرز مستقل تقسیم شد:

1. **Orchestrator:** تصمیم‌گیری، task، پروژه، memory و چرخهٔ خودتوسعه.
2. **Model Gateway:** مرز یکپارچهٔ مدل‌ها و fallback.
3. **Local Agent:** اجرای محدود فایل، ترمینال، Git و process در workspace مجاز.
4. **Control Center:** رابط وب برای پروژه، chat و activity.
5. **Desktop:** پوستهٔ دسکتاپ برای تبدیل رابط وب به برنامهٔ محلی.
6. **Provider Router:** proxy سازگار با OpenAI/Responses برای providerهای اختیاری.

### مرحلهٔ ۲ — ایمنی اجرای کد

پیش از اجازه‌دادن به خودتوسعه، مرزهای ایمنی اضافه شد:

- target باید ابتدا خوانده و در محدودهٔ workspace تأیید شود؛
- مسیرهای خارج از workspace یا مسیرهای مبهم رد می‌شوند؛
- قبل از mutation، checkpoint و snapshot گرفته می‌شود؛
- writer فقط ابزار و مسیرهای مجاز را دارد؛
- diff و validation پس از تغییر اجباری است؛
- secret و API key در handoff و runtime endpoint نمایش داده نمی‌شود؛
- خطا، timeout و restart با statusهای پایدار reconcile می‌شوند.

### مرحلهٔ ۳ — چرخهٔ self-development

چرخهٔ autonomous به‌جای یک prompt آزاد، یک قرارداد backlog دارد:

BACKLOG_KEY، SECTION، TARGET FILE و VALIDATION COMMAND

سپس Orchestrator یک run و taskهای معمولی می‌سازد. این طراحی باعث می‌شود همان policyهای task عادی برای خودتوسعه نیز اعمال شوند و سیستم به مسیرهای کنترل‌نشده تبدیل نشود.

### مرحلهٔ ۴ — معماری subagent و Supervisor Manager

رجیستری subagentها از نقش‌های عمومی و specialistهای محصول تشکیل شده است:

- **Supervisor/Monitor:** مدیر deterministic؛ lease، reconcile، duplicate prevention و barrier را کنترل می‌کند.
- **Planner:** قرارداد، ترتیب کار و validation را مشخص می‌کند.
- **Implementer:** تنها writer اصلی برای mutation.
- **Verifier:** نتیجه و validation را فقط وقتی لازم باشد بررسی می‌کند.
- **Specialistهای دامنه:** orchestrator، gateway، local-agent، UI، desktop، tests، security، docs و integration.
- **Handoff/Memory:** خروجی typed و bounded بین مراحل جابه‌جا و در SQLite ذخیره می‌شود.

### مرحلهٔ ۵ — افزایش سرعت

برای رفع گلوگاه بررسی‌های تکراری، این تغییرها اعمال شد:

- فاصلهٔ بیدارشدن Supervisor داخلی از ۳ دقیقه به ۱ دقیقه کاهش یافت؛
- workerهای پیش‌فرض از پنج نقش عمومی به planner → implementer → verifier + specialist دامنه کاهش یافتند؛
- سقف subagentهای هر run به ۴ رسید؛
- readerها حداکثر ۲ نقش موازی دارند؛ writerها همیشه تک‌به‌تک اجرا می‌شوند؛
- اگر writer هیچ mutation معتبر نداشته باشد، verifierهای بعدی ساخته نمی‌شوند؛
- در هر cycle فقط یک snapshot محدود از memory خوانده و بین نقش‌ها به اشتراک گذاشته می‌شود؛
- heartbeat پنج‌دقیقه‌ای دیگر full test و full health را در هر بیدارشدن تکرار نمی‌کند؛ validation هدفمند بعد از تغییر و full suite در milestone اجرا می‌شود.

## معماری فعلی

Supervisor Manager
  ├─ Backlog Selector
  ├─ Planner / Domain Specialist  ─┐
  ├─ Single Writer: Implementer    ├─ handoff + memory ── SQLite
  └─ Verifier فقط پس از mutation ──┘

Orchestrator :8012
  ├─ Model Gateway :8010 ── Ollama محلی
  ├─ Local Agent :8011
  ├─ Provider Router :8020 (اختیاری)
  └─ Control Center :5175 ── Desktop Shell

## اجزای اجرایی و پورت‌ها

| جزء | پورت/مسیر | وظیفه |
|---|---:|---|
| Orchestrator | 8012 | API پروژه، task، autonomy run، memory، handoff و scheduler |
| Model Gateway | 8010 | chat سازگار با OpenAI، انتخاب مدل، retry، fallback و usage |
| Local Agent | 8011 | فایل، terminal، Git و process با policy محلی |
| Provider Router | 8020 | proxy اختیاری FreeLLMAPI/OpenAI-compatible و endpoint پاسخ |
| Control Center | 5175 | رابط وب کنترل پروژه و activity |
| Desktop | local Electron/Vite | پوستهٔ برنامهٔ دسکتاپ |
| Ollama | 11434 | اجرای مدل محلی بدون API پولی |

## با چه AI و APIهایی توسعه می‌دهیم؟

### مسیر اصلی و رایگان

- **Ollama محلی** موتور اصلی است.
- مدل autonomous فعلی: qwen2.5-coder:1.5b.
- مدل پیش‌فرض interactive در تنظیمات: qwen2.5-coder:3b؛ موجودبودن هر مدل به catalog نصب‌شدهٔ Ollama بستگی دارد.
- Model Gateway به‌صورت Barmana-compatible با Ollama صحبت می‌کند.
- برای چرخهٔ خودتوسعه، همین مسیر محلی انتخاب می‌شود تا قطع اینترنت مانع ادامهٔ کار نشود.

### مسیرهای اختیاری

- Provider Router یک proxy سازگار با OpenAI Chat Completions و Codex-compatible Responses دارد.
- gateway می‌تواند provider profileهای OpenAI-compatible را از environment بخواند؛ فقط وقتی key و health probe معتبر باشند.
- fallbackها و providerهای بیرونی اختیاری‌اند و برای اجرای پایهٔ پروژه لازم نیستند.
- APIهای repoهای معرفی‌شدهٔ GitHub به‌عنوان منبع معماری و ایده بررسی شدند، اما برای اجرای اصلی به API پولی یا credential ناشناخته وابسته نشده‌ایم.

### اینترنت قطع شود چه می‌شود؟

- توسعه، task، memory، validation محلی و اجرای Ollama ادامه پیدا می‌کند.
- provider بیرونی، دریافت package و push به GitHub به اینترنت نیاز دارد.
- سیستم در صورت خطای provider بیرونی روی مسیر local Ollama می‌ماند و چرخه را متوقف نمی‌کند.

## چرخهٔ واقعی توسعه

1. **انتخاب هدف:** backlog هدفی را که اخیراً موفق یا تغییر داده نشده انتخاب می‌کند.
2. **ساخت قرارداد:** section، فایل هدف و دستور validation به run اضافه می‌شود.
3. **بازرسی خواندنی:** specialist و planner در یک snapshot مشترک، حداکثر دو تا هم‌زمان.
4. **برنامه‌ریزی:** handoffهای قبلی و memory محدود به writer داده می‌شود.
5. **Mutation:** فقط implementer با writer lock و checkpoint مجاز تغییر می‌دهد.
6. **تصمیم validation:** اگر تغییر واقعی رخ داده باشد verifier اجرا می‌شود؛ اگر نه، مرحلهٔ تکراری حذف می‌شود.
7. **ثبت نتیجه:** changed files، validations، blockers، confidence و next action در handoff ذخیره می‌شود.
8. **Checkpoint:** فقط تغییر معتبر و clean به عنوان checkpoint محلی ثبت می‌شود.
9. **هدف بعدی:** بدون نیاز به prompt جدید، چرخهٔ بعدی از backlog انتخاب می‌شود.

## وضعیت فعلی صحت و پایداری

در آخرین milestone:

- ۳۳ تست Orchestrator موفق؛
- تست‌های Model Gateway موفق؛
- compile سرویس Local Agent موفق؛
- buildهای Control Center، Provider Router و Desktop موفق؛
- health سرویس‌های 8010، 8011، 8012، 8020 و Ollama 11434 موفق؛
- UI در اجرای شبانه باز یا focus نمی‌شود؛
- backup timestamped پیش از تغییرهای مهم ساخته می‌شود؛
- checkpointهای محلی Git برای تغییرهای خودکار ثبت شده‌اند.

## وضعیت Git و انتشار

- branch محلی main چند checkpoint جلوتر از origin/main است.
- هر تغییر خودکار ابتدا در workspace و Git محلی ثبت می‌شود.
- push فقط برای remote و branch مشخص و پس از clean/verified شدن مجاز است.
- push اجباری یا ارسال credential انجام نمی‌شود؛ اگر احراز هویت یا policy شبکه اجازه ندهد، checkpoint محلی حفظ می‌شود و چرخهٔ بعدی متوقف نمی‌شود.

## چه چیزهایی هنوز باقی مانده؟

### در حال تکمیل

- UI حرفه‌ای‌تر و نزدیک‌تر به تجربهٔ Codex؛
- نمایش زندهٔ handoff و وضعیت هر specialist در Control Center/Desktop؛
- lease و telemetry کامل‌تر برای queue، oldest task و next verification؛
- specialistهای عمیق‌تر برای security، docs، release و integration؛
- retry محدود debugger و مسیر approval برای release/publish؛
- پوشش تست integration برای scheduler، restart reconciliation و UI.

### خارج از ادعای فعلی

این پروژه هنوز تمام قابلیت‌های Codex را یک‌جا ندارد. Codex یک محصول بزرگ با مدل، ابزار، UX، sandbox، collaboration و release workflow بسیار گسترده است. AI Engineer اکنون **هستهٔ محلی و خودگردان توسعه** را دارد و می‌تواند خودش را با guard و validation بهبود دهد؛ رسیدن به parity کامل با Codex یک roadmap جداگانه است.

## جمع‌بندی

پیشرفت اصلی از «یک برنامهٔ چندسرویسی» به «یک supervisor محلی که backlog را انتخاب می‌کند، subagentها را مدیریت می‌کند، تغییر امن می‌دهد، نتیجه را در memory نگه می‌دارد و خودش چرخهٔ بعدی را شروع می‌کند» بوده است.

الان اولویت فنی، افزایش throughput با حفظ writer lock و safety است؛ نه اجرای کورکورانهٔ تست در هر بیدارشدن. مدل اصلی محلی و رایگان است، بنابراین پایهٔ سیستم حتی بدون اینترنت هم فعال می‌ماند.
