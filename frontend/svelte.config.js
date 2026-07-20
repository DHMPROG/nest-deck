import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/**
 * Static build served by nginx. The Deck is a pure SPA: the Nest Hub stores
 * nothing, all state comes from the backend at runtime, so we ship an
 * index.html fallback rather than prerendering per-route.
 */
/** @type {import('@sveltejs/kit').Config} */
export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
      precompress: false,
      strict: false
    })
  }
};
