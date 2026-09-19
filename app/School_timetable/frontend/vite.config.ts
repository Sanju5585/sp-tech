import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/apps/school-timetable/app/" : "/",
  build: {
    outDir: "../../../static/timetable-app",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8001",
    },
  },
}));
