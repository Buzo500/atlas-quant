'use client';

import { useState } from 'react';
import type {
  CatalogResponse,
  TargetSpec,
  TargetRow,
  TargetHistory,
  TargetPreview,
  TargetReport,
  TargetReports,
  TargetReportPreview,
  ValuationHistory,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Choice, DataTable, Field } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useCorporateReview } from '@/features/data/corporate-shared';
import { ValuationDetails, reasonText } from './native-valuation';

const labels: Record<string, string> = {
  below_band: 'Por debajo de la banda',
  above_band: 'Por encima de la banda',
  concentration_exceeded: 'Supera el límite de concentración',
  no_target: 'Sin objetivo definido',
  non_positive_nav: 'El patrimonio debe ser positivo para calcular pesos',
};
const reason = (code: string) => labels[code] || reasonText(code);
const status = {
  complete: 'Completo',
  provisional: 'Escenario provisional',
  unavailable: 'No disponible',
};
const blank = (instrument_id: string | null): TargetRow => ({
  instrument_id,
  weight: '',
  minimum: '',
  maximum: '',
  concentration_limit: '',
});
const fields = [
  ['weight', 'Objetivo'],
  ['minimum', 'Mínimo'],
  ['maximum', 'Máximo'],
  ['concentration_limit', 'Límite'],
] as const;

function amount(value: string | null, digits: number, suffix: string) {
  return value === null ? (
    'No disponible'
  ) : (
    <data value={value} title={value}>
      {new Intl.NumberFormat('es-ES', { maximumFractionDigits: digits }).format(
        Number(value),
      )}
      {suffix}
    </data>
  );
}

function SpecTable({
  spec,
  catalog,
}: {
  spec: TargetSpec;
  catalog?: CatalogResponse;
}) {
  return (
    <DataTable
      heads={['Instrumento', 'Objetivo %', 'Mínimo %', 'Máximo %', 'Límite %']}
      numericColumns={[1, 2, 3, 4]}
      rows={spec.rows.map((r) => [
        r.instrument_id
          ? catalog?.instruments.find((i) => i.id === r.instrument_id)?.name ||
            r.instrument_id
          : 'Efectivo',
        ...fields.map(([key]) => r[key]),
      ])}
    />
  );
}

export function TargetReportDetails({ report }: { report: TargetReport }) {
  return (
    <section aria-label="Diagnóstico de objetivos">
      <h3>
        {report.target.spec.name} · v{report.target.version} ·{' '}
        {status[report.status]}
      </h3>
      <p className="muted">
        Cierre {report.cut.as_of_date} · Patrimonio{' '}
        {report.cut.value ?? 'no disponible'} EUR.{' '}
        {!report.saved
          ? 'Se comprobará el contexto de nuevo al guardar.'
          : report.current
            ? 'Contexto vigente en la última consulta.'
            : 'Contexto cambiado: diagnóstico histórico conservado.'}
      </p>
      {!!report.reasons.length && (
        <p className="notice">{report.reasons.map(reason).join('. ')}.</p>
      )}
      <p className="muted">
        La desviación es valor actual menos valor objetivo: positiva indica
        exceso y negativa, déficit. Las cotizaciones y derechos pendientes del
        mismo instrumento se suman. Los derechos no son efectivo disponible.
      </p>
      <DataTable
        heads={[
          'Instrumento',
          'Valor EUR',
          'Peso %',
          'Objetivo %',
          'Banda %',
          'Límite %',
          'Desviación pp',
          'Desviación EUR',
          'Diagnóstico',
        ]}
        numericColumns={[1, 2, 3, 5, 6, 7]}
        rows={report.rows.map((r) => [
          r.label,
          amount(r.value_eur, 2, ''),
          amount(r.weight, 4, ''),
          r.target_weight,
          r.minimum === null ? 'Sin definir' : `${r.minimum}–${r.maximum}`,
          r.concentration_limit ?? 'Sin definir',
          amount(r.deviation_pp, 4, ''),
          amount(r.deviation_eur, 2, ''),
          r.reasons.length
            ? r.reasons.map(reason).join('. ')
            : report.status === 'unavailable'
              ? 'No evaluable'
              : 'Dentro de banda',
        ])}
      />
      <details className="details">
        <summary>Efectivo, derechos y recursos</summary>
        <DataTable
          heads={['Moneda', 'Efectivo nativo', 'Valor EUR']}
          rows={report.resources.cash.map((c) => [
            c.currency,
            c.native_amount ?? 'No disponible',
            amount(c.eur_value, 2, ''),
          ])}
        />
        <DataTable
          heads={['Instrumento', 'Derechos pendientes EUR']}
          rows={report.rows
            .filter((r) => r.instrument_id && r.receivable_eur !== '0')
            .map((r) => [r.label, amount(r.receivable_eur, 2, '')])}
        />
        <p className="muted">
          Recursos comprometidos no disponibles: ATLAS aún no tiene un gestor de
          órdenes ni reservas. Este diagnóstico no propone ni envía operaciones.
        </p>
      </details>
      <details className="details">
        <summary>Patrimonio y fuentes del diagnóstico</summary>
        <ValuationDetails cut={report.cut} />
      </details>
    </section>
  );
}

