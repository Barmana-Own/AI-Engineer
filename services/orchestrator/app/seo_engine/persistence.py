"""SQLite persistence for SEO state, using the existing AI-Engineer database."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from app import db
from .models import AuditSnapshot, KeywordCluster, KeywordPageMap, SeoFinding, SeoSiteProfile


def _json(value: object, fallback: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(fallback, ensure_ascii=False)


def _site_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"], "project_id": row["project_id"], "name": row["name"],
        "base_url": row["base_url"], "platform": row["platform"], "source_mode": row["source_mode"],
        "workspace": row["workspace"], "language": row["language"], "region": row["region"],
        "canonical_host": row["canonical_host"], "status": row["status"],
        "crawl_policy": json.loads(row["crawl_policy_json"] or "{}"),
        "rendering_mode": row["rendering_mode"], "credential_refs": json.loads(row["credential_refs_json"] or "{}"),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def create_site(site: SeoSiteProfile, *, status: str = "active", rendering_mode: str = "raw") -> dict[str, Any]:
    now = db.utc_now()
    host = urlsplit(site.base_url).hostname if site.base_url else None
    with db.connect() as database:
        database.execute(
            """INSERT INTO seo_sites(
                id, project_id, name, base_url, platform, source_mode, workspace,
                language, region, canonical_host, status, crawl_policy_json,
                rendering_mode, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (site.site_id, site.project_id, site.name, site.base_url, site.platform.value,
             site.source_mode.value, site.workspace, site.language, site.region, host,
             status, _json(site.crawl_policy.as_dict(), {}), rendering_mode, now, now),
        )
    return get_site(site.site_id) or {}


def get_site(site_id: str) -> dict[str, Any] | None:
    with db.connect() as database:
        row = database.execute("SELECT * FROM seo_sites WHERE id = ?", (site_id,)).fetchone()
    return _site_row(row) if row else None


def list_sites(project_id: str | None = None, *, limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 200))
    with db.connect() as database:
        if project_id:
            rows = database.execute("SELECT * FROM seo_sites WHERE project_id = ? ORDER BY updated_at DESC LIMIT ?", (project_id, safe_limit)).fetchall()
        else:
            rows = database.execute("SELECT * FROM seo_sites ORDER BY updated_at DESC LIMIT ?", (safe_limit,)).fetchall()
    return [_site_row(row) for row in rows]


def save_snapshot(snapshot: AuditSnapshot) -> dict[str, Any]:
    with db.connect() as database:
        database.execute(
            """INSERT INTO seo_audit_snapshots(
                id, site_id, project_id, baseline, status, platform_json,
                crawl_scope_json, pages_analyzed, findings_json, provider_state_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (snapshot.snapshot_id, snapshot.site_id, snapshot.project_id, int(snapshot.baseline), snapshot.status,
             _json(snapshot.platform.as_dict(), {}), _json(snapshot.crawl_policy.as_dict(), {}), len(snapshot.pages),
             _json([item.as_dict() for item in snapshot.findings], []), _json(snapshot.provider_state, {}), snapshot.created_at or db.utc_now()),
        )
        for page in snapshot.pages:
            database.execute(
                """INSERT INTO seo_pages(
                    id, audit_id, site_id, url, final_url, status_code, content_type,
                    evidence_json, raw_html_hash, rendered_html_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid4()), snapshot.snapshot_id, snapshot.site_id, page.url, page.final_url, page.status_code,
                 page.content_type, _json(page.as_dict(), {}), page.raw_html_hash, page.rendered_html_hash, db.utc_now()),
            )
        for finding in snapshot.findings:
            save_finding_for_project(finding, snapshot.project_id, database=database)
    return get_snapshot(snapshot.snapshot_id) or {}


def get_snapshot(snapshot_id: str) -> dict[str, Any] | None:
    with db.connect() as database:
        row = database.execute("SELECT * FROM seo_audit_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"], "site_id": row["site_id"], "project_id": row["project_id"],
        "baseline": bool(row["baseline"]), "status": row["status"],
        "platform": json.loads(row["platform_json"] or "{}"),
        "crawl_scope": json.loads(row["crawl_scope_json"] or "{}"),
        "pages_analyzed": row["pages_analyzed"], "findings": json.loads(row["findings_json"] or "[]"),
        "provider_state": json.loads(row["provider_state_json"] or "{}"), "created_at": row["created_at"],
    }


