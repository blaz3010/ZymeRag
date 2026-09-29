import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    // FastAPI serves the built UI from <repo>/static (see Backend/app.py)
    outDir: '../static',
    emptyOutDir: true,
  },
})
