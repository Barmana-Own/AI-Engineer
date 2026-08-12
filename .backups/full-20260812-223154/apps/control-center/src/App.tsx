import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  approveAgentTask,
  createAgentTask,
  createProject,
  getAgentTask,
  getHealth,
  getRuntimeModels,
  listAgentTasks,
  listAutonomyRuns,
  listProjects,
  listSubagents,
  startSelfImprove,
  type AgentTask,
  type AutonomyRun,
  type HealthResponse,
  type Project,
  type RuntimeModels,
  type SubagentRole,
} from "./api";
import "./styles.css";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled", "awaiting_approval"];

const capabilities = [
  ["Inspect", "list files, read source, search code"],
  ["Build", "plan and implement one safe change"],
  ["Validate", "run build, test, lint, and smoke checks"],
  ["Git safety", "checkpoint, diff, and recovery history"],
  ["Memory", "reuse successful and failed cycle evidence"],
  ["Supervision", "roles, retries, reconciliation, and monitoring"],
];

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [models, setModels] = useState<RuntimeModels | null>(null);
  const [roles, setRoles] = useState<SubagentRole[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [runs, setRuns] = useState<AutonomyRun[]>([]);
  const [activeTask, setActiveTask] = useState<AgentTask | null>(null);
  const [projectName, setProjectName] = useState("");
  const [projectWorkspace, setProjectWorkspace] = useState("");
  const [instruction, setInstruction] = useState(
    "Inspect the existing project and complete one small, high-value safe improvement.",
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId),
    [projects, selectedProjectId],
  );

  const refreshProjectData = useCallback(async (projectId: string) => {
    if (!projectId) {
      setTasks([]);
      setRuns([]);
      return;
    }

    const [nextTasks, nextRuns] = await Promise.all([
      listAgentTasks(projectId),
      listAutonomyRuns(projectId),
    ]);
    setTasks(nextTasks);
    setRuns(nextRuns);
  }, []);

  const refreshAll = useCallback(async () => {
    const [healthResult, modelsResult, rolesResult, projectsResult] =
      await Promise.allSettled([
        getHealth(),
        getRuntimeModels(),
        listSubagents(),
        listProjects(),
      ]);

    if (healthResult.status === "fulfilled") setHealth(healthResult.value);
    if (modelsResult.status === "fulfilled") setModels(modelsResult.value);
    if (rolesResult.status === "fulfilled") setRoles(rolesResult.value);
    if (projectsResult.status === "fulfilled") {
      const nextProjects = projectsResult.value;
      setProjects(nextProjects);
      if (!selectedProjectId && nextProjects.length > 0) {
        setSelectedProjectId(nextProjects[0].id);
      }
    }
    setLastRefresh(new Date());
  }, [selectedProjectId]);

  useEffect(() => {
    void refreshAll();
    const timer = window.setInterval(() => void refreshAll(), 5000);
    return () => window.clearInterval(timer);
  }, [refreshAll]);

  useEffect(() => {
    void refreshProjectData(selectedProjectId);
  }, [refreshProjectData, selectedProjectId]);

  useEffect(() => {
    if (selectedProjectId) void refreshProjectData(selectedProjectId);
  }, [activeTask?.status, refreshProjectData, selectedProjectId]);

  async function handleCreateProject(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const project = await createProject(projectName, projectWorkspace || undefined);
      setProjectName("");
      setProjectWorkspace("");
      setSelectedProjectId(project.id);
      setMessage("Project created.");
      await refreshAll();
    } catch (error) {
      setMessage(`Error: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleRunTask(event: FormEvent) {
    event.preventDefault();
    if (!selectedProjectId) {
      setMessage("Select a project first.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const task = await createAgentTask(selectedProjectId, instruction);
      setActiveTask(task);
      setMessage("Interactive task started.");
      await refreshProjectData(selectedProjectId);
    } catch (error) {
      setMessage(`Error: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleAutonomy() {
    if (!selectedProjectId) {
      setMessage("Select a project first.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const run = await startSelfImprove(selectedProjectId, instruction);
      setMessage(`Autonomous run ${run.id.slice(0, 8)} started.`);
      await refreshProjectData(selectedProjectId);
    } catch (error) {
      setMessage(`Error: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleApproval(approved: boolean) {
    if (!activeTask) return;
    setBusy(true);
    try {
      const next = await approveAgentTask(activeTask.id, approved);
      setActiveTask(next);
      setMessage(approved ? "Operation approved." : "Task cancelled.");
    } catch (error) {
      setMessage(`Error: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function openTask(task: AgentTask) {
    try {
      setActiveTask(await getAgentTask(task.id));
    } catch (error) {
      setMessage(`Error: ${String(error)}`);
    }
  }

  const ready = health?.status === "ok";
  const runningRuns = runs.filter((run) => ["queued", "running"].includes(run.status));

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">✦</div>
          <div>
            <p className="eyebrow">LOCAL-FIRST DEVELOPMENT OS</p>
            <h1>AI Engineer</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="desktop-badge">DESKTOP APP MODE</span>
          <span className="refresh-label">
            {lastRefresh ? `Synced ${lastRefresh.toLocaleTimeString()}` : "Connecting..."}
          </span>
        </div>
      </header>

      <section className="status-grid">
        <article className="status-card primary-status">
          <span className={`status-dot ${ready ? "online" : "offline"}`} />
          <div><strong>Orchestrator</strong><span>{health?.status ?? "offline"}</span></div>
          <b>{runningRuns.length} active runs</b>
        </article>
        <article className="status-card">
          <span className={`status-dot ${health?.dependencies.model_gateway.ok ? "online" : "offline"}`} />
          <div><strong>Model Gateway</strong><span>{models?.provider ?? "offline"}</span></div>
          <b>{models?.default_model ?? "—"}</b>
        </article>
        <article className="status-card">
          <span className={`status-dot ${health?.dependencies.local_agent.ok ? "online" : "offline"}`} />
          <div><strong>Local Agent</strong><span>workspace guarded</span></div>
          <b>5 min cadence</b>
        </article>
      </section>

      <div className="layout-grid">
        <aside className="side-column">
          <section className="panel project-panel">
            <div className="panel-heading"><div><p className="panel-label">PROJECTS</p><h2>Workspace manager</h2></div><span className="count-pill">{projects.length}</span></div>
            <form onSubmit={handleCreateProject} className="stack-form">
              <input placeholder="Project name" value={projectName} onChange={(event) => setProjectName(event.target.value)} required />
              <input className="ltr" placeholder="Workspace slug (optional)" value={projectWorkspace} onChange={(event) => setProjectWorkspace(event.target.value)} />
              <button className="primary-button" disabled={busy}>Create project</button>
            </form>
            <div className="project-list">
              {projects.map((project) => (
                <button key={project.id} type="button" className={`project-item ${project.id === selectedProjectId ? "selected" : ""}`} onClick={() => setSelectedProjectId(project.id)}>
                  <strong>{project.name}</strong><span>{project.workspace}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="panel capability-panel">
            <p className="panel-label">CODEX-STYLE CAPABILITIES</p>
            <div className="capability-list">
              {capabilities.map(([name, detail]) => <div className="capability" key={name}><span>✓</span><div><strong>{name}</strong><small>{detail}</small></div></div>)}
            </div>
          </section>
        </aside>

        <section className="main-column">
          <section className="panel command-panel">
            <div className="panel-heading"><div><p className="panel-label">COMMAND DECK</p><h2>Direct the engineer</h2></div><span className="project-context">{selectedProject?.workspace ?? "no project"}</span></div>
            <p className="muted">The autonomous supervisor runs one bounded specialist pipeline every five minutes. Manual tasks use the same guarded tool loop.</p>
            <form onSubmit={handleRunTask} className="command-form">
              <textarea rows={5} value={instruction} onChange={(event) => setInstruction(event.target.value)} />
              <div className="button-row">
                <button className="primary-button" disabled={busy || !selectedProjectId}>Run interactive task</button>
                <button type="button" className="autonomy-button" disabled={busy || !selectedProjectId} onClick={() => void handleAutonomy()}>Start autonomous cycle</button>
              </div>
            </form>
            {message ? <p className="message">{message}</p> : null}
          </section>

          {activeTask ? <section className="panel active-panel">
            <div className="panel-heading"><div><p className="panel-label">LIVE TASK</p><h2>{activeTask.mode === "autonomous" ? "Autonomous sub-agent" : "Interactive agent"}</h2></div><span className={`badge status-${activeTask.status}`}>{activeTask.status}</span></div>
            <div className="metric-row"><span>Step {activeTask.current_step} / {activeTask.plan.length}</span><span>{new Date(activeTask.updated_at).toLocaleTimeString()}</span></div>
            {activeTask.status === "awaiting_approval" ? <div className="approval-box"><pre>{JSON.stringify(activeTask.pending, null, 2)}</pre><div className="button-row"><button type="button" className="primary-button" onClick={() => void handleApproval(true)}>Approve</button><button type="button" className="danger-button" onClick={() => void handleApproval(false)}>Reject</button></div></div> : null}
            <pre className="output">{activeTask.error ? `Error: ${activeTask.error}` : activeTask.final_output || JSON.stringify(activeTask.results.slice(-4), null, 2)}</pre>
          </section> : null}

          <section className="panel runs-panel">
            <div className="panel-heading"><div><p className="panel-label">AUTONOMY RUNS</p><h2>Self-development timeline</h2></div><span className="count-pill">{runningRuns.length} live</span></div>
            <div className="run-list">
              {runs.slice(0, 8).map((run) => <div className="run-item" key={run.id}><span className={`run-state state-${run.status}`} /><div className="run-main"><strong>{run.goal}</strong><small>{run.task_ids.length} specialist task{run.task_ids.length === 1 ? "" : "s"} · {new Date(run.updated_at).toLocaleString()}</small></div><span className={`badge status-${run.status}`}>{run.status}</span></div>)}
              {runs.length === 0 ? <p className="muted">No autonomous runs recorded yet.</p> : null}
            </div>
          </section>

          <section className="panel history-panel">
            <div className="panel-heading"><div><p className="panel-label">TASK HISTORY</p><h2>Recent work</h2></div></div>
            <div className="history-list">
              {tasks.slice(0, 8).map((task) => <button key={task.id} type="button" className="history-item" onClick={() => void openTask(task)}><div><strong>{task.instruction.split("\n")[0]}</strong><small>{task.mode} · {new Date(task.created_at).toLocaleString()}</small></div><span className={`badge status-${task.status}`}>{task.status}</span></button>)}
              {tasks.length === 0 ? <p className="muted">No tasks for this project.</p> : null}
            </div>
          </section>
        </section>

        <aside className="right-column">
          <section className="panel subagent-panel">
            <div className="panel-heading"><div><p className="panel-label">SUB-AGENT FACTORY</p><h2>Specialists</h2></div><span className="count-pill">{roles.length}</span></div>
            <div className="role-list">{roles.map((role) => <div className="role-item" key={role.key}><span className={`role-icon ${role.read_only ? "observe" : "build"}`}>{role.read_only ? "◌" : "✎"}</span><div><strong>{role.title}</strong><small>{role.objective}</small></div><em>{role.read_only ? "read" : "write"}</em></div>)}</div>
          </section>
          <section className="panel model-panel">
            <div className="panel-heading"><div><p className="panel-label">MODEL ROUTING</p><h2>AI stack</h2></div><span className="online-label">{models?.provider_configured ? "ready" : "offline"}</span></div>
            <div className="model-highlight"><small>Active model</small><strong>{models?.default_model ?? "loading..."}</strong></div>
            <div className="model-detail"><span>Provider</span><b>{models?.provider ?? "—"}</b></div>
            <div className="model-detail"><span>Fallbacks</span><b>{models?.fallback_models?.join(", ") || "none"}</b></div>
            <div className="model-detail"><span>Retry policy</span><b>{models ? `${models.max_retries_per_model} retry / ${models.max_fallback_attempts} candidate` : "—"}</b></div>
          </section>
        </aside>
      </div>
      <footer className="footer"><span>AI Engineer · local services on 127.0.0.1</span><span>Automatic backup before every mutation</span></footer>
    </main>
  );
}

export default App;
