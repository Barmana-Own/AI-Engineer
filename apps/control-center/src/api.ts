const API_BASE = "http://127.0.0.1:8012";

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
      typeof payload === "string"
        ? payload
        : JSON.stringify(payload, null, 2),
    );
  }

  return payload as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return parseResponse(
    await fetch(`${API_BASE}/health`),
  );
}

export async function listProjects(): Promise<Project[]> {
  return parseResponse(
    await fetch(`${API_BASE}/v1/projects`),
  );
}

export async function createProject(
  name: string,
  workspace?: string,
): Promise<Project> {
  return parseResponse(
    await fetch(`${API_BASE}/v1/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        workspace: workspace || null,
      }),
    }),
  );
}

export async function createAgentTask(
  projectId: string,
  instruction: string,
): Promise<AgentTask> {
  return parseResponse(
    await fetch(`${API_BASE}/v1/agent/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projectId,
        instruction,
      }),
    }),
  );
}

export async function getAgentTask(
  taskId: string,
): Promise<AgentTask> {
  return parseResponse(
    await fetch(`${API_BASE}/v1/agent/tasks/${taskId}`),
  );
}

export async function listAgentTasks(
  projectId?: string,
): Promise<AgentTask[]> {
  const query = projectId
    ? `?project_id=${encodeURIComponent(projectId)}`
    : "";

  return parseResponse(
    await fetch(`${API_BASE}/v1/agent/tasks${query}`),
  );
}

export async function approveAgentTask(
  taskId: string,
  approved: boolean,
): Promise<AgentTask> {
  return parseResponse(
    await fetch(
      `${API_BASE}/v1/agent/tasks/${taskId}/approval`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      },
    ),
  );
}