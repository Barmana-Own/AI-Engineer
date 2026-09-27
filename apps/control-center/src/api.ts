function apiBase(value: string | undefined, fallback: string): string {
  return (value?.trim() || fallback).replace(/\/+$/, "");
}

// Same-origin paths are used in production behind IIS. Vite proxies the same
// paths during local development, so the browser never needs a service token.
const ORCHESTRATOR_URL = apiBase(
  import.meta.env.VITE_ORCHESTRATOR_URL,
  "/api/orchestrator",
);

export type Project = {
  id: string;
  name: string;
  workspace: string;
  created_at: string;
  updated_at: string;
};

export type AgentTask = {
  id: string;
  project_id: string;
  instruction: string;
  mode: "interactive" | "autonomous";
  status: string;
  plan: Array<Record<string, unknown>>;
  current_step: number;
  results: Array<Record<string, unknown>>;
  approved_steps: number[];
  pending: Record<string, unknown> | null;
  final_output: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  dependencies: {
    model_gateway: { ok: boolean };
    local_agent: { ok: boolean };
  };
};

export type CapabilitiesResponse = {
  service: string;
  health_endpoint: string;
  workspace_guarded: boolean;
  mutation_requires_checkpoint: boolean;
  autonomous_supervisor: {
    enabled: boolean;
    interval_minutes: number;
    cycles_per_run: number;
  };
};

export type AutonomyRun = {
  id: string;
  project_id: string;
  goal: string;
  requested_cycles: number;
  completed_cycles: number;
  status: string;
  task_ids: string[];
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type SubagentRole = {
  key: string;
  title: string;
  objective: string;
  read_only: boolean;
  validation_required: boolean;
  section: string;
  capabilities: string[];
};

export type SubagentHandoff = {
  id: string;
  run_id: string;
  project_id: string;
  task_id: string | null;
  role: string;
  section: string;
  schema_version: string;
  status: string;
  summary: string;
  evidence: Array<Record<string, unknown>>;
  changed_files: string[];
  validations: Array<Record<string, unknown>>;
  blockers: string[];
  next_action: string | null;
  confidence: number;
  previous_handoff_ids: string[];
  created_at: string;
  updated_at: string;
};

export type RuntimeModels = {
  provider: string;
  provider_configured: boolean;
  default_model: string;
  fallback_models: string[];
  max_fallback_attempts: number;
  max_retries_per_model: number;
  fallback_on: string[];
  candidate_order: string;
};

export type BrowserSession = {
  authenticated: boolean;
  role: "OWNER" | "CONTROL" | null;
  username: string | null;
  expires_at: string | null;
  csrf_token: string | null;
};

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const API_TIMEOUT_MS = 10_000;
let csrfToken: string | null = null;

export function setCsrfToken(value: string | null): void {
  csrfToken = value;
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

export function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  let payload: unknown = null;

  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : typeof payload === "string"
          ? payload
          : JSON.stringify(payload, null, 2);
    throw new ApiError(response.status, detail);
  }

  return payload as T;
}

function get<T>(url: string): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  return fetch(url, { signal: controller.signal, credentials: "include" })
    .then((response) => parseResponse<T>(response))
    .finally(() => window.clearTimeout(timeout));
}

async function mutate<T>(url: string, init: RequestInit): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  return parseResponse<T>(
    await fetch(url, { ...init, headers, credentials: "include" }),
  );
}

export async function getSession(): Promise<BrowserSession> {
  const session = await get<BrowserSession>(`${ORCHESTRATOR_URL}/auth/session`);
  setCsrfToken(session.authenticated ? session.csrf_token : null);
  return session;
}

export async function login(username: string, password: string): Promise<BrowserSession> {
  const session = await mutate<BrowserSession>(`${ORCHESTRATOR_URL}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setCsrfToken(session.csrf_token);
  return session;
}

export async function logout(): Promise<void> {
  try {
    await mutate<BrowserSession>(`${ORCHESTRATOR_URL}/auth/logout`, { method: "POST" });
  } finally {
    setCsrfToken(null);
  }
}

export function getHealth(): Promise<HealthResponse> {
  return get(`${ORCHESTRATOR_URL}/health`);
}

export function getCapabilities(): Promise<CapabilitiesResponse> {
  return get(`${ORCHESTRATOR_URL}/capabilities`);
}

export function getRuntimeModels(): Promise<RuntimeModels> {
  return get(`${ORCHESTRATOR_URL}/v1/control-center/runtime/models`);
}

export function listSubagents(): Promise<SubagentRole[]> {
  return get(`${ORCHESTRATOR_URL}/v1/agent/subagents`);
}

export function listSectionSubagents(): Promise<SubagentRole[]> {
  return get(`${ORCHESTRATOR_URL}/v1/agent/subagents/sections`);
}

export function listProjects(): Promise<Project[]> {
  return get(`${ORCHESTRATOR_URL}/v1/projects`);
}

export async function createProject(
  name: string,
  workspace?: string,
): Promise<Project> {
  return mutate<Project>(`${ORCHESTRATOR_URL}/v1/projects`, {
    method: "POST",
    body: JSON.stringify({ name, workspace: workspace || null }),
  });
}

export async function createAgentTask(
  projectId: string,
  instruction: string,
): Promise<AgentTask> {
  return mutate<AgentTask>(`${ORCHESTRATOR_URL}/v1/agent/tasks`, {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, instruction }),
  });
}

export async function startSelfImprove(
  projectId: string,
  goal: string,
): Promise<AutonomyRun> {
  return mutate<AutonomyRun>(`${ORCHESTRATOR_URL}/v1/agent/projects/${projectId}/self-improve`, {
    method: "POST",
    body: JSON.stringify({ goal, cycles: 1 }),
  });
}

export function getAgentTask(taskId: string): Promise<AgentTask> {
  return get(`${ORCHESTRATOR_URL}/v1/agent/tasks/${taskId}`);
}

export function listAgentTasks(projectId?: string): Promise<AgentTask[]> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return get(`${ORCHESTRATOR_URL}/v1/agent/tasks${query}`);
}

export function listAutonomyRuns(projectId: string): Promise<AutonomyRun[]> {
  return get(
    `${ORCHESTRATOR_URL}/v1/agent/autonomy/runs?project_id=${encodeURIComponent(projectId)}&limit=12`,
  );
}

export type AutonomyRunStatus = {
  id: string;
  project_id: string;
  status: string;
  requested_cycles: number;
  completed_cycles: number;
  task_count: number;
  task_status_counts: Record<string, number>;
  error: string | null;
  updated_at: string;
};

export function getAutonomyRunStatus(runId: string): Promise<AutonomyRunStatus> {
  return get(`${ORCHESTRATOR_URL}/v1/agent/autonomy/runs/${encodeURIComponent(runId)}/status`);
}

export function listRunSubagents(runId: string): Promise<SubagentHandoff[]> {
  return get(`${ORCHESTRATOR_URL}/v1/agent/autonomy/runs/${encodeURIComponent(runId)}/subagents?limit=100`);
}

export async function approveAgentTask(
  taskId: string,
  approved: boolean,
): Promise<AgentTask> {
  return mutate<AgentTask>(`${ORCHESTRATOR_URL}/v1/agent/tasks/${taskId}/approval`, {
    method: "POST",
    body: JSON.stringify({ approved }),
  });
}