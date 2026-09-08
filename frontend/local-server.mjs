// Compiled Node runtime. Never load frontend .env files, Vite or Miniflare.
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { startProdServer } from 'vinext/server/prod-server';

process.env.NODE_ENV = 'production';
const frontend = path.dirname(fileURLToPath(import.meta.url));
const { server } = await startProdServer({
  host: '127.0.0.1', port: 3000, outDir: path.join(frontend, 'dist'),
});
const stopFile = process.env.ATLAS_STOP_FILE;
if (stopFile) {
  const timer = setInterval(() => {
    if (existsSync(stopFile)) {
      clearInterval(timer);
      server.close(() => process.exit(0));
      setTimeout(() => { server.closeAllConnections(); process.exit(0); }, 15000).unref();
    }
  }, 200);
}
