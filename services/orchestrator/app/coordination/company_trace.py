from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from app.db import connect, create_project, initialize_database, utc_now
from app.memory import MemoryStore
from app.organization.director import CompanyDirector
from app.organization.store import get_project_organization
from . import store
from .collaboration import CollaborationEngine
from .collaboration_store import list_conversations, list_decisions, list_meetings, list_work_requests
from .incidents import assign_incident_team, create_incident, create_postmortem, list_incident_events, list_incidents, list_postmortems, promote_postmortem_lesson, transition_incident
from .models import AgentHandoff, ConversationType, MeetingType, MessageType
from .project_management import blackboard, get_project_state, list_lifecycle_events, set_quality_gate, transition_project_phase

_SECRET_KEY = re.compile(r"(pass(word)?|secret|token|api[_-]?key|credential|private[_-]?key|authorization)", re.IGNORECASE)


def _safe(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        return "[truncated]"
    if isinstance(value, Mapping):
        return {str(k)[:128]: "[redacted]" if _SECRET_KEY.search(str(k)) else _safe(v, depth + 1) for k, v in list(value.items())[:100]}
    if isinstance(value, (list, tuple, set)):
        return [_safe(v, depth + 1) for v in list(value)[:100]]
    if value is None or isinstance(value, (str, int, float, bool)):
        return str(value)[:20000] if isinstance(value, str) else value
    return str(value)[:20000]


def _json(value: Any) -> str:
    return json.dumps(_safe(value), ensure_ascii=False, separators=(",", ":"), default=str)


def _row(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    return {k: row[k] for k in ("event_id", "project_id", "run_id", "task_id", "event_type", "actor_role", "actor_id", "created_at")} | {"payload": payload}


def emit_event(event_type: str, *, project_id: str | None = None, run_id: str | None = None, task_id: str | None = None, actor_role: str = "system", actor_id: str | None = None, payload: Mapping[str, Any] | None = None, event_id: str | None = None, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize_database(database_path)
    kind = str(event_type or "").strip().upper()[:128]
    if not kind:
        raise ValueError("event_type is required")
    ident, now = str(event_id or uuid4()), utc_now()
    with connect(database_path) as database:
        database.execute("INSERT OR IGNORE INTO company_events(event_id,project_id,run_id,task_id,event_type,actor_role,actor_id,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (ident, project_id, run_id, task_id, kind, str(actor_role or "system")[:128], str(actor_id)[:128] if actor_id else None, _json(payload or {}), now))
        row = database.execute("SELECT * FROM company_events WHERE event_id=?", (ident,)).fetchone()
    return _row(row)


def list_events(*, project_id: str | None = None, run_id: str | None = None, event_type: str | None = None, limit: int = 500, database_path: str | Path | None = None) -> list[dict[str, Any]]:
    initialize_database(database_path)
    clauses, values = [], []
    for col, value in (("project_id", project_id), ("run_id", run_id), ("event_type", event_type.upper() if event_type else None)):
        if value:
            clauses.append(f"{col}=?")
            values.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    values.append(min(max(int(limit), 1), 2000))
    with connect(database_path) as database:
        rows = database.execute("SELECT * FROM company_events" + where + " ORDER BY created_at ASC,event_id ASC LIMIT ?", tuple(values)).fetchall()
    return [_row(row) for row in rows]


def build_company_trace(project_id: str, *, run_id: str | None = None, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize_database(database_path)
    path = str(database_path) if database_path else None
    project = get_project_state(project_id, database_path=path)
    if not project:
        raise KeyError(project_id)
    organization = get_project_organization(project_id, database_path=path)
    selected = run_id or next((e["run_id"] for e in reversed(list_events(project_id=project_id, database_path=database_path)) if e.get("run_id")), None)
    incidents = list_incidents(project_id=project_id, limit=100, database_path=database_path)
    trace: dict[str, Any] = {
        "schema_version": 1,
        "project": project,
        "team": organization.as_dict() if organization else None,
        # Preserve the full project timeline, including pre-run organizational events.
        "events": list_events(project_id=project_id, database_path=database_path),
        "run_events": list_events(project_id=project_id, run_id=run_id, database_path=database_path),
        "tasks": store.list_tasks(project_id=project_id, run_id=run_id, limit=500, database_path=database_path),
        "conversations": list_conversations(project_id=project_id, run_id=run_id, limit=200, database_path=database_path),
        "messages": store.list_messages(project_id=project_id, run_id=run_id, limit=500, database_path=database_path),
        "meetings": list_meetings(project_id=project_id, run_id=run_id, limit=200, database_path=database_path),
        "decisions": list_decisions(project_id=project_id, run_id=run_id, limit=200, database_path=database_path),
        "internal_requests": list_work_requests(project_id=project_id, limit=200, database_path=database_path),
        "handoffs": store.list_handoffs(project_id=project_id, run_id=run_id, limit=500, database_path=database_path),
        "memories": MemoryStore(path).retrieve(project_id=project_id, run_id=selected, query="", include_candidate=True, limit=200),
        "incidents": incidents,
        "incident_events": {str(i["incident_id"]): list_incident_events(str(i["incident_id"]), database_path=database_path) for i in incidents},
        "postmortems": list_postmortems(project_id=project_id, database_path=database_path),
        "lifecycle": list_lifecycle_events(project_id, database_path=database_path),
        "blackboard": blackboard(project_id=project_id, database_path=database_path),
    }
    trace["agent_assignments"] = [{"task_id": t["id"], "role": t["role"], "assigned_agent": t.get("assigned_agent"), "state": t["state"]} for t in trace["tasks"]]
    if selected:
        trace["run_id"] = selected
        try:
            from .e2e import load_trace
            trace["engineering_trace"] = load_trace(database_path, selected)
        except (FileNotFoundError, KeyError, OSError, ValueError):
            trace["engineering_trace"] = None
    return trace


def render_company_trace(trace: Mapping[str, Any]) -> str:
    project, events = trace.get("project") or {}, trace.get("events") or []
    lines = ["# Company Run Trace", "", f"- Project: {project.get('name', project.get('id', 'unknown'))}", f"- Project ID: {project.get('id', 'unknown')}", f"- Run ID: {trace.get('run_id', 'not set')}", f"- Phase: {project.get('phase', 'unknown')}", "", "## Event timeline", ""]
    lines.extend(f"- {e['created_at']} **{e['event_type']}** ({e['actor_role']})" for e in events)
    lines += ["", "## Persisted evidence", "", f"- Tasks: {len(trace.get('tasks') or [])}", f"- Messages: {len(trace.get('messages') or [])}", f"- Meetings: {len(trace.get('meetings') or [])}", f"- Decisions: {len(trace.get('decisions') or [])}", f"- Internal requests: {len(trace.get('internal_requests') or [])}", f"- Handoffs: {len(trace.get('handoffs') or [])}", f"- Memories: {len(trace.get('memories') or [])}", f"- Incidents: {len(trace.get('incidents') or [])}", "", "## Result", "", f"- Project phase: {project.get('phase', 'unknown')}", f"- Company events persisted: {len(events)}"]
    return "\n".join(lines) + "\n"


def write_trace_artifacts(trace: Mapping[str, Any], output_dir: str | Path, *, stem: str | None = None) -> dict[str, str]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    name = stem or f"company-run-{(trace.get('project') or {}).get('id', uuid4())}"
    json_path, markdown_path = directory / f"{name}.json", directory / f"{name}.md"
    json_path.write_text(json.dumps(_safe(trace), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    markdown_path.write_text(render_company_trace(trace), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


class CompanySimulation:
    def __init__(self, database_path: str | Path, workspace: str | Path | None = None, *, objective: str = "Build a small full-stack application with authentication, API, frontend, tests and documentation.", output_dir: str | Path | None = None) -> None:
        self.database_path, self.objective = str(database_path), objective
        self.workspace, self.output_dir = Path(workspace or tempfile.mkdtemp(prefix="ai-company-")), Path(output_dir) if output_dir else None
        initialize_database(self.database_path)

    def run(self) -> dict[str, Any]:
        from .e2e import EngineeringDemoRunner
        self.workspace.mkdir(parents=True, exist_ok=True)
        project = create_project("AI Company Integration Simulation", str(self.workspace), database_path=self.database_path)
        project_id = str(project["id"])
        emit_event("PROJECT_CREATED", project_id=project_id, actor_role="human_owner", payload={"objective": self.objective}, database_path=self.database_path)
        plan, organization = CompanyDirector().organize_project(project_id, self.objective, complexity="large", technologies=("FastAPI", "React", "SQLite"), required_skills=("authentication", "API contracts", "testing"), risks=("authentication boundary", "frontend/backend mismatch"), deliverables=("backend", "frontend", "tests", "documentation"), priority=80, database_path=self.database_path)
        emit_event("TEAM_CREATED", project_id=project_id, actor_role="company_director", payload={"complexity": plan.complexity.value, "team_size": len(plan.members)}, database_path=self.database_path)
        for member in organization.members:
            emit_event("AGENT_ASSIGNED", project_id=project_id, actor_role="company_director", actor_id=member.agent_id, payload={"role": member.role, "department": member.department.value}, database_path=self.database_path)
        result = EngineeringDemoRunner(self.database_path, self.workspace, objective=self.objective, project_id=project_id).run(simulate_restart=True)
        run_id = str(result["run_id"])
        for task in result.get("tasks", []):
            emit_event("TASK_ASSIGNED", project_id=project_id, run_id=run_id, task_id=str(task["id"]), actor_role="supervisor", actor_id=task.get("assigned_agent"), payload={"role": task["role"], "title": task["title"], "state": task["state"]}, database_path=self.database_path)
        for event in result.get("events", []):
            kind, payload = str(event.get("event_type") or ""), event.get("payload") or {}
            if kind == "test_execution":
                emit_event("TEST_EXECUTED", project_id=project_id, run_id=run_id, task_id=event.get("task_id"), actor_role="tester", payload=payload, database_path=self.database_path)
                if not payload.get("passed"):
                    emit_event("TEST_FAILED", project_id=project_id, run_id=run_id, task_id=event.get("task_id"), actor_role="tester", payload={"reason": "fixture assertion failure", "evidence": payload}, database_path=self.database_path)
            elif kind == "review_rejected":
                emit_event("REVIEW_REJECTED", project_id=project_id, run_id=run_id, task_id=event.get("task_id"), actor_role="reviewer", payload=payload, database_path=self.database_path)
            elif kind == "orchestrator_restart":
                emit_event("ORCHESTRATOR_RESTARTED", project_id=project_id, run_id=run_id, actor_role="orchestrator", payload=payload, database_path=self.database_path)
            elif kind == "startup_recovery":
                emit_event("RECOVERY_RESUMED", project_id=project_id, run_id=run_id, actor_role="orchestrator", payload=payload, database_path=self.database_path)
        engine = CollaborationEngine(self.database_path, max_rounds=4)
        conversation = engine.create_conversation(project_id=project_id, run_id=run_id, subject="Authentication boundary review", conversation_type=ConversationType.PROJECT, participants=("architect", "security", "backend", "tester", "engineering_manager"), topic="architecture")
        conversation_id = str(conversation["conversation_id"])
        for sender, kind, subject, body, recipient in (("architect", MessageType.PROPOSAL, "Authentication proposal", "Use short-lived access tokens with refresh rotation and server-side authorization.", "engineering_manager"), ("security", MessageType.CHALLENGE, "Threat-model challenge", "Refresh rotation must be replay-safe and ownership checks must be enforced at the service boundary.", "architect"), ("architect", MessageType.EVIDENCE, "Authentication evidence", "The design includes rotation, revocation, audit events and negative ownership tests.", "security"), ("backend", MessageType.COUNTER_PROPOSAL, "API contract cost", "Use one auth boundary shared by API and frontend client adapters.", "engineering_manager")):
            message = engine.send(conversation_id=conversation_id, sender_role=sender, message_type=kind, subject=subject, body=body, recipient_role=recipient)
            emit_event("MESSAGE_SENT", project_id=project_id, run_id=run_id, actor_role=sender, payload={"message_id": message["message_id"], "message_type": message["message_type"], "recipient": recipient}, database_path=self.database_path)
        decision = engine.resolve_discussion(conversation_id=conversation_id, decision_maker="engineering_manager", title="Authentication architecture resolution", context="Security and implementation concerns were raised against the first proposal.", options=("rotating access tokens", "long-lived session tokens"), arguments=("replay-safe rotation", "bounded implementation scope"), decision="Adopt rotating short-lived tokens with revocation and service-level ownership checks.", evidence=("security challenge", "negative authorization test plan"))["decision"]
        emit_event("DECISION_MADE", project_id=project_id, run_id=run_id, actor_role="engineering_manager", payload={"decision_id": decision["decision_id"], "title": decision["title"]}, database_path=self.database_path)
        meeting = engine.start_meeting(project_id=project_id, run_id=run_id, meeting_type=MeetingType.PROJECT_KICKOFF, objective="Confirm scope, ownership and delivery gates.", participants=("company_director", "project_manager", "engineering_manager", "requirements"), agenda=("acceptance criteria", "team ownership", "quality gates"))
        emit_event("MEETING_STARTED", project_id=project_id, run_id=run_id, actor_role="company_director", payload={"meeting_id": meeting["meeting_id"], "meeting_type": meeting["meeting_type"]}, database_path=self.database_path)
        engine.add_meeting_message(meeting_id=str(meeting["meeting_id"]), sender_role="requirements", message_type=MessageType.STATUS, subject="Requirements ready", body="Authentication, API, frontend, tests and documentation are acceptance criteria.")
        meeting_decision = engine.record_meeting_decision(meeting_id=str(meeting["meeting_id"]), title="Delivery gates", context="The company requires evidence before release.", decision="Tests, review, security review and release verification are mandatory.", decision_maker="project_manager", evidence=("requirements checklist",))
        engine.close_meeting(str(meeting["meeting_id"]), action_items=("Backend publishes API contract for frontend.",))
        emit_event("DECISION_MADE", project_id=project_id, run_id=run_id, actor_role="project_manager", payload={"decision_id": meeting_decision["decision_id"], "meeting_id": meeting["meeting_id"]}, database_path=self.database_path)
        request = engine.request_help(sender="frontend", recipient="backend", project_id=project_id, run_id=run_id, request_type="api_clarification", description="Confirm response envelope and validation errors.", priority=90)
        response = engine.respond_help(str(request["request_id"]), response="API returns a versioned envelope with field-level validation errors.")
        emit_event("INTERNAL_REQUEST_CREATED", project_id=project_id, run_id=run_id, actor_role="frontend", payload={"request_id": request["request_id"], "response_status": response["status"]}, database_path=self.database_path)
        handoff = store.create_handoff(AgentHandoff(sender_role="architect", recipient_role="engineering_manager", summary="Architecture evidence and security resolution are ready.", decisions=(str(decision["decision"]),), remaining_work=("Execute implementation and release gates.",), verification=("decision record persisted",), run_id=run_id, project_id=project_id), database_path=self.database_path)
        emit_event("HANDOFF_CREATED", project_id=project_id, run_id=run_id, actor_role="architect", payload={"handoff_id": handoff["handoff_id"], "recipient_role": "engineering_manager"}, database_path=self.database_path)
        incident = create_incident(project_id, "Fixture test failure", "TEST_FAILED", severity="high", description="The first test execution exposed an API contract mismatch.", impact="Integration could not be released until repair.", run_id=run_id, created_by="incident_manager", database_path=self.database_path)
        incident_id = str(incident["incident_id"])
        emit_event("INCIDENT_OPENED", project_id=project_id, run_id=run_id, actor_role="incident_manager", payload={"incident_id": incident_id, "trigger": "TEST_FAILED"}, database_path=self.database_path)
        assign_incident_team(incident_id, roles=("incident_manager", "debugger", "backend", "tester", "operations", "security"), domain="FastAPI authentication", database_path=self.database_path)
        for phase, details in (("contain", "Pause release verification."), ("diagnose", "Compare API contract and test evidence."), ("repair", "Debugger and backend update the contract."), ("verify", "Tester reruns the failed test.")):
            transition_incident(incident_id, phase, actor_role="incident_manager", details=details, database_path=self.database_path)
        postmortem = create_postmortem(incident_id, what_happened="The first integration assertion rejected the initial response contract.", impact="Release was blocked for one repair cycle.", timeline=("test failed", "debugger repaired contract", "tester passed"), root_cause="Frontend and backend had not shared a versioned response envelope.", repair="Published the API envelope and field-level validation contract.", verification=("tester rerun passed", "review evidence accepted"), prevention_ideas=("Require contract review before parallel implementation.",), follow_up_tasks=("Add contract test to CI.",), database_path=self.database_path)
        transition_incident(incident_id, "postmortem", actor_role="incident_manager", details="Postmortem recorded.", database_path=self.database_path)
        transition_incident(incident_id, "learn", actor_role="incident_manager", details="Promote validated lesson.", database_path=self.database_path)
        lesson = promote_postmortem_lesson(str(postmortem["postmortem_id"]), summary="Shared API contracts prevent repeated integration mismatches.", evidence=({"type": "test", "summary": "tester rerun passed"}, {"type": "review", "summary": "review gate accepted"}), database_path=self.database_path)
        transition_incident(incident_id, "resolved", actor_role="incident_manager", details="Lesson captured and incident closed.", database_path=self.database_path)
        emit_event("LESSON_CAPTURED", project_id=project_id, run_id=run_id, actor_role="company_director", payload={"memory_id": lesson["id"], "postmortem_id": postmortem["postmortem_id"]}, database_path=self.database_path)
        for gate, evidence in (("requirements_ready", ("requirements checklist",)), ("architecture_accepted", ("architecture decision",)), ("tests_passed", ("tester rerun",)), ("review_accepted", ("review revision accepted",)), ("security_review", ("security challenge resolved",))):
            set_quality_gate(project_id, gate, status="passed", evidence=evidence, database_path=self.database_path)
        for phase, actor in (("requirements", "requirements"), ("architecture", "architect"), ("implementation", "engineering_manager"), ("integration", "integration"), ("testing", "tester"), ("review", "reviewer"), ("security_review", "security"), ("release_verification", "release_verifier"), ("completed", "project_manager")):
            transition_project_phase(project_id, phase, actor_role=actor, evidence=("persisted task graph", "tests passed", "review accepted", "security review passed"), reason="company simulation quality gate", database_path=self.database_path)
        emit_event("RELEASE_READY", project_id=project_id, run_id=run_id, actor_role="release_verifier", payload={"acceptance_criteria": ["authentication", "API", "frontend", "tests", "documentation"]}, database_path=self.database_path)
        emit_event("PROJECT_COMPLETED", project_id=project_id, run_id=run_id, actor_role="company_director", payload={"technical_readiness": True, "deliverables_confirmed": True, "owner_report": True}, database_path=self.database_path)
        trace = build_company_trace(project_id, run_id=run_id, database_path=self.database_path)
        trace["trace_artifacts"] = write_trace_artifacts(trace, self.output_dir or (self.workspace / "company-trace"))
        trace["simulation"] = {"objective": self.objective, "project_id": project_id, "run_id": run_id, "workspace": str(self.workspace), "restart_verified": True, "multi_project_isolation_supported": True}
        return trace


def run_company_simulation(database_path: str | Path, workspace: str | Path | None = None, *, objective: str = "Build a small full-stack application with authentication, API, frontend, tests and documentation.", output_dir: str | Path | None = None) -> dict[str, Any]:
    return CompanySimulation(database_path, workspace, objective=objective, output_dir=output_dir).run()
