'use client';
import { useState } from 'react';
import { api } from '@/lib/api';
import type {
  CandidateHistory,
  CandidateInput,
  CandidateRevision,
  CandidateRevisions,
  LabHistory,
} from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Choice, DataTable, Field } from '@/shared/ui';
import { useRead } from '@/shared/use-read';
import { useAction } from '@/shared/use-action';
import { QueryStatus } from '@/shared/query-status';
import { dateTime, number } from '@/shared/format';
import { CandidateBrowser } from './candidate-browser';
import { RobustnessDisclosure } from './robustness';

const statuses = [
  { value: 'researching', label: 'En investigación' },
  { value: 'watchlist', label: 'En seguimiento' },
  { value: 'discarded', label: 'Descartada' },
];
const statusLabel = (status: string) =>
  statuses.find((s) => s.value === status)?.label ?? status;
const empty: CandidateInput = {
  name: '',
  hypothesis: '',
  reason: '',
  status: 'researching',
  protocol_ids: [],
};

function CandidateEditor({
  initial,
  busy,
  onSave,
  onCancel,
}: {
  initial: CandidateRevision | null;
  busy: boolean;
  onSave: (draft: CandidateInput) => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<CandidateInput>(
    initial
      ? {
          name: initial.name,
          hypothesis: initial.hypothesis,
          status: initial.status,
          reason: '',
          protocol_ids: initial.protocol_ids,
        }
      : empty,
  );
  const [offset, setOffset] = useState(0);
  const protocols = useRead<LabHistory>({
    path: `/lab/protocols?offset=${offset}&limit=20`,
  });
  return (
    <form
      aria-label={initial ? 'Revisar candidata' : 'Nueva candidata'}
      onSubmit={(e) => {
        e.preventDefault();
        onSave(draft);
      }}
    >
      <fieldset disabled={busy} className="simulation-fields">
        <h3>
          {initial
            ? `Nueva revisión de ${initial.name}`
            : 'Nueva hipótesis de investigación'}
        </h3>
        <p className="muted">
          Guardar crea una revisión inmutable. Captura los informes vinculados
          disponibles ahora; conserva todas las revisiones anteriores. Un estado
          de seguimiento no autoriza operaciones.
        </p>
        <div className="form-grid">
          <Field label="Nombre de la candidata">
            <Input
              required
              minLength={3}
              maxLength={100}
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </Field>
          <Field label="Estado de investigación">
            <Choice
              label="Estado de investigación"
              value={draft.status ?? 'researching'}
              options={statuses}
              onChange={(value) =>
                setDraft({
                  ...draft,
                  status: value as CandidateInput['status'],
                })
              }
            />
          </Field>
        </div>
        <Field label="Hipótesis">
          <Textarea
            required
            minLength={10}
            maxLength={2000}
            rows={3}
            value={draft.hypothesis}
            onChange={(e) => setDraft({ ...draft, hypothesis: e.target.value })}
          />
        </Field>
        <Field label="Motivo y limitaciones de esta revisión">
          <Textarea
            required
            minLength={10}
            maxLength={2000}
            rows={3}
            value={draft.reason}
            onChange={(e) => setDraft({ ...draft, reason: e.target.value })}
          />
        </Field>
        <p className="muted">
          {draft.protocol_ids?.length ?? 0} de 20 informes vinculados. Los
          anteriores no se eliminan; explica los resultados desfavorables o el
          descarte en el motivo. Registrar después de calcular no es
          preregistrar una hipótesis.
        </p>
        <QueryStatus label="Protocolos para vincular" query={protocols} />
        {(protocols.data?.items ?? []).map((p) => (
          <label className="check-row" key={p.id}>
            <input
              type="checkbox"
              checked={draft.protocol_ids?.includes(p.id) ?? false}
              disabled={busy || initial?.protocol_ids.includes(p.id)}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  protocol_ids: e.target.checked
                    ? [...(draft.protocol_ids ?? []), p.id]
                    : draft.protocol_ids?.filter((id) => id !== p.id),
                })
              }
            />
            {p.name} · SMA {p.fast}/{p.slow} ·{' '}
            {p.opened ? 'Prueba final abierta' : 'Prueba final reservada'}
          </label>
        ))}
        <div className="actions">
          <Button
            variant="outline"
            disabled={busy || offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 20))}
          >
            Protocolos anteriores
          </Button>
          <Button
            variant="outline"
            disabled={busy || (protocols.data?.items.length ?? 0) < 20}
            onClick={() => setOffset(offset + 20)}
          >
            Más protocolos
          </Button>
          <Button type="submit" disabled={busy}>
            {busy
              ? 'Guardando…'
              : initial
                ? 'Guardar nueva revisión'
                : 'Registrar candidata'}
          </Button>
          <Button variant="outline" disabled={busy} onClick={onCancel}>
            Cancelar edición
          </Button>
        </div>
      </fieldset>
    </form>
  );
}

