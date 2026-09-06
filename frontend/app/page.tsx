'use client';
import { useEffect, useState } from 'react';
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
  api,
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
  const [state, setState] = useState<any>(null),
    [datasetId, setDatasetId] = useState(''),
    [portfolio, setPortfolio] = useState<any>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [tab, setTab] = useState('portfolio');
  async function refresh() {
    const s = await api('/state');
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
  const dataset = state?.datasets.find((d: any) => d.id === datasetId);
  useEffect(() => {
    let active = true;
    if (datasetId)
      api('/datasets/' + datasetId + '/portfolio')
        .then((p) => {
          if (active) setPortfolio(p);
        })
        .catch((e) => {
          if (active) setError(String(e));
        });
    else setPortfolio(null);
    return () => {
      active = false;
    };
  }, [datasetId, dataset?.version, state?.audit?.[0]?.seq]);
  useEffect(() => {
    const context = (document as any).modelContext;
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
            const s = await api('/state');
            setState(s);
            return {
              datasets: s.datasets.map((d: any) => ({
                id: d.id,
                name: d.name,
                source_kind: d.source_kind,
              })),
              experiments: s.experiments.map((j: any) => ({
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
      const d = await api('/datasets/demo', {});
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
        <a href="/" className="brand">
          <Activity size={26} />
          <span>
            ATLAS <small>QUANT</small>
          </span>
        </a>
        <div className="topbar-right">
          <span className="status-dot">
            {state ? 'Motor conectado' : 'Conectando al motor'}
          </span>
          <span className="version">v0.1</span>
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
              options={(state?.datasets || []).map((d: any) => ({
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
            {portfolio?.positions?.length > 0 && (
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
                  rows={portfolio.positions.map((p: any) => [
                    <strong>{p.symbol}</strong>,
                    p.quantity,
                    money(p.price),
                    money(p.market_value),
                    pct(p.weight),
                    <span
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
            {portfolio?.warnings?.length > 0 && (
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
          ATLAS v0.1 · Datos y experimentos guardados en este ordenador. Los
          resultados de la demo son sintéticos. Ninguna conclusión de IA
          autoriza por sí sola una operación.
        </p>
      </main>
    </div>
  );
}
