import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type {
  RetrospectiveContext,
  RetrospectivePreview,
  RetrospectiveView,
} from '@/lib/api-types';
import { deferred } from '@/test/fixtures';
import { RetrospectiveLab } from './retrospective';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/components/atlas/curve', () => ({
  Curve: () => <div>Curva retrospectiva</div>,
}));
const call = vi.mocked(api);
const context: RetrospectiveContext = {
  symbol: 'TEST',
  instrument_id: 'ISIN_TEST',
  market: 'TEST',
  currency: 'EUR',
  fast: 2,
  slow: 3,
  config: { initial_cash_eur: '1000' },
  start_date: '2025-01-01',
  development_end: '2025-01-07',
  development_sessions: 7,
  holdout_start: '2025-01-08',
  holdout_end: '2025-01-14',
  holdout_sessions: 7,
  holdout_evaluated: false,
  evidence_verified: false,
  provider: 'Fuente ficticia',
  calendar_source: 'Calendario ficticio',
  event_review: 'Sin dividendos o splits ficticios',
  source_sha256: 'a'.repeat(64),
  frozen_hash: 'b'.repeat(64),
  warnings: ['Supuesto ficticio no acreditado'],
};
const preview: RetrospectivePreview = {
  context,
  frozen_json: '{"frozen_hash":"ficticio"}',
};
const report: RetrospectiveView = {
  context,
  report_hash: 'c'.repeat(64),
  report_json: '{"format":"informe de prueba"}',
  code_matches: true,
  development: {
    start_date: '2025-01-01',
    end_date: '2025-01-07',
    sessions: 7,
    metrics: [
      {
        name: 'SMA',
        final_nav_eur: '800',
        return_pct: '-20',
        max_drawdown_pct: '20',
        fills: 2,
        fees_eur: '2',
      },
    ],
    curve: [],
    trades: [],
    rejected: 0,
    expired: 0,
    report_hash: 'd'.repeat(64),
  },
};
function edit(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}
function fill() {
  edit('Símbolo retrospectivo', 'TEST');
  edit('Identificador del instrumento / ISIN', 'ISIN_TEST');
  edit('Reserva desde', '2025-01-08');
  edit(
    'CSV retrospectivo',
    'date,open,high,low,close,volume,dividends,splits\n',
  );
  edit(
    'Calendario esperado · una fecha ISO por línea',
    '2025-01-01\n2025-01-02\n2025-01-08',
  );
  edit('Procedencia de los precios', 'Fuente ficticia');
  edit('Fuente del calendario', 'Calendario ficticio');
  edit('Revisión de dividendos y splits', 'Sin eventos en el ejemplo ficticio');
  fireEvent.click(screen.getByLabelText(/Acepto los horarios/));
}
function submit() {
  fireEvent.submit(
    screen.getByRole('button', { name: /Congelar y revisar/ }).closest('form')!,
  );
}
async function prepared() {
  fill();
  submit();
  await screen.findByRole('region', {
    name: 'Contexto retrospectivo congelado',
  });
}
function file(text: string, size?: number) {
  const value = new File([text], 'informe.json', { type: 'application/json' });
  Object.defineProperty(value, 'text', { value: () => Promise.resolve(text) });
  if (size) Object.defineProperty(value, 'size', { value: size });
  return value;
}
beforeEach(() => {
  call.mockReset();
  call.mockImplementation(async (path) =>
    path.endsWith('/prepare') ? preview : report,
  );
  vi.restoreAllMocks();
});

it('congela con calendario declarado y supuestos aceptados sin calcular ni derivar fechas del precio', async () => {
  render(<RetrospectiveLab onError={vi.fn()} />);
  expect(
    screen
      .getByRole('button', { name: /Congelar y revisar/ })
      .hasAttribute('disabled'),
  ).toBe(true);
  await prepared();
  expect(call).toHaveBeenCalledTimes(1);
  expect(call).toHaveBeenCalledWith(
    '/lab/retrospective/prepare',
    expect.objectContaining({
      settings: expect.objectContaining({
        expected_dates: ['2025-01-01', '2025-01-02', '2025-01-08'],
        acknowledge_assumptions: true,
      }),
    }),
  );
  expect(
    screen
      .getByRole('button', { name: 'Calcular desarrollo retrospectivo' })
      .hasAttribute('disabled'),
  ).toBe(true);
  expect(screen.getByText('Sin calcular · precios excluidos')).not.toBeNull();
});

it('calcula una vez tras revisión y usa la instantánea congelada, con contexto propio en el resultado', async () => {
  const pending = deferred<RetrospectiveView>();
  call.mockImplementation(async (path) =>
    path.endsWith('/prepare') ? preview : pending.promise,
  );
  render(<RetrospectiveLab onError={vi.fn()} />);
  await prepared();
  fireEvent.click(screen.getByLabelText(/He revisado el protocolo congelado/));
  const button = screen.getByRole('button', {
    name: 'Calcular desarrollo retrospectivo',
  });
  fireEvent.click(button);
  fireEvent.click(button);
  expect(call).toHaveBeenCalledTimes(2);
  expect(call).toHaveBeenLastCalledWith('/lab/retrospective/calculate', {
    frozen_json: preview.frozen_json,
    expected_frozen_hash: context.frozen_hash,
  });
  await act(async () => pending.resolve(report));
  expect(
    await screen.findByRole('region', {
      name: 'Resultado retrospectivo de desarrollo',
    }),
  ).not.toBeNull();
  expect(
    screen.getAllByRole('region', { name: 'Contexto retrospectivo congelado' }),
  ).toHaveLength(1);
});

