import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// En desarrollo el front corre en :5173 y la API en :8000, así que Vite
// redirige /api al backend y evita problemas de CORS.
// En el despliegue con Docker, nginx hace de proxy dentro del contenedor del
// frontend y el navegador ve un solo origen, de modo que esto no aplica.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.API_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
