"""Documentation Engineer for source-backed technical documentation.

The agent records structured documentation work through the existing message
bus and handoff protocol.  It deliberately does not write arbitrary source
files; a Local Agent or another controlled writer must apply documentation
changes after the returned contract has been reviewed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Callable, Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.coordination.project_management import enqueue_work
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_DOC_ROOTS = ("docs", "deploy")
_DOC_NAMES = frozenset({"README", "CHANGELOG", "CONTRIBUTING", "LICENSE"})
_DOC_EXTENSIONS = frozenset({".md", ".mdx", ".rst", ".adoc", ".txt", ".yaml", ".yml"})
_HANDOFF_TARGETS = frozenset({"reviewer", "release_verifier", "engineering_manager", "supervisor"})


def _clean(value: object, *, max_chars: int = 4000) -> str:
    cleaned, _ = sanitize_text(str(value or ""), max_chars=max_chars)
    return cleaned.strip()


def _items(values: Iterable[object] | None, *, limit: int = 100, max_chars: int = 2000) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for value in values or ():
        item = _clean(value, max_chars=max_chars)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return tuple(result)


def _sequence(values: Iterable[object] | None, *, limit: int = 100) -> tuple[object, ...]:
    result: list[object] = []
    for value in values or ():
        if isinstance(value, Mapping):
            item = {str(key): _clean(raw, max_chars=4000) for key, raw in value.items()}
        else:
            item = _clean(value, max_chars=4000)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return tuple(result)


def _normalise_path(value: object) -> str:
    raw = _clean(value, max_chars=512).replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    return raw.strip("/")


def _is_documentation_path(value: object) -> bool:
    path = _normalise_path(value)
    if not path or path.startswith("/") or ":" in path.split("/", 1)[0]:
        return False
    parts = PurePosixPath(path).parts
    if ".." in parts:
        return False
    name = PurePosixPath(path).name
    stem = PurePosixPath(name).stem.upper()
    if len(parts) == 1 and stem in _DOC_NAMES:
        return True
    if not parts or parts[0].casefold() not in _DOC_ROOTS:
        return False
    return PurePosixPath(name).suffix.casefold() in _DOC_EXTENSIONS or stem in _DOC_NAMES


@dataclass(frozen=True)
class DocumentationEvidence:
    source_file: str
    source_symbol: str | None = None
    test: str | None = None
    decision: str | None = None
    status: str = "verified"

    def as_dict(self) -> dict[str, object]:
        return {key: value for key, value in asdict(self).items() if value}


@dataclass(frozen=True)
class DocumentationDriftItem:
    drift_id: str
    topic: str
    documented: str
    actual: str
    evidence: tuple[DocumentationEvidence, ...]
    severity: str = "medium"
    status: str = "open"

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = [item.as_dict() for item in self.evidence]
        return result


@dataclass(frozen=True)
class DocumentationUpdate:
    update_id: str
    project_id: str
    task_id: str
    files: tuple[str, ...]
    summary: str
    source_files: tuple[str, ...]
    implemented_facts: tuple[str, ...]
    planned_facts: tuple[str, ...]
    evidence: tuple[DocumentationEvidence, ...]
    status: str = "updated"
    message_id: str | None = None
    handoff_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = [item.as_dict() for item in self.evidence]
        return result


@dataclass(frozen=True)
class DocumentationDriftReport:
    drift_id: str
    project_id: str
    task_id: str
    items: tuple[DocumentationDriftItem, ...]
    documentation_files: tuple[str, ...]
    source_files: tuple[str, ...]
    status: str
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["items"] = [item.as_dict() for item in self.items]
        return result


@dataclass(frozen=True)
class ReleaseNotes:
    release_id: str
    project_id: str
    task_id: str
    version: str
    entries: tuple[str, ...]
    verified_changes: tuple[str, ...]
    known_limitations: tuple[str, ...]
    status: str = "draft"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalise_evidence(values: Iterable[object] | None) -> tuple[DocumentationEvidence, ...]:
    result: list[DocumentationEvidence] = []
    for raw in values or ():
        if isinstance(raw, DocumentationEvidence):
            evidence = raw
        elif isinstance(raw, Mapping):
            source_file = _clean(raw.get("source_file") or raw.get("file"), max_chars=512)
            if not source_file:
                continue
            evidence = DocumentationEvidence(
                source_file=source_file,
                source_symbol=_clean(raw.get("source_symbol") or raw.get("symbol"), max_chars=256) or None,
                test=_clean(raw.get("test"), max_chars=1000) or None,
                decision=_clean(raw.get("decision"), max_chars=1000) or None,
                status=_clean(raw.get("status") or "verified", max_chars=64) or "verified",
            )
        else:
            source_file = _clean(raw, max_chars=512)
            if not source_file:
                continue
            evidence = DocumentationEvidence(source_file=source_file)
        if evidence not in result:
            result.append(evidence)
        if len(result) >= 100:
            break
    return tuple(result)


class DocumentationEngineerAgent:
    """Keep documentation synchronized with verified source behavior."""

    ROLE = "docs"
    DISPLAY_NAME = "Documentation Engineer"
    AGENT_ID = "employee-docs"

    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = database_path
        self.bus = MessageBus(database_path)
        self.handoffs = HandoffProtocol(database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id=self.AGENT_ID,
            display_name=self.DISPLAY_NAME,
            department=Department.DOCUMENTATION,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Documentation task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Documentation Engineer can only operate docs tasks")
        return task

    def _publish(
        self,
        *,
        message_type: MessageType,
        subject: str,
        body: object,
        project_id: str,
        task_id: str,
        run_id: str | None,
        topic: str,
        recipient_role: str | None = None,
        references: Iterable[object] = (),
    ) -> dict[str, object]:
        payload = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, default=str)
        return self.bus.publish(
            sender_role=self.ROLE,
            message_type=message_type,
            subject=_clean(subject, max_chars=500),
            body=_clean(payload, max_chars=20_000),
            project_id=project_id,
            task_id=task_id,
            run_id=run_id,
            recipient_role=recipient_role,
            references=_items(references, max_chars=512),
            topic=topic,
        )

    def inspect_source(
        self,
        task_id: str,
        source_files: Iterable[object],
        *,
        source_reader: Callable[[str], object] | None = None,
        source_symbols: Mapping[str, object] | None = None,
        tests: Iterable[object] = (),
        decisions: Iterable[object] = (),
        run_id: str | None = None,
    ) -> tuple[DocumentationEvidence, ...]:
        task = self._task(task_id)
        files = _items(source_files, max_chars=512)
        if not files:
            raise ValueError("documentation claims require source files to inspect")
        test_items = _items(tests, max_chars=1000)
        decision_items = _items(decisions, max_chars=1000)
        evidence: list[DocumentationEvidence] = []
        for index, file_name in enumerate(files):
            if source_reader is not None:
                inspected = source_reader(file_name)
                if inspected is None or (isinstance(inspected, str) and not inspected.strip()):
                    raise ValueError(f"source inspection returned no content: {file_name}")
            evidence.append(
                DocumentationEvidence(
                    source_file=file_name,
                    source_symbol=_clean((source_symbols or {}).get(file_name), max_chars=256) or None,
                    test=test_items[index] if index < len(test_items) else None,
                    decision=decision_items[index] if index < len(decision_items) else None,
                )
            )
        self._publish(
            message_type=MessageType.STATUS,
            subject="Documentation source inspection",
            body={"task_id": task_id, "source_files": files, "evidence": [item.as_dict() for item in evidence]},
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            topic="documentation_source_inspection",
        )
        return tuple(evidence)

    def detect_drift(
        self,
        task_id: str,
        *,
        documented: Mapping[str, object],
        actual: Mapping[str, object],
        documentation_files: Iterable[object],
        source_files: Iterable[object],
        evidence: Iterable[object] = (),
        severity: str = "medium",
        run_id: str | None = None,
    ) -> DocumentationDriftReport:
        task = self._task(task_id)
        docs = _items(documentation_files, max_chars=512)
        sources = _items(source_files, max_chars=512)
        if not docs or any(not _is_documentation_path(item) for item in docs):
            raise ValueError("drift reports require documentation file paths")
        if not sources:
            raise ValueError("drift reports require source file evidence")
        normalised_evidence = _normalise_evidence(evidence) or tuple(DocumentationEvidence(item) for item in sources)
        items: list[DocumentationDriftItem] = []
        for topic in sorted(set(documented) | set(actual)):
            old = _clean(documented.get(topic), max_chars=4000)
            new = _clean(actual.get(topic), max_chars=4000)
            if old != new:
                items.append(DocumentationDriftItem(str(uuid4()), _clean(topic, max_chars=256), old, new, normalised_evidence, _clean(severity, max_chars=32) or "medium"))
        status = "drift_detected" if items else "in_sync"
        drift_id = str(uuid4())
        message_type = MessageType.BLOCKER if items else MessageType.RESULT
        message = self._publish(
            message_type=message_type,
            subject="Documentation drift detected" if items else "Documentation is synchronized",
            body={"drift_id": drift_id, "status": status, "items": [item.as_dict() for item in items]},
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            topic="documentation_drift",
            references=docs + sources,
        )
        return DocumentationDriftReport(drift_id, str(task["project_id"]), str(task["id"]), tuple(items), docs, sources, status, str(message["message_id"]))

    def _validate_documentation_files(self, values: Iterable[object]) -> tuple[str, ...]:
        files = _items(values, max_chars=512)
        if not files:
            raise ValueError("documentation update requires at least one documentation file")
        invalid = [item for item in files if not _is_documentation_path(item)]
        if invalid:
            raise ValueError(f"documentation agent cannot write non-documentation paths: {invalid[0]}")
        return files

    def _handoff(self, task: Mapping[str, object], *, summary: str, files: tuple[str, ...], verification: tuple[str, ...], run_id: str | None, targets: Iterable[str]) -> str | None:
        handoff_id: str | None = None
        for target in targets:
            if target not in _HANDOFF_TARGETS:
                raise ValueError(f"unsupported documentation handoff target: {target}")
            handoff = AgentHandoff(
                sender_role=self.ROLE,
                recipient_role=target,
                summary=summary,
                completed=("Documentation facts were derived from inspected source.",),
                artifacts=("documentation_update", "documentation_evidence"),
                changed_files=files,
                verification=verification,
                remaining_work=("Review the documentation diff before release.",),
                run_id=run_id or task.get("run_id"),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
            )
            row = self.handoffs.submit(handoff)
            handoff_id = str(row["handoff_id"])
            self._publish(
                message_type=MessageType.HANDOFF,
                subject=summary,
                body={"handoff": row},
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                run_id=run_id or task.get("run_id"),
                topic="documentation_handoff",
                recipient_role=target,
                references=(f"handoff:{handoff_id}", f"task:{task['id']}"),
            )
            enqueue_work(target, str(task["project_id"]), "handoff", handoff_id, task_id=str(task["id"]), priority=int(task.get("priority") or 50), database_path=self.database_path)
        return handoff_id

    def update_documentation(
        self,
        task_id: str,
        *,
        documentation_files: Iterable[object],
        summary: str,
        source_files: Iterable[object],
        implemented_facts: Iterable[object] = (),
        planned_facts: Iterable[object] = (),
        evidence: Iterable[object] = (),
        verification: Iterable[object] = (),
        handoff_targets: Iterable[str] = (),
        run_id: str | None = None,
    ) -> DocumentationUpdate:
        task = self._task(task_id)
        files = self._validate_documentation_files(documentation_files)
        sources = _items(source_files, max_chars=512)
        implemented = _items(implemented_facts, max_chars=4000)
        planned = _items(planned_facts, max_chars=4000)
        checks = _items(verification, max_chars=1000)
        targets = _items(handoff_targets, max_chars=128)
        if implemented and not sources:
            raise ValueError("implemented documentation facts require inspected source files")
        normalised_evidence = _normalise_evidence(evidence)
        if implemented and (not normalised_evidence or not checks):
            raise ValueError("implemented documentation facts require source evidence and verification")
        message = self._publish(
            message_type=MessageType.RESULT,
            subject="Documentation update",
            body={"summary": _clean(summary, max_chars=4000), "files": files, "implemented_facts": implemented, "planned_facts": planned, "evidence": [item.as_dict() for item in normalised_evidence], "verification": checks},
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            topic="documentation_update",
            references=files + sources + checks,
        )
        handoff_id = self._handoff(task, summary="Documentation update ready for review", files=files, verification=checks, run_id=run_id, targets=targets) if targets else None
        return DocumentationUpdate(str(uuid4()), str(task["project_id"]), str(task["id"]), files, _clean(summary, max_chars=4000), sources, implemented, planned, normalised_evidence, "updated", str(message["message_id"]), handoff_id)

    def create_release_notes(
        self,
        task_id: str,
        *,
        version: str,
        entries: Iterable[object],
        verified_changes: Iterable[object],
        known_limitations: Iterable[object] = (),
        source_files: Iterable[object],
        verification: Iterable[object],
        run_id: str | None = None,
    ) -> ReleaseNotes:
        task = self._task(task_id)
        notes = _items(entries, max_chars=4000)
        changes = _items(verified_changes, max_chars=4000)
        limitations = _items(known_limitations, max_chars=4000)
        sources = _items(source_files, max_chars=512)
        checks = _items(verification, max_chars=1000)
        if not notes:
            raise ValueError("release notes require at least one entry")
        if changes and (not sources or not checks):
            raise ValueError("verified release changes require source files and verification")
        release_id = str(uuid4())
        message = self._publish(
            message_type=MessageType.RESULT,
            subject=f"Release notes { _clean(version, max_chars=128) }",
            body={"release_id": release_id, "version": _clean(version, max_chars=128), "entries": notes, "verified_changes": changes, "known_limitations": limitations, "source_files": sources, "verification": checks},
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            topic="release_notes",
            references=sources + checks,
        )
        return ReleaseNotes(release_id, str(task["project_id"]), str(task["id"]), _clean(version, max_chars=128), notes, changes, limitations, "verified" if changes else "draft", str(message["message_id"]))

    update = update_documentation
    write_documentation = update_documentation
    check_drift = detect_drift
    release_notes = create_release_notes


DocumentationAgent = DocumentationEngineerAgent
DocsAgent = DocumentationEngineerAgent

__all__ = [
    "DocumentationAgent",
    "DocumentationDriftItem",
    "DocumentationDriftReport",
    "DocumentationEngineerAgent",
    "DocumentationEvidence",
    "DocumentationUpdate",
    "DocsAgent",
    "ReleaseNotes",
]




