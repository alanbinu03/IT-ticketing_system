import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy = process.env.API_PROXY ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": { target: apiProxy, changeOrigin: true },
      "/health": { target: apiProxy, changeOrigin: true },
      "/ready": { target: apiProxy, changeOrigin: true },
    },
    watch: {
      usePolling: process.env.CHOKIDAR_USEPOLLING === "true",
    },
  },
});
