from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from app.db import DATABASE_PATH, connect, create_project, initialize_database, utc_now
from app.memory import MemoryStore
from . import store
from .models import AgentHandoff, CoordinationTask, MessageType, TaskState
from .supervisor import Supervisor

DEFAULT_OBJECTIVE = "Create a small service with an API endpoint, validation, tests, documentation and a simple frontend client."

def _safe(value: Any, limit: int = 4000) -> Any:
    if isinstance(value, str): return value[:limit]
    if isinstance(value, Mapping): return {str(k)[:128]: _safe(v) for k,v in list(value.items())[:100]}
    if isinstance(value, (list, tuple, set)): return [_safe(v, 2000) for v in list(value)[:100]]
    return value if value is None or isinstance(value, (int,float,bool)) else str(value)[:limit]

def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""): digest.update(chunk)
    return digest.hexdigest()

class TraceRecorder:
    def __init__(self, database_path: str|os.PathLike[str]|None, run_id: str, *, objective: str|None=None, project_id: str|None=None, path: str|os.PathLike[str]|None=None):
        self.database_path = str(database_path or DATABASE_PATH)
        base = Path(self.database_path).expanduser()
        self.path = Path(path) if path else base.with_name(f"{base.stem}.trace.{run_id}.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id, self._lock = str(run_id), threading.RLock()
        try: data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except (OSError, ValueError, json.JSONDecodeError): data = {}
        self.data = data if isinstance(data, dict) else {}
        self.data.setdefault("schema_version", 1); self.data.setdefault("run_id", self.run_id)
        self.data.setdefault("events", []); self.data.setdefault("created_at", utc_now())
        if objective: self.data["objective"] = str(objective)[:20000]
        if project_id: self.data["project_id"] = str(project_id)
        self._flush()
    def _flush(self) -> None:
        temp = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        temp.replace(self.path)
    def event(self, event_type: str, *, actor_role: str, task_id: str|None=None, payload: Mapping[str,Any]|None=None) -> dict[str,Any]:
        with self._lock:
            events = self.data.setdefault("events", [])
            item = {"event_id":str(uuid4()), "sequence":len(events)+1, "event_type":str(event_type)[:128], "actor_role":str(actor_role)[:128], "task_id":task_id, "created_at":utc_now(), "payload":_safe(dict(payload or {}))}
            events.append(item); self._flush(); return dict(item)
    def update(self, **values: Any) -> None:
        with self._lock: self.data.update({str(k):_safe(v) for k,v in values.items()}); self._flush()
    def snapshot(self) -> dict[str,Any]:
        with self._lock: return json.loads(json.dumps(self.data, default=str))
    @property
    def trace_path(self) -> str: return str(self.path)

class FixtureWorkspace:
    def __init__(self, root: str|os.PathLike[str], trace: TraceRecorder):
        self.root = Path(root).expanduser().resolve(); self.root.mkdir(parents=True, exist_ok=True); self.trace = trace
    def _path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if path != self.root and self.root not in path.parents: raise ValueError("fixture path escapes workspace")
        return path
    def write(self, relative: str, content: str, *, task_id: str, role: str) -> str:
        path = self._path(relative); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(str(content), encoding="utf-8")
        rel = str(path.relative_to(self.root)).replace("\\", "/")
        self.trace.event("file_change", actor_role=role, task_id=task_id, payload={"path":rel, "sha256":_sha(path), "bytes":path.stat().st_size})
        return rel
    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)).replace("\\", "/") for p in self.root.rglob("*") if p.is_file())

