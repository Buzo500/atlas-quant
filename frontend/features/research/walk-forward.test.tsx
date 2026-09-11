import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { useState } from 'react';
import type { WalkForwardReport } from '@/lib/api-types';
import {
  initialWalkForward,
  WalkForwardEditor,
  WalkForwardResult,
} from './walk-forward';

vi.mock('@/components/atlas/curve', () => ({
  Curve: () => <div>Curva de la ventana</div>,
}));

export const wfReport: WalkForwardReport = {
  policy: 'atlas-walk-forward-fixed-v1',
  config: {
    ...initialWalkForward,
    context_sessions: 7,
    evaluation_sessions: 7,
  },
  windows: [
    {
      index: 1,
      context_start: '2025-01-01',
      context_end: '2025-01-07',
      warmup_start: '2025-01-05',
      warmup_sessions: 3,
      context_metrics: [],
      context_hash: 'context',
      evaluable: false,
      passed: false,
      reasons: ['Falta una apertura acreditada.'],
      evaluation: {
        start_date: '2025-01-08',
        end_date: '2025-01-14',
        sessions: 7,
        curve: [],
        trades: [],
        expired: 1,
        rejected: 0,
        report_hash: 'window',
        metrics: [
          {
            name: 'SMA',
            final_nav_eur: null,
            return_pct: null,
            max_drawdown_pct: null,
            fills: 0,
            fees_eur: '0.00',
          },
          {
            name: 'Comprar y mantener',
            final_nav_eur: '1000',
            return_pct: '0',
            max_drawdown_pct: '0',
            fills: 0,
            fees_eur: '0.00',
          },
        ],
      },
    },
  ],
  summary: {
    status: 'insufficient_data',
    windows: 1,
    evaluable_windows: 0,
    passing_windows: 0,
    passing_pct: '0',
    mean_return_pct: null,
    mean_excess_pct: null,
    worst_drawdown_pct: null,
    reasons: ['Hay ventanas con evidencia insuficiente.'],
  },
  unused_sessions: 2,
  unused_start: '2025-01-15',
  unused_end: '2025-01-16',
  warnings: ['Cuentas independientes; no es una aprobación.'],
  report_hash: 'wf-hash',
};

it('permite predeclarar ventanas sin convertir un campo vacío en cero', () => {
  function Editor() {
    const [enabled, onEnabled] = useState(false);
    const [value, onChange] = useState(initialWalkForward);
    return <WalkForwardEditor {...{ enabled, onEnabled, value, onChange }} />;
  }
  render(<Editor />);
  expect(screen.queryByLabelText('Sesiones de contexto')).toBeNull();
  fireEvent.click(screen.getByLabelText('Añadir validación walk-forward'));
  const field = screen.getByLabelText(
    'Sesiones de contexto',
  ) as HTMLInputElement;
  expect(field.value).toBe('252');
  fireEvent.change(field, { target: { value: '' } });
  expect(field.value).toBe('');
  expect(field.validity.valueMissing).toBe(true);
  fireEvent.change(field, { target: { value: '7' } });
  expect(field.value).toBe('7');
  fireEvent.click(screen.getByLabelText('Añadir validación walk-forward'));
  expect(screen.queryByLabelText('Sesiones de contexto')).toBeNull();
});

it('distingue datos ausentes, cola sin evaluar y criterios guardados', () => {
  render(<WalkForwardResult result={wfReport} />);
  const result = screen.getByRole('region', { name: 'Resultado walk-forward' });
  expect(within(result).getAllByText('Evidencia insuficiente')).toHaveLength(2);
  expect(within(result).getAllByText('No disponible').length).toBeGreaterThan(
    2,
  );
  expect(
    within(result).getByText(/2 sesiones al final del desarrollo/),
  ).toBeTruthy();
  fireEvent.click(within(result).getByText('Detalle de la ventana 1'));
  expect(
    within(result).getByText('Falta una apertura acreditada.'),
  ).toBeTruthy();
  expect(
    within(result).getByRole('region', { name: 'Evaluación de la ventana 1' }),
  ).toBeTruthy();
  expect(within(result).getByText(/Contexto: 7 sesiones/)).toBeTruthy();
  expect(within(result).getByText(/Huella walk-forward: wf-hash/)).toBeTruthy();
});
