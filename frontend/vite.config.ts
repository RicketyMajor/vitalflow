import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base './' so the static build deploys under any path. Routing is hash-based, so the document
// URL never leaves the root and relative asset paths always resolve.
export default defineConfig({ base: "./", plugins: [react()] });
