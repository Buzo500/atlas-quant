'use client';
import { useState } from 'react';
import { Play } from 'lucide-react';
import { api } from '@/lib/api';
import type { DatasetResponse, ResearchResponse } from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Choice, Field } from '@/shared/ui';
import { CostForm, DEFAULT_COSTS } from '@/shared/research-forms';
import { useAction } from '@/shared/use-action';
import { useDatasetSymbol } from '@/shared/use-dataset-symbol';
import { ResearchResult } from './research-result';

export function Lab({
  dataset,
  onError,
}: {
  dataset: DatasetResponse | undefined;
  onError: (s: string) => void;
}) {
  type SubmittedContext = Pick<
    ResearchResponse['execution'],
    | 'dataset_id'
    | 'dataset_name'
    | 'dataset_version'
    | 'dataset_manifest_hash'
    | 'symbol'
    | 'costs'
  >;
  const { symbols, symbol, setSymbol } = useDatasetSymbol(dataset);
  const [costs, setCosts] = useState(DEFAULT_COSTS),
    [result, setResult] = useState<ResearchResponse | null>(null),
    [pending, setPending] = useState<SubmittedContext | null>(null);
  const { busy, run } = useAction(onError);
  const matchesDraft = (context: SubmittedContext) =>
    context.dataset_id === dataset?.id &&
    context.dataset_name === dataset.name &&
    context.dataset_version === dataset.version &&
    context.dataset_manifest_hash === dataset.manifest.sha256 &&
    context.symbol === symbol &&
    (Object.keys(costs) as (keyof typeof costs)[]).every(
      (key) => context.costs[key] === costs[key],
    );
  async function compare() {
    if (!dataset || !symbols.includes(symbol)) return;
    const submitted: SubmittedContext = {
      dataset_id: dataset.id,
      dataset_name: dataset.name,
      dataset_version: dataset.version,
      dataset_manifest_hash: dataset.manifest.sha256,
      symbol,
      costs: { ...costs },
    };
    setPending(submitted);
    try {
      const response = await api<ResearchResponse>('/research', {
        dataset_id: submitted.dataset_id,
        symbol: submitted.symbol,
        costs: submitted.costs,
      });
      setResult(response);
    } finally {
      setPending(null);
    }
  }
  return (
    <>
      <div className="lab-layout">
        <section className="panel lab-config">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">PARÁMETROS DE LA PRUEBA</p>
              <h2>Comparar estrategias</h2>
            </div>
            <span className="tag">{symbols.length} activos disponibles</span>
          </div>
          <p className="muted">
            Mantener el activo y dos cruces de medias, con los mismos costes y
            límite de posición.
          </p>
          <div className="field-compact">
            <Field label="Activo">
              <Choice
                value={symbol}
                onChange={setSymbol}
                label="Activo"
                options={symbols.map((s: string) => ({ value: s, label: s }))}
              />
            </Field>
          </div>
          <CostForm costs={costs} setCosts={setCosts} />
          {!dataset && (
            <p className="muted">
              Selecciona o importa un conjunto de datos para empezar.
            </p>
          )}
          <Button
            disabled={!symbols.includes(symbol) || busy}
            onClick={() => run(compare)}
          >
            <Play />
            {busy ? 'Calculando…' : 'Ejecutar comparación'}
          </Button>
        </section>
        <aside className="panel lab-method">
          <div className="panel-heading">
            <h2>Validación cronológica</h2>
            <span className="tag">60 / 20 / 20</span>
          </div>
          <ol className="method-steps">
            <li>
              <span>60 %</span>
              <div>
                <strong>Preparación</strong>
                <p>Primer tramo del histórico para preparar las estrategias.</p>
              </div>
            </li>
            <li>
              <span>20 %</span>
              <div>
                <strong>Selección</strong>
                <p>Comparación en validación y elección del candidato.</p>
              </div>
            </li>
            <li>
              <span>20 %</span>
              <div>
                <strong>Prueba reservada</strong>
                <p>Evaluación del ganador, ya congelado, fuera de muestra.</p>
              </div>
            </li>
          </ol>
          <p className="footnote">
            El resultado incluye comparación con mantener el activo y
            sensibilidad a los costes. Esta prueba no activa la simulación.
          </p>
        </aside>
      </div>
      {pending && (
        <output
          className={
            'notice vertical' + (!matchesDraft(pending) ? ' amber' : '')
          }
        >
          <strong>
            Calculando {pending.symbol} · {pending.dataset_name}
          </strong>
          <span>
            Versión visible al enviar: {pending.dataset_version}. El resultado
            identificará la versión utilizada.
          </span>
          {!matchesDraft(pending) && (
            <span>
              El formulario ha cambiado durante el cálculo. El resultado
              conservará los datos y parámetros de la ejecución enviada.
            </span>
          )}
        </output>
      )}
      {result && (
        <>
          {!matchesDraft(result.execution) && (
            <div className="notice amber vertical">
              <strong>Resultado de otra configuración</strong>
              <span>
                El conjunto, su versión o los parámetros actuales no coinciden
                con esta ejecución. Sus datos originales se muestran a
                continuación; ejecuta otra comparación para aplicar los cambios.
              </span>
            </div>
          )}
          <ResearchResult result={result} />
        </>
      )}
    </>
  );
}
