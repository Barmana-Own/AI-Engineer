from __future__ import annotations
import hashlib,json,os,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Iterable
from uuid import uuid4
from app.config import settings
from app.db import connect,initialize_database,list_autonomy_runs,list_tasks,utc_now
from app.memory import MemoryStore
from app.memory.sanitizer import sanitize_memory

TERMINAL={"accepted","rejected","rolled_back"}
ACTIVE={"candidate","diagnosed","planned","in_progress","tested"}

def _j(v,f):
    try:return json.loads(str(v or ""))
    except (TypeError,ValueError,json.JSONDecodeError):return f
def _ss(values,limit,item_limit=500):
    out=[]
    for v in values:
        s=str(v or "").strip()
        if s and s not in out:out.append(s[:item_limit])
        if len(out)>=limit:break
    return out
def _sw(v):return {"critical":1.0,"high":.82,"medium":.56,"low":.28}.get(str(v or "").casefold(),.35)
def _rj(r,k,f):return _j(r[k],f) if r and k in r.keys() else f
def _cand(r):
    return {"id":r["id"],"project_id":r["project_id"],"run_id":r["run_id"],"problem":r["problem"],"evidence":_rj(r,"evidence_json",[]),"severity":r["severity"],"affected_modules":_rj(r,"affected_modules_json",[]),"proposed_outcome":r["proposed_outcome"],"estimated_risk":r["estimated_risk"],"expected_verification":_rj(r,"expected_verification_json",[]),"status":r["status"],"priority_score":float(r["priority_score"] or 0),"attempts":int(r["attempts"] or 0),"failure_signature":r["failure_signature"],"last_attempt_at":r["last_attempt_at"],"next_attempt_after":r["next_attempt_after"],"created_at":r["created_at"],"updated_at":r["updated_at"]}
def _cycle(r):
    return {"id":r["id"],"candidate_id":r["candidate_id"],"project_id":r["project_id"],"run_id":r["run_id"],"stage":r["stage"],"baseline_commit":r["baseline_commit"],"baseline_status":r["baseline_status"],"checkpoint_ref":r["checkpoint_ref"],"expected_files":_rj(r,"expected_files_json",[]),"expected_tests":_rj(r,"expected_tests_json",[]),"tests_before":_rj(r,"tests_before_json",{}),"tests_after":_rj(r,"tests_after_json",{}),"review_result":_rj(r,"review_result_json",{}),"regressions":_rj(r,"regressions_json",[]),"assessment":_rj(r,"assessment_json",{}),"lesson_memory_id":r["lesson_memory_id"],"confidence":float(r["confidence"] or 0),"follow_up_tasks":_rj(r,"follow_up_tasks_json",[]),"error":r["error"],"started_at":r["started_at"],"finished_at":r["finished_at"],"updated_at":r["updated_at"]}

