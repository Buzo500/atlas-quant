'use client';
import { useState } from 'react';
import type { SourcePreflight } from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/shared/ui';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { date } from '@/shared/format';

export function SourcePrevalidation({
  id,
  version,
}: {
  id: string;
  version: number;
}) {
  const [enabled, setEnabled] = useState(false);
  const query = useRead<SourcePreflight>({
    path: enabled
      ? `/lab/sources/preflight?series_id=${encodeURIComponent(id)}&series_version=${version}`
      : null,
  });
  const value = query.data;
  return (
    <section aria-label="Prevalidación del CSV" className="source-preflight">
      <Button
        variant="outline"
        onClick={() => {
          setEnabled(true);
          if (enabled) void query.refresh();
        }}
      >
        Prevalidar CSV antes de configurar
      </Button>
      <QueryStatus label="Prevalidación del CSV" query={query} />
      {value && (
        <>
          <h3>
            {value.checks.some((c) => c.status === 'block')
              ? 'Hay bloqueos en esta versión'
              : 'Revisión del protocolo pendiente'}
          </h3>
          <p className="muted">
            {value.rows} barras · {date(value.start)} → {date(value.end)}.
            Revisión de toda la versión, sin calcular rentabilidad ni abrir la
            prueba final. No certifica el origen de los datos.
          </p>
          <DataTable
            heads={['Estado', 'Comprobación']}
            rows={value.checks.map((c) => [
              c.status === 'block'
                ? 'Bloqueo'
                : c.status === 'review'
                  ? 'Revisar'
                  : 'Conforme',
              c.message,
            ])}
          />
          <p className="muted">
            El cálculo volverá a comprobar la evidencia y el periodo elegido.
            Corrige los datos mediante una nueva versión; nunca inventes
            disponibilidad histórica.
          </p>
        </>
      )}
    </section>
  );
}
