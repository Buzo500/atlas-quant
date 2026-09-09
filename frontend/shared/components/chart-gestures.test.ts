import { act, fireEvent, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { type PointerEvent as ReactPointerEvent } from 'react';
import {
  clampChartWindow,
  useChartGestures,
  zoomChartWindow,
} from './chart-gestures';

const elements: SVGSVGElement[] = [];
afterEach(() => {
  for (const element of elements.splice(0)) element.remove();
});

function example(
  overrides: Partial<Parameters<typeof useChartGestures>[0]> = {},
) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 1000 500');
  document.body.appendChild(svg);
  elements.push(svg);
  svg.getBoundingClientRect = () => ({
    left: 10,
    top: 20,
    right: 1010,
    bottom: 520,
    x: 10,
    y: 20,
    width: 1000,
    height: 500,
    toJSON() {},
  });
  const setPointerCapture = vi.fn();
  const releasePointerCapture = vi.fn();
  svg.setPointerCapture = setPointerCapture;
  svg.releasePointerCapture = releasePointerCapture;
  svg.hasPointerCapture = vi.fn(() => true);
  const onNavigate = vi.fn();
  const onGesture = vi.fn();
  const initial = {
    svgRef: { current: svg },
    enabled: true,
    start: 200,
    count: 101,
    total: 1000,
    onNavigate,
    onGesture,
    plotLeft: 100,
    plotWidth: 800,
    ...overrides,
  };
  const hook = renderHook((options) => useChartGestures(options), {
    initialProps: initial,
  });
  const pointer = (clientX: number, other = {}) =>
    ({
      currentTarget: svg,
      pointerId: 1,
      pointerType: 'mouse',
      button: 0,
      clientX,
      clientY: 200,
      preventDefault: vi.fn(),
      ...other,
    }) as unknown as ReactPointerEvent<SVGSVGElement>;
  const wheel = (init: WheelEventInit = {}) => {
    const event = new WheelEvent('wheel', {
      bubbles: true,
      cancelable: true,
      clientX: 510,
      clientY: 200,
      deltaY: -100,
      ...init,
    });
    act(() => {
      svg.dispatchEvent(event);
    });
    return event;
  };
  return {
    svg,
    ...hook,
    initial,
    onNavigate,
    onGesture,
    pointer,
    wheel,
    setPointerCapture,
    releasePointerCapture,
  };
}

describe('chart navigation bounds', () => {
  it('preserva muestras, limita extremos y permite una sola observación', () => {
    expect(clampChartWindow(-400, 80, 100)).toEqual({ start: 0, count: 80 });
    expect(clampChartWindow(500, 80, 100)).toEqual({ start: 20, count: 80 });
    expect(clampChartWindow(20, 3000, 10000, 1000)).toEqual({
      start: 20,
      count: 1000,
    });
    expect(clampChartWindow(Infinity, NaN, 0)).toEqual({ start: 0, count: 0 });
    expect(zoomChartWindow(10, 2, 100, 0.5)).toEqual({ start: 11, count: 1 });
    expect(zoomChartWindow(0, 0, 0, 2)).toEqual({ start: 0, count: 0 });
  });
});

