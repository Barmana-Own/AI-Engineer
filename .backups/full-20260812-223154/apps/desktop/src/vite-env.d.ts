/// <reference types="vite/client" />

type ServiceName = "orchestrator" | "agent" | "gateway";

interface Window {
  aiDesktop: {
    api: (
      service: ServiceName,
      method: string,
      path: string,
      body?: unknown,
    ) => Promise<any>;
    openFolder: (workspace: string) => Promise<boolean>;
    openCode: (workspace: string) => Promise<boolean>;
    window: {
      minimize: () => Promise<void>;
      maximize: () => Promise<void>;
      close: () => Promise<void>;
    };
  };
}
