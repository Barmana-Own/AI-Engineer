# SEO Manager Integration

The `seo_manager` role is implemented in `app.organization.seo_manager` and exported from `app.organization`. It is a read-only managerial role. Persistence is intentionally delegated to existing coordination and memory stores; there are no SEO-specific tables.

Public objects: `SEOProjectProfile`, `SEOAuditFinding`, `SEOKeywordCluster`, `SEOBacklogTask`, `SEOQualityGate`, `SEOReport`, `SEOManagerAgent`/`SEOManager`.

The role records structured messages under `seo_site_profile`, `seo_audit`, `seo_keyword_map`, `seo_task_delegation`, `seo_quality_gate`, `seo_decision`, and `seo_report`. It creates normal DAG tasks, work queue entries, handoffs, technical decisions, and evidence-gated project memories. Missing external data is represented as `DATA NOT AVAILABLE`; analytics are never estimated.

The implementation and deterministic tests are covered by the SEO Manager report files in `reports/seo-manager-report.en.md` and `reports/seo-manager-report.fa.md`.