import { defineConfig } from "vite";

export default defineConfig({
  build: {
    emptyOutDir: false,
    lib: {
      entry: "worker/index.ts",
      formats: ["es"],
      fileName: () => "index.js",
    },
    outDir: "dist/server",
    target: "es2022",
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