type Props = {
  portfolioId: string;
  revision: number;
  auditSequence?: number;
  active: boolean;
};

export function TargetsWorkspace({
  portfolioId,
  revision,
  auditSequence,
  active,
}: Props) {
  const base = `/v2/portfolios/${portfolioId}`;
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [rows, setRows] = useState<TargetRow[]>([blank(null)]);
  const [instrument, setInstrument] = useState('');
  const [offset, setOffset] = useState(0);
  const [cutOffset, setCutOffset] = useState(0);
  const [reportOffset, setReportOffset] = useState(0);
  const [cut, setCut] = useState('');
  const [selectedReport, setSelectedReport] = useState('');
  const history = useRead<TargetHistory>({
    path: `${base}/targets?offset=${offset}&limit=20`,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const catalog = useRead<CatalogResponse>({
    path: '/catalog',
    revision: auditSequence,
    enabled: active,
  });
  const cuts = useRead<ValuationHistory>({
    path: `${base}/valuations?offset=${cutOffset}&limit=20`,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const reports = useRead<TargetReports>({
    path: `${base}/target-reports?offset=${reportOffset}&limit=20`,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const saved = useRead<TargetReport>({
    path: selectedReport ? `${base}/target-reports/${selectedReport}` : null,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const draft = useCorporateReview<TargetPreview>(
    `${base}/targets`,
    history.refresh,
    setError,
  );
  const activation = useCorporateReview<TargetPreview>(
    `${base}/targets/activate`,
    history.refresh,
    setError,
  );
  const evaluation = useCorporateReview<TargetReportPreview>(
    `${base}/target-reports`,
    reports.refresh,
    setError,
  );
  const head = history.data;
  const context = {
    expected_revision: revision,
    expected_targets_revision: head?.revision ?? 0,
  };
  const busy = draft.busy || activation.busy || evaluation.busy;
  const currentPreview =
    evaluation.preview &&
    evaluation.preview.report.target.id === head?.active?.id
      ? evaluation.preview
      : null;
  const report =
    currentPreview?.report ??
    (selectedReport && saved.data?.id === selectedReport ? saved.data : null);
  const edit = () => {
    draft.invalidate();
    activation.invalidate();
    setError('');
  };
  const allowed =
    catalog.data?.instruments.filter(
      (i) => !rows.some((r) => r.instrument_id === i.id),
    ) ?? [];
  return (
    <>
      <QueryStatus label="Objetivos de cartera" query={history} />
      <QueryStatus label="Catálogo de objetivos" query={catalog} />
      {error && (
        <p className="notice" role="alert">
          {error}
        </p>
      )}
      {head && (
        <>
          <h3>
            {head.active
              ? `Activo: ${head.active.spec.name} · v${head.active.version}`
              : 'Sin objetivos activos'}
          </h3>
          {head.active && (
            <SpecTable
              spec={head.active.spec}
              catalog={catalog.data ?? undefined}
            />
          )}
          <details className="details">
            <summary>Crear o editar un borrador de objetivos</summary>
            <p className="muted">
              Introduce tus porcentajes. Incluye efectivo; deben sumar
              exactamente 100. Mínimo ≤ objetivo ≤ máximo ≤ límite. Las bandas
              se expresan en puntos porcentuales absolutos.
            </p>
            {head.active && (
              <Button
                variant="outline"
                onClick={() => {
                  edit();
                  setName(head.active!.spec.name);
                  setRows(head.active!.spec.rows.map((r) => ({ ...r })));
                }}
              >
                Copiar objetivos activos al borrador
              </Button>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void draft.review({ ...context, spec: { name, rows } });
              }}
            >
              <Field label="Nombre de los objetivos">
                <Input
                  required
                  maxLength={120}
                  value={name}
                  onChange={(e) => {
                    edit();
                    setName(e.target.value);
                  }}
                />
              </Field>
              <div className="targets-editor">
                {rows.map((r, index) => {
                  const label = r.instrument_id
                    ? catalog.data?.instruments.find(
                        (i) => i.id === r.instrument_id,
                      )?.name || r.instrument_id
                    : 'Efectivo';
                  return (
                    <fieldset
                      className="target-edit-row"
                      key={r.instrument_id ?? 'cash'}
                    >
                      <legend>{label}</legend>
                      {fields.map(([key, title]) => (
                        <Field key={key} label={`${title} % · ${label}`}>
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="0.000001"
                            required
                            value={r[key]}
                            onChange={(e) => {
                              edit();
                              setRows(
                                rows.map((old, n) =>
                                  n === index
                                    ? { ...old, [key]: e.target.value }
                                    : old,
                                ),
                              );
                            }}
                          />
                        </Field>
                      ))}
                      {r.instrument_id && (
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => {
                            edit();
                            setRows(rows.filter((_, n) => n !== index));
                          }}
                        >
                          Quitar {label}
                        </Button>
                      )}
                    </fieldset>
                  );
                })}
              </div>
              <div className="form-grid">
                <Choice
                  label="Instrumento para objetivos"
                  value={instrument}
                  onChange={setInstrument}
                  options={allowed.map((i) => ({ value: i.id, label: i.name }))}
                />
                <Button
                  type="button"
                  variant="outline"
                  disabled={
                    !allowed.some((i) => i.id === instrument) ||
                    rows.length >= 200
                  }
                  onClick={() => {
                    edit();
                    setRows([...rows, blank(instrument)]);
                    setInstrument('');
                  }}
                >
                  Añadir instrumento
                </Button>
                <Button
                  type="submit"
                  disabled={busy || !catalog.data || history.loading}
                >
                  Revisar borrador
                </Button>
              </div>
            </form>
            {draft.preview && (
              <>
                <h3>Borrador revisado · v{draft.preview.target.version}</h3>
                <SpecTable
                  spec={draft.preview.target.spec}
                  catalog={catalog.data ?? undefined}
                />
                <Button disabled={busy} onClick={() => void draft.confirm()}>
                  Guardar borrador
                </Button>
              </>
            )}
            {draft.message && <output>{draft.message}</output>}
          </details>
          <details className="details">
            <summary>Versiones y activación</summary>
            <DataTable
              heads={['Versión', 'Nombre', 'Creado', 'Estado', 'Acción']}
              rows={head.targets.map((t) => [
                t.version,
                t.spec.name,
                t.created_at.slice(0, 10),
                t.id === head.active?.id ? 'Activo' : 'Guardado',
                <Button
                  key={t.id}
                  variant="outline"
                  disabled={busy || history.loading || t.id === head.active?.id}
                  onClick={() => {
                    evaluation.invalidate();
                    setSelectedReport('');
                    void activation.review({ ...context, target_id: t.id });
                  }}
                >
                  Revisar activación v{t.version}
                </Button>,
              ])}
            />
            <div className="actions">
              <Button
                variant="outline"
                disabled={offset === 0 || history.loading}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Versiones recientes
              </Button>
              <Button
                variant="outline"
                disabled={head.targets.length < 20 || history.loading}
                onClick={() => setOffset(offset + 20)}
              >
                Versiones anteriores
              </Button>
            </div>
            {activation.preview && (
              <>
                <h3>
                  Activar {activation.preview.target.spec.name} · v
                  {activation.preview.target.version}
                </h3>
                <SpecTable
                  spec={activation.preview.target.spec}
                  catalog={catalog.data ?? undefined}
                />
                <p className="notice">
                  Sustituye los objetivos activos para futuros diagnósticos. Se
                  conserva el historial.
                </p>
                <Button
                  disabled={busy}
                  onClick={() => void activation.confirm()}
                >
                  Confirmar activación de objetivos
                </Button>
              </>
            )}
            {activation.message && <output>{activation.message}</output>}
          </details>
          <h3>Diagnóstico sobre un corte guardado</h3>
          <QueryStatus label="Cortes para objetivos" query={cuts} />
          <div className="form-grid">
            <Choice
              label="Corte para diagnóstico"
              value={cut}
              onChange={(v) => {
                evaluation.invalidate();
                setSelectedReport('');
                setCut(v);
              }}
              options={(cuts.data?.cuts ?? []).map((c) => ({
                value: c.id,
                label: `${c.as_of_date} · r${c.portfolio_revision} · ${c.value ?? 'incompleto'} EUR · ${c.id.slice(0, 6)}`,
              }))}
            />
            <Button
              disabled={busy || !cut || !head.active || history.loading}
              onClick={() => {
                setSelectedReport('');
                void evaluation.review({ ...context, cut_id: cut });
              }}
            >
              Calcular desviaciones
            </Button>
          </div>
          <p className="muted">
            Primero calcula y guarda un patrimonio vigente en «Patrimonio en
            EUR». Un corte incompleto o no positivo no produce pesos globales.
          </p>
          <div className="actions">
            <Button
              variant="outline"
              disabled={cutOffset === 0 || cuts.loading}
              onClick={() => setCutOffset(Math.max(0, cutOffset - 20))}
            >
              Cortes recientes
            </Button>
            <Button
              variant="outline"
              disabled={(cuts.data?.cuts.length ?? 0) < 20 || cuts.loading}
              onClick={() => setCutOffset(cutOffset + 20)}
            >
              Cortes anteriores para objetivos
            </Button>
          </div>
        </>
      )}
      {report && <TargetReportDetails report={report} />}
      {currentPreview && (
        <Button disabled={busy} onClick={() => void evaluation.confirm()}>
          Guardar diagnóstico
        </Button>
      )}
      {evaluation.message && <output>{evaluation.message}</output>}
      <details className="details">
        <summary>Diagnósticos guardados</summary>
        <QueryStatus label="Historial de objetivos" query={reports} />
        {selectedReport && (
          <QueryStatus label="Diagnóstico guardado" query={saved} />
        )}
        {reports.data && (
          <>
            <DataTable
              heads={['Cierre', 'Objetivos', 'Estado', 'Acción']}
              rows={reports.data.reports.map((r) => [
                r.as_of_date,
                `v${r.target_version}`,
                status[r.status],
                <Button
                  key={r.id}
                  variant="outline"
                  onClick={() => {
                    evaluation.invalidate();
                    setSelectedReport(r.id);
                  }}
                >
                  Consultar diagnóstico {r.as_of_date}
                </Button>,
              ])}
            />
            <div className="actions">
              <Button
                variant="outline"
                disabled={reportOffset === 0 || reports.loading}
                onClick={() => setReportOffset(Math.max(0, reportOffset - 20))}
              >
                Diagnósticos recientes
              </Button>
              <Button
                variant="outline"
                disabled={reports.data.reports.length < 20 || reports.loading}
                onClick={() => setReportOffset(reportOffset + 20)}
              >
                Diagnósticos anteriores
              </Button>
            </div>
          </>
        )}
      </details>
    </>
  );
}

export function NativeTargets(props: Props) {
  const [open, setOpen] = useState(false);
  const [visited, setVisited] = useState(false);
  return (
    <section
      className="panel native-targets"
      aria-label="Objetivos y desviaciones"
    >
      <div className="panel-heading">
        <h2>Objetivos y desviaciones</h2>
        <span className="tag neutral">Planificación manual</span>
      </div>
      <p className="muted">
        Define pesos, bandas y límites. Consulta el diagnóstico con precios y
        divisas identificados.
      </p>
      <details
        className="details"
        onToggle={(e) => {
          setOpen(e.currentTarget.open);
          if (e.currentTarget.open) setVisited(true);
        }}
      >
        <summary>Consultar y editar objetivos</summary>
        {visited && (
          <TargetsWorkspace {...props} active={props.active && open} />
        )}
      </details>
    </section>
  );
}
