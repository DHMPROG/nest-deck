import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import http from 'node:http';
import { defineConfig, type Plugin } from 'vite';

const API_TARGET = process.env.API_TARGET || 'http://127.0.0.1:8000';

/**
 * `vite preview` wraps responses in compression middleware, which buffers a
 * Server-Sent Events stream and never flushes it — the page loads and normal
 * requests work, but no event ever arrives.
 *
 * Middleware registered inside `configurePreviewServer` runs *before* Vite's
 * internal stack, so forwarding `/api` here short-circuits compression and
 * lets the stream through untouched. Written against `node:http` to avoid
 * pulling in a proxy dependency.
 *
 * Only relevant when casting a production build through preview. The real
 * deployment (phase 7) serves the build from nginx and points the client
 * straight at the backend via VITE_API_BASE, with no proxy in between.
 */
function streamingApiProxy(): Plugin {
  const target = new URL(API_TARGET);

  return {
    name: 'nest-deck-streaming-api-proxy',
    configurePreviewServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith('/api')) return next();

        const proxyReq = http.request(
          {
            protocol: target.protocol,
            hostname: target.hostname,
            port: target.port,
            path: req.url,
            method: req.method,
            headers: { ...req.headers, host: target.host }
          },
          (proxyRes) => {
            res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
            // Raw pipe: no buffering, so SSE frames reach the client as sent.
            proxyRes.pipe(res);
          }
        );

        proxyReq.on('error', () => {
          if (!res.headersSent) res.writeHead(502, { 'content-type': 'text/plain' });
          res.end('backend unreachable');
        });

        req.pipe(proxyReq);
      });
    }
  };
}

export default defineConfig({
  plugins: [tailwindcss(), sveltekit(), streamingApiProxy()],
  server: {
    port: 5173,
    // Dev only. `VITE_API_BASE` can stay empty locally because everything is
    // same-origin through this proxy.
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true }
    }
  },
  preview: { port: 4173 }
});
