import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const backendProxy = {
  target: 'http://127.0.0.1:8000',
  xfwd: true,
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': backendProxy,
      '/artifacts': backendProxy,
      '/admin': backendProxy,
      '/django-static': backendProxy,
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': backendProxy,
      '/artifacts': backendProxy,
      '/admin': backendProxy,
      '/django-static': backendProxy,
    },
  },
});