class EngineeringDemoRunner:
    def __init__(self, database_path: str|os.PathLike[str], workspace: str|os.PathLike[str]|None=None, *, objective: str=DEFAULT_OBJECTIVE, project_id: str|None=None):
        self.database_path=str(database_path); initialize_database(self.database_path)
        self.objective=str(objective); self.workspace_path=Path(workspace or tempfile.mkdtemp(prefix="ai-engineer-e2e-"))
        self.project_id=project_id; self.run_id=None; self.trace=None; self.workspace=None
        self.supervisor=Supervisor(self.database_path, max_retries=2); self.task_ids={}; self.test_failed=False; self.review_rejected=False; self.restart_count=0
    def _project(self):
        if not self.project_id: self.project_id=str(create_project("phase6-e2e-demo", str(self.workspace_path), database_path=self.database_path)["id"])
    def _task(self, key: str) -> dict[str,Any]:
        item=store.get_task(self.task_ids[key], database_path=self.database_path)
        if not item: raise KeyError(self.task_ids[key])
        return item
    def _done(self, key: str) -> bool:
        return key in self.task_ids and str(self._task(key)["state"]) == TaskState.COMPLETED.value
    def _start(self, key: str) -> dict[str,Any]:
        assert self.trace
        item=self._task(key)
        if str(item["state"]) == TaskState.COMPLETED.value: return item
        running=self.supervisor._ensure_running(str(item["id"]))
        self.trace.event("task_started", actor_role=str(running["role"]), task_id=str(running["id"]), payload={"title":running["title"],"dependencies":running.get("dependencies",[])})
        return running
    def _message(self, sender: str, kind: MessageType, subject: str, body: str, *, task_id: str|None=None, recipient: str|None=None, references: Iterable[str]=()):
        assert self.trace and self.run_id and self.project_id
        result=self.supervisor.bus.publish(sender_role=sender, recipient_role=recipient, message_type=kind, subject=subject, body=body, run_id=self.run_id, project_id=self.project_id, task_id=task_id, references=list(references))
        self.trace.event("message_published", actor_role=sender, task_id=task_id, payload={"message_id":result.get("message_id"),"message_type":result.get("message_type"),"recipient_role":recipient,"subject":subject})
        return result
    def _handoff(self, sender: str, recipient: str, task_id: str, summary: str, *, files: Iterable[str]=(), evidence: Iterable[str]=()):
        assert self.trace and self.run_id and self.project_id
        record=store.create_handoff(AgentHandoff(sender_role=sender, recipient_role=recipient, summary=summary, changed_files=tuple(files), verification=tuple(evidence), run_id=self.run_id, project_id=self.project_id, task_id=task_id), database_path=self.database_path)
        self.trace.event("handoff", actor_role=sender, task_id=task_id, payload={"handoff_id":record["handoff_id"],"recipient_role":recipient,"summary":summary,"changed_files":list(files),"evidence":list(evidence)})
        self._message(sender, MessageType.HANDOFF, f"{sender} -> {recipient}", summary, task_id=task_id, recipient=recipient, references=evidence)
    def _finish(self, key: str, summary: str, evidence: Iterable[str], *, files: Iterable[str]=(), handoff_to: str|None=None):
        assert self.trace
        task=self._start(key)
        if str(task["state"]) == TaskState.COMPLETED.value: return
        evidence=list(evidence); result=self.supervisor.record_result(str(task["id"]), summary=summary, evidence=evidence, approved=True)
        self.trace.event("task_completed", actor_role=str(task["role"]), task_id=str(task["id"]), payload={"summary":summary,"evidence":evidence,"state":result.get("state"),"changed_files":list(files)})
        if handoff_to: self._handoff(str(task["role"]), handoff_to, str(task["id"]), summary, files=files, evidence=evidence)
    def _add_support(self, started: Mapping[str,Any]):
        assert self.run_id and self.project_id and self.trace
        for item in started["tasks"]: self.task_ids[str(item["role"])]=str(item["id"])
        specs=[("debugger","Repair failing tests",(self.task_ids["integration"],),("service.py",)),("docs","Document the service",(self.task_ids["integration"],),("README.md",)),("revision","Apply reviewer revision",(self.task_ids["reviewer"],),("REVIEW_NOTES.md",))]
        for key,title,deps,scope in specs:
            item=store.create_task(CoordinationTask(project_id=self.project_id,run_id=self.run_id,title=title,description=title,role="implementer" if key=="revision" else key,dependencies=deps,expected_outputs=("summary","evidence"),acceptance_criteria=("Persist evidence.",),scope=scope,writer=True),database_path=self.database_path)
            self.task_ids[key]=str(item["id"]); self.trace.event("task_created",actor_role="supervisor",task_id=str(item["id"]),payload={"role":item["role"],"title":title,"dependencies":list(deps)})
        with connect(self.database_path) as database:
            row=database.execute("SELECT task_ids_json FROM autonomy_runs WHERE id=?",(self.run_id,)).fetchone(); ids=json.loads(row["task_ids_json"] or "[]") if row else []
            ids.extend(x for x in self.task_ids.values() if x not in ids); database.execute("UPDATE autonomy_runs SET task_ids_json=?,updated_at=? WHERE id=?",(json.dumps(ids),utc_now(),self.run_id))
    def _write(self, relative: str, content: str, task: Mapping[str,Any]) -> str:
        assert self.workspace; return self.workspace.write(relative,content,task_id=str(task["id"]),role=str(task["role"]))
    def _parallel(self):
        assert self.trace
        keys=[k for k in ("backend","frontend","implementer") if not self._done(k)]
        if not keys: return
        started={k:self._start(k) for k in keys}; self.trace.event("parallel_batch_started",actor_role="supervisor",payload={"roles":keys,"task_ids":[x["id"] for x in started.values()]})
        def write(key):
            task=started[key]
            if key=="backend": return key,self._write("service.py","def calculate_value():\n    return 2\n\ndef health():\n    return {'status':'ok'}\n",task)
            if key=="frontend": return key,self._write("client.py","from service import calculate_value\n\ndef fetch_value():\n    return calculate_value()\n",task)
            return key,self._write("contracts.py","EXPECTED_VALUE = 3\n",task)
        changes={}
        with ThreadPoolExecutor(max_workers=len(keys)) as pool:
            for future in as_completed([pool.submit(write,k) for k in keys]):
                key,path=future.result(); changes[key]=path
        self.trace.event("parallel_batch_completed",actor_role="supervisor",payload={"roles":list(changes),"files":list(changes.values())})
        for key in keys: self._finish(key,f"{key} implementation persisted.",["file write completed","sha256 recorded"],files=[changes[key]],handoff_to="integration")
    def _lock_probe(self):
        assert self.trace
        first,second,res=str(uuid4()),str(uuid4()),"shared/conflict-probe.py"
        owner_a=self.task_ids["backend"]; owner_b=self.task_ids["frontend"]; acquired=store.acquire_lock(res,owner_a,"backend",database_path=self.database_path); denied=not store.acquire_lock(res,owner_b,"frontend",database_path=self.database_path); store.release_lock(res,owner_a,database_path=self.database_path)
        self.trace.event("write_conflict_protection",actor_role="supervisor",payload={"resource":res,"first_acquired":acquired,"second_denied":denied})
        if not (acquired and denied): raise RuntimeError("single-writer conflict protection failed")
    def _tester(self, retry: bool):
        assert self.trace and self.workspace
        task=self._start("tester")
        if not retry: self._write("tests/test_service.py","import unittest\nfrom service import calculate_value\n\nclass ServiceTests(unittest.TestCase):\n    def test_value_contract(self): self.assertEqual(calculate_value(), 3)\n\nif __name__ == '__main__': unittest.main()\n",task)
        command=[sys.executable,"-m","unittest","discover","-s","tests","-q"]; result=subprocess.run(command,cwd=str(self.workspace.root),capture_output=True,text=True,timeout=30,check=False)
        payload={"command":command,"returncode":result.returncode,"passed":result.returncode==0,"stdout_tail":result.stdout[-1500:],"stderr_tail":result.stderr[-1500:],"retry":retry}; self.trace.event("test_execution",actor_role="tester",task_id=str(task["id"]),payload=payload)
        if result.returncode==0: self._finish("tester","Tests passed after repair.",["unittest returned 0"],files=["tests/test_service.py"],handoff_to="reviewer")
        else:
            self.supervisor.record_failure(str(task["id"]),reason="Fixture test failure; debugger must repair service.py."); self.test_failed=True
            self._message("tester",MessageType.BLOCKER,"Test failure","Debugger must repair the implementation.",task_id=str(task["id"]),recipient="debugger",references=["tests/test_service.py","service.py"])
            self._handoff("tester","debugger",str(task["id"]),"Repair the failing value contract.",files=["tests/test_service.py"],evidence=["unittest returned non-zero"])
        return payload
    def _review(self):
        task=self._start("reviewer")
        if not self.review_rejected:
            self.supervisor.request_revision(str(task["id"]),reason="Reviewer rejected first pass; explicit review evidence is required."); self.review_rejected=True
            assert self.trace; self.trace.event("review_rejected",actor_role="reviewer",task_id=str(task["id"]),payload={"reason":"explicit review artifact missing"})
            self._message("reviewer",MessageType.REVISION_REQUEST,"Revision requested","Add REVIEW_NOTES.md and resubmit.",task_id=str(task["id"]),recipient="implementer")
            self._handoff("reviewer","implementer",str(task["id"]),"Revision artifact required.",evidence=["review gate rejected first pass"])
        else: self._finish("reviewer","Review accepted after revision evidence.",["review checklist passed","test evidence available"],handoff_to="release_verifier")
    def _release(self):
        assert self.trace and self.workspace
        task=self._start("release_verifier"); required={"service.py","client.py","contracts.py","app.py","README.md","REVIEW_NOTES.md","tests/test_service.py"}; missing=sorted(required-set(self.workspace.files()))
        result=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-q"],cwd=str(self.workspace.root),capture_output=True,text=True,timeout=30,check=False)
        self.trace.event("release_verification",actor_role="release_verifier",task_id=str(task["id"]),payload={"missing_files":missing,"test_returncode":result.returncode,"tests_passed":result.returncode==0,"acceptance_criteria":sorted(required)})
        if missing or result.returncode: raise RuntimeError(f"release verification failed: missing={missing}, returncode={result.returncode}")
        self._finish("release_verifier","Release verification passed with evidence.",["all required files exist","tests returned 0","review accepted"],files=sorted(required),handoff_to="supervisor")
    def _execute(self, simulate_restart: bool):
        assert self.trace and self.workspace and self.run_id and self.project_id
        if not self._done("requirements"): self._finish("requirements","Acceptance criteria derived from objective.",["endpoint","validation","tests","documentation","client contract"],handoff_to="planner")
        if not self._done("planner"): self._finish("planner","Deliverables decomposed into a dependency-aware task DAG.",["independent scopes","integration gate","verification gates"],handoff_to="architect")
        if not self._done("architect"): self._finish("architect","Architecture defines service, client, contract, tests, and release boundaries.",["service.py","client.py","contracts.py","app.py"],handoff_to="backend")
        self._parallel(); self._lock_probe()
        if not self._done("integration"):
            task=self._start("integration"); self._finish("integration","Components integrated behind an endpoint.",["imports resolve","boundaries preserved"],files=[self._write("app.py","from service import health\n\ndef endpoint(): return health()\n",task)],handoff_to="tester")
        if not self._done("docs"):
            task=self._start("docs"); self._finish("docs","Runnable fixture documentation persisted.",["README.md exists"],files=[self._write("README.md","# Phase 6 Demo Service\n\nA validated service, client adapter, tests, and release evidence.\n",task)],handoff_to="release_verifier")
        if not self._done("tester"):
            if not self.test_failed: self._tester(retry=False)
            if self.test_failed and simulate_restart and self.restart_count==0: self._restart()
            if self.test_failed and not self._done("debugger"):
                task=self._start("debugger"); self._finish("debugger","Debugger repaired implementation without weakening tests.",["service.py satisfies assertion","test retained"],files=[self._write("service.py","def calculate_value():\n    return 3\n\ndef health():\n    return {'status':'ok'}\n",task)],handoff_to="tester")
            if self.test_failed and not self._done("tester"): self._tester(retry=True)
        if not self._done("reviewer"): self._review()
        if self.review_rejected and not self._done("reviewer"): self._review()
        if self.review_rejected and not self._done("revision"):
            task=self._start("revision"); self._finish("revision","Reviewer revision artifact persisted.",["rejection resolved","artifact available"],files=[self._write("REVIEW_NOTES.md","Review revision accepted after test and artifact evidence.\n",task)],handoff_to="reviewer")
        if not self._done("release_verifier"): self._release()
        return self._finalize()
    def _restart(self):
        assert self.trace and self.run_id
        self.restart_count+=1; self.trace.event("orchestrator_restart",actor_role="orchestrator",payload={"reason":"simulated restart after test failure","count":self.restart_count})
        self.supervisor=Supervisor(self.database_path,max_retries=2); self.trace=TraceRecorder(self.database_path,self.run_id,objective=self.objective,project_id=self.project_id); status=self.supervisor.status(self.run_id)
        self.trace.event("startup_recovery",actor_role="orchestrator",payload={"run_status":status.get("run_status"),"failed_tasks":status.get("failed"),"completed_tasks":status.get("states",{}).get(TaskState.COMPLETED.value,0)})
    def _finalize(self):
        assert self.trace and self.run_id and self.project_id and self.workspace
        status=self.supervisor.status(self.run_id); memories=MemoryStore(self.database_path).retrieve(project_id=self.project_id,query="",run_id=self.run_id,include_candidate=True,limit=100); lessons=[x for x in memories if x.get("lifecycle") in {"validated","trusted"}]
        if not lessons:
            memory=MemoryStore(self.database_path).create(project_id=self.project_id,run_id=self.run_id,memory_type="lesson",summary="Repair implementation rather than weakening assertions.",content={"workflow":"tester -> debugger -> tester -> reviewer","pattern":"preserve failing test evidence"},evidence=[{"type":"tests","summary":"fixture tests returned 0"},{"type":"review","summary":"review accepted after revision"}],role="supervisor",task_type="e2e_validation")
            lessons=[MemoryStore(self.database_path).promote(str(memory["id"]),evidence=[{"type":"tests","summary":"tests passed after repair"},{"type":"review","summary":"review gate accepted"}],target="validated")]
        self.trace.event("final_result",actor_role="supervisor",payload={"completed":bool(status.get("complete")),"run_status":status.get("run_status"),"lesson_ids":[x.get("id") for x in lessons],"evidence":["messages","handoffs","dependencies","parallel execution","write lock","real tests","restart recovery","validated lesson"]})
        trace=self.trace.snapshot(); trace.update({"project_id":self.project_id,"run_id":self.run_id,"objective":self.objective,"tasks":status.get("tasks",[]),"agent_assignments":[{"task_id":t.get("id"),"role":t.get("role"),"assigned_agent":t.get("assigned_agent"),"state":t.get("state")} for t in status.get("tasks",[])],"messages":store.list_messages(run_id=self.run_id,limit=500,database_path=self.database_path),"handoffs":store.list_handoffs(run_id=self.run_id,limit=500,database_path=self.database_path),"lessons":lessons,"files":self.workspace.files(),"final_result":{"completed":bool(status.get("complete")),"run_status":status.get("run_status"),"evidence":["all required files exist","tests returned 0","review accepted after revision"]},"trace_path":self.trace.trace_path})
        self.trace.update(**{key:trace[key] for key in ("project_id","tasks","agent_assignments","messages","handoffs","lessons","files","final_result","trace_path")})
        return trace
    def run(self, *, simulate_restart: bool=True):
        self._project(); started=self.supervisor.start_objective(project_id=str(self.project_id),objective=self.objective); self.run_id=str(started["run_id"]); self.trace=TraceRecorder(self.database_path,self.run_id,objective=self.objective,project_id=self.project_id); self.workspace=FixtureWorkspace(self.workspace_path,self.trace); self.trace.event("objective_received",actor_role="supervisor",payload={"objective":self.objective,"project_id":self.project_id}); self._add_support(started); return self._execute(simulate_restart)
    def resume(self, run_id: str):
        self.run_id=str(run_id)
        with connect(self.database_path) as database: row=database.execute("SELECT project_id,goal FROM autonomy_runs WHERE id=?",(self.run_id,)).fetchone()
        if not row: raise KeyError(run_id)
        self.project_id,self.objective=str(row["project_id"]),str(row["goal"]); self.supervisor=Supervisor(self.database_path,max_retries=2); self.trace=TraceRecorder(self.database_path,self.run_id,objective=self.objective,project_id=self.project_id); self.workspace=FixtureWorkspace(self.workspace_path,self.trace)
        tasks=store.list_tasks(run_id=self.run_id,limit=500,database_path=self.database_path)
        for task in tasks: self.task_ids["revision" if task["title"]=="Apply reviewer revision" else str(task["role"])]=str(task["id"])
        self.test_failed=any(t["role"]=="tester" and t["state"]==TaskState.FAILED.value for t in tasks); self.review_rejected=any(m["message_type"]==MessageType.REVISION_REQUEST.value for m in store.list_messages(run_id=self.run_id,limit=500,database_path=self.database_path))
        return self._execute(False)

def run_engineering_demo(database_path: str|os.PathLike[str], workspace: str|os.PathLike[str]|None=None, *, objective: str=DEFAULT_OBJECTIVE):
    return EngineeringDemoRunner(database_path,workspace,objective=objective).run()

def load_trace(database_path: str|os.PathLike[str]|None, run_id: str):
    base=Path(database_path or DATABASE_PATH).expanduser(); path=base.with_name(f"{base.stem}.trace.{run_id}.json")
    if not path.exists(): raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))

def get_trace_for_run(run_id: str, *, database_path: str|os.PathLike[str]|None=None):
    with connect(database_path) as database:
        if not database.execute("SELECT 1 FROM autonomy_runs WHERE id=?",(run_id,)).fetchone(): raise KeyError(run_id)
    return load_trace(database_path,run_id)



