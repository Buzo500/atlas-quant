import { describe, expect, it } from 'vitest';
import {
  dateWindow,
  nearestObservation,
  panWindow,
  zoomWindow,
} from './curve-window';

describe('Ventanas de observaciones originales', () => {
  const dates = ['2026-01-02', '2026-01-05', '2026-02-02', '2026-12-31'].map(
    (date) => ({ date }),
  );

  it('incluye extremos y no rellena huecos de sesión', () => {
    expect(dateWindow(dates, '2026-01-05', '2026-02-02')).toEqual({
      start: 1,
      end: 2,
    });
    expect(dateWindow(dates, '2026-01-03', '2026-01-04')).toEqual({
      start: 1,
      end: 0,
    });
    expect(dateWindow(dates, '', '')).toEqual({ start: 0, end: 3 });
    expect(dateWindow([], '', '')).toEqual({ start: 0, end: -1 });
  });

  it('selecciona por observaciones, acota extremos y desempata hacia la siguiente', () => {
    expect(nearestObservation(0.5, { start: 10, end: 13 })).toBe(12);
    expect(nearestObservation(-2, { start: 10, end: 13 })).toBe(10);
    expect(nearestObservation(2, { start: 10, end: 13 })).toBe(13);
    expect(nearestObservation(0.5, { start: 7, end: 7 })).toBe(7);
  });

  it('acerca alrededor de la observación seleccionada, sin exceder los datos', () => {
    expect(zoomWindow({ start: 0, end: 9 }, 10, 0.5, 0)).toEqual({
      start: 0,
      end: 4,
    });
    expect(zoomWindow({ start: 0, end: 9 }, 10, 0.5, 9)).toEqual({
      start: 5,
      end: 9,
    });
    expect(zoomWindow({ start: 5, end: 9 }, 10, 2, 9)).toEqual({
      start: 0,
      end: 9,
    });
    expect(zoomWindow({ start: 4, end: 4 }, 10, 0.5, 4)).toEqual({
      start: 4,
      end: 4,
    });
    expect(zoomWindow({ start: 4, end: 4 }, 10, 2, 4)).toEqual({
      start: 4,
      end: 5,
    });
  });

  it('desplaza conservando la cantidad y se detiene en los extremos', () => {
    expect(panWindow({ start: 0, end: 4 }, 10, -1)).toEqual({
      start: 0,
      end: 4,
    });
    expect(panWindow({ start: 0, end: 4 }, 10, 1)).toEqual({
      start: 2,
      end: 6,
    });
    expect(panWindow({ start: 5, end: 9 }, 10, 1)).toEqual({
      start: 5,
      end: 9,
    });
    expect(panWindow({ start: 0, end: -1 }, 0, 1)).toEqual({
      start: 0,
      end: -1,
    });
  });
});
