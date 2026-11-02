import { fileURLToPath } from "node:url"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"
import { backendUnreachableHandler } from "./src/lib/devProxy.js"

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
          // Backend not running: answer 502 with a JSON message instead of Vite's empty 500.
          configure: (proxy) => {
            proxy.on('error', backendUnreachableHandler(apiUrl))
          }
        },
      },
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
  }
})
