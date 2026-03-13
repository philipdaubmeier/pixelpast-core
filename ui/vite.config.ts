import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

function normalizeApiProxyTarget(value: string): string {
  return value.replace(/\/api\/?$/, "").replace(/\/$/, "");
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const apiProxyTarget = normalizeApiProxyTarget(
    env.VITE_PIXELPAST_API_BASE_URL || "http://127.0.0.1:8000",
  );

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
