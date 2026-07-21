import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

// Talk to the FastAPI backend same-origin so `VITE_API_BASE` can stay empty
// locally (in Docker it points at the server IP). `preview` needs its own
// copy — Vite does not inherit `server.proxy` there, and preview is what we
// cast to the Nest Hub when testing a production build.
const proxy = {
  '/api': {
    target: process.env.API_TARGET || 'http://127.0.0.1:8000',
    changeOrigin: true
  }
};

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy }
});
