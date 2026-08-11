import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  approveAgentTask,
  createAgentTask,
  createProject,
  getAgentTask,
  getHealth,
  listAgentTasks,
  listProjects,
  type AgentTask,
  type HealthResponse,
  type Project,
} from "./api";
import "./styles.css";

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [activeTask, setActiveTask] = useState<AgentTask | null>(null);

  const [projectName, setProjectName] = useState("");
  const [projectWorkspace, setProjectWorkspace] = useState("");
  const [instruction, setInstruction] = useState(
    "فایل README.md پروژه را بررسی کن و ساختار پروژه را خلاصه کن.",
  );

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId),
    [projects, selectedProjectId],
  );

  async function refreshProjects() {
    const next = await listProjects();
    setProjects(next);

    if (!selectedProjectId && next.length > 0) {
      setSelectedProjectId(next[0].id);
    }
  }

  async function refreshTasks(projectId = selectedProjectId) {
    if (!projectId) {
      setTasks([]);
      return;
    }

    setTasks(await listAgentTasks(projectId));
  }

  async function refreshHealth() {
    setHealth(await getHealth());
  }

  useEffect(() => {
    void Promise.all([refreshHealth(), refreshProjects()]);
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      void refreshTasks(selectedProjectId);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    if (!activeTask) {
      return;
    }

    if (
      ["completed", "failed", "cancelled", "awaiting_approval"].includes(
        activeTask.status,
      )
    ) {
      return;
    }

    const timer = window.setInterval(async () => {
      const next = await getAgentTask(activeTask.id);
      setActiveTask(next);

      if (
        ["completed", "failed", "cancelled", "awaiting_approval"].includes(
          next.status,
        )
      ) {
        await refreshTasks(next.project_id);
      }
    }, 1500);

    return () => window.clearInterval(timer);
  }, [activeTask?.id, activeTask?.status]);

  async function handleCreateProject(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      const project = await createProject(
        projectName,
        projectWorkspace || undefined,
      );
      await refreshProjects();
      setSelectedProjectId(project.id);
      setProjectName("");
      setProjectWorkspace("");
      setMessage("پروژه ساخته شد.");
    } catch (error) {
      setMessage(`خطا: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleRunTask(event: FormEvent) {
    event.preventDefault();

    if (!selectedProjectId) {
      setMessage("اول یک پروژه انتخاب کن.");
      return;
    }

    setBusy(true);
    setMessage("");

    try {
      const task = await createAgentTask(
        selectedProjectId,
        instruction,
      );
      setActiveTask(task);
      await refreshTasks(selectedProjectId);
      setMessage("Task شروع شد.");
    } catch (error) {
      setMessage(`خطا: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleApproval(approved: boolean) {
    if (!activeTask) {
      return;
    }

    setBusy(true);

    try {
      const next = await approveAgentTask(activeTask.id, approved);
      setActiveTask(next);
      setMessage(approved ? "عملیات تأیید شد." : "Task لغو شد.");
    } catch (error) {
      setMessage(`خطا: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const gatewayReady =
    health?.dependencies.model_gateway.ok ?? false;
  const agentReady =
    health?.dependencies.local_agent.ok ?? false;

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">LOCAL AUTONOMOUS DEVELOPMENT SYSTEM</p>
          <h1>AI Engineer</h1>
          <p className="subtitle">
            مدیریت پروژه، برنامه‌ریزی Task و اجرای کنترل‌شده
          </p>
        </div>
      </header>

      <section className="status-grid">
        <article className="status-card">
          <span className={`status-dot ${health?.status === "ok" ? "online" : "offline"}`} />
          <div><strong>Orchestrator</strong><span>{health?.status ?? "..."}</span></div>
        </article>
        <article className="status-card">
          <span className={`status-dot ${gatewayReady ? "online" : "offline"}`} />
          <div><strong>Model Gateway</strong><span>{gatewayReady ? "متصل" : "قطع"}</span></div>
        </article>
        <article className="status-card">
          <span className={`status-dot ${agentReady ? "online" : "offline"}`} />
          <div><strong>Local Agent</strong><span>{agentReady ? "متصل" : "قطع"}</span></div>
        </article>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <p className="panel-label">PROJECT MANAGER</p>
          <h2>پروژه‌ها</h2>

          <form onSubmit={handleCreateProject}>
            <input
              placeholder="نام پروژه"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              required
            />
            <input
              className="ltr"
              placeholder="workspace اختیاری؛ مثال my-shop"
              value={projectWorkspace}
              onChange={(event) => setProjectWorkspace(event.target.value)}
            />
            <button className="primary-button" disabled={busy}>
              ساخت پروژه
            </button>
          </form>

          <div className="project-list">
            {projects.map((project) => (
              <button
                key={project.id}
                type="button"
                className={`project-item ${
                  project.id === selectedProjectId ? "selected" : ""
                }`}
                onClick={() => setSelectedProjectId(project.id)}
              >
                <strong>{project.name}</strong>
                <span>{project.workspace}</span>
              </button>
            ))}
          </div>
        </article>

        <article className="panel">
          <p className="panel-label">AGENT LOOP</p>
          <h2>اجرای Task</h2>
          <p className="muted">
            پروژه فعال: {selectedProject?.name ?? "انتخاب نشده"}
          </p>

          <form onSubmit={handleRunTask}>
            <textarea
              rows={8}
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
            />
            <button className="primary-button" disabled={busy || !selectedProjectId}>
              شروع Task
            </button>
          </form>

          {activeTask ? (
            <div className="task-box">
              <div className="task-line">
                <strong>Status</strong>
                <span className={`badge status-${activeTask.status}`}>
                  {activeTask.status}
                </span>
              </div>
              <div className="task-line">
                <strong>Progress</strong>
                <span>
                  {activeTask.current_step}/{activeTask.plan.length}
                </span>
              </div>

              {activeTask.status === "awaiting_approval" ? (
                <div className="approval-box">
                  <pre>{JSON.stringify(activeTask.pending, null, 2)}</pre>
                  <div className="button-row">
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => void handleApproval(true)}
                    >
                      تأیید و ادامه
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => void handleApproval(false)}
                    >
                      رد و لغو
                    </button>
                  </div>
                </div>
              ) : null}

              <pre className="output">
                {activeTask.error
                  ? `Error: ${activeTask.error}`
                  : activeTask.final_output ||
                    JSON.stringify(activeTask.results, null, 2)}
              </pre>
            </div>
          ) : null}
        </article>

        <article className="panel wide-panel">
          <p className="panel-label">TASK HISTORY</p>
          <h2>تاریخچه</h2>

          <div className="history">
            {tasks.map((task) => (
              <button
                key={task.id}
                type="button"
                className="history-item"
                onClick={() => setActiveTask(task)}
              >
                <div>
                  <strong>{task.instruction}</strong>
                  <span>{new Date(task.created_at).toLocaleString("fa-IR")}</span>
                </div>
                <span className={`badge status-${task.status}`}>
                  {task.status}
                </span>
              </button>
            ))}
          </div>

          <p className="file-status">{message}</p>
        </article>
      </section>
    </main>
  );
}

export default App;