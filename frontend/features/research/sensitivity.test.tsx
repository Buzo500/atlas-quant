import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { useState } from 'react';
import {
  initialSensitivity,
  SensitivityEditor,
  sensitivityInput,
} from './sensitivity';

it('deja ejes vacíos sin inventar valores y conserva los decimales de costes', () => {
  expect(
    sensitivityInput({ fast: '', slow: '40, 60', costs: '1, 1.0001, 2' }),
  ).toEqual({
    policy: 'atlas-sensitivity-oat-v1',
    fast_windows: [],
    slow_windows: [40, 60],
    cost_multipliers: ['1', '1.0001', '2'],
  });
});

it.each(['2,', '2,,3', '2.5', '2e1', '-2'])(
  'rechaza ventanas ambiguas: %s',
  (fast) => {
    expect(() => sensitivityInput({ fast, slow: '', costs: '1, 2' })).toThrow(
      /enteros/,
    );
  },
);

it.each(['1,', 'NaN', '-1', '1e1'])(
  'rechaza multiplicadores ambiguos: %s',
  (costs) => {
    expect(() => sensitivityInput({ fast: '', slow: '', costs })).toThrow(
      /decimal/,
    );
  },
);

it('la sensibilidad es opcional y conserva el borrador al alternarla', () => {
  function Editor() {
    const [enabled, onEnabled] = useState(false);
    const [value, onChange] = useState(initialSensitivity);
    return <SensitivityEditor {...{ enabled, onEnabled, value, onChange }} />;
  }
  render(<Editor />);
  expect(screen.queryByLabelText('Ventanas rápidas alternativas')).toBeNull();
  fireEvent.click(screen.getByLabelText('Añadir análisis de sensibilidad'));
  fireEvent.change(screen.getByLabelText('Ventanas lentas alternativas'), {
    target: { value: '40, 60' },
  });
  fireEvent.click(screen.getByLabelText('Añadir análisis de sensibilidad'));
  fireEvent.click(screen.getByLabelText('Añadir análisis de sensibilidad'));
  expect(
    (screen.getByLabelText('Ventanas lentas alternativas') as HTMLInputElement)
      .value,
  ).toBe('40, 60');
});
