import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { QueryStatus } from './query-status';
import { dateTime } from './format';
import { deferred } from '@/test/fixtures';

const at = Date.parse('2026-09-08T10:00:00Z');
const ready = () => ({
  data: { id: 'a' },
  error: '',
  loading: false,
  updatedAt: at,
  refresh: vi.fn(async () => {}),
});

describe('Estado accesible de consultas', () => {
  it('anuncia la carga inicial y mantiene el sondeo y las horas fuera de las regiones vivas', () => {
    const query = ready();
    const { rerender } = render(
      <QueryStatus
        label="Cartera"
        query={{ ...query, data: null, loading: true, updatedAt: null }}
      />,
    );
    expect(screen.getByRole('status').textContent).toBe('Cargando cartera…');
    rerender(<QueryStatus label="Cartera" query={query} />);
    const status = screen.getByRole('status');
    expect(status.textContent).toBe('Cartera: datos cargados.');
    for (let index = 1; index <= 3; index++) {
      rerender(
        <QueryStatus label="Cartera" query={{ ...query, loading: true }} />,
      );
      expect(status.textContent).toBe('Cartera: datos cargados.');
      expect(
        screen
          .getByText(/Actualizando cartera/)
          .closest('[role="status"], [role="alert"]'),
      ).toBeNull();
      const updatedAt = at + index * 5000;
      rerender(<QueryStatus label="Cartera" query={{ ...query, updatedAt }} />);
      expect(status.textContent).toBe('Cartera: datos cargados.');
      const visible = screen.getByText(
        `Última consulta: ${dateTime(new Date(updatedAt).toISOString())}.`,
      );
      expect(visible.closest('[role="status"], [role="alert"]')).toBeNull();
    }
  });

  it('anuncia errores y recuperación sin incluir la hora ni repetir actualizaciones correctas', () => {
    const query = ready();
    const { rerender } = render(<QueryStatus label="Cartera" query={query} />);
    expect(screen.getByRole('status').textContent).toBe('');
    rerender(
      <QueryStatus
        label="Cartera"
        query={{ ...query, error: 'Motor sin conexión' }}
      />,
    );
    expect(screen.getByRole('alert').textContent).toBe(
      'Cartera: Motor sin conexión',
    );
    rerender(
      <QueryStatus
        label="Cartera"
        query={{ ...query, error: 'Motor sin conexión', loading: true }}
      />,
    );
    expect(screen.getByRole('alert').textContent).toBe(
      'Cartera: Motor sin conexión',
    );
    expect(screen.getByRole('status').textContent).toBe('');
    rerender(
      <QueryStatus
        label="Cartera"
        query={{ ...query, error: 'Respuesta no válida' }}
      />,
    );
    expect(screen.getByRole('alert').textContent).toBe(
      'Cartera: Respuesta no válida',
    );
    rerender(
      <QueryStatus
        label="Cartera"
        query={{ ...query, updatedAt: at + 5000 }}
      />,
    );
    expect(screen.getByRole('alert').textContent).toBe('');
    expect(screen.getByRole('status').textContent).toBe(
      'Cartera: conexión recuperada.',
    );
    rerender(
      <QueryStatus
        label="Cartera"
        query={{ ...query, loading: true, updatedAt: at + 5000 }}
      />,
    );
    expect(screen.getByRole('status').textContent).toBe(
      'Cartera: conexión recuperada.',
    );
  });

  it('conserva el error y anuncia un reintento fallido activado por teclado', async () => {
    const user = userEvent.setup();
    const pending = deferred<void>();
    const query = {
      ...ready(),
      error: 'Motor sin conexión',
      refresh: vi.fn(() => pending.promise),
    };
    const { rerender } = render(<QueryStatus label="Cartera" query={query} />);
    const button = screen.getByRole('button', { name: 'Reintentar cartera' });
    button.focus();
    await user.keyboard('{Enter}');
    expect(query.refresh).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('status').textContent).toBe(
      'Reintentando cartera…',
    );
    expect(screen.getByRole('alert').textContent).toBe(
      'Cartera: Motor sin conexión',
    );
    rerender(
      <QueryStatus label="Cartera" query={{ ...query, loading: true }} />,
    );
    await user.keyboard('{Enter}');
    expect(query.refresh).toHaveBeenCalledTimes(1);
    expect(document.activeElement).toBe(button);
    rerender(<QueryStatus label="Cartera" query={query} />);
    await act(async () => pending.resolve());
    expect(screen.getByRole('status').textContent).toBe(
      'Cartera: el reintento ha fallado. Motor sin conexión',
    );
    expect(document.activeElement).toBe(button);
  });

  it('lleva el foco al resumen visible si desaparece el botón de reintento enfocado', async () => {
    const user = userEvent.setup();
    const pending = deferred<void>();
    const query = {
      ...ready(),
      error: 'Motor sin conexión',
      refresh: vi.fn(() => pending.promise),
    };
    const { rerender } = render(<QueryStatus label="Cartera" query={query} />);
    screen.getByRole('button', { name: 'Reintentar cartera' }).focus();
    await user.keyboard('{Enter}');
    rerender(
      <QueryStatus label="Cartera" query={{ ...query, loading: true }} />,
    );
    await act(async () => {
      rerender(
        <QueryStatus
          label="Cartera"
          query={{ ...query, error: '', updatedAt: at + 5000 }}
        />,
      );
      pending.resolve();
    });
    expect(
      screen.queryByRole('button', { name: 'Reintentar cartera' }),
    ).toBeNull();
    const summary = screen.getByText(
      `Última consulta: ${dateTime(new Date(at + 5000).toISOString())}.`,
    );
    expect(document.activeElement).toBe(summary);
    expect(summary.getAttribute('tabindex')).toBe('-1');
    expect(screen.getByRole('status').textContent).toBe(
      'Cartera: consulta actualizada.',
    );
  });

  it('no roba el foco si el usuario pasa a otro campo antes de terminar el reintento', async () => {
    const user = userEvent.setup();
    const pending = deferred<void>();
    const query = {
      ...ready(),
      error: 'Motor sin conexión',
      refresh: vi.fn(() => pending.promise),
    };
    const view = (error: string) => (
      <>
        <QueryStatus label="Cartera" query={{ ...query, error }} />
        <input aria-label="Otro campo" />
      </>
    );
    const { rerender } = render(view(query.error));
    screen.getByRole('button', { name: 'Reintentar cartera' }).focus();
    await user.keyboard('{Enter}');
    await user.tab();
    const field = screen.getByRole('textbox', { name: 'Otro campo' });
    expect(document.activeElement).toBe(field);
    await act(async () => {
      rerender(view(''));
      pending.resolve();
    });
    expect(document.activeElement).toBe(field);
  });

  it('no mueve el foco durante una recuperación automática ni al desmontar el panel', async () => {
    const query = { ...ready(), error: 'Motor sin conexión' };
    const view = (error: string) => (
      <>
        <QueryStatus label="Cartera" query={{ ...query, error }} />
        <input aria-label="Otro campo" />
      </>
    );
    const { rerender, unmount } = render(view(query.error));
    const field = screen.getByRole('textbox', { name: 'Otro campo' });
    field.focus();
    await act(async () => rerender(view('')));
    expect(document.activeElement).toBe(field);
    rerender(view(query.error));
    screen.getByRole('button', { name: 'Reintentar cartera' }).focus();
    await act(async () => unmount());
    expect(document.activeElement).toBe(document.body);
  });
});
