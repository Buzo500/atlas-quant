import { availableParallelism } from 'node:os';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Component tests run without the production Sites/Cloudflare/Vinext plugins.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('.', import.meta.url)),
      'next/link': 'vinext/shims/link',
    },
  },
  test: {
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'http://localhost/' } },
    setupFiles: ['./test/setup.ts'],
    include: [
      '{app,lib,components/atlas,features,shared}/**/*.{test,spec}.{ts,tsx}',
    ],
    clearMocks: true,
    restoreMocks: true,
    unstubGlobals: true,
    unstubEnvs: true,
    // jsdom is CPU-heavy: leave capacity for Vite and React on small runners.
    // Preserve per-file isolation and the default timeout for shorter tests.
    maxWorkers: Math.max(
      1,
      Math.min(4, Math.floor(availableParallelism() / 2)),
    ),
  },
});