it('editar costes invalida revisión y congelación antes de calcular', async () => {
  render(<RetrospectiveLab onError={vi.fn()} />);
  await prepared();
  fireEvent.click(screen.getByLabelText(/He revisado el protocolo congelado/));
  edit('Comisión fija EUR', '2');
  expect(
    screen.queryByRole('button', { name: 'Calcular desarrollo retrospectivo' }),
  ).toBeNull();
  expect(call).toHaveBeenCalledTimes(1);
});

it('ignora una previsualización tardía cuyo borrador ha cambiado', async () => {
  const pending = deferred<RetrospectivePreview>();
  call.mockReturnValue(pending.promise);
  render(<RetrospectiveLab onError={vi.fn()} />);
  fill();
  submit();
  edit('Símbolo retrospectivo', 'OTRO');
  await act(async () => pending.resolve(preview));
  expect(
    screen.queryByRole('region', { name: 'Contexto retrospectivo congelado' }),
  ).toBeNull();
});

it('reabre mediante recálculo y distingue cambios de código sin afirmar igualdad de entorno', async () => {
  call.mockResolvedValue({ ...report, code_matches: false });
  render(<RetrospectiveLab onError={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Informe retrospectivo guardado'), {
    target: { files: [file(report.report_json)] },
  });
  await screen.findByRole('region', {
    name: 'Resultado retrospectivo de desarrollo',
  });
  expect(call).toHaveBeenCalledWith('/lab/retrospective/reopen', {
    report_json: report.report_json,
  });
  expect(screen.getByText(/el código ha cambiado/)).not.toBeNull();
  expect(
    screen.getByText('Informe reabierto y cálculo reproducido.'),
  ).not.toBeNull();
});

it('rechaza archivos grandes antes de enviarlos al motor', async () => {
  const error = vi.fn();
  render(<RetrospectiveLab onError={error} />);
  fireEvent.change(screen.getByLabelText('Informe retrospectivo guardado'), {
    target: { files: [file('x', 3_000_001)] },
  });
  await waitFor(() =>
    expect(error).toHaveBeenCalledWith(
      'El archivo supera el tamaño permitido.',
    ),
  );
  expect(call).not.toHaveBeenCalled();
});

it('lee el CSV local y lo incorpora al borrador sin ejecutar el cálculo', async () => {
  render(<RetrospectiveLab onError={vi.fn()} />);
  const csv =
    'date,open,high,low,close,volume,dividends,splits\n2025-01-01,10,10,10,10,100,0,0';
  fireEvent.change(screen.getByLabelText(/Archivo de precios retrospectivos/), {
    target: { files: [file(csv)] },
  });
  await waitFor(() =>
    expect(
      (screen.getByLabelText('CSV retrospectivo') as HTMLTextAreaElement).value,
    ).toBe(csv),
  );
  expect(call).not.toHaveBeenCalled();
});

it.each(['Exportar paquete JSON/CSV', 'Exportar fuente LaTeX'])(
  'un fallo de %s informa del error y conserva el resultado',
  async (name) => {
    const error = vi.fn();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('error', { status: 422 }),
    );
    render(<RetrospectiveLab onError={error} />);
    fireEvent.change(screen.getByLabelText('Informe retrospectivo guardado'), {
      target: { files: [file(report.report_json)] },
    });
    fireEvent.click(await screen.findByRole('button', { name }));
    await waitFor(() =>
      expect(error).toHaveBeenCalledWith(
        expect.stringContaining('No se pudo verificar'),
      ),
    );
    expect(
      screen.getByRole('region', {
        name: 'Resultado retrospectivo de desarrollo',
      }),
    ).not.toBeNull();
  },
);

it('exporta la fuente LaTeX verificada una sola vez y mantiene la descarga JSON independiente', async () => {
  const pending = deferred<Response>();
  const fetcher = vi
    .spyOn(globalThis, 'fetch')
    .mockReturnValue(pending.promise);
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:latex-test');
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});
  render(<RetrospectiveLab onError={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Informe retrospectivo guardado'), {
    target: { files: [file(report.report_json)] },
  });
  const button = await screen.findByRole('button', {
    name: 'Exportar fuente LaTeX',
  });
  fireEvent.click(button);
  fireEvent.click(button);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher).toHaveBeenCalledWith(
    '/api/lab/retrospective/latex',
    expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ report_json: report.report_json }),
      headers: {
        'Content-Type': 'application/json',
        'X-Atlas-Client': 'local-v1',
      },
    }),
  );
  await act(async () =>
    pending.resolve(
      new Response('zip', { headers: { 'Content-Type': 'application/zip' } }),
    ),
  );
  expect(click).toHaveBeenCalledTimes(1);
  expect((click.mock.instances[0] as HTMLAnchorElement).download).toBe(
    'atlas-retrospectivo-latex-cccccccccccc.zip',
  );
  expect(
    screen
      .getByRole('button', { name: 'Descargar informe JSON' })
      .hasAttribute('disabled'),
  ).toBe(false);
});
