'use client';
import { useMemo } from 'react';
import type { LabPeriod } from '@/lib/api-types';
import { Curve } from '@/components/atlas/curve';
import { DataTable } from '@/shared/ui';
import { moneyEUR, number, date } from '@/shared/format';

const amount = (value: string | null) =>
  value === null ? 'No disponible' : moneyEUR(Number(value));
const percentage = (value: string | null) =>
  value === null
    ? 'No disponible'
    : `${number(Number(value), { maximumFractionDigits: 3 })} %`;

export function PeriodResult({
  result,
  title,
}: {
  result: LabPeriod;
  title: string;
}) {
  const curve = useMemo(
    () =>
      result.curve.every((p) => p.sma_eur !== null && p.buy_hold_eur !== null)
        ? result.curve.map((p) => ({
            date: p.date,
            equity: Number(p.sma_eur),
            benchmark: Number(p.buy_hold_eur),
          }))
        : [],
    [result],
  );
  return (
    <section className="panel" aria-label={title}>
      <div className="panel-heading">
        <div>
          <h3>{title}</h3>
          <p className="muted">
            {date(result.start_date)} → {date(result.end_date)} ·{' '}
            {result.sessions} sesiones
          </p>
        </div>
      </div>
      <DataTable
        heads={[
          'Referencia',
          'NAV final',
          'Rentabilidad',
          'Caída máxima',
          'Ejecuciones',
          'Comisiones',
        ]}
        numericColumns={[1, 2, 3, 4, 5]}
        rows={result.metrics.map((m) => [
          m.name,
          amount(m.final_nav_eur),
          percentage(m.return_pct),
          percentage(m.max_drawdown_pct),
          m.fills,
          amount(m.fees_eur),
        ])}
      />
      <p className="muted">
        {result.rejected} intentos rechazados · {result.expired} oportunidades
        caducadas. La posición final se valora sin venderla automáticamente.
      </p>
      {curve.length > 0 ? (
        <>
          <p className="muted">SMA y referencia comprar/mantener, en EUR.</p>
          <Curve data={curve} benchmarkLabel="Comprar y mantener" />
        </>
      ) : (
        <p className="notice">
          Hay valoraciones no disponibles. Consulta las observaciones; los
          huecos no se sustituyen por cero.
        </p>
      )}
      <details className="details">
        <summary>Operaciones simuladas y observaciones</summary>
        <DataTable
          heads={[
            'Estrategia',
            'Fecha',
            'Operación',
            'Cantidad',
            'Precio EUR',
            'Comisión EUR',
          ]}
          numericColumns={[3, 4, 5]}
          rows={result.trades.map((t) => [
            t.strategy,
            date(t.date),
            t.side === 'buy' ? 'Compra' : 'Venta',
            t.quantity,
            amount(t.price_eur),
            amount(t.fee_eur),
          ])}
        />
        <DataTable
          heads={['Fecha', 'SMA EUR', 'Comprar/mantener EUR', 'Efectivo EUR']}
          numericColumns={[1, 2, 3]}
          rows={result.curve.map((p) => [
            date(p.date),
            amount(p.sma_eur),
            amount(p.buy_hold_eur),
            amount(p.cash_eur),
          ])}
        />
        <p className="mono native-hash">
          Huella del resultado: {result.report_hash}
        </p>
      </details>
    </section>
  );
}
