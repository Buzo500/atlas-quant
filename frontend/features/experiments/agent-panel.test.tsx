import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { ExperimentResponse } from '@/lib/api-types';
import {
  dataset,
  deferred,
  experimentResponse,
  mockFetch,
  stateResponse,
} from '@/test/fixtures';
import { AgentPanel } from './agent-panel';

const props = (experiments: ExperimentResponse[] = []) => ({
  dataset: dataset(),
  state: stateResponse({ experiments }),
  refresh: vi.fn(async () => {}),
  onError: vi.fn(),
});

function jsonBody(init?: RequestInit): Record<string, unknown> {
  if (typeof init?.body !== 'string')
    throw new Error('Se esperaba un cuerpo JSON textual');
  return JSON.parse(init.body) as Record<string, unknown>;
}

describe('Controles del expediente de experimento', () => {
  it.each([
    {
      action: 'pause',
      button: 'Pausar',
      initial: 'observing',
      final: 'paused',
      heading: 'A · Pausado',
    },
    {
      action: 'resume',
      button: 'Reanudar',
      initial: 'paused',
      final: 'observing',
      heading: 'A · Observando',
    },
    {
      action: 'cancel',
      button: 'Cancelar experimento',
      initial: 'observing',
      final: 'cancelled',
      heading: 'A · Cancelado',
    },
  ] as const)(
    'envía $action y muestra el estado leído del motor',
    async ({ action, button, initial, final, heading }) => {
      let detail = experimentResponse({ status: initial });
      const initialDetail = detail;
      const fetchMock = mockFetch((path, init) => {
        if (path === '/api/experiments/experiment-a/control') {
          expect(jsonBody(init)).toEqual({ action });
          detail = experimentResponse({ status: final });
          // The POST result is deliberately stale: the UI must read canonical state.
          return initialDetail;
        }
        if (path === '/api/experiments/experiment-a') return detail;
        throw new Error(`Petición inesperada: ${path}`);
      });
      const input = props([detail]);
      render(<AgentPanel {...input} />);
      const user = userEvent.setup();
      await user.click(await screen.findByRole('button', { name: button }));
      await screen.findByRole('heading', { name: heading });
      expect(input.refresh).toHaveBeenCalledOnce();
      expect(
        fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST'),
      ).toHaveLength(1);
      expect(input.onError).not.toHaveBeenCalledWith(
        expect.stringMatching(/Petición inesperada/),
      );
    },
  );

  it.each([
    { execution_active: true, reserved_usd: 0 },
    { execution_active: false, reserved_usd: 0.0001 },
  ])(
    'bloquea reanudar con ejecución/reserva pendiente: %j',
    async (pending) => {
      const detail = experimentResponse({ status: 'paused', ...pending });
      const fetchMock = mockFetch(() => detail);
      render(<AgentPanel {...props([detail])} />);
      const resume = await screen.findByRole('button', { name: 'Reanudar' });
      expect((resume as HTMLButtonElement).disabled).toBe(true);
      fireEvent.click(resume);
      expect(
        fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST'),
      ).toHaveLength(0);
    },
  );

  it('el control antiguo no sustituye el expediente seleccionado mientras termina', async () => {
    const first = experimentResponse();
    const second = experimentResponse({
      id: 'experiment-b',
      symbol: 'B',
      status: 'paused',
    });
    const control = deferred<ExperimentResponse>();
    const fetchMock = mockFetch((path, init) => {
      if (
        path === '/api/experiments/experiment-a/control' &&
        init?.method === 'POST'
      )
        return control.promise;
      if (path === '/api/experiments/experiment-a') return first;
      if (path === '/api/experiments/experiment-b') return second;
      throw new Error(`Petición inesperada: ${path}`);
    });
    render(<AgentPanel {...props([first, second])} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'Pausar' }));
    await user.click(
      screen.getByRole('button', { name: 'Ver experimento B experime' }),
    );
    expect(
      screen.queryByRole('heading', { name: 'A · Observando' }),
    ).toBeNull();
    await act(async () =>
      control.resolve(experimentResponse({ status: 'paused' })),
    );
    await screen.findByRole('heading', { name: 'B · Pausado' });
    expect(screen.queryByRole('heading', { name: 'A · Pausado' })).toBeNull();
    expect(
      screen.queryByRole('heading', { name: 'A · Observando' }),
    ).toBeNull();
    const writes = fetchMock.mock.calls.filter(
      ([, init]) => init?.method === 'POST',
    );
    expect(writes).toHaveLength(1);
    expect(writes[0][0]).toBe('/api/experiments/experiment-a/control');
  });
});

