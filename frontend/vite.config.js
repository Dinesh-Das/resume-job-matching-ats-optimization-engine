import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    optimizeDeps: {
        include: [
            'recharts',
            'recharts/es6/chart/BarChart',
            'recharts/es6/chart/PieChart',
            'd3-scale',
            'd3-shape',
            'd3-interpolate',
        ],
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            }
        }
    }
})
