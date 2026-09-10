'use client';

import type {
  CorporatePortfolio,
  NativeCorporatePortfolio,
} from '@/lib/api-types';
import { DataTable } from '@/shared/ui';

const statuses = {
  pending_payment: 'Derecho pendiente de cobro',
  reconciled: 'Cobro conciliado',
  applied: 'Split aplicado',
  outdated: 'Requiere nueva revisión',
  cancelled: 'Aplicación cancelada',
};
export function CorporateBalances({
  value,
}: {
  value: CorporatePortfolio | NativeCorporatePortfolio;
}) {
  const rights =
    'pending_receivables_by_currency' in value
      ? value.pending_receivables_by_currency
          .map((b) => `${b.amount} ${b.currency}`)
          .join(' · ')
      : `${value.pending_receivables} EUR`;
  const cash =
    'balances' in value.balance
      ? value.balance.balances.map((b) => `${b.cash} ${b.currency}`).join(' · ')
      : `${value.balance.cash} EUR`;
  return (
    <>
      <p>
        <strong>Derechos pendientes: {rights}</strong> · Efectivo del libro:{' '}
        {cash} · al {value.as_of_date}
      </p>
      <p className="muted">
        El derecho se muestra separado del efectivo y se cancela al registrar su
        cobro, evitando contar dos veces el dividendo.
      </p>
      <DataTable
        heads={[
          'Evento',
          'Estado',
          'Cantidad elegible / anterior',
          'Derecho pendiente',
          'Base de precios',
        ]}
        numericColumns={[2, 3]}
        rows={value.applications.map((a) => [
          `${a.event_type === 'dividend' ? 'Dividendo' : 'Split'} · ${a.effective_date} · r${a.event_revision}`,
          statuses[a.status],
          a.eligible_quantity ?? a.basis_quantity,
          `${a.receivable} ${a.event_snapshot.currency}`,
          a.price_status === 'not_applicable'
            ? '—'
            : a.price_status === 'compatible'
              ? 'Bruta compatible'
              : 'Sin acreditar',
        ])}
        emptyMessage="Todavía no hay aplicaciones de eventos en este corte."
      />
      {[
        ...new Set([
          ...value.warnings,
          ...value.applications.flatMap((a) => a.warnings),
        ]),
      ].map((warning) => (
        <p className="muted" key={warning}>
          {warning}
        </p>
      ))}
    </>
  );
}