def list_pages(audit_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 1_000))
    with db.connect() as database:
        rows = database.execute(
            "SELECT id, audit_id, site_id, url, final_url, status_code, content_type, evidence_json, raw_html_hash, rendered_html_hash, created_at FROM seo_pages WHERE audit_id = ? ORDER BY url LIMIT ?",
            (audit_id, safe_limit),
        ).fetchall()
    return [{
        "id": row["id"], "audit_id": row["audit_id"], "site_id": row["site_id"], "url": row["url"],
        "final_url": row["final_url"], "status_code": row["status_code"], "content_type": row["content_type"],
        "evidence": json.loads(row["evidence_json"] or "{}"), "raw_html_hash": row["raw_html_hash"],
        "rendered_html_hash": row["rendered_html_hash"], "created_at": row["created_at"],
    } for row in rows]


def compare_snapshots(baseline_id: str, current_id: str) -> dict[str, Any] | None:
    baseline = get_snapshot(baseline_id)
    current = get_snapshot(current_id)
    if not baseline or not current:
        return None
    def keyed(findings: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
        return {
            (str(item.get("category", "")), str(item.get("resource", "")), str(item.get("title", ""))): item
            for item in findings
        }
    before = keyed(list(baseline.get("findings") or []))
    after = keyed(list(current.get("findings") or []))
    resolved = [key for key in before.keys() & after.keys() if before[key].get("status") != "verified" and after[key].get("status") == "verified"]
    new_findings = [key for key in after.keys() - before.keys()]
    unresolved = [key for key in after.keys() if after[key].get("status") != "verified"]
    return {
        "baseline_id": baseline_id,
        "current_id": current_id,
        "site_id": current["site_id"],
        "project_id": current["project_id"],
        "resolved": [list(item) for item in resolved],
        "new_findings": [list(item) for item in new_findings],
        "unresolved": [list(item) for item in unresolved],
        "before_count": len(before),
        "after_count": len(after),
    }

def list_snapshots(site_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 100))
    with db.connect() as database:
        rows = database.execute("SELECT * FROM seo_audit_snapshots WHERE site_id = ? ORDER BY created_at DESC LIMIT ?", (site_id, safe_limit)).fetchall()
    return [{
        "id": row["id"], "site_id": row["site_id"], "project_id": row["project_id"], "baseline": bool(row["baseline"]),
        "status": row["status"], "platform": json.loads(row["platform_json"] or "{}"),
        "pages_analyzed": row["pages_analyzed"], "findings": json.loads(row["findings_json"] or "[]"),
        "provider_state": json.loads(row["provider_state_json"] or "{}"), "created_at": row["created_at"],
    } for row in rows]


