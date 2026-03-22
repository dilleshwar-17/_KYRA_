import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    base: './',
    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
    server: {
        port: 5173,
        proxy: {
            '/health': 'http://127.0.0.1:8091',
            '/chat': 'http://127.0.0.1:8091',
            '/reset': 'http://127.0.0.1:8091',
            '/ws': {
                target: 'ws://127.0.0.1:8091',
                ws: true,
            },
        },
    },
})