class SelfImprovementEngine:
    def __init__(self,database_path=None,*,repo_root=None,allowed_roots=None):
        self.database_path=database_path;initialize_database(database_path)
        configured=repo_root or getattr(settings,"autonomous_repo_root","") or os.getenv("AI_ENGINE_PROJECT_ROOT",os.getcwd())
        self.repo_root=self._resolve(Path(configured))
        roots=list(allowed_roots) if allowed_roots is not None else [x.strip() for x in str(getattr(settings,"autonomous_allowed_project_roots","")).split(",") if x.strip()]
        self.allowed_roots=tuple(self._resolve(Path(x)) for x in (roots or [self.repo_root]))
        self.max_changes=max(1,int(getattr(settings,"autonomous_max_changes_per_run",1)));self.max_retries=max(0,int(getattr(settings,"autonomous_max_retries",2)));self.max_runtime=max(60,int(getattr(settings,"autonomous_max_runtime_seconds",1800)));self.max_files=max(1,int(getattr(settings,"autonomous_max_files_changed",8)))
    @staticmethod
    def _resolve(p):
        try:return p.expanduser().resolve()
        except OSError:return p.expanduser().absolute()
    def _safe_repo(self,root=None):
        p=self._resolve(Path(root or self.repo_root))
        if not p.is_dir() or not any(p==a or a in p.parents for a in self.allowed_roots):raise ValueError("Improvement repository root is outside the allowed roots")
        if not (p/".git").exists():raise ValueError("Improvement checkpoint requires a Git repository")
        return p
    def _git(self,root,*args,timeout=60):
        env=os.environ.copy();env.update({"GIT_TERMINAL_PROMPT":"0","GCM_INTERACTIVE":"Never","GIT_ASKPASS":"echo","GIT_EDITOR":"true","GIT_PAGER":"cat","NO_COLOR":"1"})
        return subprocess.run(["git",*args],cwd=str(root),env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,shell=False,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    def _gc(self,i):
        with connect(self.database_path) as d:r=d.execute("SELECT * FROM improvement_candidates WHERE id=?",(i,)).fetchone()
        return _cand(r) if r else None
    def _gx(self,i):
        with connect(self.database_path) as d:r=d.execute("SELECT * FROM improvement_cycles WHERE id=?",(i,)).fetchone()
        return _cycle(r) if r else None
    def list_candidates(self,project_id=None,*,statuses=None,limit=50):
        c=[];v=[]
        if project_id:c.append("project_id=?");v.append(project_id)
        s=[str(x).casefold() for x in (statuses or ())]
        if s:c.append("status IN ("+(",".join("?" for _ in s))+")");v+=s
        w=" WHERE "+" AND ".join(c) if c else ""
        with connect(self.database_path) as d:rows=d.execute(f"SELECT * FROM improvement_candidates{w} ORDER BY priority_score DESC,updated_at DESC LIMIT ?",(*v,max(1,min(int(limit),200)))).fetchall()
        return [_cand(r) for r in rows]
    def list_cycles(self,project_id=None,*,candidate_id=None,limit=50):
        c=[];v=[]
        if project_id:c.append("project_id=?");v.append(project_id)
        if candidate_id:c.append("candidate_id=?");v.append(candidate_id)
        w=" WHERE "+" AND ".join(c) if c else ""
        with connect(self.database_path) as d:rows=d.execute(f"SELECT * FROM improvement_cycles{w} ORDER BY updated_at DESC LIMIT ?",(*v,max(1,min(int(limit),200)))).fetchall()
        return [_cycle(r) for r in rows]
    def observe(self,project_id,*,repo_root=None):
        out=[]
        try:tasks=list_tasks(project_id)
        except Exception:tasks=[]
        for x in tasks:
            status=str(x.get("status") or "").casefold();retries=int(x.get("retry_count") or 0);err=str(x.get("error") or "").strip()
            if status=="failed" or err:out.append({"kind":"agent_failure","problem":err or "Agent task failed.","severity":"high" if status=="failed" else "medium","module":str(x.get("mode") or "orchestrator"),"evidence":[{"source":"agent_tasks","task_id":x.get("id"),"status":status}]})
            if retries:out.append({"kind":"retries","problem":"Agent task required repeated retries.","severity":"medium","module":str(x.get("mode") or "orchestrator"),"frequency":retries,"evidence":[{"source":"agent_tasks","task_id":x.get("id"),"retry_count":retries}]})
        try:runs=list_autonomy_runs(project_id,limit=100)
        except Exception:runs=[]
        for x in runs:
            if str(x.get("status") or "").casefold()=="failed":out.append({"kind":"autonomy_failure","problem":str(x.get("error") or "Autonomous run failed."),"severity":"high","module":"autonomy","evidence":[{"source":"autonomy_runs","run_id":x.get("id")}]})
        root=self._resolve(Path(repo_root or self.repo_root));skip={".git","node_modules",".venv","venv","backups","data","__pycache__"};ext={".py",".ts",".tsx",".js",".md",".toml",".yaml",".yml"}
        if root.is_dir():
            n=0
            for p in root.rglob("*"):
                if n>=400:break
                if not p.is_file() or p.suffix.casefold() not in ext or any(q.casefold() in skip for q in p.parts):continue
                try:text=p.read_text(encoding="utf-8",errors="replace")
                except OSError:continue
                n+=1
                for marker in ("TODO","FIXME"):
                    count=len(re.findall(rf"\b{marker}\b",text,re.I))
                    if count:
                        rel=str(p.relative_to(root)).replace("\\","/")
                        out.append({"kind":"maintenance_hotspot","problem":f"{marker} marker remains in a maintained module.","severity":"low","module":rel,"frequency":min(count,10),"evidence":[{"source":marker,"file":rel,"count":count}]})
        return out[:100]
    @staticmethod
    def diagnose(observations):
        groups={}
        for x in observations:
            problem=str(x.get("problem") or "").strip()
            if not problem:continue
            module=str(x.get("module") or "").replace("\\","/")
            sig=hashlib.sha256((problem.casefold()+"|"+module+"|"+str(x.get("kind") or "")).encode()).hexdigest()[:20]
            groups.setdefault(sig,[]).append({"kind":str(x.get("kind") or "observation"),"problem":problem[:4000],"severity":str(x.get("severity") or "medium").casefold(),"module":module,"evidence":list(x.get("evidence") or [])[:20],"frequency":max(int(x.get("frequency") or 1),1)})
        out=[]
        for sig,items in groups.items():
            first=items[0];freq=min(sum(x["frequency"] for x in items),100);sev=max(items,key=lambda x:_sw(x["severity"]))["severity"]
            out.append({"failure_signature":sig,"problem":first["problem"],"evidence":[e for x in items for e in x["evidence"] if isinstance(e,dict)][:40],"severity":sev,"affected_modules":_ss((x["module"] for x in items),20),"proposed_outcome":f"Resolve the observed {first['kind']} without regressing existing behavior.","estimated_risk":"high" if sev in {"critical","high"} else "medium","expected_verification":["Run the focused regression test.","Run the existing orchestrator test suite.","Review the resulting diff and changed-file scope."],"frequency":freq,"confidence":min(.95,.45+freq*.05)})
        return sorted(out,key=lambda x:(_sw(x["severity"]),x["frequency"]),reverse=True)
    def propose(self,project_id,observations=None):
        for x in self.diagnose(list(observations) if observations is not None else self.observe(project_id)):
            problem,_,ev,_=sanitize_memory(x["problem"],{"frequency":x["frequency"],"confidence":x["confidence"],"source":"observation"},x["evidence"]);now=utc_now();score=_sw(x["severity"])+min(x["frequency"],10)*.05
            with connect(self.database_path) as d:
                old=d.execute("SELECT id FROM improvement_candidates WHERE project_id IS ? AND failure_signature=? AND status NOT IN ('accepted','rejected','rolled_back')",(project_id,x["failure_signature"])).fetchone()
                if old:d.execute("UPDATE improvement_candidates SET evidence_json=?,priority_score=?,updated_at=? WHERE id=?",(json.dumps(ev,ensure_ascii=False),score,now,old["id"]))
                else:d.execute("INSERT INTO improvement_candidates(id,project_id,run_id,problem,evidence_json,severity,affected_modules_json,proposed_outcome,estimated_risk,expected_verification_json,status,priority_score,attempts,failure_signature,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(str(uuid4()),project_id,None,problem,json.dumps(ev,ensure_ascii=False),x["severity"],json.dumps(x["affected_modules"],ensure_ascii=False),x["proposed_outcome"],x["estimated_risk"],json.dumps(x["expected_verification"],ensure_ascii=False),"candidate",score,0,x["failure_signature"],now,now))
        return self.list_candidates(project_id)
    def prioritize(self,project_id,*,limit=1):
        rows=self.list_candidates(project_id,statuses=ACTIVE,limit=200);now=datetime.now(timezone.utc);rank=[]
        for x in rows:
            score=_sw(x["severity"])+min(len(x.get("evidence") or []),10)*.04-min(x["attempts"],10)*.12
            if x.get("last_attempt_at"):
                try:
                    if (now-datetime.fromisoformat(str(x["last_attempt_at"]).replace("Z","+00:00"))).total_seconds()<3600:score-=.4
                except (TypeError,ValueError):score-=.1
            x["priority_score"]=round(max(score,0),4);rank.append((x["priority_score"],x))
            with connect(self.database_path) as d:d.execute("UPDATE improvement_candidates SET status='diagnosed',priority_score=?,updated_at=? WHERE id=? AND status='candidate'",(x["priority_score"],utc_now(),x["id"]))
        rank.sort(key=lambda z:z[0],reverse=True);return [x for _,x in rank[:max(1,min(int(limit),20))]]
    def start_cycle(self,candidate_id,*,project_id=None,run_id=None,expected_files=(),expected_tests=()):
        x=self._gc(candidate_id)
        if not x:raise KeyError(candidate_id)
        if project_id and x["project_id"]!=project_id:raise ValueError("Candidate does not belong to the requested project")
        if x["status"] in TERMINAL:raise ValueError("Candidate is already terminal")
        if int(x.get("attempts") or 0) > self.max_retries:raise ValueError("Maximum retries exceeded for candidate")
        for c in self.list_cycles(x["project_id"],candidate_id=candidate_id,limit=20):
            if c["stage"] not in TERMINAL:return c
        files=_ss(expected_files or x["affected_modules"],self.max_files);tests=_ss(expected_tests or x["expected_verification"],20,1000);i=str(uuid4());now=utc_now()
        with connect(self.database_path) as d:
            d.execute("INSERT INTO improvement_cycles(id,candidate_id,project_id,run_id,stage,expected_files_json,expected_tests_json,confidence,started_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(i,candidate_id,x["project_id"],run_id,"planned",json.dumps(files,ensure_ascii=False),json.dumps(tests,ensure_ascii=False),x["priority_score"],now,now))
            d.execute("UPDATE improvement_candidates SET status='planned',attempts=attempts+1,last_attempt_at=?,updated_at=? WHERE id=?",(now,now,candidate_id))
        return self._gx(i) or {}
    def checkpoint(self,cycle_id,*,repo_root=None):
        c=self._gx(cycle_id)
        if not c:raise KeyError(cycle_id)
        if c["stage"] not in {"planned","interrupted"}:raise ValueError("Cycle is not ready for checkpointing")
        root=self._safe_repo(repo_root)
        for name in c.get("expected_files") or []:
            p=self._resolve(root/name)
            if root not in p.parents and p!=root:raise ValueError("Expected file is outside the allowed project root")
        status=self._git(root,"status","--porcelain","--untracked-files=all");head=self._git(root,"rev-parse","HEAD")
        if status.returncode or head.returncode:raise ValueError("Unable to inspect the Git baseline")
        dirty=status.stdout[:16000];commit=head.stdout.strip()[:128];ref=f"refs/ai-engineer/checkpoints/{cycle_id}"
        if dirty.strip():
            stash=self._git(root,"stash","create",f"AI Engineer checkpoint {cycle_id[:8]}")
            if stash.returncode or not stash.stdout.strip():raise ValueError("Unable to create a safe checkpoint for the dirty tree")
            sh=stash.stdout.strip().splitlines()[-1].strip()
            if self._git(root,"update-ref",ref,sh).returncode:raise ValueError("Unable to persist the dirty-tree checkpoint")
            ref=f"{ref}:{sh}"
        elif self._git(root,"update-ref",ref,commit).returncode:raise ValueError("Unable to persist the Git checkpoint")
        now=utc_now()
        with connect(self.database_path) as d:
            d.execute("UPDATE improvement_cycles SET stage='checkpointed',baseline_commit=?,baseline_status=?,checkpoint_ref=?,updated_at=? WHERE id=?",(commit,dirty,ref,now,cycle_id));d.execute("UPDATE improvement_candidates SET status='in_progress',updated_at=? WHERE id=?",(now,c["candidate_id"]))
        return self._gx(cycle_id) or {}
    def record_tests(self,cycle_id,*,phase,results,passed):
        if not self._gx(cycle_id):raise KeyError(cycle_id)
        summary,clean,_,_=sanitize_memory(str(results.get("summary") or ""),results,[]);clean["summary"]=summary;field="tests_before_json" if str(phase).casefold()=="before" else "tests_after_json";stage=self._gx(cycle_id)["stage"] if str(phase).casefold()=="before" else "tested"
        with connect(self.database_path) as d:d.execute(f"UPDATE improvement_cycles SET {field}=?,stage=?,updated_at=? WHERE id=?",(json.dumps({**clean,"passed":bool(passed)},ensure_ascii=False),stage,utc_now(),cycle_id))
        return self._gx(cycle_id) or {}
    def _lesson(self,c,accepted,summary,evidence):
        m=MemoryStore(self.database_path).create(project_id=c["project_id"],run_id=c.get("run_id"),memory_type="lesson",summary=summary[:4000] or ("Accepted improvement lesson." if accepted else "Rejected improvement attempt."),content={"cycle_id":c["id"],"candidate_id":c["candidate_id"],"accepted":accepted},evidence=evidence,lifecycle="candidate",source="self-improvement")
        if accepted:
            store = MemoryStore(self.database_path)
            m = store.promote(m["id"], target="validated", evidence=evidence)
            m = store.promote(m["id"], target="trusted", evidence=evidence + [{"type":"supervisor_validation", "summary":"Improvement review gate passed"}])
        return str(m.get("id") or "") or None
    def review(self,cycle_id,*,tests_passed,review_accepted,acceptance_met,regressions=(),review_summary="",follow_up_tasks=(),confidence=.5,rollback=False):
        c=self._gx(cycle_id)
        if not c:raise KeyError(cycle_id)
        regressions=_ss(regressions,50,1000);gate=bool(tests_passed and review_accepted and acceptance_met and not regressions);ev=[{"type":"tests","passed":bool(tests_passed)},{"type":"review","accepted":bool(review_accepted)},{"type":"acceptance_criteria","met":bool(acceptance_met)}];lesson=self._lesson(c,gate,review_summary,ev);stage="accepted" if gate else ("rolled_back" if rollback else "rejected");now=utc_now();cand=self._gc(c["candidate_id"]);assessment={"problem_detected":cand["problem"] if cand else "unknown","action_taken":"improvement accepted" if gate else "improvement rejected","tests_before":c.get("tests_before") or {},"tests_after":c.get("tests_after") or {},"review_result":{"accepted":bool(review_accepted),"acceptance_met":bool(acceptance_met),"gate_passed":gate},"regressions":regressions,"lesson_learned":lesson,"confidence":max(0,min(float(confidence),1)),"follow_up_tasks":_ss(follow_up_tasks,20)}
        with connect(self.database_path) as d:
            d.execute("UPDATE improvement_cycles SET stage=?,review_result_json=?,regressions_json=?,assessment_json=?,lesson_memory_id=?,confidence=?,follow_up_tasks_json=?,finished_at=?,updated_at=? WHERE id=?",(stage,json.dumps({"tests_passed":bool(tests_passed),"review_accepted":bool(review_accepted),"acceptance_met":bool(acceptance_met),"gate_passed":gate,"summary":review_summary[:4000]},ensure_ascii=False),json.dumps(regressions,ensure_ascii=False),json.dumps(assessment,ensure_ascii=False),lesson,max(0,min(float(confidence),1)),json.dumps(_ss(follow_up_tasks,20),ensure_ascii=False),now,now,cycle_id));d.execute("UPDATE improvement_candidates SET status=?,updated_at=? WHERE id=?",("accepted" if gate else stage,now,c["candidate_id"]))
        result=self._gx(cycle_id) or {}
        if rollback:result["rollback"]=self.rollback(cycle_id,execute=False)
        return result
    def interrupt(self,cycle_id,reason):
        if not self._gx(cycle_id):raise KeyError(cycle_id)
        with connect(self.database_path) as d:d.execute("UPDATE improvement_cycles SET stage='interrupted',error=?,updated_at=? WHERE id=?",(str(reason)[:4000],utc_now(),cycle_id))
        return self._gx(cycle_id) or {}
    def resume(self,cycle_id):
        c=self._gx(cycle_id)
        if not c:raise KeyError(cycle_id)
        if c["stage"]=="interrupted":
            with connect(self.database_path) as d:d.execute("UPDATE improvement_cycles SET stage=?,error=NULL,updated_at=? WHERE id=?",("checkpointed" if c.get("checkpoint_ref") else "planned",utc_now(),cycle_id))
        return self._gx(cycle_id) or {}
    def rollback(self,cycle_id,*,execute=False):
        c=self._gx(cycle_id)
        if not c:raise KeyError(cycle_id)
        if not execute:return {"performed":False,"reason":"rollback is recorded but requires explicit execution","checkpoint_ref":c.get("checkpoint_ref")}
        if not bool(getattr(settings,"autonomous_rollback_enabled",False)):return {"performed":False,"reason":"autonomous rollback is disabled by policy","checkpoint_ref":c.get("checkpoint_ref")}
        ref=str(c.get("checkpoint_ref") or "").split(":",1)[0]
        if self._git(self._safe_repo(),"reset","--hard",ref,timeout=120).returncode:raise ValueError("Checkpoint rollback failed")
        with connect(self.database_path) as d:d.execute("UPDATE improvement_cycles SET stage='rolled_back',updated_at=? WHERE id=?",(utc_now(),cycle_id));d.execute("UPDATE improvement_candidates SET status='rolled_back',updated_at=? WHERE id=?",(utc_now(),c["candidate_id"]))
        return {"performed":True,"checkpoint_ref":ref}
    def enforce_limits(self,*,changes,files_changed,retries,elapsed_seconds):
        bad=[] 
        if changes>self.max_changes:bad.append("maximum changes per run exceeded")
        if files_changed>self.max_files:bad.append("maximum changed files exceeded")
        if retries>self.max_retries:bad.append("maximum retries exceeded")
        if elapsed_seconds>self.max_runtime:bad.append("maximum runtime exceeded")
        return {"allowed":not bad,"violations":bad}
    def observe_and_propose(self,project_id,*,repo_root=None):return self.propose(project_id,self.observe(project_id,repo_root=repo_root))
    def render_goal(self,c):
        return "CONTROLLED SELF-IMPROVEMENT CANDIDATE\n"+f"CANDIDATE_ID: {c['id']}\nPROBLEM: {c['problem']}\nSEVERITY: {c['severity']}\nAFFECTED_MODULES: {', '.join(c.get('affected_modules') or [])}\nPROPOSED_OUTCOME: {c['proposed_outcome']}\nEXPECTED_VERIFICATION: {json.dumps(c.get('expected_verification') or [],ensure_ascii=False)}\nEVIDENCE: {json.dumps(c.get('evidence') or [],ensure_ascii=False)[:4000]}\nFollow OBSERVE -> DIAGNOSE -> PROPOSE -> PLAN -> CHECKPOINT -> IMPLEMENT -> TEST -> REVIEW -> ACCEPT/REJECT -> LEARN. Do not push to a remote."
