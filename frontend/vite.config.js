import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // Listen on all network addresses (0.0.0.0 / 127.0.0.1) for Windows & Mac
    proxy: {
      '/user': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/upload': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/query': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/sources': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/delete': {
        target: 'http://127.0.0.1:8000',
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
