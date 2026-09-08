import {
  act,
  fireEvent,
  render,
  waitFor,
  within,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import Home from './page';
import {
  dataset,
  deferred,
  experimentResponse,
  mockFetch,
  portfolioResponse,
  stateResponse,
} from '@/test/fixtures';

beforeEach(() => {
  window.history.replaceState(null, '', '/');
});
function responses() {
  return mockFetch((path) => {
    if (path === '/api/state')
      return stateResponse({
        datasets: [dataset(), dataset('b')],
        experiments: [
          experimentResponse(),
          experimentResponse({ id: 'experiment-b', symbol: 'B' }),
        ],
      });
    if (path.endsWith('/portfolio')) return portfolioResponse();
    if (path === '/api/experiments/experiment-b')
      return experimentResponse({ id: 'experiment-b', symbol: 'B' });
    if (path === '/api/experiments/experiment-a') return experimentResponse();
    throw new Error('Solicitud inesperada: ' + path);
  });
}
describe('Navegación y borradores', () => {
  it('mantiene CSV, hipótesis y costes al cambiar de pestaña', async () => {
    responses();
    // A timed-out async test must never query the next test's document.
    const screen = within(render(<Home />).container);
    const user = userEvent.setup();
    await screen.findByText('Motor conectado');
    const tabs = within(
      screen.getByRole('tablist', { name: 'Secciones de ATLAS' }),
    );
    await user.click(tabs.getByRole('tab', { name: 'Datos' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Contenido CSV' }), {
      target: { value: 'borrador-csv' },
    });
    await user.click(tabs.getByRole('tab', { name: 'Laboratorio' }));
    fireEvent.change(
      screen.getByRole('spinbutton', { name: 'Comisión (pb)' }),
      { target: { value: '9' } },
    );
    await user.click(tabs.getByRole('tab', { name: 'Agente IA' }));
    await user.click(screen.getByRole('button', { name: 'Nuevo experimento' }));
    fireEvent.change(
      screen.getByRole('textbox', { name: 'Hipótesis de investigación' }),
      { target: { value: 'hipótesis sin enviar' } },
    );
    await user.click(tabs.getByRole('tab', { name: 'Datos' }));
    expect(
      (
        screen.getByRole('textbox', {
          name: 'Contenido CSV',
        }) as HTMLTextAreaElement
      ).value,
    ).toBe('borrador-csv');
    await user.click(tabs.getByRole('tab', { name: 'Laboratorio' }));
    expect(
      (
        screen.getByRole('spinbutton', {
          name: 'Comisión (pb)',
        }) as HTMLInputElement
      ).value,
    ).toBe('9');
    await user.click(tabs.getByRole('tab', { name: 'Agente IA' }));
    expect(
      (
        screen.getByRole('textbox', {
          name: 'Hipótesis de investigación',
        }) as HTMLTextAreaElement
      ).value,
    ).toBe('hipótesis sin enviar');
    expect(window.location.search).toBe('?tab=agent');
    expect(localStorage.length + sessionStorage.length).toBe(0);
    // This covers seven user clicks and three full mounted panels in jsdom.
  }, 15_000);

  it('recupera selección desde el enlace y después de recargar sin autorizar simulación', async ({
    signal,
  }) => {
    window.history.replaceState(
      null,
      '',
      '/?tab=agent&dataset=b&experiment=experiment-b',
    );
    const requests = responses();
    let view = render(<Home />);
    let screen = within(view.container);
    await screen.findByRole(
      'heading',
      { name: 'B · Observando' },
      { timeout: 3000 },
    );
    expect(
      screen.getByRole('combobox', { name: 'Conjunto de datos' }).textContent,
    ).toContain('Datos b');
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Nuevo experimento' }));
    const toggle = screen.getByRole('switch', {
      name: /Activar simulación automáticamente/,
    });
    await user.click(toggle);
    expect(toggle.getAttribute('aria-checked')).toBe('true');
    signal.throwIfAborted();
    view.unmount();
    view = render(<Home />);
    screen = within(view.container);
    await screen.findByRole(
      'heading',
      { name: 'B · Observando' },
      { timeout: 3000 },
    );
    await user.click(screen.getByRole('button', { name: 'Nuevo experimento' }));
    expect(
      screen
        .getByRole('switch', { name: /Activar simulación automáticamente/ })
        .getAttribute('aria-checked'),
    ).toBe('false');
    expect(
      requests.mock.calls.every(([, init]) => init?.method !== 'POST'),
    ).toBe(true);
  });

  it('respeta navegación atrás sin perder el borrador de datos', async () => {
    responses();
    const screen = within(render(<Home />).container);
    await screen.findByText('Motor conectado');
    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: 'Datos' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Contenido CSV' }), {
      target: { value: 'draft' },
    });
    await user.click(screen.getByRole('tab', { name: 'Laboratorio' }));
    await act(async () => {
      window.history.replaceState(null, '', '/?tab=data');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    expect(
      screen.getByRole('tab', { name: 'Datos' }).getAttribute('aria-selected'),
    ).toBe('true');
    expect(
      (
        screen.getByRole('textbox', {
          name: 'Contenido CSV',
        }) as HTMLTextAreaElement
      ).value,
    ).toBe('draft');
  });

  it('distingue carga y error de una cartera vacía y permite reintentar', async () => {
    const pending = deferred<unknown>();
    let attempts = 0;
    mockFetch((path) => {
      if (path === '/api/state') return stateResponse();
      if (path.endsWith('/portfolio'))
        return ++attempts === 1 ? pending.promise : portfolioResponse();
      throw new Error('unexpected');
    });
    const screen = within(render(<Home />).container);
    await screen.findByRole('heading', { name: 'Cargando cartera…' });
    expect(
      screen.queryByRole('heading', { name: 'Importa tus movimientos' }),
    ).toBeNull();
    await act(async () => pending.reject(new Error('offline')));
    await screen.findByRole('heading', {
      name: 'No se pudo consultar la cartera',
    });
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: 'Reintentar cartera' }));
    await screen.findByRole('heading', { name: 'Evolución del patrimonio' });
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: 'Reintentar cartera' }),
      ).toBeNull(),
    );
  });
});
