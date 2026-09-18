from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from app.db import connect, initialize_database, utc_now

from .models import MemoryLifecycle, MemoryType, OutcomeType
from .sanitizer import sanitize_memory, sanitize_text

_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]{3,}")
_TYPES = {item.value for item in MemoryType}
_LIFECYCLES = {item.value for item in MemoryLifecycle}
_OUTCOMES = {item.value for item in OutcomeType}


def _tokens(value: object) -> set[str]:
    return {item.casefold() for item in _TOKEN_RE.findall(str(value or ""))}


def _safe_json(value: object, fallback: Any) -> Any:
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return parsed


def _memory_dict(row: Any, score: float | None = None) -> dict[str, Any]:
    content = _safe_json(row["content_json"], {})
    evidence = _safe_json(row["evidence_json"], [])
    result = {
        "id": row["id"], "project_id": row["project_id"], "run_id": row["run_id"],
        "task_id": row["task_id"], "memory_type": row["memory_type"],
        "lifecycle": row["lifecycle"], "role": row["role"],
        "task_type": row["task_type"], "summary": row["summary"],
        "content": content if isinstance(content, dict) else {},
        "evidence": evidence if isinstance(evidence, list) else [],
        "confidence": float(row["confidence"] or 0),
        "usefulness": float(row["usefulness"] or 0),
        "use_count": int(row["use_count"] or 0),
        "successful_uses": int(row["successful_uses"] or 0),
        "failed_uses": int(row["failed_uses"] or 0),
        "source": row["source"], "created_at": row["created_at"],
        "updated_at": row["updated_at"], "last_used_at": row["last_used_at"],
        "superseded_by": row["superseded_by"],
    }
    if score is not None:
        result["rank_score"] = score
    return result


