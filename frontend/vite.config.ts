import { sites } from "@openai/sites-vite-plugin";
import react from "@vitejs/plugin-react";
import { existsSync } from "node:fs";
import { defineConfig } from "vite";

const hasSitesConfig = existsSync(new URL("./.openai/hosting.json", import.meta.url));
const isPagesBuild = process.env.VITE_PAGES_BUILD === "true";
const base = process.env.VITE_BASE_PATH ?? "/";

export default defineConfig({
  base,
  plugins: [react(), ...(hasSitesConfig && !isPagesBuild ? [sites()] : [])],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
