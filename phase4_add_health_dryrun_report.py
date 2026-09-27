from pathlib import Path

root = Path(r"C:\Services\AI-Engineer\current\reports")
english = "\n\n### Health-script shape validation\n\nThe health script completed its response-shape and safety assertions with ephemeral non-secret test tokens against the reachable HTTP proxy. This validates the script logic only; real authenticated production validation remains NOT_RUN until machine tokens are configured and the services are restarted.\n"
persian = "\n\n### یادداشت اعتبارسنجی health script\n\nاسکریپت health با توکن‌های آزمایشی موقت و غیرمحرمانه، بررسی شکل پاسخ و assertionهای ایمنی را در proxy قابل دسترس HTTP با موفقیت انجام داد. این فقط منطق اسکریپت را تأیید می‌کند؛ اعتبارسنجی واقعی Production تا زمان تنظیم توکن‌های machine و restart سرویس‌ها NOT_RUN است.\n"
for name in ("technical-report.en.md", "customer-report.en.md"):
    path = root / name
    path.write_text(path.read_text(encoding="utf-8").rstrip() + english, encoding="utf-8", newline="")
for name in ("technical-report.fa.md", "customer-report.fa.md"):
    path = root / name
    path.write_text(path.read_text(encoding="utf-8").rstrip() + persian, encoding="utf-8", newline="")
print("recorded health-script dry-run evidence")
