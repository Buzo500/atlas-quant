import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, stateResponse } from '@/test/fixtures';
import { SettingsPanel } from './settings-panel';

describe('Ajustes y borradores', () => {
  it('guardar el límite no envía la parada de un estado antiguo', async () => {
    const stale = stateResponse();
    stale.settings.kill_switch = false;
    const fetchMock = mockFetch(() => ({
      ...stale.settings,
      kill_switch: true,
      max_position_weight: 0.4,
    }));
    const refresh = vi.fn(async () => {});
    render(<SettingsPanel state={stale} refresh={refresh} onError={vi.fn()} />);
    fireEvent.change(
      screen.getByRole('spinbutton', {
        name: 'Peso máximo por posición (0–1)',
      }),
      { target: { value: '0.4' } },
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Guardar límite' }));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledOnce();
    const init = fetchMock.mock.calls[0][1];
    expect(typeof init?.body).toBe('string');
    expect(JSON.parse(init?.body as string)).toEqual({
      max_position_weight: 0.4,
    });
  });

  it('cambiar la parada no envía el límite de un estado antiguo', async () => {
    const stale = stateResponse();
    const fetchMock = mockFetch(() => ({
      ...stale.settings,
      kill_switch: false,
      max_position_weight: 0.4,
    }));
    const refresh = vi.fn(async () => {});
    render(<SettingsPanel state={stale} refresh={refresh} onError={vi.fn()} />);
    const user = userEvent.setup();
    await user.click(
      screen.getByRole('switch', { name: 'Parada de ejecución' }),
    );
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledOnce();
    const init = fetchMock.mock.calls[0][1];
    expect(typeof init?.body).toBe('string');
    expect(JSON.parse(init?.body as string)).toEqual({ kill_switch: false });
  });

  it('admite proveedores cuyo catálogo todavía no está disponible', () => {
    render(
      <SettingsPanel
        state={stateResponse()}
        refresh={vi.fn(async () => {})}
        onError={vi.fn()}
      />,
    );
    expect(
      screen.getAllByText('Catálogo de modelos no disponible.'),
    ).toHaveLength(2);
    expect(
      screen.getByText('Se muestran hasta 40 eventos recientes.'),
    ).toBeTruthy();
  });

  it('el sondeo no pisa el límite editado e identifica su diferencia', () => {
    const state = stateResponse();
    const props = { refresh: vi.fn(async () => {}), onError: vi.fn() };
    const view = render(<SettingsPanel state={state} {...props} />);
    fireEvent.change(
      screen.getByRole('spinbutton', {
        name: 'Peso máximo por posición (0–1)',
      }),
      { target: { value: '0.3' } },
    );
    view.rerender(
      <SettingsPanel
        state={{
          ...state,
          settings: { ...state.settings, max_position_weight: 0.4 },
        }}
        {...props}
      />,
    );
    expect(
      (
        screen.getByRole('spinbutton', {
          name: 'Peso máximo por posición (0–1)',
        }) as HTMLInputElement
      ).value,
    ).toBe('0.3');
    expect(
      screen.getByText(/El borrador difiere del límite vigente/).textContent,
    ).toContain('40,00');
  });
});