def save_finding(finding: SeoFinding, *, database: Any | None = None) -> dict[str, Any]:
    own_connection = database is None
    connection = database or db.connect()
    try:
        now = db.utc_now()
        site_row = connection.execute(
            "SELECT project_id FROM seo_sites WHERE id = ?",
            (finding.site_id,),
        ).fetchone()
        project_id = str(site_row["project_id"]) if site_row and site_row["project_id"] else ""
        connection.execute(
            """INSERT OR REPLACE INTO seo_findings(
                id, site_id, project_id, audit_id, category, severity, confidence, url_resource,
                title, description, evidence_json, provenance, impact, recommended_action,
                responsible_role, acceptance_criteria, verification_method, status,
                source_task_id, assigned_task_id, created_at, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (finding.finding_id, finding.site_id, project_id, finding.source_snapshot_id, finding.category, finding.severity.value,
             finding.confidence, finding.resource, finding.title, finding.description, _json(finding.evidence, []),
             finding.provenance.value, finding.impact, finding.recommended_action, finding.responsible_role,
             finding.acceptance_criteria, finding.verification_method, finding.status.value, None, finding.assigned_task_id,
             now, now if finding.status.value == "verified" else None),
        )
        if own_connection:
            connection.commit()
        return get_finding(finding.finding_id) or {}
    finally:
        if own_connection:
            connection.close()


def save_finding_for_project(finding: SeoFinding, project_id: str, *, database: Any | None = None) -> dict[str, Any]:
    own_connection = database is None
    connection = database or db.connect()
    try:
        now = db.utc_now()
        connection.execute(
            """INSERT OR REPLACE INTO seo_findings(
                id, site_id, project_id, audit_id, category, severity, confidence, url_resource,
                title, description, evidence_json, provenance, impact, recommended_action,
                responsible_role, acceptance_criteria, verification_method, status,
                source_task_id, assigned_task_id, created_at, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (finding.finding_id, finding.site_id, project_id, finding.source_snapshot_id, finding.category, finding.severity.value,
             finding.confidence, finding.resource, finding.title, finding.description, _json(finding.evidence, []),
             finding.provenance.value, finding.impact, finding.recommended_action, finding.responsible_role,
             finding.acceptance_criteria, finding.verification_method, finding.status.value, None, finding.assigned_task_id,
             now, now if finding.status.value == "verified" else None),
        )
        if own_connection:
            connection.commit()
        return get_finding(finding.finding_id) or {}
    finally:
        if own_connection:
            connection.close()


def get_finding(finding_id: str) -> dict[str, Any] | None:
    with db.connect() as database:
        row = database.execute("SELECT * FROM seo_findings WHERE id = ?", (finding_id,)).fetchone()
    return _finding_row(row) if row else None


def _finding_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"], "site_id": row["site_id"], "project_id": row["project_id"], "audit_id": row["audit_id"],
        "category": row["category"], "severity": row["severity"], "confidence": row["confidence"],
        "resource": row["url_resource"], "title": row["title"], "description": row["description"],
        "evidence": json.loads(row["evidence_json"] or "[]"), "provenance": row["provenance"], "impact": row["impact"],
        "recommended_action": row["recommended_action"], "responsible_role": row["responsible_role"],
        "acceptance_criteria": row["acceptance_criteria"], "verification_method": row["verification_method"],
        "status": row["status"], "source_task_id": row["source_task_id"], "assigned_task_id": row["assigned_task_id"],
        "created_at": row["created_at"], "verified_at": row["verified_at"],
    }


def list_findings(site_id: str, *, snapshot_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    with db.connect() as database:
        if snapshot_id:
            rows = database.execute("SELECT * FROM seo_findings WHERE site_id = ? AND audit_id = ? ORDER BY created_at DESC LIMIT ?", (site_id, snapshot_id, safe_limit)).fetchall()
        else:
            rows = database.execute("SELECT * FROM seo_findings WHERE site_id = ? ORDER BY created_at DESC LIMIT ?", (site_id, safe_limit)).fetchall()
    return [_finding_row(row) for row in rows]


def update_finding_status(finding_id: str, status: str, *, evidence: list[str] | None = None, assigned_task_id: str | None = None) -> dict[str, Any] | None:
    with db.connect() as database:
        current = database.execute("SELECT evidence_json FROM seo_findings WHERE id = ?", (finding_id,)).fetchone()
        if not current:
            return None
        old = json.loads(current["evidence_json"] or "[]")
        merged = list(dict.fromkeys([str(item) for item in old + list(evidence or [])]))[:100]
        database.execute("UPDATE seo_findings SET status = ?, evidence_json = ?, assigned_task_id = COALESCE(?, assigned_task_id), verified_at = ? WHERE id = ?", (status, _json(merged, []), assigned_task_id, db.utc_now() if status == "verified" else None, finding_id))
    return get_finding(finding_id)


def save_keyword_plan(site_id: str, project_id: str, clusters: tuple[KeywordCluster, ...], maps: tuple[KeywordPageMap, ...]) -> None:
    with db.connect() as database:
        for cluster in clusters:
            database.execute("INSERT OR REPLACE INTO seo_keyword_clusters(id, site_id, project_id, primary_keyword, terms_json, intent, language, region, evidence_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (cluster.cluster_id, site_id, project_id, cluster.primary_keyword, _json(cluster.terms, []), cluster.intent, cluster.language, cluster.region, _json(cluster.evidence, []), db.utc_now()))
        for mapping in maps:
            database.execute("INSERT OR REPLACE INTO seo_keyword_maps(id, site_id, project_id, cluster_id, target_page, current_page, intent, page_type, conflict, priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (mapping.mapping_id, site_id, project_id, mapping.cluster_id, mapping.target_page, mapping.current_page, mapping.intent, mapping.page_type, mapping.conflict, mapping.priority.value, db.utc_now()))
