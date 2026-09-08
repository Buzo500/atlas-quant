import { renderToStaticMarkup } from 'react-dom/server';
import { describe, test } from 'vitest';
import type { PortfolioPoint } from '@/lib/api-types';
import { Curve } from './curve';

// Run from frontend:
// node node_modules/vitest/vitest.mjs bench --config vitest.config.ts --run components/atlas/curve.bench.tsx --reporter=verbose
// Measures actual React SSR preparation/serialization, not browser layout or paint.
// Data generation is deliberately outside the measured callback.
describe('Curve: React SSR con 1k, 10k y 100k observaciones', () => {
  for (const count of [1_000, 10_000, 100_000]) {
    const data: PortfolioPoint[] = Array.from(
      { length: count },
      (_, index) => ({
        date: new Date(Date.UTC(2000, 0, 1 + index)).toISOString().slice(0, 10),
        nav:
          10000 +
          index * 0.002 +
          Math.sin(index / 7) * 30 +
          (index % 947 === 0 ? 120 : 0) -
          (index % 1297 === 0 ? 160 : 0),
        twr_index: 1,
      }),
    );
    test(`${count.toLocaleString('es-ES')} observaciones`, async ({
      bench,
    }) => {
      const result = await bench('Preparación y serialización de Curve', () => {
        renderToStaticMarkup(<Curve data={data} />);
      }).run({ time: 300, iterations: 10, warmupTime: 100 });
      const markup = renderToStaticMarkup(<Curve data={data} />);
      console.info(
        JSON.stringify({
          panel: 'curve',
          count,
          minimum_ms: result.latency.min,
          mean_ms: result.latency.mean,
          p75_ms: result.latency.p75,
          samples: result.latency.samplesCount,
          html_bytes: new TextEncoder().encode(markup).byteLength,
        }),
      );
    });
  }
});
