const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("aiDesktop", {
  api: (service, method, path, body) =>
    ipcRenderer.invoke("api:request", { service, method, path, body }),

  openFolder: (workspace) =>
    ipcRenderer.invoke("project:open-folder", workspace),

  openCode: (workspace) =>
    ipcRenderer.invoke("project:open-code", workspace),

  window: {
    minimize: () => ipcRenderer.invoke("window:minimize"),
    maximize: () => ipcRenderer.invoke("window:maximize"),
    close: () => ipcRenderer.invoke("window:close"),
  },
});
