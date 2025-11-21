import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
    root: resolve(__dirname, 'front'),
    plugins: [react()],
    build: {
        outDir: resolve(__dirname, 'front', 'dist'),
        emptyOutDir: true,
        rollupOptions: {
            input: resolve(__dirname, 'front', 'index.html'),
        },
    },
    server: {
        port: 5173,
        strictPort: true,
    },
});
