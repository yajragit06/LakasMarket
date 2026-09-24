import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// The shared package is consumed directly from source so that web and a future
// React Native app import the same domain logic.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@lakasmarket/shared": path.resolve(__dirname, "../packages/shared/src"),
    },
  },
  server: { port: 5173 },
});
