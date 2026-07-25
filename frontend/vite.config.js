import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/resolve": "http://localhost:8080",
      "/download": "http://localhost:8080",
      "/queue": "http://localhost:8080",
      "/auth": "http://localhost:8080",
    },
  },
  build: {
    outDir: "../app/static",
    emptyOutDir: true,
  },
});
