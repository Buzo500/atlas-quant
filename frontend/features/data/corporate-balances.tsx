'use client';

import type { CorporatePortfolio } from '@/lib/api-types';
import { DataTable } from '@/shared/ui';

const statuses = {
  pending_payment: 'Derecho pendiente de cobro',
  reconciled: 'Cobro conciliado',
  applied: 'Split aplicado',
  outdated: 'Requiere nueva revisión',
  cancelled: 'Aplicación cancelada',
};
export function CorporateBalances({ value }: { value: CorporatePortfolio }) {
  return (
    <>
      <p>
        <strong>Derechos pendientes: {value.pending_receivables} EUR</strong> ·
        Efectivo del libro: {value.balance.cash} EUR · al {value.as_of_date}
      </p>
      <p className="muted">
        El derecho se muestra separado del efectivo. La valoración y la
        rentabilidad del libro exacto llegarán en las siguientes entregas.
      </p>
      <DataTable
        heads={[
          'Evento',
          'Estado',
          'Cantidad elegible / anterior',
          'Derecho pendiente EUR',
          'Base de precios',
        ]}
        numericColumns={[2, 3]}
        rows={value.applications.map((a) => [
          `${a.event_type === 'dividend' ? 'Dividendo' : 'Split'} · ${a.effective_date} · r${a.event_revision}`,
          statuses[a.status],
          a.eligible_quantity ?? a.basis_quantity,
          a.receivable,
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
