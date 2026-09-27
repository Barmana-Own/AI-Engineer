import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5175,
    strictPort: true,
    proxy: {
      "/api/orchestrator": {
        target: "http://127.0.0.1:8012",
        rewrite: (path) => path.replace(/^\/api\/orchestrator/, "") || "/",
      },
      "/api/gateway": {
        target: "http://127.0.0.1:8010",
        rewrite: (path) => path.replace(/^\/api\/gateway/, "") || "/",
      },
    },
  },
});