describe('Creación acotada sin llamadas reales', () => {
  it.each(['submit', 'other-field', 'hidden-panel'] as const)(
    'gestiona el foco al completar una creación asíncrona: %s',
    async (focus) => {
      const creation = deferred<ExperimentResponse>();
      mockFetch((path, init) => {
        if (path === '/api/experiments' && init?.method === 'POST') {
          expect(jsonBody(init)).toMatchObject({
            provider: 'none',
            budget_usd: 0,
            auto_paper: false,
          });
          return creation.promise;
        }
        if (path === '/api/experiments/experiment-a')
          return experimentResponse();
        throw new Error(`Petición inesperada: ${path}`);
      });
      const input = props();
      const view = (active: boolean) => (
        <>
          <div hidden={!active}>
            <AgentPanel {...input} active={active} />
          </div>
          <input aria-label="Otro campo" />
        </>
      );
      const { rerender } = render(view(true));
      const user = userEvent.setup();
      screen.getByRole('button', { name: 'Iniciar experimento' }).focus();
      await user.keyboard('{Enter}');
      const other = screen.getByRole('textbox', { name: 'Otro campo' });
      if (focus !== 'submit') other.focus();
      if (focus === 'hidden-panel') rerender(view(false));
      await act(async () => creation.resolve(experimentResponse()));
      await waitFor(() => expect(input.refresh).toHaveBeenCalledOnce());
      expect(
        screen.queryByRole('button', { name: 'Iniciar experimento' }),
      ).toBeNull();
      expect(document.activeElement).toBe(
        focus === 'submit'
          ? screen.getByRole('button', { name: 'Nuevo experimento' })
          : other,
      );
    },
  );

  it('bloquea un proveedor sin clave y también un proveedor configurado con presupuesto cero', async () => {
    const fetchMock = mockFetch(() => {
      throw new Error('No debe solicitar el motor');
    });
    const input = props();
    const view = render(<AgentPanel {...input} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('combobox', { name: 'Proveedor de IA' }));
    await user.click(
      screen.getByRole('option', { name: 'OpenAI · GPT-5.4 mini' }),
    );
    expect(screen.getByText(/Falta la clave local de openai/)).not.toBeNull();
    const submit = screen.getByRole('button', {
      name: 'Iniciar experimento',
    }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    view.rerender(
      <AgentPanel
        {...input}
        state={stateResponse({
          providers: [{ provider: 'openai', configured: true, models: [] }],
        })}
      />,
    );
    expect(screen.queryByText(/Falta la clave local/)).toBeNull();
    expect(submit.disabled).toBe(true);
    fireEvent.click(submit);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('envía una sola creación sin IA, presupuesto cero y simulación automática desactivada', async () => {
    const creation = deferred<ExperimentResponse>();
    let posted: Record<string, unknown> | undefined;
    const fetchMock = mockFetch((path, init) => {
      if (path === '/api/experiments' && init?.method === 'POST') {
        posted = jsonBody(init);
        return creation.promise;
      }
      if (path === '/api/experiments/experiment-a')
        return experimentResponse({ hours: 720 });
      throw new Error(`Petición inesperada: ${path}`);
    });
    const input = props();
    render(<AgentPanel {...input} />);
    const duration = screen.getByRole('spinbutton', {
      name: /Duración \(horas\)/,
    });
    fireEvent.change(duration, { target: { value: '720' } });
    const submit = screen.getByRole('button', { name: 'Iniciar experimento' });
    act(() => {
      fireEvent.click(submit);
      fireEvent.click(submit);
    });
    expect(posted).toMatchObject({
      dataset_id: 'a',
      symbol: 'A',
      provider: 'none',
      budget_usd: 0,
      hours: 720,
      auto_paper: false,
      costs: {
        initial_cash: 10000,
        commission_bps: 5,
        slippage_bps: 5,
        minimum_fee: 1.25,
        max_position_weight: 0.25,
      },
      policy: {
        min_oos_observations: 126,
        min_trades: 10,
        min_sharpe: 0.5,
        max_drawdown: 0.15,
        min_excess_return: 0,
        min_forward_sessions: 20,
      },
    });
    fireEvent.change(duration, { target: { value: '24' } });
    expect(posted?.hours).toBe(720);
    expect(
      fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST'),
    ).toHaveLength(1);
    await act(async () => creation.resolve(experimentResponse({ hours: 720 })));
    await waitFor(() => expect(input.refresh).toHaveBeenCalledOnce());
    expect(
      screen.queryByRole('button', { name: 'Iniciar experimento' }),
    ).toBeNull();
  });
});