function RevisionEvidence({ value }: { value: CandidateRevision }) {
  return (
    <section aria-label={`Revisión ${value.revision} de ${value.name}`}>
      <h3>
        {value.name} · revisión {value.revision}
      </h3>
      <p>
        {statusLabel(value.status)} · {dateTime(value.created_at)}
      </p>
      <p>
        <strong>Hipótesis:</strong> {value.hypothesis}
      </p>
      <p>
        <strong>Motivo:</strong> {value.reason}
      </p>
      <DataTable
        heads={[
          'Informe',
          'SMA neta en desarrollo',
          'Validación capturada',
          'Prueba final capturada',
        ]}
        numericColumns={[1]}
        rows={value.evidence.map((e) => [
          e.protocol.name,
          e.development_metrics[0].return_pct === null
            ? 'No disponible'
            : `${number(Number(e.development_metrics[0].return_pct), { maximumFractionDigits: 3 })} %`,
          [
            e.walk_forward_hash ? 'Walk-forward' : '',
            e.sensitivity_hash ? 'Sensibilidad' : '',
          ]
            .filter(Boolean)
            .join(' · ') || 'Desarrollo',
          e.holdout_hash ? 'Incluida' : 'No incluida',
        ])}
      />
      <details className="details">
        <summary>Huellas de la evidencia de esta revisión</summary>
        {value.evidence.map((e) => (
          <div key={e.protocol.id}>
            <p className="mono native-hash">Protocolo: {e.protocol.id}</p>
            <p className="mono native-hash">Desarrollo: {e.development_hash}</p>
            {e.walk_forward_hash && (
              <p className="mono native-hash">
                Walk-forward: {e.walk_forward_hash}
              </p>
            )}
            {e.sensitivity_hash && (
              <p className="mono native-hash">
                Sensibilidad: {e.sensitivity_hash}
              </p>
            )}
            {e.holdout_hash && (
              <p className="mono native-hash">Prueba final: {e.holdout_hash}</p>
            )}
          </div>
        ))}
        <p className="mono native-hash">Revisión: {value.revision_hash}</p>
      </details>
    </section>
  );
}

