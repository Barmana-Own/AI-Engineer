from __future__ import annotations

import argparse
import json
from pathlib import Path

WORKSPACE_ROOT = Path(r"F:\AI-Engineer\workspaces").resolve()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def validate_target(raw_target: str) -> Path:
    target = Path(raw_target).resolve()

    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise SystemExit(
            "Target must be inside F:\\AI-Engineer\\workspaces."
        ) from exc

    target.mkdir(parents=True, exist_ok=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    root = validate_target(args.target)

    files: dict[str, str] = {
        "package.json": r'''{
  "name": "taskflow",
  "version": "1.0.0",
  "private": true,
  "workspaces": ["client", "server"],
  "scripts": {
    "dev": "concurrently -k -n SERVER,CLIENT \"npm --workspace server run dev\" \"npm --workspace client run dev\"",
    "build": "npm --workspace client run build",
    "smoke": "npm --workspace server run smoke",
    "verify": "npm run build && npm run smoke"
  },
  "devDependencies": {
    "concurrently": "^9.2.1"
  }
}
''',
        ".gitignore": r'''node_modules/
client/dist/
*.log
.env
.DS_Store
''',
        "README.md": r'''# TaskFlow

TaskFlow is a local full-stack test project generated and verified by AI Engineer.

## Stack

- React
- TypeScript
- Vite
- Node.js
- Express
- JSON file storage

## Ports

- Frontend: `http://127.0.0.1:5176`
- Backend: `http://127.0.0.1:5055`

## Install

```powershell
npm install
```

## Development

```powershell
npm run dev
```

## Verify

```powershell
npm run verify
```
''',
        "client/package.json": r'''{
  "name": "taskflow-client",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1 --port 5176",
    "build": "tsc --noEmit -p tsconfig.json && vite build"
  },
  "dependencies": {
    "react": "^19.1.1",
    "react-dom": "^19.1.1"
  },
  "devDependencies": {
    "@types/react": "^19.1.10",
    "@types/react-dom": "^19.1.7",
    "@vitejs/plugin-react": "^5.0.2",
    "typescript": "^5.9.2",
    "vite": "^7.1.5"
  }
}
''',
        "client/tsconfig.json": r'''{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
''',
        "client/vite.config.ts": r'''import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5176,
    strictPort: true,
  },
});
''',
        "client/index.html": r'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TaskFlow</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
''',
        "client/src/main.tsx": r'''import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
''',
        "client/src/App.tsx": r'''import { FormEvent, useEffect, useMemo, useState } from "react";

type TaskStatus = "todo" | "doing" | "done";

type Task = {
  id: string;
  title: string;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
};

const API_URL = "http://127.0.0.1:5055/api/tasks";

const columns: Array<{ status: TaskStatus; label: string }> = [
  { status: "todo", label: "To do" },
  { status: "doing", label: "Doing" },
  { status: "done", label: "Done" },
];

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & { error?: string };

  if (!response.ok) {
    throw new Error(payload.error ?? "Request failed.");
  }

  return payload;
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function loadTasks() {
    setLoading(true);
    setError("");

    try {
      setTasks(await parseResponse<Task[]>(await fetch(API_URL)));
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTasks();
  }, []);

  async function createTask(event: FormEvent) {
    event.preventDefault();
    const cleanTitle = title.trim();

    if (!cleanTitle) return;

    setError("");

    try {
      const created = await parseResponse<Task>(
        await fetch(API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: cleanTitle, status: "todo" }),
        }),
      );

      setTasks((current) => [created, ...current]);
      setTitle("");
    } catch (nextError) {
      setError(String(nextError));
    }
  }

  async function updateTask(
    id: string,
    changes: Partial<Pick<Task, "title" | "status">>,
  ) {
    setBusyId(id);
    setError("");

    try {
      const updated = await parseResponse<Task>(
        await fetch(`${API_URL}/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(changes),
        }),
      );

      setTasks((current) =>
        current.map((task) => (task.id === id ? updated : task)),
      );
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setBusyId(null);
    }
  }

  async function deleteTask(id: string) {
    setBusyId(id);
    setError("");

    try {
      await parseResponse<{ deleted: boolean }>(
        await fetch(`${API_URL}/${id}`, { method: "DELETE" }),
      );

      setTasks((current) => current.filter((task) => task.id !== id));
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setBusyId(null);
    }
  }

  async function saveEdit(id: string) {
    const cleanTitle = editingTitle.trim();

    if (!cleanTitle) return;

    await updateTask(id, { title: cleanTitle });
    setEditingId(null);
    setEditingTitle("");
  }

  const visibleTasks = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    return normalized
      ? tasks.filter((task) =>
          task.title.toLowerCase().includes(normalized),
        )
      : tasks;
  }, [query, tasks]);

  return (
    <main className="page-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">FULL-STACK TEST PROJECT</p>
          <h1>TaskFlow</h1>
          <p className="subtitle">
            A compact task dashboard built by AI Engineer.
          </p>
        </div>

        <div className="count-card">
          <strong>{tasks.length}</strong>
          <span>Total tasks</span>
        </div>
      </header>

      <section className="toolbar">
        <form className="create-form" onSubmit={createTask}>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Add a new task"
            maxLength={120}
          />
          <button type="submit">Add task</button>
        </form>

        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search tasks"
        />
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      {loading ? (
        <section className="state-card">Loading tasks...</section>
      ) : (
        <section className="board">
          {columns.map((column) => {
            const columnTasks = visibleTasks.filter(
              (task) => task.status === column.status,
            );

            return (
              <article className="column" key={column.status}>
                <div className="column-heading">
                  <h2>{column.label}</h2>
                  <span>{columnTasks.length}</span>
                </div>

                <div className="task-list">
                  {columnTasks.map((task) => (
                    <div className="task-card" key={task.id}>
                      {editingId === task.id ? (
                        <div className="edit-row">
                          <input
                            value={editingTitle}
                            onChange={(event) =>
                              setEditingTitle(event.target.value)
                            }
                            maxLength={120}
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={() => void saveEdit(task.id)}
                          >
                            Save
                          </button>
                        </div>
                      ) : (
                        <strong>{task.title}</strong>
                      )}

                      <div className="task-actions">
                        <select
                          value={task.status}
                          disabled={busyId === task.id}
                          onChange={(event) =>
                            void updateTask(task.id, {
                              status: event.target.value as TaskStatus,
                            })
                          }
                        >
                          {columns.map((option) => (
                            <option key={option.status} value={option.status}>
                              {option.label}
                            </option>
                          ))}
                        </select>

                        <button
                          type="button"
                          disabled={busyId === task.id}
                          onClick={() => {
                            setEditingId(task.id);
                            setEditingTitle(task.title);
                          }}
                        >
                          Edit
                        </button>

                        <button
                          className="danger"
                          type="button"
                          disabled={busyId === task.id}
                          onClick={() => void deleteTask(task.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}

                  {columnTasks.length === 0 ? (
                    <p className="empty">No matching tasks.</p>
                  ) : null}
                </div>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}
''',
        "client/src/styles.css": r''':root {
  font-family: Inter, "Segoe UI", Arial, sans-serif;
  color: #edf4ff;
  background: #07111f;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 8%, #193965 0, transparent 30%),
    radial-gradient(circle at 88% 5%, #17483d 0, transparent 28%),
    linear-gradient(150deg, #07111f, #0a1628 52%, #07111f);
}

button,
input,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.55;
}

.page-shell {
  width: min(1240px, calc(100% - 32px));
  margin: 0 auto;
  padding: 42px 0 80px;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #61dcff;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.16em;
}

h1 {
  margin: 0;
  font-size: clamp(48px, 8vw, 78px);
  line-height: 0.95;
}

.subtitle {
  margin: 13px 0 0;
  color: #9fb0c9;
}

.count-card {
  display: grid;
  min-width: 145px;
  padding: 18px;
  border: 1px solid rgba(148, 175, 215, 0.18);
  border-radius: 18px;
  background: rgba(10, 22, 39, 0.84);
}

.count-card strong {
  font-size: 30px;
}

.count-card span {
  color: #92a5bf;
}

.toolbar {
  display: grid;
  grid-template-columns: 1.5fr 0.7fr;
  gap: 14px;
  margin-bottom: 20px;
}

.create-form {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

input,
select,
button {
  min-height: 46px;
  border-radius: 12px;
}

input,
select {
  border: 1px solid rgba(148, 175, 215, 0.22);
  outline: none;
  background: #091526;
  color: #edf4ff;
}

input {
  width: 100%;
  padding: 0 14px;
}

select {
  padding: 0 10px;
}

button {
  border: 0;
  padding: 0 16px;
  background: linear-gradient(135deg, #55d6ff, #658dff);
  color: #06111e;
  font-weight: 900;
}

.board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.column {
  min-height: 430px;
  padding: 18px;
  border: 1px solid rgba(148, 175, 215, 0.16);
  border-radius: 20px;
  background: rgba(9, 20, 36, 0.86);
}

.column-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.column-heading h2 {
  margin: 0;
  font-size: 19px;
}

.column-heading span {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: #162a43;
  color: #8fdcff;
}

.task-list {
  display: grid;
  gap: 12px;
}

.task-card {
  padding: 15px;
  border: 1px solid rgba(148, 175, 215, 0.14);
  border-radius: 15px;
  background: #07111e;
}

.task-actions,
.edit-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 13px;
}

.task-actions button,
.edit-row button {
  min-height: 38px;
  padding: 0 12px;
}

.task-actions select {
  min-height: 38px;
  flex: 1;
}

.danger {
  background: #63243a;
  color: #ffdce5;
}

.empty,
.state-card {
  color: #899bb5;
}

.state-card,
.error-banner {
  padding: 18px;
  border-radius: 15px;
}

.state-card {
  border: 1px solid rgba(148, 175, 215, 0.16);
  background: rgba(9, 20, 36, 0.86);
}

.error-banner {
  border: 1px solid rgba(255, 101, 126, 0.3);
  background: rgba(111, 24, 43, 0.62);
  color: #ffd8df;
}

@media (max-width: 900px) {
  .board,
  .toolbar {
    grid-template-columns: 1fr;
  }
}
''',
        "server/package.json": r'''{
  "name": "taskflow-server",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "node --watch src/server.js",
    "start": "node src/server.js",
    "smoke": "node smoke.mjs"
  },
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^5.1.0"
  },
  "devDependencies": {
    "supertest": "^7.1.4"
  }
}
''',
        "server/src/app.js": r'''import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import cors from "cors";
import express from "express";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const defaultTasksFile = path.resolve(currentDirectory, "../data/tasks.json");

function tasksFile() {
  return process.env.TASKS_FILE
    ? path.resolve(process.env.TASKS_FILE)
    : defaultTasksFile;
}

async function ensureStore() {
  const file = tasksFile();
  await fs.mkdir(path.dirname(file), { recursive: true });

  try {
    await fs.access(file);
  } catch {
    await fs.writeFile(file, "[]\n", "utf8");
  }
}

async function readTasks() {
  await ensureStore();
  const value = JSON.parse(await fs.readFile(tasksFile(), "utf8"));

  if (!Array.isArray(value)) {
    throw new Error("Task storage is invalid.");
  }

  return value;
}

async function writeTasks(tasks) {
  await ensureStore();
  await fs.writeFile(
    tasksFile(),
    `${JSON.stringify(tasks, null, 2)}\n`,
    "utf8",
  );
}

const statuses = new Set(["todo", "doing", "done"]);

function validTitle(value) {
  return typeof value === "string" &&
    value.trim().length > 0 &&
    value.trim().length <= 120;
}

function validStatus(value) {
  return statuses.has(value);
}

const app = express();

app.use(
  cors({
    origin: [
      "http://127.0.0.1:5176",
      "http://localhost:5176",
    ],
  }),
);
app.use(express.json({ limit: "64kb" }));

app.get("/health", (_request, response) => {
  response.json({ status: "ok", service: "taskflow-server" });
});

app.get("/api/tasks", async (_request, response, next) => {
  try {
    response.json(await readTasks());
  } catch (error) {
    next(error);
  }
});

app.post("/api/tasks", async (request, response, next) => {
  try {
    const title = request.body?.title;
    const status = request.body?.status ?? "todo";

    if (!validTitle(title) || !validStatus(status)) {
      return response.status(400).json({
        error: "A valid title and status are required.",
      });
    }

    const now = new Date().toISOString();
    const task = {
      id: crypto.randomUUID(),
      title: title.trim(),
      status,
      createdAt: now,
      updatedAt: now,
    };

    const tasks = await readTasks();
    tasks.unshift(task);
    await writeTasks(tasks);

    return response.status(201).json(task);
  } catch (error) {
    return next(error);
  }
});

app.patch("/api/tasks/:id", async (request, response, next) => {
  try {
    const tasks = await readTasks();
    const index = tasks.findIndex(
      (task) => task.id === request.params.id,
    );

    if (index < 0) {
      return response.status(404).json({ error: "Task not found." });
    }

    const changes = {};

    if ("title" in request.body) {
      if (!validTitle(request.body.title)) {
        return response.status(400).json({
          error: "Title must contain 1 to 120 characters.",
        });
      }

      changes.title = request.body.title.trim();
    }

    if ("status" in request.body) {
      if (!validStatus(request.body.status)) {
        return response.status(400).json({
          error: "Status must be todo, doing, or done.",
        });
      }

      changes.status = request.body.status;
    }

    if (Object.keys(changes).length === 0) {
      return response.status(400).json({
        error: "No valid fields were supplied.",
      });
    }

    tasks[index] = {
      ...tasks[index],
      ...changes,
      updatedAt: new Date().toISOString(),
    };

    await writeTasks(tasks);
    return response.json(tasks[index]);
  } catch (error) {
    return next(error);
  }
});

app.delete("/api/tasks/:id", async (request, response, next) => {
  try {
    const tasks = await readTasks();
    const index = tasks.findIndex(
      (task) => task.id === request.params.id,
    );

    if (index < 0) {
      return response.status(404).json({ error: "Task not found." });
    }

    const [deleted] = tasks.splice(index, 1);
    await writeTasks(tasks);

    return response.json({ deleted: true, task: deleted });
  } catch (error) {
    return next(error);
  }
});

app.use((error, _request, response, _next) => {
  console.error(error);
  response.status(500).json({ error: "Internal server error." });
});

export default app;
''',
        "server/src/server.js": r'''import app from "./app.js";

const port = Number(process.env.PORT ?? 5055);

app.listen(port, "127.0.0.1", () => {
  console.log(`TaskFlow API: http://127.0.0.1:${port}`);
});
''',
        "server/smoke.mjs": r'''import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import request from "supertest";

const temporaryDirectory = await fs.mkdtemp(
  path.join(os.tmpdir(), "taskflow-smoke-"),
);

process.env.TASKS_FILE = path.join(temporaryDirectory, "tasks.json");

const { default: app } = await import(
  `./src/app.js?smoke=${Date.now()}`
);

const created = await request(app)
  .post("/api/tasks")
  .send({ title: "Smoke task", status: "todo" })
  .expect(201);

assert.equal(created.body.title, "Smoke task");
assert.equal(created.body.status, "todo");

const listed = await request(app)
  .get("/api/tasks")
  .expect(200);

assert.equal(listed.body.length, 1);
assert.equal(listed.body[0].id, created.body.id);

const updated = await request(app)
  .patch(`/api/tasks/${created.body.id}`)
  .send({ title: "Updated smoke task", status: "done" })
  .expect(200);

assert.equal(updated.body.title, "Updated smoke task");
assert.equal(updated.body.status, "done");

await request(app)
  .delete(`/api/tasks/${created.body.id}`)
  .expect(200);

const empty = await request(app)
  .get("/api/tasks")
  .expect(200);

assert.deepEqual(empty.body, []);

await fs.rm(temporaryDirectory, {
  recursive: true,
  force: true,
});

console.log("TASKFLOW_API_SMOKE_OK");
''',
        "server/data/tasks.json": "[]\n",
    }

    for relative_path, content in files.items():
        write_text(root / relative_path, content)

    expected = [
        root / "package.json",
        root / "README.md",
        root / "client/src/App.tsx",
        root / "server/src/app.js",
        root / "server/data/tasks.json",
    ]

    missing = [str(path) for path in expected if not path.is_file()]

    if missing:
        raise SystemExit(f"Scaffolding failed; missing: {missing}")

    print(
        json.dumps(
            {
                "ok": True,
                "root": str(root),
                "files_written": len(files),
            }
        )
    )


if __name__ == "__main__":
    main()
