import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// API target: inside Docker Compose set VITE_API_URL=http://backend:8000
const apiTarget = process.env.VITE_API_URL || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // Listen on all network addresses (0.0.0.0 / 127.0.0.1) for Windows & Mac
    proxy: {
      '/user': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/upload': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/query': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/sources': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/delete': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  base: './',
  build: {
    // FastAPI serves the built UI from <repo>/static (see Backend/app.py)
    outDir: '../static',
    emptyOutDir: true,
  },
})
