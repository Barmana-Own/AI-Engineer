const ORCHESTRATOR_URL = "http://127.0.0.1:8012";
const GATEWAY_URL = "http://127.0.0.1:8010";

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
    throw new Error(
      typeof payload === "string" ? payload : JSON.stringify(payload, null, 2),
    );
  }

  return payload as T;
}

function get<T>(url: string): Promise<T> {
  return fetch(url).then((response) => parseResponse<T>(response));
}

export function getHealth(): Promise<HealthResponse> {
  return get(`${ORCHESTRATOR_URL}/health`);
}

export function getRuntimeModels(): Promise<RuntimeModels> {
  return get(`${GATEWAY_URL}/v1/runtime/models`);
}

export function listSubagents(): Promise<SubagentRole[]> {
  return get(`${ORCHESTRATOR_URL}/v1/agent/subagents`);
}

export function listProjects(): Promise<Project[]> {
  return get(`${ORCHESTRATOR_URL}/v1/projects`);
}

export async function createProject(
  name: string,
  workspace?: string,
): Promise<Project> {
  return parseResponse(
    await fetch(`${ORCHESTRATOR_URL}/v1/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, workspace: workspace || null }),
    }),
  );
}

export async function createAgentTask(
  projectId: string,
  instruction: string,
): Promise<AgentTask> {
  return parseResponse(
    await fetch(`${ORCHESTRATOR_URL}/v1/agent/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId, instruction }),
    }),
  );
}

export async function startSelfImprove(
  projectId: string,
  goal: string,
): Promise<AutonomyRun> {
  return parseResponse(
    await fetch(`${ORCHESTRATOR_URL}/v1/agent/projects/${projectId}/self-improve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, cycles: 1 }),
    }),
  );
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

export async function approveAgentTask(
  taskId: string,
  approved: boolean,
): Promise<AgentTask> {
  return parseResponse(
    await fetch(`${ORCHESTRATOR_URL}/v1/agent/tasks/${taskId}/approval`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved }),
    }),
  );
}
