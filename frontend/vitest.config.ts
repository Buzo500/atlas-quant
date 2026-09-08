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
    maxWorkers: 4,
  },
});
