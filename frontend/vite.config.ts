import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// En desarrollo el front corre en :5173 y la API en :8000, así que Vite
// redirige /api al backend y evita problemas de CORS.
// En el despliegue con Docker, nginx hace de proxy dentro del contenedor del
// frontend y el navegador ve un solo origen, de modo que esto no aplica.
//
// /media/cargas/ también va al backend: son las imágenes que se suben desde
// el panel (EP-16), que nacen en ejecución y no están en public/. El resto
// de /media/ (las fotos de la siembra) sí sale de public/. `preview` repite
// el proxy para que `vite preview` se comporte igual que el desarrollo.
const destino = process.env.API_URL || 'http://127.0.0.1:8000'
const proxy = {
  '/api': { target: destino, changeOrigin: true },
  '/media/cargas': { target: destino, changeOrigin: true },
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: { port: 5173, proxy },
  preview: { proxy },
  build: { outDir: 'dist', sourcemap: false },
})
