'use client';
import { SourcePrevalidation } from './source-preflight';
import { useState } from 'react';
import { api } from '@/lib/api';
import type {
  LabHistory,
  LabReport,
  LabReproduction,
  MarketCatalog,
  SimulationConfig,
} from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Choice, DataTable, Field } from '@/shared/ui';
import { useRead } from '@/shared/use-read';
import { useAction } from '@/shared/use-action';
import { QueryStatus } from '@/shared/query-status';
import { date } from '@/shared/format';

import { PeriodResult } from './simulation-result';
import {
  SensitivityEditor,
  SensitivityResult,
  initialSensitivity,
  sensitivityInput,
} from './sensitivity';
import {
  WalkForwardEditor,
  WalkForwardResult,
  initialWalkForward,
} from './walk-forward';

const initialConfig: SimulationConfig = {
  policy: 'sma-economics-eur-v1',
  initial_cash_eur: '10000',
  strategy_weight: '1',
  max_position_weight: '1',
  quantity_step: '1',
  fixed_fee_eur: '1',
  fee_bps: '5',
  slippage_bps: '5',
  purchases_enabled: true,
};
export function SimulationLab({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const sources = useRead<MarketCatalog>({ path: '/v2/market' });
  const [offset, setOffset] = useState(0);
  const history = useRead<LabHistory>({
    path: `/lab/protocols?offset=${offset}&limit=20`,
  });
  const [selected, setSelected] = useState('');
  const saved = useRead<LabReport>({
    path: selected ? `/lab/protocols/${selected}` : null,
  });
  const [published, setPublished] = useState<LabReport | null>(null);
  const report = published?.protocol.id === selected ? published : saved.data;
  const [sourceKey, setSourceKey] = useState('');
  const [name, setName] = useState('Mi protocolo SMA');
  const [start, setStart] = useState(''),
    [split, setSplit] = useState(''),
    [end, setEnd] = useState('');
  const [fast, setFast] = useState('20'),
    [slow, setSlow] = useState('50');
  const [sessions, setSessions] = useState('');
  const [openingSource, setOpeningSource] = useState(''),
    [eventSource, setEventSource] = useState('');
  const [reviewed, setReviewed] = useState(false),
    [acknowledged, setAcknowledged] = useState(false);
  const [config, setConfig] = useState(initialConfig);
  const [walkForward, setWalkForward] = useState(initialWalkForward);
  const [withWalkForward, setWithWalkForward] = useState(false);
  const [sensitivity, setSensitivity] = useState(initialSensitivity);
  const [withSensitivity, setWithSensitivity] = useState(false);
  const [reproduction, setReproduction] = useState('');
  const { busy, run } = useAction(onError);
  const available =
    sources.data?.series.filter(
      (s) => s.kind === 'prices' && s.currency === 'EUR',
    ) ?? [];
  const source = available.find((s) => `${s.id}:${s.version}` === sourceKey);
  const ready =
    !!source &&
    source.price_basis === 'raw' &&
    source.basis_verified &&
    source.calendar_verified;
  const configFields = [
    ['initial_cash_eur', 'Capital inicial EUR'],
    ['strategy_weight', 'Peso de la estrategia (0–1)'],
    ['max_position_weight', 'Límite de posición (0–1)'],
    ['quantity_step', 'Lote mínimo'],
    ['fixed_fee_eur', 'Comisión fija EUR'],
    ['fee_bps', 'Comisión proporcional (pb)'],
    ['slippage_bps', 'Deslizamiento (pb)'],
  ] as const;
  function choose(ident: string) {
    setSelected(ident);
    setPublished(null);
    setAcknowledged(false);
    setReproduction('');
  }
  async function create() {
    if (!source || !ready) return;
    const result = await api<LabReport>('/lab/protocols', {
      name,
      series_id: source.id,
      series_version: source.version,
      start_date: start,
      holdout_date: split,
      end_date: end,
      fast: Number(fast),
      slow: Number(slow),
      sessions_csv: sessions,
      opening_source: openingSource,
      event_free_source: eventSource,
      evidence_reviewed: reviewed,
      config,
      ...(withWalkForward ? { walk_forward: walkForward } : {}),
      ...(withSensitivity
        ? { sensitivity: sensitivityInput(sensitivity) }
        : {}),
    });
    setSelected(result.protocol.id);
    setPublished(result);
    setAcknowledged(false);
    setReproduction('');
    await history.refresh();
  }
  return (
    <div className="research-result">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">INVESTIGACIÓN · SMA</p>
            <h2>Nuevo protocolo temporal</h2>
          </div>
          <span className="tag">EUR · simulación local</span>
        </div>
        <p className="muted">
          Congela una versión CSV y decide el corte antes de ver resultados.
          Desarrollo y prueba final usan cuentas independientes; cada una
          empieza en efectivo y calienta sus propias medias.
        </p>
        <QueryStatus label="Series nativas para simular" query={sources} />
        <Button
          variant="outline"
          disabled={busy}
          onClick={() => run(sources.refresh)}
        >
          Actualizar series
        </Button>
        <form
          aria-label="Configuración del protocolo SMA"
          onSubmit={(event) => {
            event.preventDefault();
            void run(create);
          }}
        >
          <fieldset disabled={busy} className="simulation-fields">
            <div className="form-grid">
              <Field label="Nombre del protocolo">
                <Input
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Versión CSV nativa EUR">
                <Choice
                  label="Versión CSV nativa EUR"
                  value={sourceKey}
                  onChange={(value) => {
                    setSourceKey(value);
                    setReviewed(false);
                  }}
                  options={available.map((s) => ({
                    value: `${s.id}:${s.version}`,
                    label: `${s.name} · v${s.version}`,
                  }))}
                />
              </Field>
            </div>
            {!source && (
              <p className="notice">
                Importa tu CSV de precios nativos EUR en Datos, asigna una
                cotización con mercado y acredita su base raw, calendario y
                disponibilidad. Después actualiza las series aquí.
              </p>
            )}
            {source && !ready && (
              <output className="notice">
                Esta versión no acredita base raw y calendario. Revisa su
                evidencia en Datos e importa una nueva versión; no se inferirá
                automáticamente.
              </output>
            )}
            {source && (
              <p className="muted">
                {date(source.date_min)} → {date(source.date_max)} ·{' '}
                {source.row_count} barras · {source.source}
              </p>
            )}
            {source && (
              <SourcePrevalidation
                key={`${source.id}:${source.version}`}
                id={source.id}
                version={source.version}
              />
            )}
            <div className="form-grid">
              <Field label="Inicio del desarrollo">
                <Input
                  required
                  type="date"
                  value={start}
                  onChange={(e) => {
                    setStart(e.target.value);
                    setReviewed(false);
                  }}
                />
              </Field>
              <Field label="Inicio de la prueba final">
                <Input
                  required
                  type="date"
                  value={split}
                  onChange={(e) => {
                    setSplit(e.target.value);
                    setReviewed(false);
                  }}
                />
              </Field>
              <Field label="Fin del protocolo">
                <Input
                  required
                  type="date"
                  value={end}
                  onChange={(e) => {
                    setEnd(e.target.value);
                    setReviewed(false);
                  }}
                />
              </Field>
              <Field label="Media rápida (sesiones)">
                <Input
                  required
                  type="number"
                  min={2}
                  max={249}
                  value={fast}
                  onChange={(e) => setFast(e.target.value)}
                />
              </Field>
              <Field label="Media lenta (sesiones)">
                <Input
                  required
                  type="number"
                  min={3}
                  max={250}
                  value={slow}
                  onChange={(e) => setSlow(e.target.value)}
                />
              </Field>
            </div>
            <p className="muted">
              Mínimo ventana lenta + 2 sesiones por periodo. Máximo 2.000 en
              total. Los cruces se ejecutan exclusivamente en la apertura
              siguiente disponible.
            </p>
            <Field
              label="CSV de sesiones y disponibilidad de apertura"
              hint="Cabecera: date,open_at,close_at,open_available_at. Una fila por sesión abierta del periodo; marcas ISO con zona horaria. El cierre debe coincidir con el calendario de Datos."
            >
              <Textarea
                aria-label="CSV de sesiones y disponibilidad de apertura"
                required
                rows={6}
                value={sessions}
                onChange={(e) => {
                  setSessions(e.target.value);
                  setReviewed(false);
                }}
                placeholder="date,open_at,close_at,open_available_at"
              />
            </Field>
            <div className="form-grid">
              <Field label="Procedencia de aperturas y disponibilidad">
                <Input
                  required
                  minLength={3}
                  maxLength={500}
                  value={openingSource}
                  onChange={(e) => {
                    setOpeningSource(e.target.value);
                    setReviewed(false);
                  }}
                />
              </Field>
              <Field label="Evidencia de ausencia de eventos corporativos">
                <Input
                  required
                  minLength={3}
                  maxLength={500}
                  value={eventSource}
                  onChange={(e) => {
                    setEventSource(e.target.value);
                    setReviewed(false);
                  }}
                />
              </Field>
            </div>
            <p className="muted">
              Debe cubrir todo el periodo: splits, dividendos y otros ajustes
              quedan fuera de esta simulación. ATLAS contrasta los eventos
              registrados, pero no certifica la declaración.
            </p>
            <div className="form-grid">
              {configFields.map(([key, label]) => (
                <Field key={key} label={label}>
                  <Input
                    required
                    inputMode="decimal"
                    value={config[key]}
                    onChange={(e) =>
                      setConfig({ ...config, [key]: e.target.value })
                    }
                  />
                </Field>
              ))}
            </div>
            <label className="check-row">
              <input
                type="checkbox"
                checked={config.purchases_enabled}
                onChange={(e) =>
                  setConfig({ ...config, purchases_enabled: e.target.checked })
                }
              />{' '}
              Permitir compras en esta simulación
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                required
                checked={reviewed}
                onChange={(e) => setReviewed(e.target.checked)}
              />{' '}
              He revisado la evidencia y la ausencia de eventos corporativos en
              el periodo
            </label>
            <WalkForwardEditor
              enabled={withWalkForward}
              onEnabled={setWithWalkForward}
              value={walkForward}
              onChange={setWalkForward}
            />
            <SensitivityEditor
              enabled={withSensitivity}
              onEnabled={setWithSensitivity}
              value={sensitivity}
              onChange={setSensitivity}
            />
            <Button type="submit" disabled={!ready || !reviewed || busy}>
              {busy ? 'Procesando…' : 'Congelar y simular desarrollo'}
            </Button>
          </fieldset>
        </form>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Protocolos guardados</h2>
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => run(history.refresh)}
          >
            Actualizar historial
          </Button>
        </div>
        <QueryStatus label="Historial de simulaciones" query={history} />
        <DataTable
          heads={[
            'Protocolo',
            'Desarrollo desde',
            'Prueba final desde',
            'Estado',
            'Informe',
          ]}
          rows={(history.data?.items ?? []).map((p) => [
            p.name,
            date(p.start_date),
            date(p.holdout_date),
            p.opened ? 'Prueba final abierta' : 'Prueba final reservada',
            <Button
              key={p.id}
              variant="outline"
              disabled={busy}
              onClick={() => choose(p.id)}
            >
              Ver {p.name}
            </Button>,
          ])}
        />
        <div className="actions">
          <Button
            variant="outline"
            disabled={busy || offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 20))}
          >
            Página anterior
          </Button>
          <Button
            variant="outline"
            disabled={busy || (history.data?.items.length ?? 0) < 20}
            onClick={() => setOffset(offset + 20)}
          >
            Página siguiente
          </Button>
        </div>
      </section>
      {selected && !published && (
        <QueryStatus label="Informe del protocolo" query={saved} />
      )}
      {report && (
        <>
          <section className="panel" aria-label="Protocolo seleccionado">
            <h2>{report.protocol.name}</h2>
            <p className="muted">
              SMA {report.protocol.fast}/{report.protocol.slow} · versión de
              precios {report.protocol.series_version} · parámetros congelados.
              Editar el formulario crea otro protocolo.
            </p>
            <details className="details">
              <summary>Supuestos y trazabilidad</summary>
              <ul>
                {report.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
              <DataTable
                heads={['Supuesto', 'Valor']}
                rows={configFields.map(([key, label]) => [
                  label,
                  report.config[key],
                ])}
              />
              <p>
                Compras simuladas:{' '}
                {report.config.purchases_enabled ? 'permitidas' : 'bloqueadas'}
              </p>
              <p className="mono native-hash">
                Protocolo: {report.protocol.id}
              </p>
              <p className="mono native-hash">
                Fuente: {report.protocol.source_hash}
              </p>
              <p className="mono native-hash">
                Evidencia: {report.evidence_hash}
              </p>
            </details>
            <Button
              variant="outline"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  const result = await api<LabReproduction>(
                    `/lab/protocols/${report.protocol.id}/reproduce`,
                    {},
                  );
                  setReproduction(
                    result.development_matches &&
                      result.holdout_matches !== false &&
                      (!report.walk_forward ||
                        result.walk_forward_matches === true) &&
                      (!report.sensitivity ||
                        result.sensitivity_matches === true)
                      ? 'Reproducción correcta: coincide con el informe guardado.'
                      : 'La reproducción no coincide. Conserva el informe y revisa la versión del motor.',
                  );
                })
              }
            >
              Comprobar reproducción
            </Button>
            <output>{reproduction}</output>
          </section>
          <PeriodResult
            result={report.development}
            title="Resultado de desarrollo"
          />
          {report.walk_forward && (
            <WalkForwardResult result={report.walk_forward} />
          )}
          {report.sensitivity && (
            <SensitivityResult result={report.sensitivity} />
          )}
          {report.holdout ? (
            <PeriodResult
              result={report.holdout}
              title="Resultado de la prueba final"
            />
          ) : (
            <section className="panel">
              <h3>Prueba final reservada</h3>
              <p>
                {date(report.protocol.holdout_date)} →{' '}
                {date(report.protocol.end_date)}. Abrirla registra la exposición
                y bloquea su uso como prueba no vista en otros protocolos de
                este Laboratorio.
              </p>
              <label className="check-row">
                <input
                  type="checkbox"
                  disabled={busy}
                  checked={acknowledged}
                  onChange={(e) => setAcknowledged(e.target.checked)}
                />{' '}
                Entiendo que abrir la prueba final consume su reserva
              </label>
              <Button
                disabled={busy || !acknowledged}
                onClick={() =>
                  run(async () => {
                    const result = await api<LabReport>(
                      `/lab/protocols/${report.protocol.id}/holdout`,
                      {
                        protocol_hash: report.protocol.id,
                        acknowledge_exposure: true,
                      },
                    );
                    setPublished(result);
                    setAcknowledged(false);
                    setReproduction('');
                    await history.refresh();
                  })
                }
              >
                Abrir prueba final
              </Button>
            </section>
          )}
        </>
      )}
    </div>
  );
}
