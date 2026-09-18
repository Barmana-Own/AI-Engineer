from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    PROJECT = "project"
    LESSON = "lesson"
    FAILURE = "failure"


class MemoryLifecycle(str, Enum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    TRUSTED = "trusted"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class OutcomeType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    REVIEW_REJECTED = "review_rejected"
    TEST_FAILED = "test_failed"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    project_id: str | None
    run_id: str | None
    task_id: str | None
    memory_type: str
    lifecycle: str
    role: str | None
    task_type: str | None
    summary: str
    content: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    usefulness: float = 0.5
    use_count: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    source: str = "system"
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str | None = None
    superseded_by: str | None = None
    rank_score: float | None = None

    def as_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id, "project_id": self.project_id, "run_id": self.run_id,
            "task_id": self.task_id, "memory_type": self.memory_type,
            "lifecycle": self.lifecycle, "role": self.role,
            "task_type": self.task_type, "summary": self.summary,
            "content": self.content, "evidence": self.evidence,
            "confidence": self.confidence, "usefulness": self.usefulness,
            "use_count": self.use_count, "successful_uses": self.successful_uses,
            "failed_uses": self.failed_uses, "source": self.source,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "last_used_at": self.last_used_at, "superseded_by": self.superseded_by,
        }
        if self.rank_score is not None:
            result["rank_score"] = self.rank_score
        return result

