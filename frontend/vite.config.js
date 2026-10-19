import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"

export default defineConfig(({ mode }) => {
  // Load environment variables based on mode (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), '')
  
  // Use environment variable for API URL or fallback to localhost for development
  const apiUrl = env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'
  
  console.log(`[Vite] Using API URL for proxy: ${apiUrl}`)
  
  return {
    server: {
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
          // Preserve the trailing slashes
          rewrite: (path) => path,
          configure: (proxy, _options) => {
            proxy.on('error', (err) => {
              console.log('Proxy error:', err)
            })
          }
        },
      },
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  }
})
