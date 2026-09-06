'use client';
import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { version } from '../package.json';
import { api } from '@/lib/api';
import type { StateResponse, PortfolioResponse, DatasetResponse } from '@/lib/api-types';
import {
  Activity,
  Database,
  ShieldCheck,
  Wallet,
  FlaskConical,
  Bot,
  Settings,
  FolderInput,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  money,
  pct,
  Metric,
  Curve,
  Choice,
  DataTable,
  Lab,
  AgentPanel,
  DataPanel,
  SettingsPanel,
} from './workbench';

export default function Home() {
  const [state, setState] = useState<StateResponse | null>(null),
    [datasetId, setDatasetId] = useState(''),
    [savedPortfolio, setPortfolio] = useState<{ datasetId: string; value: PortfolioResponse } | null>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [tab, setTab] = useState('portfolio');
  const stateRevision = useRef(0);
  const portfolio = savedPortfolio?.datasetId === datasetId ? savedPortfolio.value : null;
  async function refresh() {
    const revision = ++stateRevision.current;
    const s = await api<StateResponse>('/state');
    if (revision !== stateRevision.current) return;
    setState(s);
    setDatasetId((previous) => previous || s.datasets[0]?.id || '');
  }
  useEffect(() => {
    void refresh().catch((e) => setError(String(e)));
    const timer = setInterval(
      () => void refresh().catch((e) => setError(String(e))),
      5000,
    );
    return () => clearInterval(timer);
  }, []);
  const dataset = state?.datasets.find((d) => d.id === datasetId);
  const auditSequence = state?.audit[0]?.seq;
  useEffect(() => {
    let active = true;
    if (datasetId)
      api<PortfolioResponse>('/datasets/' + datasetId + '/portfolio')
        .then((p) => {
          if (active) setPortfolio({ datasetId, value: p });
        })
        .catch((e) => {
          if (active) setError(String(e));
        });
    return () => {
      active = false;
    };
  }, [datasetId, dataset?.version, auditSequence]);
  useEffect(() => {
    const context = (document as Document & { modelContext?: { registerTool: (
      tool: { name: string; title: string; description: string; inputSchema: object;
        annotations: object; execute: (input: unknown) => Promise<unknown> },
      options: { signal: AbortSignal }) => unknown } }).modelContext;
    if (!context?.registerTool) return;
    const controller = new AbortController();
    Promise.resolve(
      context.registerTool(
        {
          name: 'read_atlas_state',
          title: 'Leer estado de ATLAS',
          description:
            'Lee conjuntos de datos, experimentos y límites actuales; no crea ni ejecuta órdenes.',
          inputSchema: {
            type: 'object',
            properties: {},
            additionalProperties: false,
          },
          annotations: { readOnlyHint: true, untrustedContentHint: true },
          execute: async (input: unknown) => {
            if (
              !input ||
              typeof input !== 'object' ||
              Array.isArray(input) ||
              Object.keys(input).length
            )
              throw new Error('Se requiere un objeto vacío.');
            const s = await api<StateResponse>('/state');
            setState(s);
            return {
              datasets: s.datasets.map((d) => ({
                id: d.id,
                name: d.name,
                source_kind: d.source_kind,
              })),
              experiments: s.experiments.map((j) => ({
                id: j.id,
                status: j.status,
                symbol: j.symbol,
              })),
              settings: s.settings,
            };
          },
        },
        { signal: controller.signal },
      ),
    ).catch(() => {});
    return () => controller.abort();
  }, []);
  async function demo() {
    setBusy(true);
    setError('');
    try {
      const d = await api<DatasetResponse>('/datasets/demo', {});
      setDatasetId(d.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="atlas-shell">
      <header className="topbar">
        <Link href="/" className="brand">
          <Activity size={26} />
          <span>
            ATLAS <small>QUANT</small>
          </span>
        </Link>
        <div className="topbar-right">
          <span className="status-dot">
            {state ? 'Motor conectado' : 'Conectando al motor'}
          </span>
          <span className="version">v{version}</span>
        </div>
      </header>
      <main className="workspace">
        <div className="title-row">
          <div>
            <p className="eyebrow">TU ESPACIO DE INVERSIÓN</p>
            <h1>
              {tab === 'portfolio'
                ? 'La cartera, con perspectiva.'
                : tab === 'lab'
                  ? 'Poner las ideas a prueba.'
                  : tab === 'agent'
                    ? 'Investigar. Observar. Decidir.'
                    : tab === 'data'
                      ? 'El origen de cada resultado.'
                      : 'El control sigue en tus manos.'}
            </h1>
          </div>
          <Button variant="secondary" disabled={busy} onClick={demo}>
            <Database />
            {busy ? 'Cargando…' : 'Cargar demostración'}
          </Button>
        </div>
        <div className="notice">
          <ShieldCheck size={19} />
          <span>
            Modo análisis y simulación ·{' '}
            {state?.settings.kill_switch
              ? 'Parada de ejecución activada'
              : 'Simulación bajo reglas habilitada'}{' '}
            · Dinero real pendiente de integración con bróker
          </span>
        </div>
        {error && (
          <div role="alert" className="error">
            {error}
            <button
              className="dismiss"
              aria-label="Cerrar aviso"
              onClick={() => setError('')}
            >
              ×
            </button>
          </div>
        )}
        <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
          <TabsList className="main-tabs" variant="line">
            <TabsTrigger value="portfolio">
              <Wallet />
              Cartera
            </TabsTrigger>
            <TabsTrigger value="lab">
              <FlaskConical />
              Laboratorio
            </TabsTrigger>
            <TabsTrigger value="agent">
              <Bot />
              Agente IA
            </TabsTrigger>
            <TabsTrigger value="data">
              <FolderInput />
              Datos
            </TabsTrigger>
            <TabsTrigger value="settings">
              <Settings />
              Ajustes
            </TabsTrigger>
          </TabsList>
          <div className="toolbar">
            <Choice
              label="Conjunto de datos"
              value={datasetId}
              onChange={setDatasetId}
              options={(state?.datasets || []).map((d) => ({
                value: d.id,
                label: d.name,
              }))}
            />
            {dataset && (
              <>
                <span
                  className={
                    'tag ' +
                    (dataset.source_kind === 'synthetic' ? 'amber' : '')
                  }
                >
                  {dataset.source_kind === 'synthetic'
                    ? 'DATOS SINTÉTICOS'
                    : 'DATOS IMPORTADOS'}
                </span>
                <span className="muted">
                  EUR · hasta {dataset.manifest.date_max}
                </span>
              </>
            )}
          </div>
          <TabsContent value="portfolio">
            <div className="stats">
              <Metric
                title="Valor de la cartera"
                value={portfolio ? money(portfolio.nav) : '—'}
              />
              <Metric
                title="Efectivo disponible"
                value={portfolio ? money(portfolio.cash) : '—'}
              />
              <Metric
                title="Resultado acumulado"
                value={portfolio ? money(portfolio.pnl) : '—'}
              />
              <Metric
                title="Rentabilidad TWR"
                value={portfolio ? pct(portfolio.twr) : '—'}
              />
            </div>
            <section className="panel">
              <div className="panel-heading">
                <h2>Evolución del patrimonio</h2>
                <span className="muted">Valoración diaria · EUR</span>
              </div>
              {portfolio?.curve?.length ? (
                <Curve data={portfolio.curve} />
              ) : (
                <div className="empty">
                  <Wallet size={36} />
                  <h3>
                    {dataset
                      ? 'Importa tus movimientos'
                      : 'Empieza con un conjunto de datos'}
                  </h3>
                  <p>
                    {dataset
                      ? 'Los precios ya están disponibles. Añade depósitos, compras y otros movimientos desde Datos para construir tu cartera.'
                      : 'Explora la demostración con tres activos ficticios o importa tu historial de precios y operaciones.'}
                  </p>
                  <div className="actions centered">
                    <Button onClick={() => setTab('data')}>
                      Importar datos
                    </Button>
                    <Button variant="secondary" disabled={busy} onClick={demo}>
                      Explorar demo
                    </Button>
                  </div>
                </div>
              )}
            </section>
            {portfolio && portfolio.positions.length > 0 && (
              <section className="panel">
                <div className="panel-heading">
                  <h2>Posiciones</h2>
                  <span className="muted">
                    Aportaciones netas: {money(portfolio.net_contributions)}
                  </span>
                </div>
                <DataTable
                  heads={[
                    'Activo',
                    'Cantidad',
                    'Último precio',
                    'Valor',
                    'Peso',
                    'P&L no realizado',
                  ]}
                  rows={portfolio.positions.map((p) => [
                    <strong key="symbol">{p.symbol}</strong>,
                    p.quantity,
                    money(p.price),
                    money(p.market_value),
                    pct(p.weight),
                    <span
                      key="pnl"
                      className={
                        p.unrealized_pnl >= 0 ? 'positive' : 'negative'
                      }
                    >
                      {money(p.unrealized_pnl)}
                    </span>,
                  ])}
                />
              </section>
            )}
            {portfolio && portfolio.warnings.length > 0 && (
              <details className="details">
                <summary>Convenciones de valoración</summary>
                <ul>
                  {portfolio.warnings.map((w: string, i: number) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </details>
            )}
          </TabsContent>
          <TabsContent value="lab">
            <Lab dataset={dataset} onError={setError} />
          </TabsContent>
          <TabsContent value="agent">
            {state && (
              <AgentPanel
                dataset={dataset}
                state={state}
                refresh={refresh}
                onError={setError}
              />
            )}
          </TabsContent>
          <TabsContent value="data">
            <DataPanel
              dataset={dataset}
              refresh={refresh}
              selectDataset={setDatasetId}
              onError={setError}
            />
          </TabsContent>
          <TabsContent value="settings">
            {state && (
              <SettingsPanel
                state={state}
                refresh={refresh}
                onError={setError}
              />
            )}
          </TabsContent>
        </Tabs>
        <p className="footnote">
          ATLAS v{version} · Datos y experimentos guardados en este ordenador. Los
          resultados de la demo son sintéticos. Ninguna conclusión de IA
          autoriza por sí sola una operación.
        </p>
      </main>
    </div>
  );
}
