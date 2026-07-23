import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, process.cwd(), "");
  const backendTarget =
    environment.VITE_DEV_API_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./tests/setup.ts",
      css: true,
      globals: true,
    },
  };
});