class MemoryStore:
    """Evidence-gated project memory, failure patterns, and agent outcomes."""

    def __init__(self, database_path: str | None = None):
        self.database_path = database_path
        initialize_database(database_path)

    def create(
        self, *, project_id: str | None, memory_type: str | MemoryType,
        summary: str, content: dict[str, Any] | None = None,
        evidence: Iterable[dict[str, Any]] = (),
        lifecycle: str | MemoryLifecycle = MemoryLifecycle.CANDIDATE,
        run_id: str | None = None, task_id: str | None = None,
        role: str | None = None, task_type: str | None = None,
        source: str = "system",
    ) -> dict[str, Any]:
        kind = str(memory_type.value if isinstance(memory_type, MemoryType) else memory_type).casefold()
        state = str(lifecycle.value if isinstance(lifecycle, MemoryLifecycle) else lifecycle).casefold()
        if kind not in _TYPES or state not in _LIFECYCLES:
            raise ValueError("Unsupported memory type or lifecycle")
        clean_summary, clean_content, clean_evidence, redacted = sanitize_memory(summary, content or {}, list(evidence))
        if not clean_summary.strip():
            raise ValueError("Memory summary is required")
        if redacted:
            clean_content = {**clean_content, "redacted": True}
        memory_id, now = str(uuid4()), utc_now()
        with connect(self.database_path) as database:
            database.execute(
                """
                INSERT INTO experience_memories(
                    id,project_id,run_id,task_id,memory_type,lifecycle,role,task_type,
                    summary,content_json,evidence_json,confidence,usefulness,source,
                    created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    memory_id, project_id, run_id, task_id, kind, state,
                    str(role)[:128] if role else None,
                    str(task_type)[:256] if task_type else None,
                    clean_summary, json.dumps(clean_content, ensure_ascii=False, default=str),
                    json.dumps(clean_evidence, ensure_ascii=False, default=str),
                    0.35 if state == "candidate" else 0.5, 0.5,
                    str(source)[:128], now, now,
                ),
            )
        return self.get(memory_id) or {}

    def get(self, memory_id: str) -> dict[str, Any] | None:
        with connect(self.database_path) as database:
            row = database.execute("SELECT * FROM experience_memories WHERE id=?", (memory_id,)).fetchone()
        return _memory_dict(row) if row else None

    def promote(self, memory_id: str, *, evidence: Iterable[dict[str, Any]], target: str | MemoryLifecycle = MemoryLifecycle.VALIDATED) -> dict[str, Any]:
        target = str(target.value if isinstance(target, MemoryLifecycle) else target).casefold()
        evidence = [item for item in evidence if isinstance(item, dict) and any(str(item.get(k) or "").strip() for k in ("type", "command", "artifact", "summary"))][:20]
        if target not in {"validated", "trusted"} or not evidence:
            raise ValueError("Promotion requires validated evidence")
        with connect(self.database_path) as database:
            row = database.execute("SELECT * FROM experience_memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                raise KeyError(memory_id)
            current = str(row["lifecycle"])
            if current in {"rejected", "superseded"}:
                raise ValueError(f"Cannot promote {current} memory")
            if target == "trusted" and current == "candidate":
                target = "validated"
            merged = _safe_json(row["evidence_json"], [])
            merged = (merged if isinstance(merged, list) else []) + evidence
            confidence = 0.85 if target == "trusted" else max(float(row["confidence"] or 0), 0.65)
            database.execute(
                "UPDATE experience_memories SET lifecycle=?,evidence_json=?,confidence=?,updated_at=? WHERE id=?",
                (target, json.dumps(merged[-40:], ensure_ascii=False, default=str), confidence, utc_now(), memory_id),
            )
        return self.get(memory_id) or {}

    def reject(self, memory_id: str, *, reason: str) -> dict[str, Any]:
        clean, _ = sanitize_text(reason, max_chars=1_000)
        with connect(self.database_path) as database:
            row = database.execute("SELECT content_json FROM experience_memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                raise KeyError(memory_id)
            content = _safe_json(row["content_json"], {})
            content = content if isinstance(content, dict) else {}
            content["rejection_reason"] = clean
            database.execute(
                "UPDATE experience_memories SET lifecycle='rejected',content_json=?,updated_at=? WHERE id=?",
                (json.dumps(content, ensure_ascii=False), utc_now(), memory_id),
            )
        return self.get(memory_id) or {}

    def supersede(self, memory_id: str, replacement_id: str) -> dict[str, Any]:
        if memory_id == replacement_id:
            raise ValueError("A memory cannot supersede itself")
        with connect(self.database_path) as database:
            if not database.execute("SELECT 1 FROM experience_memories WHERE id=?", (replacement_id,)).fetchone():
                raise KeyError(replacement_id)
            database.execute(
                "UPDATE experience_memories SET lifecycle='superseded',superseded_by=?,updated_at=? WHERE id=?",
                (replacement_id, utc_now(), memory_id),
            )
        return self.get(memory_id) or {}

    def retrieve(
        self, *, project_id: str | None, query: str = "", role: str | None = None,
        task_type: str | None = None, files: Iterable[str] = (), run_id: str | None = None,
        task_id: str | None = None, limit: int = 8, include_candidate: bool = False,
    ) -> list[dict[str, Any]]:
        safe_limit = min(max(int(limit), 1), 50)
        params: list[Any] = [project_id, "validated", "trusted"]
        candidate = ""
        if include_candidate and (run_id or task_id):
            candidate = " OR (lifecycle='candidate' AND (run_id=? OR task_id=?))"
            params.extend([run_id, task_id])
        with connect(self.database_path) as database:
            rows = database.execute(
                "SELECT * FROM experience_memories WHERE (project_id IS NULL OR project_id=?) AND (lifecycle IN (?, ?)" + candidate + ") ORDER BY updated_at DESC LIMIT 200",
                params,
            ).fetchall()
        query_terms, file_terms = _tokens(query), _tokens(" ".join(files))
        now = datetime.now(timezone.utc)
        ranked: list[tuple[float, Any]] = []
        for row in rows:
            content_text = json.dumps(_safe_json(row["content_json"], {}), ensure_ascii=False, default=str).casefold()
            haystack = f"{row['summary']} {content_text}".casefold()
            matched = sum(term in haystack for term in query_terms)
            file_matched = sum(term in haystack for term in file_terms)
            score = float(row["confidence"] or 0) * 2 + float(row["usefulness"] or 0) * 1.5
            score += 1.0 if project_id and row["project_id"] == project_id else 0.25
            score += 0.9 if role and str(row["role"] or "").casefold() == role.casefold() else 0
            score += 0.7 if task_type and str(row["task_type"] or "").casefold() == task_type.casefold() else 0
            score += matched * 0.7 + file_matched * 0.9
            score += 0.4 if row["lifecycle"] == "trusted" else 0
            try:
                age_days = max((now - datetime.fromisoformat(str(row["updated_at"]).replace("Z", "+00:00"))).total_seconds() / 86400, 0)
                score += max(0, 0.5 - age_days * 0.01)
            except (TypeError, ValueError):
                pass
            scope_match = bool((role and str(row["role"] or "").casefold() == role.casefold()) or (task_type and str(row["task_type"] or "").casefold() == task_type.casefold()))
            if query_terms and matched == 0 and file_matched == 0 and not scope_match:
                continue
            ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[:safe_limit]
        if selected:
            with connect(self.database_path) as database:
                database.executemany(
                    "UPDATE experience_memories SET use_count=use_count+1,last_used_at=? WHERE id=?",
                    [(utc_now(), row["id"]) for _, row in selected],
                )
        return [_memory_dict(row, score) for score, row in selected]

    def record_outcome(
        self, memory_id: str, *, outcome: str | OutcomeType,
        task_success: bool | None = None, tests_passed: bool | None = None,
        review_accepted: bool | None = None, rework_required: bool = False,
        notes: dict[str, Any] | None = None, evidence: Iterable[dict[str, Any]] = (),
    ) -> dict[str, Any]:
        result = str(outcome.value if isinstance(outcome, OutcomeType) else outcome).casefold()
        if result not in _OUTCOMES:
            raise ValueError("Unsupported memory outcome")
        with connect(self.database_path) as database:
            row = database.execute("SELECT * FROM experience_memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                raise KeyError(memory_id)
            success = result == "success" and bool(task_success)
            successes = int(row["successful_uses"] or 0) + int(success)
            failures = int(row["failed_uses"] or 0) + int(not success)
            usefulness = max(0, min(1, float(row["usefulness"] or 0.5) * 0.7 + (0.3 if success else 0)))
            confidence = max(0, min(1, float(row["confidence"] or 0.35) * 0.85 + (0.15 if success else 0)))
            lifecycle = str(row["lifecycle"])
            if success and lifecycle == "candidate" and (tests_passed or review_accepted):
                lifecycle, confidence = "validated", max(confidence, 0.65)
            if success and lifecycle == "validated" and successes >= 2:
                lifecycle, confidence = "trusted", max(confidence, 0.85)
            clean_notes, _, clean_evidence, _ = sanitize_memory("", notes or {}, list(evidence))
            database.execute(
                "UPDATE experience_memories SET lifecycle=?,use_count=use_count+1,successful_uses=?,failed_uses=?,usefulness=?,confidence=?,updated_at=? WHERE id=?",
                (lifecycle, successes, failures, usefulness, confidence, utc_now(), memory_id),
            )
            database.execute(
                """
                INSERT INTO experience_outcomes(
                    id,memory_id,project_id,run_id,task_id,outcome,task_success,
                    tests_passed,review_accepted,rework_required,notes_json,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(uuid4()), memory_id, row["project_id"], row["run_id"], row["task_id"],
                    result, None if task_success is None else int(task_success),
                    None if tests_passed is None else int(tests_passed),
                    None if review_accepted is None else int(review_accepted),
                    int(rework_required),
                    json.dumps({"notes": clean_notes, "evidence": clean_evidence}, ensure_ascii=False, default=str),
                    utc_now(),
                ),
            )
        return self.get(memory_id) or {}

    def record_agent_outcome(
        self, *, role: str, model_profile: str, domain: str = "",
        success: bool, review_accepted: bool = True, tests_passed: bool = True,
        retries: int = 0, duration_seconds: float = 0.0,
        successful_domain: str | None = None,
    ) -> dict[str, Any]:
        clean_role, _ = sanitize_text(role, max_chars=128)
        clean_profile, _ = sanitize_text(model_profile, max_chars=128)
        clean_domain, _ = sanitize_text(domain, max_chars=128)
        with connect(self.database_path) as database:
            row = database.execute(
                "SELECT * FROM agent_performance WHERE role=? AND model_profile=? AND domain=?",
                (clean_role, clean_profile, clean_domain),
            ).fetchone()
            domains = _safe_json(row["successful_domains_json"], []) if row else []
            domains = domains if isinstance(domains, list) else []
            if successful_domain and success and successful_domain not in domains:
                domains.append(successful_domain)
            values = (
                int(success), int(not review_accepted), int(not tests_passed),
                max(int(retries), 0), max(float(duration_seconds), 0), json.dumps(domains, ensure_ascii=False), utc_now(),
            )
            if row:
                database.execute(
                    """
                    UPDATE agent_performance SET
                    tasks_attempted=tasks_attempted+1,tasks_completed=tasks_completed+?,
                    review_rejections=review_rejections+?,test_failures=test_failures+?,
                    total_retries=total_retries+?,total_duration_seconds=total_duration_seconds+?,
                    successful_domains_json=?,updated_at=?
                    WHERE role=? AND model_profile=? AND domain=?
                    """,
                    values + (clean_role, clean_profile, clean_domain),
                )
            else:
                database.execute(
                    """
                    INSERT INTO agent_performance(
                    role,model_profile,domain,tasks_attempted,tasks_completed,
                    review_rejections,test_failures,total_retries,total_duration_seconds,
                    successful_domains_json,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (clean_role, clean_profile, clean_domain, 1, values[0], values[1], values[2], values[3], values[4], values[5], values[6]),
                )
        return self.performance(role=clean_role, model_profile=clean_profile, domain=clean_domain)[0]

    def performance(self, *, role: str | None = None, model_profile: str | None = None, domain: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        clauses, params = [], []
        for column, value in (("role", role), ("model_profile", model_profile), ("domain", domain)):
            if value is not None:
                clauses.append(column + "=?")
                params.append(value)
        params.append(min(max(int(limit), 1), 100))
        with connect(self.database_path) as database:
            rows = database.execute(
                "SELECT * FROM agent_performance WHERE " + (" AND ".join(clauses) or "1=1") +
                " ORDER BY tasks_completed DESC,updated_at DESC LIMIT ?", params
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["successful_domains"] = _safe_json(row["successful_domains_json"], [])
            result.append(item)
        return result

    def capture_failure(
        self, *, project_id: str | None, role: str | None, title: str,
        reason: str, successful_fix: str | None = None, run_id: str | None = None,
        task_id: str | None = None, evidence: Iterable[dict[str, Any]] = (),
    ) -> dict[str, Any]:
        clean_title, _ = sanitize_text(title, max_chars=256)
        clean_reason, _ = sanitize_text(reason, max_chars=2_000)
        clean_fix, _ = sanitize_text(successful_fix or "", max_chars=2_000)
        signature = "-".join(sorted(_tokens(clean_reason)))[:180] or "unknown-failure"
        memory = self.create(
            project_id=project_id, run_id=run_id, task_id=task_id, role=role,
            task_type="failure", memory_type=MemoryType.FAILURE,
            summary=clean_title or "Engineering failure pattern",
            content={"root_cause": clean_reason, "successful_fix": clean_fix, "signature": signature},
            evidence=evidence, source="failure-observer",
        )
        now = utc_now()
        with connect(self.database_path) as database:
            existing = database.execute(
                "SELECT * FROM failure_patterns WHERE project_id IS ? AND signature=?",
                (project_id, signature),
            ).fetchone()
            if existing:
                database.execute(
                    "UPDATE failure_patterns SET occurrences=occurrences+1,confidence=MIN(1.0,confidence+0.05),updated_at=?,last_seen_at=?,linked_memory_id=? WHERE id=?",
                    (now, now, memory["id"], existing["id"]),
                )
                pattern_id = existing["id"]
            else:
                pattern_id = str(uuid4())
                database.execute(
                    """
                    INSERT INTO failure_patterns(
                    id,project_id,signature,title,root_cause,successful_fix,linked_memory_id,
                    created_at,updated_at,last_seen_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (pattern_id, project_id, signature, clean_title or "Failure pattern", clean_reason, clean_fix or None, memory["id"], now, now, now),
                )
        memory["failure_pattern_id"] = pattern_id
        return memory

    def failure_patterns(self, *, project_id: str | None, query: str = "", limit: int = 10) -> list[dict[str, Any]]:
        tokens = _tokens(query)
        with connect(self.database_path) as database:
            rows = database.execute(
                "SELECT * FROM failure_patterns WHERE project_id IS NULL OR project_id=? ORDER BY occurrences DESC,confidence DESC,updated_at DESC LIMIT 100",
                (project_id,),
            ).fetchall()
        result = []
        for row in rows:
            text = f"{row['title']} {row['root_cause']} {row['successful_fix'] or ''}".casefold()
            if tokens and not any(token in text for token in tokens):
                continue
            result.append(dict(row))
            if len(result) >= min(max(int(limit), 1), 50):
                break
        return result

    def extract_task_experience(
        self, *, project_id: str | None, run_id: str | None, task_id: str | None,
        role: str, task_type: str, summary: str,
        evidence: Iterable[dict[str, Any]] = (), changed_files: Iterable[str] = (),
        validations: Iterable[str] = (), success: bool, failure_reason: str | None = None,
        retry_count: int = 0, model_profile: str = "balanced",
        duration_seconds: float = 0.0, tests_passed: bool | None = None,
        review_accepted: bool | None = None,
    ) -> dict[str, Any]:
        clean_summary, _, _, _ = sanitize_memory(summary, {}, [])
        kind = MemoryType.LESSON if success else MemoryType.FAILURE
        memory = self.create(
            project_id=project_id, run_id=run_id, task_id=task_id, role=role,
            task_type=task_type, memory_type=kind,
            summary=clean_summary or ("Successful engineering outcome" if success else "Failed engineering outcome"),
            content={
                "changed_files": list(changed_files)[:50],
                "validations": list(validations)[:20],
                "failure_reason": failure_reason or "",
                "retry_count": int(retry_count),
            },
            evidence=evidence, source="supervisor-extractor",
        )
        self.record_agent_outcome(
            role=role, model_profile=model_profile, domain=task_type,
            success=success,
            review_accepted=success if review_accepted is None else bool(review_accepted),
            tests_passed=success if tests_passed is None else bool(tests_passed),
            retries=retry_count, duration_seconds=duration_seconds,
        )
        return memory




