import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        proxy: {
            "/vp": {
                target: "http://localhost:8001",
                changeOrigin: true,
            },
            "/sensor": {
                target: "http://localhost:8001",
                changeOrigin: true,
            },
        },
    },
});
