import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    server: {
        host: "0.0.0.0",
        port: 5173,
        proxy: {
            "/health": "http://localhost:8000",
            "/config": "http://localhost:8000",
            "/streams": "http://localhost:8000",
            "/alerts": "http://localhost:8000",
            "/zones": "http://localhost:8000",
            "/metrics": "http://localhost:8000"
        }
    }
});
