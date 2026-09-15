from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import UsageModelSummary, UsageSummary


@dataclass(frozen=True)
class UsageRecord:
    request_id: str
    project_id: str | None
    task_id: str | None
    agent_id: str | None
    requested_model: str | None
    selected_model: str | None
    attempted_models: list[str]
    status: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error_code: str | None


class UsageStore:
    """Small local SQLite store for model usage and request outcomes."""

    def __init__(self, path: Path) -> None:
        self._path = path

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    async def record(self, record: UsageRecord) -> None:
        await asyncio.to_thread(self._record_sync, record)

    async def summary(self) -> UsageSummary:
        return await asyncio.to_thread(self._summary_sync)

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_sync(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS model_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL UNIQUE,
                    project_id TEXT,
                    task_id TEXT,
                    agent_id TEXT,
                    requested_model TEXT,
                    selected_model TEXT,
                    attempted_models TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_model_usage_selected_model
                ON model_usage(selected_model)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_model_usage_project_task
                ON model_usage(project_id, task_id)
                """
            )

    def _record_sync(self, record: UsageRecord) -> None:
        attempted_models = ",".join(record.attempted_models)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO model_usage (
                    request_id,
                    project_id,
                    task_id,
                    agent_id,
                    requested_model,
                    selected_model,
                    attempted_models,
                    status,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    error_code,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.request_id,
                    record.project_id,
                    record.task_id,
                    record.agent_id,
                    record.requested_model,
                    record.selected_model,
                    attempted_models,
                    record.status,
                    record.latency_ms,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.error_code,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def _summary_sync(self) -> UsageSummary:
        with self._connect() as connection:
            totals = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_requests,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)
                        AS successful_requests,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
                        AS failed_requests,
                    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens
                FROM model_usage
                """
            ).fetchone()

            rows = connection.execute(
                """
                SELECT
                    COALESCE(selected_model, requested_model, 'unknown') AS model,
                    COUNT(*) AS request_count,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)
                        AS success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
                        AS failure_count,
                    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(AVG(latency_ms), 0) AS average_latency_ms
                FROM model_usage
                GROUP BY COALESCE(selected_model, requested_model, 'unknown')
                ORDER BY request_count DESC, model ASC
                """
            ).fetchall()

        by_model = [
            UsageModelSummary(
                model=row["model"],
                request_count=row["request_count"],
                success_count=row["success_count"] or 0,
                failure_count=row["failure_count"] or 0,
                prompt_tokens=row["prompt_tokens"],
                completion_tokens=row["completion_tokens"],
                total_tokens=row["total_tokens"],
                average_latency_ms=round(float(row["average_latency_ms"]), 2),
            )
            for row in rows
        ]

        return UsageSummary(
            total_requests=totals["total_requests"] or 0,
            successful_requests=totals["successful_requests"] or 0,
            failed_requests=totals["failed_requests"] or 0,
            prompt_tokens=totals["prompt_tokens"],
            completion_tokens=totals["completion_tokens"],
            total_tokens=totals["total_tokens"],
            by_model=by_model,
        )
