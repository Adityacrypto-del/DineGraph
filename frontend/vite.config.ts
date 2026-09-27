import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api/* is forwarded to the FastAPI server so the browser
// talks to one origin. Point it elsewhere with DINEGRAPH_API (e.g. http://localhost:9000).
const target = process.env.DINEGRAPH_API ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target, changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
    },
  },
});
