import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
  const apiBaseUrl = env.VITE_API_BASE_URL || ''
  const useProxy = !apiBaseUrl

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: useProxy
        ? {
            '/api': {
              target: apiProxyTarget,
              changeOrigin: true,
            },
            '/health': {
              target: apiProxyTarget,
              changeOrigin: true,
            },
          }
        : undefined,
    },
  }
})
