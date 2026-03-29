export default {
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    theme: {
        extend: {
            colors: {
                surface: "#0f1720",
                panel: "#162130",
                panelAlt: "#1c2b40",
                accent: "#f97316",
                signal: "#22c55e",
                warning: "#facc15",
                danger: "#ef4444",
                mist: "#94a3b8"
            },
            boxShadow: {
                glow: "0 20px 60px rgba(249, 115, 22, 0.16)"
            },
            fontFamily: {
                display: ["Space Grotesk", "Segoe UI", "sans-serif"],
                body: ["Manrope", "Segoe UI", "sans-serif"]
            }
        }
    },
    plugins: []
};
