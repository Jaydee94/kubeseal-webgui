import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

// https://vitejs.dev/config/
export default defineConfig({
  // Relative asset URLs, so that one build works at the root of a host and
  // under any path prefix (e.g. https://example.com/kubeseal-webgui/).
  base: './',
  server: {
    port: 8080,
    proxy: {
      "^/(secrets$|namespaces$|clusters$|config$|sealed-secrets/|docs|openapi\\.json)": {
        target: "http://localhost:5000",
        changeOrigin: false
      }
    }
  },
  plugins: [
    vue(),
    vuetify({
      autoImport: true
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  test: {
    // Unit tests; tests/test_ui.py holds the Playwright E2E tests.
    include: ['tests/unit/**/*.test.js'],
    environment: 'node'
  }
})
