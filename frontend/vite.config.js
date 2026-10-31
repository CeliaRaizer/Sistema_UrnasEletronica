import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // aceita acesso por qualquer endereço (necessário para o túnel https do celular)
    allowedHosts: true,
    // o navegador chama /api no mesmo endereço do site e o Vite repassa ao Django
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
