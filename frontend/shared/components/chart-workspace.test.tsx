import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ChartWorkspace } from './chart-workspace';
import { ChartTooltip } from './chart-tooltip';

afterEach(() => {
  cleanup();
  document.body.style.overflow = '';
});

function Example({
  total = 100,
  initialCount = 20,
  maxCount = total,
  zoomAnchor,
}: {
  total?: number;
  initialCount?: number;
  maxCount?: number;
  zoomAnchor?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const [range, setRange] = useState({ start: 40, count: initialCount });
  return (
    <>
      <button>Fuera del gráfico</button>
      <ChartWorkspace
        title="Patrimonio"
        noun="curva"
        expanded={expanded}
        onExpandedChange={setExpanded}
        start={range.start}
        count={range.count}
        total={total}
        maxCount={maxCount}
        zoomAnchor={zoomAnchor}
        onNavigate={(start, count) => setRange({ start, count })}
        onReset={() => setRange({ start: 0, count: total })}
      >
        {/* Test the same focusable SVG used by production charts. */}
        {/* oxlint-disable-next-line jsx-a11y/no-noninteractive-tabindex, jsx-a11y/prefer-tag-over-role */}
        <svg role="img" aria-label="Serie original" tabIndex={0}>
          <text>
            {range.start}:{range.count}
          </text>
        </svg>
        {expanded && (
          <ChartTooltip anchor={{ x: 100, y: 100 }}>
            Valor original
          </ChartTooltip>
        )}
      </ChartWorkspace>
    </>
  );
}

describe('ChartWorkspace', () => {
  it('conserva la última observación inspeccionada al ampliar con la lupa', () => {
    render(<Example zoomAnchor={1} />);
    fireEvent.click(screen.getByRole('button', { name: 'Acercar curva' }));
    // Initial observations 40..59 become 50..59: the inspected final point stays visible.
    expect(screen.getByRole('img').textContent).toBe('50:10');
    fireEvent.click(screen.getByRole('button', { name: 'Alejar curva' }));
    expect(screen.getByRole('img').textContent).toBe('40:20');
  });
  it('navega con una ventana proporcional y lupas sin cambiar el número de observaciones al desplazar', () => {
    render(<Example />);
    const slider = screen.getByRole<HTMLInputElement>('slider', {
      name: 'Desplazar curva',
    });
    expect(slider.max).toBe('80');
    expect(slider.value).toBe('40');
    expect(slider.style.getPropertyValue('--chart-window-width')).toBe('20%');
    fireEvent.change(slider, { target: { value: '70' } });
    expect(screen.getByRole('img').textContent).toBe('70:20');
    const zoom = screen.getByRole('button', { name: 'Acercar curva' });
    expect(zoom.textContent).toBe('');
    fireEvent.click(zoom);
    expect(screen.getByRole('img').textContent).toBe('75:10');
    expect(slider.max).toBe('90');
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer curva' }));
    expect(slider.disabled).toBe(true);
    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Alejar curva' })
        .disabled,
    ).toBe(true);
  });

  it('admite una observación y respeta el límite de renderizado', () => {
    render(<Example initialCount={1} maxCount={30} />);
    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Acercar curva' })
        .disabled,
    ).toBe(true);
    const zoomOut = screen.getByRole<HTMLButtonElement>('button', {
      name: 'Alejar curva',
    });
    for (let step = 0; step < 6; step += 1) fireEvent.click(zoomOut);
    expect(zoomOut.disabled).toBe(true);
    expect(
      screen
        .getByRole<HTMLInputElement>('slider')
        .style.getPropertyValue('--chart-window-width'),
    ).toBe('30%');
  });

  it('omite herramientas sin serie y permite restablecer un filtro vacío', () => {
    const { unmount } = render(<Example total={0} initialCount={0} />);
    expect(screen.queryByRole('slider')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Acercar curva' })).toBeNull();
    unmount();
    render(<Example initialCount={0} />);
    expect(screen.getByRole<HTMLInputElement>('slider').disabled).toBe(true);
    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Acercar curva' })
        .disabled,
    ).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer curva' }));
    expect(screen.getByRole('img').textContent).toBe('0:100');
  });

  it('usa un diálogo si fullscreen es rechazado, mantiene el SVG y la ficha, y restaura foco/scroll con Escape', async () => {
    const { container } = render(<Example />);
    const svg = screen.getByRole('img');
    const outside = screen.getByRole('button', { name: 'Fuera del gráfico' });
    const root = container.querySelector<HTMLDivElement>('.chart-workspace')!;
    const requestFullscreen = vi
      .fn()
      .mockRejectedValue(new Error('Unavailable in embedded browser'));
    root.requestFullscreen = requestFullscreen;
    const open = screen.getByRole('button', {
      name: 'Pantalla completa: Patrimonio',
    });
    document.body.style.overflow = 'scroll';
    open.focus();
    fireEvent.click(open);
    await waitFor(() =>
      expect(screen.getByRole('dialog', { name: 'Patrimonio' })).toBe(root),
    );
    expect(requestFullscreen).toHaveBeenCalledOnce();
    expect(screen.getByRole('img')).toBe(svg);
    expect(root.classList.contains('is-expanded')).toBe(true);
    expect(screen.getByRole('tooltip').parentElement).toBe(root);
    expect(document.body.style.overflow).toBe('hidden');
    expect(outside.hasAttribute('inert')).toBe(true);
    expect(document.activeElement).toBe(
      screen.getByRole('button', { name: 'Salir de pantalla completa' }),
    );
    outside.focus();
    expect(root.contains(document.activeElement)).toBe(true);
    const first = screen.getByRole('button', { name: 'Acercar curva' });
    first.focus();
    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(screen.getByRole('slider'));
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByRole('img')).toBe(svg);
    expect(outside.hasAttribute('inert')).toBe(false);
    expect(document.activeElement).toBe(open);
    expect(document.body.style.overflow).toBe('scroll');
    document.body.style.overflow = '';
  });

  it('sigue la salida nativa del navegador sin remontar la serie', async () => {
    const { container, unmount } = render(<Example />);
    const root = container.querySelector<HTMLDivElement>('.chart-workspace')!;
    let fullscreenElement: Element | null = null;
    const original = Object.getOwnPropertyDescriptor(
      document,
      'fullscreenElement',
    );
    Object.defineProperty(document, 'fullscreenElement', {
      configurable: true,
      get: () => fullscreenElement,
    });
    root.requestFullscreen = vi.fn(async () => {
      fullscreenElement = root;
      document.dispatchEvent(new Event('fullscreenchange'));
    });
    try {
      const svg = screen.getByRole('img');
      await act(async () => {
        fireEvent.click(
          screen.getByRole('button', { name: 'Pantalla completa: Patrimonio' }),
        );
      });
      expect(screen.getByRole('dialog')).toBe(root);
      await act(async () => {
        fullscreenElement = null;
        document.dispatchEvent(new Event('fullscreenchange'));
      });
      expect(screen.queryByRole('dialog')).toBeNull();
      expect(screen.getByRole('img')).toBe(svg);
      expect(document.body.style.overflow).toBe('');
    } finally {
      unmount();
      if (original)
        Object.defineProperty(document, 'fullscreenElement', original);
      else Reflect.deleteProperty(document, 'fullscreenElement');
    }
  });

  it('limpia bloqueo y atributos al desmontarse expandido', () => {
    const { container, unmount } = render(<Example />);
    const outside = screen.getByRole('button', { name: 'Fuera del gráfico' });
    fireEvent.click(
      screen.getByRole('button', { name: 'Pantalla completa: Patrimonio' }),
    );
    expect(container.contains(screen.getByRole('dialog'))).toBe(true);
    unmount();
    expect(document.body.style.overflow).toBe('');
    expect(outside.hasAttribute('inert')).toBe(false);
    expect(document.body.querySelector('[inert]')).toBeNull();
  });
});
