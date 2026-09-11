'use client';
import { useState } from 'react';
import { api } from '@/lib/api';
import type {
  CandidateComparison,
  CandidateRef,
  CandidateRevisions,
} from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Choice, DataTable, Field } from '@/shared/ui';
import { useRead } from '@/shared/use-read';
import { useAction } from '@/shared/use-action';
import { QueryStatus } from '@/shared/query-status';
import { date, dateTime, number } from '@/shared/format';

const labels: Record<string, string> = {
  researching: 'En investigación',
  watchlist: 'En seguimiento',
  discarded: 'Descartada',
};
const key = (r: CandidateRef) => `${r.candidate_id}:${r.revision}`;
const percent = (s: string | null | undefined) =>
  s == null
    ? 'No disponible'
    : `${number(Number(s), { maximumFractionDigits: 3 })} %`;

export function CandidateBrowser({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const [draft, setDraft] = useState('');
  const [status, setStatus] = useState('');
  const [filter, setFilter] = useState({ q: '', status: '' });
  const [offset, setOffset] = useState(0);
  const query = useRead<CandidateRevisions>({
    path: `/lab/candidates/search?${new URLSearchParams({ q: filter.q, ...(filter.status ? { status: filter.status } : {}), offset: String(offset), limit: '20' })}`,
  });
  const [selected, setSelected] = useState<
    Array<CandidateRef & { name: string }>
  >([]);
  const [report, setReport] = useState<CandidateComparison | null>(null);
  const { busy, run } = useAction(onError);
  function remove(id: string) {
    setSelected(selected.filter((r) => key(r) !== id));
    setReport(null);
  }
  return (
    <section
      aria-label="Buscar y comparar revisiones"
      className="candidate-browser"
    >
      <h3>Buscar y comparar revisiones</h3>
      <p className="muted">
        Busca en nombres, hipótesis y motivos de todas las revisiones
        conservadas. El estado corresponde a esa revisión, incluso si la
        candidata cambió después.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setFilter({ q: draft.trim(), status });
          setOffset(0);
        }}
      >
        <div className="form-grid">
          <Field label="Texto de búsqueda">
            <Input
              maxLength={200}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
          </Field>
          <Field label="Estado de la revisión">
            <Choice
              label="Estado de la revisión"
              value={status || 'all'}
              options={[
                { value: 'all', label: 'Todos los estados' },
                ...Object.entries(labels).map(([value, label]) => ({
                  value,
                  label,
                })),
              ]}
              onChange={(v) => setStatus(v === 'all' ? '' : v)}
            />
          </Field>
        </div>
        <Button type="submit" variant="outline">
          Buscar revisiones
        </Button>
      </form>
      <QueryStatus label="Resultados de búsqueda" query={query} />
      <DataTable
        heads={[
          'Seleccionar',
          'Candidata y revisión',
          'Estado y fecha',
          'Hipótesis',
          'Motivo',
        ]}
        rows={(query.data?.items ?? []).map((r) => [
          <input
            type="checkbox"
            key={r.id}
            aria-label={`Comparar ${r.name} revisión ${r.revision}`}
            checked={selected.some((s) => key(s) === r.id)}
            disabled={
              busy ||
              (selected.length >= 4 && !selected.some((s) => key(s) === r.id))
            }
            onChange={(e) => {
              setReport(null);
              if (e.target.checked)
                setSelected([
                  ...selected,
                  {
                    candidate_id: r.candidate_id,
                    revision: r.revision,
                    name: r.name,
                  },
                ]);
              else remove(r.id);
            }}
          />,
          `${r.name} · r${r.revision}`,
          `${labels[r.status]} · ${dateTime(r.created_at)}`,
          r.hypothesis,
          r.reason,
        ])}
      />
      <div className="actions">
        <Button
          variant="outline"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Resultados anteriores
        </Button>
        <Button
          variant="outline"
          disabled={(query.data?.items.length ?? 0) < 20}
          onClick={() => setOffset(offset + 20)}
        >
          Más resultados
        </Button>
      </div>
      <p>
        {selected.length} de 4 revisiones seleccionadas. La selección se
        conserva al buscar en otra página.
      </p>
      <div className="actions">
        {selected.map((r) => (
          <Button
            key={key(r)}
            variant="outline"
            disabled={busy}
            onClick={() => remove(key(r))}
          >
            Quitar {r.name} r{r.revision}
          </Button>
        ))}
      </div>
      <Button
        disabled={busy || selected.length < 2}
        onClick={() =>
          void run(async () => {
            setReport(null);
            const value = await api<CandidateComparison>(
              '/lab/candidates/compare',
              {
                items: selected.map(({ candidate_id, revision }) => ({
                  candidate_id,
                  revision,
                })),
              },
            );
            setReport(value);
          })
        }
      >
        {busy ? 'Comparando…' : 'Comparar revisiones seleccionadas'}
      </Button>
      {report && (
        <section aria-label="Comparación de revisiones">
          <h3>
            {report.same_context
              ? 'Mismo contexto de desarrollo'
              : 'Contextos distintos o evidencia insuficiente'}
          </h3>
          {report.warnings.map((w) => (
            <p className="muted" key={w}>
              {w}
            </p>
          ))}
          <DataTable
            heads={[
              'Revisión',
              'Informe y SMA',
              'Fuente y periodo',
              'SMA neta',
              'Comprar y mantener',
              'Efectivo',
              'Prueba final capturada',
            ]}
            numericColumns={[3, 4, 5]}
            rows={report.items.flatMap((r) =>
              r.evidence.map((e) => [
                `${r.name} · r${r.revision}`,
                `${e.protocol.name} · ${e.protocol.fast}/${e.protocol.slow}`,
                <span key={e.protocol.id}>
                  v{e.protocol.series_version} · {date(e.protocol.start_date)} →
                  antes de {date(e.protocol.holdout_date)}
                  <br />
                  <span className="mono" title={e.protocol.series_id}>
                    Serie {e.protocol.series_id.slice(0, 10)}…
                  </span>
                </span>,
                percent(
                  e.development_metrics.find((m) => m.name === 'SMA')
                    ?.return_pct,
                ),
                percent(
                  e.development_metrics.find(
                    (m) => m.name === 'Comprar y mantener',
                  )?.return_pct,
                ),
                percent(
                  e.development_metrics.find((m) => m.name === 'Efectivo')
                    ?.return_pct,
                ),
                e.holdout_hash ? 'Incluida en la revisión' : 'No incluida',
              ]),
            )}
          />
          {report.items.map((r) => (
            <div key={r.id} className="candidate-revision-note">
              <h4>
                {r.name} · r{r.revision} · {labels[r.status]}
              </h4>
              <p>{r.hypothesis}</p>
              <p>{r.reason}</p>
              {!r.evidence.length && (
                <p className="notice">
                  Sin informes capturados en esta revisión.
                </p>
              )}
            </div>
          ))}
          <h4>Condiciones económicas de desarrollo</h4>
          <DataTable
            heads={[
              'Informe / revisión',
              'Capital EUR',
              'Comisión fija EUR',
              'Comisión (pb)',
              'Deslizamiento (pb)',
              'Límite de exposición',
              'Lote',
            ]}
            rows={report.contexts.map((c) => [
              `${report.items.find((r) => r.id === c.revision_id)?.name} r${report.items.find((r) => r.id === c.revision_id)?.revision} · ${report.items.flatMap((r) => r.evidence).find((e) => e.protocol.id === c.protocol_id)?.protocol.name}`,
              c.config.initial_cash_eur,
              c.config.fixed_fee_eur,
              c.config.fee_bps,
              c.config.slippage_bps,
              percent(
                c.config.max_position_weight == null
                  ? null
                  : String(Number(c.config.max_position_weight) * 100),
              ),
              c.config.quantity_step,
            ])}
          />
          <details className="details">
            <summary>Contextos y huella de la comparación</summary>
            {report.contexts.map((c) => (
              <p
                className="mono native-hash"
                key={`${c.revision_id}:${c.protocol_id}`}
              >
                {c.revision_id} · {c.protocol_id} · {c.context_hash}
              </p>
            ))}
            <p className="mono native-hash">{report.comparison_hash}</p>
          </details>
        </section>
      )}
    </section>
  );
}
