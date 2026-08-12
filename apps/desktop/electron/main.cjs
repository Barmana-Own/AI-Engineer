const {
  app,
  BrowserWindow,
  ipcMain,
  shell,
} = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const { spawn } = require("node:child_process");

const PROJECT_ROOT = "F:\\AI-Engineer";
const WORKSPACE_ROOT = path.resolve(PROJECT_ROOT, "workspaces");
const SELF_WORKSPACE_NAME = "ai-engineer";

const SERVICE_BASES = {
  orchestrator: "http://127.0.0.1:8012",
  agent: "http://127.0.0.1:8011",
  gateway: "http://127.0.0.1:8010",
};

let mainWindow = null;

function safeWorkspace(workspace) {
  if (typeof workspace !== "string" || !workspace.trim()) {
    throw new Error("Workspace is required.");
  }

  if (workspace.trim().toLowerCase() === SELF_WORKSPACE_NAME) {
    return PROJECT_ROOT;
  }

  const resolved = path.resolve(WORKSPACE_ROOT, workspace);

  if (
    resolved !== WORKSPACE_ROOT &&
    !resolved.startsWith(`${WORKSPACE_ROOT}${path.sep}`)
  ) {
    throw new Error("Workspace path is outside the allowed root.");
  }

  return resolved;
}

async function apiRequest({ service, method, path: apiPath, body }) {
  const base = SERVICE_BASES[service];

  if (!base) {
    throw new Error("Unknown local service.");
  }

  if (typeof apiPath !== "string" || !apiPath.startsWith("/")) {
    throw new Error("Invalid API path.");
  }

  const response = await fetch(`${base}${apiPath}`, {
    method: method || "GET",
    headers: body === undefined
      ? { Accept: "application/json" }
      : {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await response.text();
  let payload = null;

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

  return payload;
}

function findVSCode() {
  const candidates = [
    process.env.LOCALAPPDATA &&
      path.join(
        process.env.LOCALAPPDATA,
        "Programs",
        "Microsoft VS Code",
        "Code.exe",
      ),
    process.env.ProgramFiles &&
      path.join(
        process.env.ProgramFiles,
        "Microsoft VS Code",
        "Code.exe",
      ),
    process.env["ProgramFiles(x86)"] &&
      path.join(
        process.env["ProgramFiles(x86)"],
        "Microsoft VS Code",
        "Code.exe",
      ),
  ].filter(Boolean);

  return candidates.find((candidate) => fs.existsSync(candidate));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1580,
    height: 960,
    minWidth: 1180,
    minHeight: 720,
    frame: false,
    backgroundColor: "#f5f5f4",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (!mainWindow) return;

    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }

    mainWindow.focus();
  });

  app.whenReady().then(() => {
    ipcMain.handle("api:request", (_event, payload) =>
      apiRequest(payload),
    );

    ipcMain.handle("project:open-folder", async (_event, workspace) => {
      const projectPath = safeWorkspace(workspace);
      const error = await shell.openPath(projectPath);

      if (error) {
        throw new Error(error);
      }

      return true;
    });

    ipcMain.handle("project:open-code", async (_event, workspace) => {
      const projectPath = safeWorkspace(workspace);
      const code = findVSCode();

      if (!code) {
        throw new Error("Visual Studio Code پیدا نشد.");
      }

      const child = spawn(code, [projectPath], {
        detached: true,
        stdio: "ignore",
        windowsHide: true,
      });

      child.unref();
      return true;
    });

    ipcMain.handle("window:minimize", () => {
      mainWindow?.minimize();
    });

    ipcMain.handle("window:maximize", () => {
      if (!mainWindow) return;

      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    });

    ipcMain.handle("window:close", () => {
      mainWindow?.close();
    });

    createWindow();
  });
}

app.on("window-all-closed", () => {
  app.quit();
});
