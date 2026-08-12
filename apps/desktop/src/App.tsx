import {
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type Project = {
  id: string;
  name: string;
  workspace: string;
};

type Health = {
  status: string;
  dependencies?: {
    model_gateway?: { ok?: boolean };
    local_agent?: { ok?: boolean };
  };
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
};

type AgentTask = {
  id: string;
  project_id: string;
  instruction: string;
  status: string;
  plan: Array<Record<string, unknown>>;
  current_step: number;
  results: Array<Record<string, unknown>>;
  pending: Record<string, unknown> | null;
  final_output: string | null;
  error: string | null;
};

type FileEntry = {
  name: string;
  path: string;
  type: string;
  size?: number;
};

type ManagedProcess = {
  id: string;
  name: string;
  cwd: string;
  pid: number;
  running: boolean;
  stdout_log: string;
  stderr_log: string;
};

type RightTab = "activity" | "files" | "terminal" | "git" | "preview";

const api = window.aiDesktop.api;

function now(): string {
  return new Date().toLocaleTimeString("fa-IR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function messageId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function storageKey(projectId: string): string {
  return `ai-engineer-chat:${projectId || "general"}`;
}

function loadMessages(projectId: string): Message[] {
  try {
    const raw = localStorage.getItem(storageKey(projectId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function stringifyError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : null;
}

function taskTool(step: Record<string, unknown>): string {
  return String(step.tool || step.action || "unknown");
}

function taskArguments(step: Record<string, unknown>): Record<string, unknown> {
  return asRecord(step.arguments) || asRecord(step.args) || {};
}

function taskOutcome(
  task: AgentTask,
  stepIndex: number,
): Record<string, unknown> | null {
  const item = task.results.find(
    (result) => Number(result.step_index) === stepIndex,
  );

  return asRecord(item?.outcome);
}

function pendingRecord(task: AgentTask): Record<string, unknown> | null {
  return asRecord(task.pending);
}

function pendingStep(task: AgentTask): Record<string, unknown> | null {
  return asRecord(pendingRecord(task)?.step);
}

function pendingReason(task: AgentTask): string {
  const pending = pendingRecord(task);
  const outcome = asRecord(pending?.outcome);
  return String(
    outcome?.reason ||
      pendingStep(task)?.reason ||
      "این عملیات نیازمند تأیید شماست.",
  );
}

function activityLabel(
  tool: string,
  outcome: Record<string, unknown> | null,
  waiting: boolean,
): string {
  if (waiting) return "Waiting for approval";
  if (outcome?.ok === false) {
    if (tool === "run_terminal") return "Build or test failed";
    return "Tool failed";
  }
  if (outcome?.ok === true) {
    const labels: Record<string, string> = {
      list_files: "Files inspected",
      search_files: "Search completed",
      read_file: "File read",
      detect_environment: "Environment detected",
      git_checkpoint: "Checkpoint created",
      write_file: "File written",
      replace_text: "File edited",
      apply_patch: "Patch applied",
      git_diff: "Git diff captured",
      git_status: "Git status read",
      run_terminal: "Command passed",
      start_process: "Process started",
      list_processes: "Processes listed",
      stop_process: "Process stopped",
      git_rollback: "Rollback completed",
      finish_task: "Task completed",
    };
    return labels[tool] || "Completed";
  }

  const labels: Record<string, string> = {
    list_files: "Inspecting files",
    search_files: "Searching code",
    read_file: "Reading file",
    detect_environment: "Detecting environment",
    git_checkpoint: "Creating checkpoint",
    write_file: "Writing file",
    replace_text: "Editing file",
    apply_patch: "Applying patch",
    git_diff: "Reading Git diff",
    git_status: "Reading Git status",
    run_terminal: "Running build or test",
    start_process: "Starting process",
    list_processes: "Listing processes",
    stop_process: "Stopping process",
    git_rollback: "Rolling back",
    finish_task: "Checking completion guards",
  };
  return labels[tool] || "Working";
}

function activityDetail(
  tool: string,
  outcome: Record<string, unknown> | null,
): string {
  if (!outcome) return "";

  if (outcome.error) {
    return String(outcome.error);
  }

  const result = asRecord(outcome.result);
  if (!result) return "";

  if (tool === "run_terminal") {
    return [
      `Exit code: ${String(result.exit_code ?? "-")}`,
      String(result.stdout || ""),
      String(result.stderr || ""),
    ]
      .filter(Boolean)
      .join("\n")
      .slice(0, 2600);
  }

  if (tool === "git_diff") {
    return String(result.diff || "").slice(0, 2600);
  }

  if (tool === "read_file") {
    return String(result.path || "");
  }

  if (["write_file", "replace_text", "apply_patch"].includes(tool)) {
    return `Changed: ${String(result.path || "")}`;
  }

  return "";
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState<"chat" | "agent">("agent");
  const [busy, setBusy] = useState(false);
  const [activeTask, setActiveTask] = useState<AgentTask | null>(null);
  const [rightTab, setRightTab] = useState<RightTab>("activity");
  const [notice, setNotice] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">(
    () =>
      (localStorage.getItem("ai-engineer-theme") as
        | "light"
        | "dark") || "light",
  );

  const [currentPath, setCurrentPath] = useState(".");
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [selectedFile, setSelectedFile] = useState("");
  const [fileContent, setFileContent] = useState("");
  const [fileDirty, setFileDirty] = useState(false);

  const [terminalCommand, setTerminalCommand] = useState("npm run verify");
  const [terminalOutput, setTerminalOutput] = useState("");
  const [terminalBusy, setTerminalBusy] = useState(false);

  const [gitStatus, setGitStatus] = useState<any>(null);
  const [gitDiff, setGitDiff] = useState("");
  const [checkpointMessage, setCheckpointMessage] =
    useState("AI Engineer checkpoint");
  const [rollbackCommit, setRollbackCommit] = useState("");

  const [processes, setProcesses] = useState<ManagedProcess[]>([]);
  const [previewUrl, setPreviewUrl] = useState(
    "http://127.0.0.1:5176",
  );

  const messageEnd = useRef<HTMLDivElement | null>(null);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedId) ?? null,
    [projects, selectedId],
  );

  const workspacePath = useMemo(() => {
    if (!selectedProject) return "";
    return currentPath === "."
      ? selectedProject.workspace
      : `${selectedProject.workspace}/${currentPath}`;
  }, [selectedProject, currentPath]);

  async function refreshHealth() {
    try {
      setHealth(await api("orchestrator", "GET", "/health"));
    } catch {
      setHealth(null);
    }
  }

  async function refreshProjects() {
    const next = (await api(
      "orchestrator",
      "GET",
      "/v1/projects",
    )) as Project[];

    setProjects(next);

    if (!selectedId && next.length > 0) {
      setSelectedId(next[0].id);
    }
  }

  async function refreshFiles(pathValue = currentPath) {
    if (!selectedProject) {
      setFiles([]);
      return;
    }

    const relative =
      pathValue === "."
        ? selectedProject.workspace
        : `${selectedProject.workspace}/${pathValue}`;

    const result = await api(
      "agent",
      "GET",
      `/files/list?path=${encodeURIComponent(relative)}`,
    );

    setFiles(result.entries ?? []);
  }

  async function refreshProcesses() {
    try {
      setProcesses(
        await api(
          "orchestrator",
          "GET",
          "/v1/developer/processes",
        ),
      );
    } catch {
      setProcesses([]);
    }
  }

  async function refreshGit() {
    if (!selectedProject) return;

    const status = await api(
      "orchestrator",
      "GET",
      `/v1/developer/projects/${selectedProject.id}/git/status`,
    );
    setGitStatus(status);

    const diff = await api(
      "orchestrator",
      "POST",
      `/v1/developer/projects/${selectedProject.id}/git/diff`,
      { staged: false, base: null },
    );
    setGitDiff(diff.diff || "");
  }

  useEffect(() => {
    void Promise.all([refreshHealth(), refreshProjects()]);

    const timer = window.setInterval(() => {
      void refreshHealth();
    }, 10000);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    setMessages(loadMessages(selectedId));
    setActiveTask(null);
    setCurrentPath(".");
    setSelectedFile("");
    setFileContent("");
    setFileDirty(false);

    if (selectedId) {
      void refreshFiles(".");
      void refreshProcesses();
      void refreshGit();
    }
  }, [selectedId]);

  useEffect(() => {
    localStorage.setItem(
      storageKey(selectedId),
      JSON.stringify(messages),
    );
    messageEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, selectedId]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("ai-engineer-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!activeTask) return;

    if (
      ["completed", "failed", "cancelled", "awaiting_approval"].includes(
        activeTask.status,
      )
    ) {
      return;
    }

    const timer = window.setInterval(async () => {
      const next = (await api(
        "orchestrator",
        "GET",
        `/v1/agent/tasks/${activeTask.id}`,
      )) as AgentTask;

      setActiveTask(next);

      if (next.status === "completed") {
        setMessages((current) => [
          ...current,
          {
            id: messageId(),
            role: "assistant",
            content:
              next.final_output ||
              "کار با موفقیت انجام شد.",
            time: now(),
          },
        ]);
        setBusy(false);
        void refreshFiles();
        void refreshGit();
      }

      if (next.status === "failed") {
        setMessages((current) => [
          ...current,
          {
            id: messageId(),
            role: "assistant",
            content: `خطا: ${next.error || "Task ناموفق بود."}`,
            time: now(),
          },
        ]);
        setBusy(false);
      }
    }, 1300);

    return () => window.clearInterval(timer);
  }, [activeTask?.id, activeTask?.status]);

  function addMessage(role: Message["role"], content: string) {
    setMessages((current) => [
      ...current,
      {
        id: messageId(),
        role,
        content,
        time: now(),
      },
    ]);
  }

  async function send() {
    const text = draft.trim();

    if (!text || busy) return;

    if (!selectedProject) {
      setNotice("اول یک پروژه انتخاب کن.");
      return;
    }

    setDraft("");
    setBusy(true);
    setNotice("");
    addMessage("user", text);

    try {
      if (mode === "chat") {
        const response = await api(
          "orchestrator",
          "POST",
          "/v1/tasks/chat",
          {
            model: "qwen2.5-coder:1.5b",
            messages: [{ role: "user", content: text }],
            temperature: 0,
            max_tokens: 1200,
            project_id: selectedProject.id,
            task_id: `desktop-chat-${Date.now()}`,
            agent_id: "desktop",
          },
        );

        addMessage(
          "assistant",
          response?.choices?.[0]?.message?.content ||
            "پاسخی دریافت نشد.",
        );
        setBusy(false);
        return;
      }

      const task = (await api(
        "orchestrator",
        "POST",
        "/v1/agent/tasks",
        {
          project_id: selectedProject.id,
          instruction: text,
        },
      )) as AgentTask;

      setActiveTask(task);
      setRightTab("activity");
    } catch (error) {
      addMessage("assistant", `خطا: ${stringifyError(error)}`);
      setBusy(false);
    }
  }

  function handleComposerKey(
    event: KeyboardEvent<HTMLTextAreaElement>,
  ) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  async function approveTask(approved: boolean) {
    if (!activeTask) return;

    const next = (await api(
      "orchestrator",
      "POST",
      `/v1/agent/tasks/${activeTask.id}/approval`,
      { approved },
    )) as AgentTask;

    setActiveTask(next);

    if (!approved) {
      setBusy(false);
      addMessage("assistant", "عملیات لغو شد.");
    }
  }

  async function createProject() {
    const name = window.prompt("نام پروژه:");
    if (!name?.trim()) return;

    const workspace = window.prompt(
      "نام پوشه Workspace:",
      name.trim().toLowerCase().replace(/\s+/g, "-"),
    );

    if (!workspace?.trim()) return;

    const project = (await api(
      "orchestrator",
      "POST",
      "/v1/projects",
      {
        name: name.trim(),
        workspace: workspace.trim(),
      },
    )) as Project;

    await refreshProjects();
    setSelectedId(project.id);
  }

  async function openEntry(entry: FileEntry) {
    if (!selectedProject) return;

    if (entry.type === "directory") {
      const next =
        currentPath === "."
          ? entry.name
          : `${currentPath}/${entry.name}`;
      setCurrentPath(next);
      setSelectedFile("");
      setFileContent("");
      setFileDirty(false);
      await refreshFiles(next);
      return;
    }

    const fullPath =
      currentPath === "."
        ? `${selectedProject.workspace}/${entry.name}`
        : `${selectedProject.workspace}/${currentPath}/${entry.name}`;

    const result = await api(
      "agent",
      "GET",
      `/files/read?path=${encodeURIComponent(fullPath)}`,
    );

    setSelectedFile(fullPath);
    setFileContent(result.content ?? "");
    setFileDirty(false);
  }

  async function goUp() {
    if (currentPath === ".") return;

    const parts = currentPath.split("/").filter(Boolean);
    parts.pop();
    const next = parts.length ? parts.join("/") : ".";

    setCurrentPath(next);
    setSelectedFile("");
    setFileContent("");
    setFileDirty(false);
    await refreshFiles(next);
  }

  async function saveFile() {
    if (!selectedFile || !fileDirty) return;

    const approved = window.confirm(
      `فایل زیر بازنویسی شود؟\n${selectedFile}`,
    );

    if (!approved) return;

    await api("agent", "POST", "/files/write", {
      path: selectedFile,
      content: fileContent,
      overwrite: true,
    });

    setFileDirty(false);
    setNotice("فایل ذخیره شد.");
    void refreshGit();
  }

  async function runTerminal() {
    if (!selectedProject || !terminalCommand.trim()) return;

    setTerminalBusy(true);
    setTerminalOutput("");

    try {
      const preview = await api(
        "agent",
        "POST",
        "/terminal/preview",
        {
          command: terminalCommand,
          cwd: selectedProject.workspace,
          shell: "powershell",
        },
      );

      if (preview.risk === "blocked") {
        throw new Error(
          `دستور مسدود شد: ${(preview.reasons || []).join(", ")}`,
        );
      }

      let approved = false;

      if (preview.requires_approval) {
        approved = window.confirm(
          `اجرای این دستور نیاز به تأیید دارد:\n\n${terminalCommand}`,
        );

        if (!approved) {
          setTerminalOutput("عملیات لغو شد.");
          return;
        }
      }

      const result = await api(
        "agent",
        "POST",
        "/terminal/run",
        {
          command: terminalCommand,
          cwd: selectedProject.workspace,
          shell: "powershell",
          approved,
          timeout_seconds: 600,
        },
      );

      setTerminalOutput(
        [
          `Exit code: ${result.exit_code}`,
          "",
          result.stdout || "",
          result.stderr || "",
        ].join("\n"),
      );

      void refreshFiles();
      void refreshGit();
    } catch (error) {
      setTerminalOutput(`ERROR\n${stringifyError(error)}`);
    } finally {
      setTerminalBusy(false);
    }
  }

  async function startProject() {
    if (!selectedProject) return;

    try {
      const started = await api(
        "orchestrator",
        "POST",
        `/v1/developer/projects/${selectedProject.id}/processes/start`,
        {
          name: `${selectedProject.name} Dev Server`,
          executable: "npm.cmd",
          args: ["run", "dev"],
          cwd: ".",
          approved: true,
        },
      );

      setNotice(`پروژه اجرا شد. PID: ${started.pid}`);
      setRightTab("preview");
      await refreshProcesses();

      window.setTimeout(() => {
        setPreviewUrl((current) => `${current.split("?")[0]}?t=${Date.now()}`);
      }, 2500);
    } catch (error) {
      setNotice(`اجرای پروژه ناموفق بود: ${stringifyError(error)}`);
    }
  }

  async function stopProcess(processId: string) {
    await api(
      "orchestrator",
      "POST",
      "/v1/developer/processes/stop",
      {
        process_id: processId,
        approved: true,
      },
    );

    await refreshProcesses();
    setNotice("Process متوقف شد.");
  }

  async function createCheckpoint() {
    if (!selectedProject) return;

    const result = await api(
      "orchestrator",
      "POST",
      `/v1/developer/projects/${selectedProject.id}/git/checkpoint`,
      {
        message: checkpointMessage,
        include_untracked: true,
      },
    );

    setRollbackCommit(result.commit || "");
    setNotice(
      result.created
        ? `Checkpoint ساخته شد: ${String(result.commit).slice(0, 12)}`
        : "تغییری برای Commit وجود نداشت.",
    );

    await refreshGit();
  }

  async function rollback() {
    if (!selectedProject || !rollbackCommit.trim()) return;

    const approved = window.confirm(
      `پروژه به Commit زیر برگردد؟\n${rollbackCommit}`,
    );

    if (!approved) return;

    await api(
      "orchestrator",
      "POST",
      `/v1/developer/projects/${selectedProject.id}/git/rollback`,
      {
        commit: rollbackCommit.trim(),
        approved: true,
      },
    );

    setNotice("Rollback انجام شد.");
    await refreshFiles();
    await refreshGit();
  }

  function newChat() {
    setMessages([]);
    setActiveTask(null);
    setNotice("");
    localStorage.removeItem(storageKey(selectedId));
  }

  const agentReady =
    health?.dependencies?.local_agent?.ok === true;
  const gatewayReady =
    health?.dependencies?.model_gateway?.ok === true;

  return (
    <div className="app-shell" dir="ltr">
      <header className="titlebar">
        <div className="titlebar-brand">
          <div className="brand-mark">AI</div>
          <span>AI Engineer</span>
        </div>

        <div className="titlebar-project">
          {selectedProject?.name || "بدون پروژه"}
        </div>

        <div className="window-controls">
          <button onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
            {theme === "light" ? "◐" : "☀"}
          </button>
          <button onClick={() => void window.aiDesktop.window.minimize()}>
            —
          </button>
          <button onClick={() => void window.aiDesktop.window.maximize()}>
            □
          </button>
          <button
            className="close-button"
            onClick={() => void window.aiDesktop.window.close()}
          >
            ×
          </button>
        </div>
      </header>

      <div className="workspace-layout">
        <aside className="sidebar">
          <button className="new-chat-button" onClick={newChat}>
            <span>＋</span>
            گفت‌وگوی جدید
          </button>

          <button className="new-project-button" onClick={() => void createProject()}>
            ساخت پروژه
          </button>

          <div className="sidebar-heading">پروژه‌ها</div>

          <div className="project-list">
            {projects.map((project) => (
              <button
                key={project.id}
                className={`project-row ${
                  selectedId === project.id ? "selected" : ""
                }`}
                onClick={() => setSelectedId(project.id)}
              >
                <span className="folder-icon">▱</span>
                <span className="project-copy">
                  <strong>{project.name}</strong>
                  <small>{project.workspace}</small>
                </span>
              </button>
            ))}
          </div>

          <div className="sidebar-footer">
            <span className={`dot ${health?.status === "ok" ? "ok" : ""}`} />
            Core
            <span className={`dot ${agentReady ? "ok" : ""}`} />
            Agent
            <span className={`dot ${gatewayReady ? "ok" : ""}`} />
            Model
          </div>
        </aside>

        <main className="chat-panel" dir="rtl">
          <div className="chat-toolbar">
            <div>
              <h1>{selectedProject?.name || "AI Engineer"}</h1>
              <p>
                {selectedProject
                  ? selectedProject.workspace.toLowerCase() === "ai-engineer"
                    ? "F:\\AI-Engineer"
                    : `F:\\AI-Engineer\\workspaces\\${selectedProject.workspace}`
                  : "یک پروژه انتخاب کن"}
              </p>
            </div>

            <div className="project-actions">
              <button
                disabled={!selectedProject}
                onClick={() =>
                  selectedProject &&
                  void window.aiDesktop.openFolder(selectedProject.workspace)
                }
              >
                پوشه
              </button>
              <button
                disabled={!selectedProject}
                onClick={() =>
                  selectedProject &&
                  void window.aiDesktop.openCode(selectedProject.workspace)
                }
              >
                VS Code
              </button>
              <button
                className="run-button"
                disabled={!selectedProject}
                onClick={() => void startProject()}
              >
                اجرا
              </button>
            </div>
          </div>

          <section className="messages">
            {messages.length === 0 ? (
              <div className="empty-chat">
                <div className="empty-logo">AI</div>
                <h2>روی پروژه چه کاری انجام بدهم؟</h2>
                <p>
                  فایل‌ها را بررسی می‌کنم، کد می‌نویسم، دستور اجرا می‌کنم،
                  Build و Test می‌گیرم و نتیجه را مرحله‌به‌مرحله نشان می‌دهم.
                </p>
                <div className="suggestions">
                  <button
                    onClick={() =>
                      setDraft(
                        "ساختار پروژه را بررسی کن و مشکلات اصلی را گزارش بده.",
                      )
                    }
                  >
                    بررسی پروژه
                  </button>
                  <button
                    onClick={() =>
                      setDraft(
                        "پروژه را Build و Test کن و هر خطایی پیدا شد اصلاح کن.",
                      )
                    }
                  >
                    Build و تعمیر
                  </button>
                  <button
                    onClick={() =>
                      setDraft(
                        "فایل‌های مهم پروژه را بخوان و یک برنامه مرحله‌ای برای ادامه کار بده.",
                      )
                    }
                  >
                    برنامه ادامه کار
                  </button>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <article
                  key={message.id}
                  className={`message ${message.role}`}
                >
                  <div className="message-role">
                    {message.role === "user" ? "شما" : "AI Engineer"}
                  </div>
                  <div className="message-content">{message.content}</div>
                  <time>{message.time}</time>
                </article>
              ))
            )}
            {activeTask &&
            !["completed", "failed", "cancelled"].includes(
              activeTask.status,
            ) ? (
              <article className="agent-live-card">
                <div className="agent-live-head">
                  <strong>Agent Execution</strong>
                  <span>{activeTask.status}</span>
                </div>
                <p>
                  {activityLabel(
                    taskTool(
                      activeTask.plan[activeTask.plan.length - 1] || {},
                    ),
                    taskOutcome(
                      activeTask,
                      activeTask.plan.length - 1,
                    ),
                    activeTask.status === "awaiting_approval",
                  )}
                </p>
                {activeTask.status === "awaiting_approval" ? (
                  <div className="agent-live-approval">
                    <span>{pendingReason(activeTask)}</span>
                    <button onClick={() => void approveTask(true)}>
                      تأیید و ادامه
                    </button>
                    <button onClick={() => void approveTask(false)}>
                      لغو
                    </button>
                  </div>
                ) : null}
              </article>
            ) : null}
            <div ref={messageEnd} />
          </section>

          <footer className="composer-wrap">
            {notice ? <div className="notice">{notice}</div> : null}

            <div className="mode-switch">
              <button
                className={mode === "agent" ? "active" : ""}
                onClick={() => setMode("agent")}
              >
                Agent
              </button>
              <button
                className={mode === "chat" ? "active" : ""}
                onClick={() => setMode("chat")}
              >
                Chat
              </button>
            </div>

            <div className="composer">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleComposerKey}
                placeholder={
                  mode === "agent"
                    ? "بگو روی پروژه چه کاری انجام دهد..."
                    : "سؤالت را بپرس..."
                }
                rows={3}
              />
              <button
                className="send-button"
                disabled={!draft.trim() || busy}
                onClick={() => void send()}
              >
                {busy ? "…" : "↑"}
              </button>
            </div>

            <div className="composer-hint">
              Enter برای ارسال — Shift+Enter برای خط جدید
            </div>
          </footer>
        </main>

        <aside className="right-panel" dir="rtl">
          <div className="right-tabs">
            {[
              ["activity", "فعالیت"],
              ["files", "فایل‌ها"],
              ["terminal", "ترمینال"],
              ["git", "Git"],
              ["preview", "Preview"],
            ].map(([value, label]) => (
              <button
                key={value}
                className={rightTab === value ? "active" : ""}
                onClick={() => {
                  setRightTab(value as RightTab);
                  if (value === "files") void refreshFiles();
                  if (value === "git") void refreshGit();
                  if (value === "activity") void refreshProcesses();
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="right-content">
            {rightTab === "activity" ? (
              <div className="activity-view">
                <div className="panel-header">
                  <strong>Agent Activity</strong>
                  <span>{activeTask?.status || "idle"}</span>
                </div>

                {activeTask ? (
                  <>
                    <div className="progress-line">
                      <div
                        style={{
                          width: `${
                            activeTask.plan.length
                              ? (activeTask.current_step /
                                  activeTask.plan.length) *
                                100
                              : 0
                          }%`,
                        }}
                      />
                    </div>

                    <div className="task-summary">
                      <strong>{activeTask.instruction}</strong>
                      <span>
                        مرحله {activeTask.current_step} از{" "}
                        {activeTask.plan.length}
                      </span>
                    </div>

                    <div className="plan-list">
                      {activeTask.plan.map((step, index) => {
                        const outcome = taskOutcome(activeTask, index);
                        const pending = pendingRecord(activeTask);
                        const waiting =
                          activeTask.status === "awaiting_approval" &&
                          Number(pending?.step_index) === index;
                        const tool = taskTool(step);
                        const detail = activityDetail(tool, outcome);
                        const state = waiting
                          ? "waiting"
                          : outcome?.ok === false
                            ? "failed"
                            : outcome?.ok === true
                              ? "done"
                              : index === activeTask.current_step
                                ? "current"
                                : "";

                        return (
                          <div
                            key={index}
                            className={`plan-row ${state}`}
                          >
                            <span>
                              {waiting
                                ? "…"
                                : outcome?.ok === false
                                  ? "!"
                                  : outcome?.ok === true
                                    ? "✓"
                                    : index + 1}
                            </span>
                            <div>
                              <strong>
                                {activityLabel(tool, outcome, waiting)}
                              </strong>
                              <small>{tool}</small>
                              {step.reason ? (
                                <p className="tool-reason">
                                  {String(step.reason)}
                                </p>
                              ) : null}
                              {detail ? (
                                <pre className="activity-detail ltr">
                                  {detail}
                                </pre>
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {activeTask.status === "awaiting_approval" ? (
                      <div className="approval-card">
                        <strong>نیاز به تأیید</strong>
                        <p>{pendingReason(activeTask)}</p>
                        <dl className="approval-details">
                          <div>
                            <dt>Tool</dt>
                            <dd>{taskTool(pendingStep(activeTask) || {})}</dd>
                          </div>
                          <div>
                            <dt>Reason</dt>
                            <dd>
                              {String(
                                pendingStep(activeTask)?.reason || "-",
                              )}
                            </dd>
                          </div>
                          <div>
                            <dt>Expected</dt>
                            <dd>
                              {String(
                                pendingStep(activeTask)?.expected_result || "-",
                              )}
                            </dd>
                          </div>
                        </dl>
                        <pre>
                          {JSON.stringify(
                            taskArguments(pendingStep(activeTask) || {}),
                            null,
                            2,
                          )}
                        </pre>
                        <div>
                          <button
                            className="approve"
                            onClick={() => void approveTask(true)}
                          >
                            تأیید و ادامه
                          </button>
                          <button
                            className="reject"
                            onClick={() => void approveTask(false)}
                          >
                            لغو
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="panel-empty">
                    هنوز Task فعالی وجود ندارد.
                  </div>
                )}

                <div className="process-section">
                  <div className="panel-header">
                    <strong>Processها</strong>
                    <button onClick={() => void refreshProcesses()}>↻</button>
                  </div>

                  {processes.map((process) => (
                    <div className="process-row" key={process.id}>
                      <div>
                        <strong>{process.name}</strong>
                        <small>
                          PID {process.pid} — {process.running ? "running" : "stopped"}
                        </small>
                      </div>
                      {process.running ? (
                        <button onClick={() => void stopProcess(process.id)}>
                          توقف
                        </button>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {rightTab === "files" ? (
              <div className="files-editor-view">
                <div className="file-browser">
                  <div className="panel-header">
                    <strong>{currentPath}</strong>
                    <div>
                      <button disabled={currentPath === "."} onClick={() => void goUp()}>
                        ↑
                      </button>
                      <button onClick={() => void refreshFiles()}>↻</button>
                    </div>
                  </div>

                  {files.map((entry) => (
                    <button
                      className="file-row"
                      key={entry.path}
                      onClick={() => void openEntry(entry)}
                    >
                      <span>{entry.type === "directory" ? "▱" : "·"}</span>
                      <div>
                        <strong>{entry.name}</strong>
                        <small>{entry.type}</small>
                      </div>
                    </button>
                  ))}
                </div>

                <div className="editor-pane">
                  <div className="panel-header">
                    <strong className="ltr">
                      {selectedFile || "فایلی انتخاب نشده"}
                    </strong>
                    <button
                      disabled={!selectedFile || !fileDirty}
                      onClick={() => void saveFile()}
                    >
                      ذخیره
                    </button>
                  </div>

                  <textarea
                    className="code-editor ltr"
                    value={fileContent}
                    disabled={!selectedFile}
                    onChange={(event) => {
                      setFileContent(event.target.value);
                      setFileDirty(true);
                    }}
                    spellCheck={false}
                  />
                </div>
              </div>
            ) : null}

            {rightTab === "terminal" ? (
              <div className="terminal-view">
                <div className="terminal-command">
                  <textarea
                    className="ltr"
                    value={terminalCommand}
                    onChange={(event) => setTerminalCommand(event.target.value)}
                    rows={3}
                    spellCheck={false}
                  />
                  <button
                    disabled={terminalBusy || !terminalCommand.trim()}
                    onClick={() => void runTerminal()}
                  >
                    {terminalBusy ? "در حال اجرا…" : "اجرا"}
                  </button>
                </div>

                <pre className="terminal-output ltr">
                  {terminalOutput || "خروجی ترمینال اینجا نمایش داده می‌شود."}
                </pre>
              </div>
            ) : null}

            {rightTab === "git" ? (
              <div className="git-view">
                <div className="panel-header">
                  <strong>Git</strong>
                  <button onClick={() => void refreshGit()}>↻</button>
                </div>

                <div className="git-status-card">
                  <strong>
                    {gitStatus?.clean ? "Working tree clean" : "Changes detected"}
                  </strong>
                  <span className="ltr">
                    Branch: {gitStatus?.branch || "-"}
                  </span>
                  <pre className="ltr">
                    {(gitStatus?.changes || []).join("\n") || "No changes"}
                  </pre>
                </div>

                <div className="git-actions">
                  <input
                    value={checkpointMessage}
                    onChange={(event) => setCheckpointMessage(event.target.value)}
                    placeholder="Checkpoint message"
                  />
                  <button onClick={() => void createCheckpoint()}>
                    ساخت Checkpoint
                  </button>

                  <input
                    className="ltr"
                    value={rollbackCommit}
                    onChange={(event) => setRollbackCommit(event.target.value)}
                    placeholder="Commit hash"
                  />
                  <button className="danger-action" onClick={() => void rollback()}>
                    Rollback
                  </button>
                </div>

                <pre className="git-diff ltr">
                  {gitDiff || "Diff خالی است."}
                </pre>
              </div>
            ) : null}

            {rightTab === "preview" ? (
              <div className="preview-view">
                <div className="preview-toolbar">
                  <button
                    onClick={() =>
                      setPreviewUrl((current) =>
                        `${current.split("?")[0]}?t=${Date.now()}`,
                      )
                    }
                  >
                    ↻
                  </button>
                  <input
                    className="ltr"
                    value={previewUrl.split("?")[0]}
                    onChange={(event) => setPreviewUrl(event.target.value)}
                  />
                </div>
                <iframe
                  key={previewUrl}
                  src={previewUrl}
                  title="Project Preview"
                />
              </div>
            ) : null}
          </div>
        </aside>
      </div>
    </div>
  );
}
