import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' 让 FastAPI 在 / 下托管 dist 时静态资源用相对路径正确加载。
// 开发态(npm run dev)把 /api 代理到 FastAPI(8000),前端自身跑 5173。
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist' },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