describe('useChartGestures', () => {
  it('permite recorrer una y dos observaciones con rueda manteniendo el ancla', () => {
    const test = example({ start: 20, count: 1, total: 100 });
    test.wheel({ deltaY: 100, clientX: 910 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(19, 2);
    test.wheel({ deltaY: -100, clientX: 910 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(20, 1);
    test.wheel({ deltaY: -100, clientX: 910 });
    expect(test.onNavigate.mock.calls).toEqual([
      [19, 2],
      [20, 1],
    ]);
  });

  it('el progreso mínimo del zoom no rebasa la serie ni el límite de renderizado', () => {
    const test = example({ start: 0, count: 2, total: 2 });
    test.wheel({ deltaY: 100 });
    expect(test.onNavigate).not.toHaveBeenCalled();
    test.rerender({ ...test.initial, total: 100, maxCount: 2 });
    test.wheel({ deltaY: 100 });
    expect(test.onNavigate).not.toHaveBeenCalled();
    test.rerender({ ...test.initial, total: 1, count: 1 });
    test.wheel({ deltaY: 100 });
    test.wheel({ deltaY: -100 });
    expect(test.onNavigate).not.toHaveBeenCalled();
  });
  it('desplaza con umbral horizontal y captura, conserva cantidad y suprime el click final', () => {
    const test = example();
    expect(test.result.current.onPointerDown(test.pointer(510))).toBe(false);
    expect(test.setPointerCapture).toHaveBeenCalledWith(1);
    expect(test.result.current.onPointerMove(test.pointer(512))).toBe(false);
    expect(test.onNavigate).not.toHaveBeenCalled();
    expect(test.result.current.onPointerMove(test.pointer(590))).toBe(true);
    expect(test.onNavigate).toHaveBeenLastCalledWith(190, 101);
    expect(test.onGesture).toHaveBeenCalledOnce();
    expect(test.svg.dataset.chartDragging).toBe('true');
    expect(test.result.current.onPointerUp(test.pointer(590))).toBe(true);
    expect(test.svg.dataset.chartDragging).toBeUndefined();
    expect(test.releasePointerCapture).toHaveBeenCalledWith(1);
    expect(test.result.current.onClick()).toBe(true);
    expect(test.result.current.onClick()).toBe(false);
    expect(test.result.current.onPointerMove(test.pointer(700))).toBe(false);
  });

  it('respeta ambos extremos y termina un arrastre cancelado o sin captura', () => {
    const test = example();
    test.result.current.onPointerDown(test.pointer(510));
    test.result.current.onPointerMove(test.pointer(10000));
    expect(test.onNavigate).toHaveBeenLastCalledWith(0, 101);
    test.result.current.onPointerMove(test.pointer(-10000));
    expect(test.onNavigate).toHaveBeenLastCalledWith(899, 101);
    expect(test.result.current.onPointerCancel(test.pointer(0))).toBe(true);
    expect(test.result.current.onPointerMove(test.pointer(400))).toBe(false);
    test.result.current.onPointerDown(test.pointer(510));
    test.result.current.onPointerMove(test.pointer(590));
    expect(test.result.current.onLostPointerCapture(test.pointer(590))).toBe(
      true,
    );
    expect(test.svg.dataset.chartDragging).toBeUndefined();
  });

  it('solo intercepta rueda sin modificadores sobre el área del gráfico expandido', () => {
    const test = example();
    expect(test.wheel({ ctrlKey: true }).defaultPrevented).toBe(false);
    expect(test.wheel({ metaKey: true }).defaultPrevented).toBe(false);
    expect(test.wheel({ altKey: true }).defaultPrevented).toBe(false);
    expect(test.wheel({ clientX: 30 }).defaultPrevented).toBe(false);
    expect(test.wheel({ deltaY: 0 }).defaultPrevented).toBe(false);
    expect(test.onNavigate).not.toHaveBeenCalled();
    expect(test.wheel().defaultPrevented).toBe(true);
    expect(test.onNavigate).toHaveBeenLastCalledWith(210, 81);
    test.rerender({ ...test.initial, enabled: false });
    expect(test.wheel().defaultPrevented).toBe(false);
    expect(test.result.current.onPointerDown(test.pointer(510))).toBe(false);
    expect(test.result.current.onPointerMove(test.pointer(700))).toBe(false);
    test.unmount();
    expect(test.wheel().defaultPrevented).toBe(false);
  });

  it('ancla zoom en la observación del puntero y limita precios a 1000 visibles', () => {
    const test = example({ count: 100, total: 100000, maxCount: 1000 });
    test.wheel({ clientX: 110 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(200, 80);
    test.rerender({ ...test.initial, count: 100 });
    test.wheel({ clientX: 910 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(220, 80);
    test.rerender({ ...test.initial, count: 900 });
    test.wheel({ deltaY: 100 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(150, 1000);
    test.wheel({ deltaY: 100 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(150, 1000);
  });

  it('acumula ruedas antes del próximo render y usa callbacks actualizados', () => {
    const test = example({ count: 100 });
    act(() => {
      fireEvent.wheel(test.svg, { deltaY: -100, clientX: 110, clientY: 200 });
      fireEvent.wheel(test.svg, { deltaY: -100, clientX: 110, clientY: 200 });
    });
    expect(test.onNavigate.mock.calls).toEqual([
      [200, 80],
      [200, 64],
    ]);
    const updated = vi.fn();
    test.rerender({ ...test.initial, onNavigate: updated, start: 50 });
    test.wheel({ clientX: 110 });
    expect(updated).toHaveBeenLastCalledWith(50, 80);
    expect(test.onNavigate).toHaveBeenCalledTimes(2);
  });

  it('convierte coordenadas mediante CTM inversa incluyendo traslación y escala', () => {
    const test = example({ count: 100 });
    Object.defineProperty(test.svg, 'getScreenCTM', {
      value: () => ({ inverse: () => ({ a: 2, c: 0, e: -200 }) }),
    });
    test.wheel({ clientX: 150 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(200, 80);
    test.rerender(test.initial);
    test.wheel({ clientX: 550 });
    expect(test.onNavigate).toHaveBeenLastCalledWith(220, 80);
  });

  it('centra el viewBox si no hay CTM, y no navega con matrices singulares', () => {
    const test = example({ count: 100 });
    test.svg.getBoundingClientRect = () => ({
      left: 10,
      top: 20,
      right: 1010,
      bottom: 270,
      x: 10,
      y: 20,
      width: 1000,
      height: 250,
      toJSON() {},
    });
    test.wheel({ clientX: 310 }); // letterbox 250 + plot-left 50 + left 10
    expect(test.onNavigate).toHaveBeenLastCalledWith(200, 80);
    Object.defineProperty(test.svg, 'getScreenCTM', {
      value: () => ({
        inverse: () => {
          throw new Error('Singular');
        },
      }),
    });
    expect(test.wheel().defaultPrevented).toBe(false);
    expect(test.onNavigate).toHaveBeenCalledOnce();
  });

  it('descarta botones secundarios, toques y punteros ajenos al arrastre', () => {
    const test = example();
    test.result.current.onPointerDown(test.pointer(510, { button: 2 }));
    expect(test.result.current.onPointerMove(test.pointer(590))).toBe(false);
    test.result.current.onPointerDown(
      test.pointer(510, { pointerType: 'touch' }),
    );
    expect(test.result.current.onPointerMove(test.pointer(590))).toBe(false);
    test.result.current.onPointerDown(test.pointer(510));
    expect(
      test.result.current.onPointerMove(test.pointer(590, { pointerId: 2 })),
    ).toBe(false);
    expect(test.onNavigate).not.toHaveBeenCalled();
  });
});
