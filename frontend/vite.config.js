import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev proxy makes local development same-origin like production, so the session cookie just works.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
