import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  base: './', // <-- FONDAMENTALE PER ELECTRON
  plugins: [
    vue(),
    vueDevTools(),
  ],
  server: {
    host: true,
    port: 5173,
    strictPort: true, 
    watch: {
      usePolling: true
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})