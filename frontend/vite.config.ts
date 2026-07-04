import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      onwarn(warning, warn) {
        const warningId = typeof warning.id === 'string' ? warning.id.replace(/\\/g, '/') : ''
        if (warning.code === 'INVALID_ANNOTATION' && warningId.includes('/node_modules/@vueuse/core/')) {
          return
        }
        warn(warning)
      },
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, '/')
          if (!normalizedId.includes('/node_modules/')) return undefined
          if (
            normalizedId.includes('/node_modules/element-plus/') ||
            normalizedId.includes('/node_modules/@element-plus/')
          ) {
            return 'vendor-element-plus'
          }
          if (
            normalizedId.includes('/node_modules/vue/') ||
            normalizedId.includes('/node_modules/@vue/') ||
            normalizedId.includes('/node_modules/vue-router/') ||
            normalizedId.includes('/node_modules/pinia/')
          ) {
            return 'vendor-vue'
          }
          if (normalizedId.includes('/node_modules/axios/')) {
            return 'vendor-http'
          }
          return 'vendor'
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
