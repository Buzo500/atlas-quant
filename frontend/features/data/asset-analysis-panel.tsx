'use client';
import { useState } from 'react';
import type {
  AssetSource,
  AssetSourceCatalog,
  AssetAnalysisHistory,
  AssetAnalysisReport,
  AssetAnalysisPreview,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Choice, DataTable, Field } from '@/shared/ui';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useCorporateReview } from './corporate-shared';
import { AssetAnalysisResults } from './asset-analysis-results';

type Props = {
  active: boolean;
  revision?: number;
  refresh: () => Promise<void>;
  onError: (error: string) => void;
};
const path = '/v2/asset-analysis/reports';
const sourceLabel = (s: AssetSource) =>
  `${s.name} · ${s.dataset_name} · ${s.currency} · v${s.ref.version} · ${s.ref.id.slice(0, 8)}`;
export function AssetAnalysisPanel(props: Props) {
  const [opened, setOpened] = useState(false);
  const [visited, setVisited] = useState(false);
  return (
    <section
      className="panel asset-analysis"
      aria-label="Fichas y comparador de activos"
    >
      <h2>Fichas y comparador de activos</h2>
      <p>
        Precios, volatilidad y correlaciones con fechas y fuentes explícitas.
      </p>
      <details
        open={opened}
        onToggle={(event) => {
          setOpened(event.currentTarget.open);
          if (event.currentTarget.open) setVisited(true);
        }}
      >
        <summary>Abrir comparador de activos</summary>
        {visited && (
          <AssetAnalysisEditor {...props} active={props.active && opened} />
        )}
      </details>
    </section>
  );
}
export function AssetAnalysisEditor({
  active,
  revision,
  refresh,
  onError,
}: Props) {
  const catalog = useRead<AssetSourceCatalog>({
    path: '/v2/asset-analysis/sources',
    revision,
    enabled: active,
  });
  const [sources, setSources] = useState<AssetSource[]>([]);
  const [candidate, setCandidate] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [fx, setFx] = useState('');
  const [offset, setOffset] = useState(0);
  const [savedId, setSavedId] = useState('');
  const history = useRead<AssetAnalysisHistory>({
    path: `${path}?offset=${offset}&limit=20`,
    revision,
    enabled: active,
  });
  const saved = useRead<AssetAnalysisReport>({
    path: savedId ? `${path}/${savedId}` : null,
    revision,
    enabled: active,
  });
  const review = useCorporateReview<AssetAnalysisPreview>(
    path,
    async () => {
      await refresh();
      await history.refresh();
    },
    onError,
  );
  const invalidate = () => {
    review.invalidate();
    setSavedId('');
  };
  const needsFx = sources.some((s) => s.currency === 'USD');
  const fxSource = catalog.data?.fx.find(
    (f) => `${f.ref.id}:${f.ref.version}` === fx,
  );
  const stale =
    sources.some((s) => !catalog.data?.sources.some((c) => c.key === s.key)) ||
    (needsFx && !!fx && !fxSource);
  const [yesterday] = useState(() =>
    new Date(Date.now() - 86400000).toISOString().slice(0, 10),
  );
  const chosen = catalog.data?.sources.find((s) => s.key === candidate);
  const valid =
    sources.length > 0 &&
    start < end &&
    end <= yesterday &&
    !stale &&
    (!needsFx || !!fxSource);
  const report = savedId ? saved.data : !stale ? review.preview?.report : null;
  function add() {
    if (
      !chosen ||
      sources.length >= 12 ||
      sources.some((s) => s.key === chosen.key)
    )
      return;
    invalidate();
    setSources([...sources, chosen]);
    setCandidate('');
    if (!sources.length) {
      setStart(chosen.date_min);
      setEnd(chosen.date_max < yesterday ? chosen.date_max : yesterday);
    }
  }
  return (
    <>
      <QueryStatus label="Fuentes del comparador" query={catalog} />
      <p>
        Hasta 12 fuentes de precios EUR/USD. Las métricas necesitan precios
        brutos y calendario verificados; no se descarga ni modifica ningún dato
        al calcular.
      </p>
      <div className="asset-analysis-fields">
        <Choice
          label="Activo y fuente para comparar"
          value={candidate}
          onChange={setCandidate}
          options={(catalog.data?.sources || [])
            .filter((s) => !sources.some((v) => v.key === s.key))
            .map((s) => ({ value: s.key, label: sourceLabel(s) }))}
        />
        <Button
          disabled={!chosen || sources.length >= 12 || review.busy}
          onClick={add}
        >
          Añadir activo a la comparación
        </Button>
      </div>
      <DataTable
        heads={['Fuente elegida', 'Cobertura de origen', 'Acción']}
        rows={sources.map((s) => [
          sourceLabel(s),
          `${s.date_min} — ${s.date_max}`,
          <Button
            key={s.key}
            variant="outline"
            disabled={review.busy}
            aria-label={`Quitar ${sourceLabel(s)}`}
            onClick={() => {
              invalidate();
              setSources(sources.filter((v) => v.key !== s.key));
            }}
          >
            Quitar
          </Button>,
        ])}
      />
      {stale && (
        <p role="alert">
          Una fuente ha cambiado. Quita la versión anterior y selecciona la
          actual antes de volver a calcular.
        </p>
      )}
      <div className="asset-analysis-fields">
        <Field label="Inicio de comparación">
          <Input
            type="date"
            max={yesterday}
            value={start}
            onChange={(e) => {
              invalidate();
              setStart(e.target.value);
            }}
          />
        </Field>
        <Field label="Fin de comparación">
          <Input
            type="date"
            max={yesterday}
            value={end}
            onChange={(e) => {
              invalidate();
              setEnd(e.target.value);
            }}
          />
        </Field>
        {needsFx && (
          <Choice
            label="Fuente EUR por USD para comparar"
            value={fx}
            onChange={(v) => {
              invalidate();
              setFx(v);
            }}
            options={(catalog.data?.fx || []).map((f) => ({
              value: `${f.ref.id}:${f.ref.version}`,
              label: `${f.name} · v${f.ref.version} · ${f.date_min} — ${f.date_max} · ${f.ref.id.slice(0, 8)}`,
            }))}
          />
        )}
      </div>
      <p className="muted">
        Máximo 3.660 días, hasta ayer UTC, y 200.000 barras de origen. El cambio
        USD debe existir para cada fecha, sin arrastre entre sesiones.
      </p>
      <div className="actions">
        <Button
          disabled={!valid || review.busy}
          onClick={() => {
            setSavedId('');
            void review.review({
              sources: sources.map((s) => s.ref),
              start_date: start,
              end_date: end,
              fx: needsFx ? fxSource?.ref : null,
            });
          }}
        >
          Calcular comparación
        </Button>
        {review.preview && !stale && (
          <Button
            disabled={review.busy}
            variant="outline"
            onClick={() => void review.confirm()}
          >
            Guardar comparación
          </Button>
        )}
      </div>
      {review.message && <output>{review.message}</output>}
      {savedId && <QueryStatus label="Comparación guardada" query={saved} />}
      {report && <AssetAnalysisResults key={report.id} report={report} />}
      <details>
        <summary>Comparaciones guardadas</summary>
        <QueryStatus label="Historial del comparador" query={history} />
        <DataTable
          heads={['Activos', 'Periodo', 'Guardado', 'Acción']}
          rows={(history.data?.reports || []).map((r) => [
            r.names.join(' · '),
            `${r.start_date} — ${r.end_date}`,
            r.created_at,
            <Button
              key={r.id}
              variant="outline"
              aria-label={`Consultar comparación ${r.created_at}`}
              onClick={() => {
                review.invalidate();
                setSavedId(r.id);
              }}
            >
              Consultar
            </Button>,
          ])}
        />
        <div className="actions">
          <Button
            variant="outline"
            disabled={!offset}
            onClick={() => setOffset(Math.max(0, offset - 20))}
          >
            Comparaciones anteriores
          </Button>
          <Button
            variant="outline"
            disabled={(history.data?.reports.length || 0) < 20}
            onClick={() => setOffset(offset + 20)}
          >
            Más comparaciones
          </Button>
        </div>
      </details>
    </>
  );
}
