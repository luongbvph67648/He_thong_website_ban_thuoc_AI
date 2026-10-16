import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  // Ant Design chiếm phần lớn bundle; sẽ tách theo khu (lazy route) khi các khu có trang thật.
  build: { chunkSizeWarningLimit: 1200 },
  server: {
    port: 5173,
    strictPort: true,
    // Chuyển /api sang backend FastAPI khi dev, nên trình duyệt không gặp lỗi CORS.
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true, // bật dọn DOM tự động của Testing Library sau mỗi test
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
