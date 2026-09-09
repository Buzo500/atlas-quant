import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ChartTooltip } from './chart-tooltip';

describe('ChartTooltip', () => {
  it('solo aparece durante la inspección y se monta fuera de contenedores que recortan', () => {
    const { rerender, container } = render(
      <ChartTooltip anchor={null}>Valor</ChartTooltip>,
    );
    expect(screen.queryByRole('tooltip')).toBeNull();
    rerender(<ChartTooltip anchor={{ x: 40, y: 50 }}>Valor</ChartTooltip>);
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip.parentElement).toBe(document.body);
    expect(container.contains(tooltip)).toBe(false);
    expect(tooltip.style.left).toBe('56px');
    expect(tooltip.style.top).toBe('66px');
    rerender(<ChartTooltip anchor={null}>Valor</ChartTooltip>);
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('cambia de lado y se mantiene dentro de la pantalla en sus cuatro extremos', () => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 280,
      bottom: 220,
      width: 280,
      height: 220,
      toJSON() {},
    });
    const { rerender } = render(
      <ChartTooltip anchor={{ x: innerWidth - 10, y: innerHeight - 10 }}>
        Valor
      </ChartTooltip>,
    );
    let tooltip = screen.getByRole('tooltip');
    expect(Number.parseFloat(tooltip.style.left) + 280).toBeLessThan(
      innerWidth - 10,
    );
    expect(Number.parseFloat(tooltip.style.top) + 220).toBeLessThan(
      innerHeight - 10,
    );
    rerender(<ChartTooltip anchor={{ x: -40, y: -50 }}>Valor</ChartTooltip>);
    tooltip = screen.getByRole('tooltip');
    expect(tooltip.style.left).toBe('8px');
    expect(tooltip.style.top).toBe('8px');
  });

  it('descarta la ficha al desplazar, redimensionar, salir de la ventana o pulsar Escape', () => {
    const dismiss = vi.fn();
    const { unmount } = render(
      <ChartTooltip anchor={{ x: 50, y: 50 }} onDismiss={dismiss}>
        Valor
      </ChartTooltip>,
    );
    fireEvent.scroll(document);
    fireEvent.resize(window);
    fireEvent.blur(window);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(dismiss).toHaveBeenCalledTimes(4);
    unmount();
    fireEvent.scroll(document);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(dismiss).toHaveBeenCalledTimes(4);
  });
});
