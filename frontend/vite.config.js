import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // 核心框架
          vendor: ['react', 'react-dom'],
          // UI 组件库
          antd: ['antd', '@ant-design/icons'],
          // 图表库
          echarts: ['echarts'],
          // 工具库
          utils: ['axios', 'dayjs'],
        },
      },
    },
    chunkSizeWarningLimit: 800,
  },
  server: {
    port: 3000,
    open: false,  // 禁用Vite自动打开浏览器
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/get-minute-tick': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})