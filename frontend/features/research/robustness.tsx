'use client';
import { useState } from 'react';
import type {
  CandidateRevision,
  RobustnessHistory,
  RobustnessReport,
  RobustnessReproduction,
} from '@/lib/api-types';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Choice, DataTable, Field } from '@/shared/ui';
import { useAction } from '@/shared/use-action';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { date, dateTime, number } from '@/shared/format';

const direction = {
  positive: 'Positivo',
  negative: 'Negativo',
  uncertain: 'Incluye cero',
};
const pp = (value: string | null | undefined) =>
  value == null
    ? 'No disponible'
    : number(Number(value), { maximumFractionDigits: 12 });

export function RobustnessDisclosure(props: {
  candidate: CandidateRevision;
  onError: (message: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="details"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>Robustez estadística del desarrollo</summary>
      {open && <RobustnessPanel {...props} />}
    </details>
  );
}

export function RobustnessResult({ report }: { report: RobustnessReport }) {
  const result = report.result;
  return (
    <section
      aria-label="Informe de robustez estadística"
      className="research-result"
    >
      <div className="panel-heading">
        <h3>Incertidumbre del exceso diario</h3>
        <span className="tag neutral">
          {result.status === 'exploratory' ? 'Exploratorio' : 'No evaluable'}
        </span>
      </div>
      <p>
        {report.protocol.name} · revisión {report.request.revision} de la
        candidata · {dateTime(report.created_at)}
      </p>
      <p>{report.request.reason}</p>
      <p>
        {result.intervals} intervalos posteriores a {result.warmup_sessions}{' '}
        sesiones de calentamiento.
        {result.start_date && result.end_date && (
          <>
            {' '}
            Del {date(result.start_date)} al {date(result.end_date)}.
          </>
        )}
      </p>
      {result.reasons.map((reason) => (
        <p className="notice" key={reason}>
          {reason}
        </p>
      ))}
      {result.status === 'exploratory' && (
        <>
          <p>
            Media del exceso SMA menos comprar/mantener:{' '}
            <strong>{pp(result.mean_excess_pp)} pp diarios</strong>.
          </p>
          <DataTable
            heads={[
              'Bloque esperado',
              'Especificación',
              'Límite inferior 95 % nominal',
              'Límite superior 95 % nominal',
              'Dirección',
            ]}
            numericColumns={[0, 2, 3]}
            rows={result.lengths.map((l) => [
              `${l.length} sesiones`,
              l.principal ? 'Principal' : 'Sensibilidad',
              `${pp(l.lower_pp)} pp/día`,
              `${pp(l.upper_pp)} pp/día`,
              direction[l.direction],
            ])}
          />
          <p>
            {result.principal_includes_zero
              ? 'El intervalo principal incluye cero: dirección incierta.'
              : 'El intervalo principal excluye cero bajo esta especificación exploratoria.'}{' '}
            {result.direction_changes
              ? 'La dirección cambia con la longitud del bloque.'
              : 'La dirección coincide en las tres longitudes.'}
          </p>
        </>
      )}
      <details className="details">
        <summary>Contexto económico y ensayos declarados</summary>
        <p>
          Capital {pp(report.config.initial_cash_eur)} EUR · peso configurado{' '}
          {pp(report.config.strategy_weight)} · límite de posición{' '}
          {pp(report.config.max_position_weight)}.
        </p>
        <p>
          Comisión fija {report.config.fixed_fee_eur} EUR · proporcional{' '}
          {report.config.fee_bps} pb · deslizamiento{' '}
          {report.config.slippage_bps} pb.
        </p>
        <DataTable
          heads={[
            'Cuenta',
            'Rentabilidad del desarrollo',
            'Caída máxima',
            'Operaciones',
            'Comisiones EUR',
          ]}
          numericColumns={[1, 2, 3, 4]}
          rows={report.metrics.map((m) => [
            m.name,
            pp(m.return_pct),
            pp(m.max_drawdown_pct),
            m.fills,
            pp(m.fees_eur),
          ])}
        />
        <p>
          {report.rejected} ejecuciones rechazadas y {report.expired} expiradas.
          Las rentabilidades y caídas de esta tabla están en % y abarcan el
          desarrollo completo.
        </p>
        <ul>
          {report.trials.map((trial) => (
            <li key={trial.protocol_id}>
              {trial.name}
              <span className="mono native-hash"> · {trial.protocol_id}</span>
            </li>
          ))}
        </ul>
        {new Set(report.trials.map((t) => t.context_hash)).size > 1 && (
          <p className="notice">
            Los ensayos declarados tienen contextos económicos distintos; no se
            agregan ni comparan sus intervalos.
          </p>
        )}
      </details>
      <details className="details">
        <summary>Método y reproducción</summary>
        <p>
          Bootstrap estacionario pareado · 5.000 réplicas por longitud · PCG64 ·
          NumPy {result.numpy_version} · semilla maestra {result.master_seed}.
        </p>
        <p>
          Percentiles bilaterales 95 % con interpolación lineal. Entorno
          registrado: {report.platform}, Python {report.python_version}.
        </p>
        <p className="mono native-hash">Informe: {report.report_hash}</p>
        <p className="mono native-hash">
          Desarrollo:{' '}
          {
            report.trials.find(
              (t) => t.protocol_id === report.request.protocol_id,
            )?.development_hash
          }
        </p>
        <p className="mono native-hash">NAV: {result.nav_hash}</p>
        {result.returns_hash && (
          <p className="mono native-hash">Retornos: {result.returns_hash}</p>
        )}
        {result.lengths.map((l) => (
          <p className="mono native-hash" key={l.length}>
            L={l.length} · semilla {l.seed} · índices {l.indices_hash}
          </p>
        ))}
      </details>
      <ul className="muted">
        {result.warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  );
}

export function RobustnessPanel({
  candidate,
  onError,
}: {
  candidate: CandidateRevision;
  onError: (message: string) => void;
}) {
  const [protocol, setProtocol] = useState(
    candidate.evidence[0]?.protocol.id ?? '',
  );
  const [reason, setReason] = useState('');
  const [acknowledged, setAcknowledged] = useState(false);
  const [offset, setOffset] = useState(0);
  const history = useRead<RobustnessHistory>({
    path: `/lab/robustness?candidate_id=${candidate.candidate_id}&offset=${offset}&limit=20`,
  });
  const [report, setReport] = useState<RobustnessReport | null>(null);
  const [reproduction, setReproduction] = useState('');
  const { busy, run } = useAction(onError);
  const eligible = candidate.evidence.some((e) => e.protocol.id === protocol);
  async function calculate() {
    if (!eligible || !acknowledged || reason.trim().length < 10) return;
    const result = await api<RobustnessReport>('/lab/robustness', {
      protocol_id: protocol,
      candidate_id: candidate.candidate_id,
      revision: candidate.revision,
      revision_hash: candidate.revision_hash,
      related_protocol_ids: candidate.protocol_ids,
      reason: reason.trim(),
      acknowledge_exploratory: true,
    });
    setReport(result);
    setReproduction('');
    await history.refresh();
  }
  return (
    <section
      aria-label="Robustez estadística"
      className="research-result robustness-panel"
    >
      <h3>Robustez estadística del desarrollo</h3>
      <p className="muted">
        Estima la incertidumbre de una SMA fija frente a comprar/mantener.
        Necesita 504 intervalos completos después del calentamiento. Conserva un
        informe independiente; la prueba final permanece fuera del cálculo.
      </p>
      <form
        aria-label="Calcular robustez"
        onSubmit={(e) => {
          e.preventDefault();
          if (eligible && acknowledged && reason.trim().length >= 10)
            void run(calculate);
        }}
      >
        <fieldset disabled={busy} className="simulation-fields">
          <Field label="Protocolo para robustez">
            <Choice
              label="Protocolo para robustez"
              value={protocol}
              options={candidate.evidence.map((e) => ({
                value: e.protocol.id,
                label: e.protocol.name,
              }))}
              onChange={setProtocol}
            />
          </Field>
          {!eligible && (
            <p className="notice">
              Vincula un protocolo calculado a la candidata antes de consultar
              su robustez.
            </p>
          )}
          <Field label="Motivo de la consulta estadística">
            <Textarea
              required
              minLength={10}
              maxLength={2000}
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </Field>
          <p>
            Ensayos relacionados declarados en esta revisión:{' '}
            {candidate.protocol_ids.length}.
          </p>
          <ul>
            {candidate.evidence.map((e) => (
              <li key={e.protocol.id}>{e.protocol.name}</li>
            ))}
          </ul>
          <label className="check-row">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />
            Declaro estos ensayos relacionados y entiendo que el intervalo es
            exploratorio, sin ajuste por selección ni autorización de
            operaciones.
          </label>
          <Button
            type="submit"
            disabled={
              busy || !eligible || !acknowledged || reason.trim().length < 10
            }
          >
            {busy ? 'Calculando…' : 'Calcular y guardar robustez'}
          </Button>
        </fieldset>
      </form>
      <QueryStatus label="Informes estadísticos" query={history} />
      {(history.data?.items ?? []).map((item) => (
        <Button
          key={item.id}
          variant="outline"
          className="robustness-history-entry"
          disabled={busy}
          onClick={() => {
            setReport(item);
            setReproduction('');
          }}
        >
          <span>
            Consultar robustez · {item.protocol.name} · revisión{' '}
            {item.request.revision} · {dateTime(item.created_at)}
          </span>
        </Button>
      ))}
      <div className="actions">
        <Button
          variant="outline"
          disabled={busy || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Informes anteriores
        </Button>
        <Button
          variant="outline"
          disabled={busy || (history.data?.items.length ?? 0) < 20}
          onClick={() => setOffset(offset + 20)}
        >
          Más informes estadísticos
        </Button>
      </div>
      {report && (
        <>
          <RobustnessResult report={report} />
          <Button
            variant="outline"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                const result = await api<RobustnessReproduction>(
                  `/lab/robustness/${report.id}/reproduce`,
                  {},
                );
                setReproduction(
                  (result.matches
                    ? 'Reproducción coincidente: instantánea y resultado conservados.'
                    : 'La reproducción no coincide con el informe guardado.') +
                    ' ' +
                    result.warnings.join(' '),
                );
              })
            }
          >
            Comprobar reproducción estadística
          </Button>
          <output>{reproduction}</output>
        </>
      )}
    </section>
  );
}
