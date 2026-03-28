import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // REST API proxy
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Disable response buffering so MJPEG streams flow continuously
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            const contentType = proxyRes.headers['content-type'] ?? '';
            if (contentType.startsWith('multipart/')) {
              // Don't buffer streaming responses
              proxyRes.headers['x-accel-buffering'] = 'no';
            }
          });
        },
      },
      // WebSocket proxy for live detections
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