export function Candidates({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const [offset, setOffset] = useState(0);
  const [browse, setBrowse] = useState(false);
  const history = useRead<CandidateHistory>({
    path: `/lab/candidates?offset=${offset}&limit=20`,
  });
  const [selected, setSelected] = useState('');
  const current = useRead<CandidateRevision>({
    path: selected ? `/lab/candidates/${selected}` : null,
  });
  const [revisionOffset, setRevisionOffset] = useState(0);
  const revisions = useRead<CandidateRevisions>({
    path: selected
      ? `/lab/candidates/${selected}/revisions?offset=${revisionOffset}&limit=20`
      : null,
  });
  const [published, setPublished] = useState<CandidateRevision | null>(null);
  const value = published?.candidate_id === selected ? published : current.data;
  const [editing, setEditing] = useState(false);
  const [editingSource, setEditingSource] = useState<CandidateRevision | null>(
    null,
  );
  const { busy, run } = useAction(onError);
  function choose(ident: string) {
    setSelected(ident);
    setPublished(null);
    setRevisionOffset(0);
    setEditing(false);
  }
  async function save(draft: CandidateInput) {
    const result = await api<CandidateRevision>(
      selected ? `/lab/candidates/${selected}/revisions` : '/lab/candidates',
      selected
        ? { ...draft, expected_revision: editingSource!.revision }
        : draft,
    );
    setSelected(result.candidate_id);
    setPublished(result);
    setEditing(false);
    setRevisionOffset(0);
    await history.refresh();
    await revisions.refresh();
  }
  return (
    <section className="panel" aria-label="Registro de candidatas">
      <div className="panel-heading">
        <h2>Registro de candidatas</h2>
        <span className="tag neutral">Investigación · sin órdenes</span>
      </div>
      <p className="muted">
        Conserva hipótesis, evidencia y motivos de seguimiento o descarte. Cada
        decisión crea una revisión; ninguna activa una estrategia.
      </p>
      <div className="actions">
        <Button
          disabled={busy || editing}
          onClick={() => {
            choose('');
            setEditingSource(null);
            setEditing(true);
          }}
        >
          Nueva candidata
        </Button>
        <Button
          variant="outline"
          disabled={busy || editing}
          onClick={() =>
            run(async () => {
              setPublished(null);
              setEditing(false);
              await history.refresh();
              await current.refresh();
              await revisions.refresh();
            })
          }
        >
          Actualizar candidatas
        </Button>
      </div>
      <QueryStatus label="Historial de candidatas" query={history} />
      <details
        className="details"
        onToggle={(e) => setBrowse(e.currentTarget.open)}
      >
        <summary>Buscar hipótesis, descartes y comparar revisiones</summary>
        {browse && <CandidateBrowser onError={onError} />}
      </details>
      <DataTable
        heads={['Candidata', 'Estado', 'Revisión', 'Informes', 'Detalle']}
        rows={(history.data?.items ?? []).map((c) => [
          c.name,
          statusLabel(c.status),
          c.revision,
          c.protocols,
          <Button
            key={c.id}
            variant="outline"
            disabled={busy || editing}
            onClick={() => choose(c.id)}
          >
            Ver candidata {c.name}
          </Button>,
        ])}
      />
      <div className="actions">
        <Button
          variant="outline"
          disabled={busy || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Candidatas anteriores
        </Button>
        <Button
          variant="outline"
          disabled={busy || (history.data?.items.length ?? 0) < 20}
          onClick={() => setOffset(offset + 20)}
        >
          Más candidatas
        </Button>
      </div>
      {selected && (
        <QueryStatus label="Candidata seleccionada" query={current} />
      )}
      {value && (
        <>
          <RevisionEvidence value={value} />
          <RobustnessDisclosure key={value.revision_hash} candidate={value} onError={onError} />
          <Button
            disabled={busy || editing || value.revision >= 100}
            onClick={() => {
              setEditingSource(value);
              setEditing(true);
            }}
          >
            Revisar candidata
          </Button>
          <details className="details">
            <summary>Revisiones conservadas</summary>
            <QueryStatus label="Revisiones de la candidata" query={revisions} />
            {(revisions.data?.items ?? []).map((v) => (
              <details className="details" key={v.id}>
                <summary>
                  Revisión {v.revision} · {statusLabel(v.status)}
                </summary>
                <RevisionEvidence value={v} />
              </details>
            ))}
            <div className="actions">
              <Button
                variant="outline"
                disabled={busy || revisionOffset === 0}
                onClick={() =>
                  setRevisionOffset(Math.max(0, revisionOffset - 20))
                }
              >
                Revisiones anteriores
              </Button>
              <Button
                variant="outline"
                disabled={busy || (revisions.data?.items.length ?? 0) < 20}
                onClick={() => setRevisionOffset(revisionOffset + 20)}
              >
                Más revisiones
              </Button>
            </div>
          </details>
        </>
      )}
      {editing && (!selected || value) && (
        <CandidateEditor
          key={`${selected}:${editingSource?.revision ?? 0}`}
          initial={editingSource}
          busy={busy}
          onSave={(draft) => void run(() => save(draft))}
          onCancel={() => setEditing(false)}
        />
      )}
    </section>
  );
}
