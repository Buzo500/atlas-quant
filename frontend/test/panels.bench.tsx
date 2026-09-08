import { renderToStaticMarkup } from 'react-dom/server';
import { describe, test } from 'vitest';
import { AgentPanel } from '@/features/experiments/agent-panel';
import { SettingsPanel } from '@/features/settings/settings-panel';
import { DataTable } from '@/shared/ui';
import { dataset, experimentResponse, stateResponse } from './fixtures';

// node node_modules/vitest/vitest.mjs bench --config vitest.config.ts --run test/panels.bench.tsx --reporter=verbose
// Actual React SSR. Excludes network, data generation, browser layout and paint.
// This is a repeatable cost probe, not an assertion of browser responsiveness.
const refresh = async () => {};
const onError = () => {};
const audit = Array.from({ length: 40 }, (_, index) => ({
  seq: index + 1,
  at: '2026-09-08T12:00:00+00:00',
  event: 'experiment.created',
  entity: `experiment-${index}`,
  details: {},
}));

describe('Paneles de ATLAS: preparación y serialización SSR', () => {
  for (const count of [10, 100, 1000]) {
    const state = stateResponse({
      experiments: Array.from({ length: count }, (_, index) =>
        experimentResponse({
          id: `experiment-${index}`,
          symbol: index % 2 === 0 ? 'A' : 'B',
          status: index % 3 === 0 ? 'completed' : 'observing',
          prompt:
            'Comparación sintética de reglas de tendencia, con costes y separación cronológica de entrenamiento, validación y prueba.',
        }),
      ),
      audit,
    });
    test(`Agente con ${count} experimentos`, async ({ bench }) => {
      const draw = () =>
        renderToStaticMarkup(
          <AgentPanel
            dataset={dataset()}
            state={state}
            active={false}
            refresh={refresh}
            onError={onError}
          />,
        );
      const result = await bench(
        'Agente: listado y estado inicial del expediente',
        draw,
      ).run({
        time: 300,
        iterations: 10,
        warmupTime: 100,
      });
      const markup = draw();
      console.info(
        JSON.stringify({
          panel: 'agent',
          count,
          minimum_ms: result.latency.min,
          mean_ms: result.latency.mean,
          p75_ms: result.latency.p75,
          samples: result.latency.samplesCount,
          html_bytes: new TextEncoder().encode(markup).byteLength,
          table_rows_including_headers: (markup.match(/<tr[\s>]/g) ?? [])
            .length,
        }),
      );
    }, 15_000);

    // Row values are prepared before timing: this isolates the maintained table.
    const rows = Array.from({ length: count }, (_, index) => [
      `TEST_${String(index + 1).padStart(4, '0')}`,
      '10',
      '100,00 €',
      '1000,00 €',
      `${(100 / count).toFixed(2)} %`,
      '0,00 €',
    ]);
    test(`Tabla de posiciones con ${count} filas`, async ({ bench }) => {
      const draw = () =>
        renderToStaticMarkup(
          <DataTable
            heads={[
              'Activo',
              'Cantidad',
              'Último precio',
              'Valor',
              'Peso',
              'P&L no realizado',
            ]}
            rows={rows}
            numericColumns={[1, 2, 3, 4, 5]}
          />,
        );
      const result = await bench(
        'Tabla: filas preparadas antes de medir',
        draw,
      ).run({
        time: 300,
        iterations: 10,
        warmupTime: 100,
      });
      const markup = draw();
      console.info(
        JSON.stringify({
          panel: 'positions_table',
          count,
          minimum_ms: result.latency.min,
          mean_ms: result.latency.mean,
          p75_ms: result.latency.p75,
          samples: result.latency.samplesCount,
          html_bytes: new TextEncoder().encode(markup).byteLength,
          table_rows_including_headers: (markup.match(/<tr[\s>]/g) ?? [])
            .length,
        }),
      );
    }, 15_000);
  }

  test('Ajustes con 40 entradas de auditoría', async ({ bench }) => {
    const state = stateResponse({ audit });
    const draw = () =>
      renderToStaticMarkup(
        <SettingsPanel state={state} refresh={refresh} onError={onError} />,
      );
    const result = await bench(
      'Ajustes: controles, proveedores y auditoría',
      draw,
    ).run({
      time: 300,
      iterations: 10,
      warmupTime: 100,
    });
    const markup = draw();
    console.info(
      JSON.stringify({
        panel: 'settings',
        audit_count: 40,
        minimum_ms: result.latency.min,
        mean_ms: result.latency.mean,
        p75_ms: result.latency.p75,
        samples: result.latency.samplesCount,
        html_bytes: new TextEncoder().encode(markup).byteLength,
        table_rows_including_headers: (markup.match(/<tr[\s>]/g) ?? []).length,
      }),
    );
  });
});
