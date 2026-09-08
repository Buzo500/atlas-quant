'use client';
import { useEffect, useRef, useState } from 'react';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { useNavigation, type Section } from '@/shared/navigation';
import Link from 'next/link';
import { version } from '../package.json';
import { api } from '@/lib/api';
import type { StateResponse, DatasetResponse } from '@/lib/api-types';
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
import { Choice } from '@/shared/ui';
import { Lab } from '@/features/research/lab';
import { AgentPanel } from '@/features/experiments/agent-panel';
import { DataPanel } from '@/features/data/data-panel';
import { SettingsPanel } from '@/features/settings/settings-panel';
import { PortfolioPanel } from '@/features/portfolio/portfolio-panel';
import { date } from '@/shared/format';

export default function Home() {
  const dataTab = useRef<HTMLButtonElement | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const { navigation, navigate } = useNavigation();
  const tab = navigation.tab;
  const setTab = (tab: Section) => navigate({ tab });
  const setDatasetId = (dataset: string) => navigate({ dataset });
  const stateQuery = useRead<StateResponse>({
    path: '/state',
    intervalMs: 5000,
  });
  const state = stateQuery.data;
  const refresh = stateQuery.refresh;
  const connected = !!state && !stateQuery.error;
  const datasetId = navigation.dataset || state?.datasets[0]?.id || '';
  const dataset = state?.datasets.find((d) => d.id === datasetId);
  useEffect(() => {
    const context = (
      document as Document & {
        modelContext?: {
          registerTool: (
            tool: {
              name: string;
              title: string;
              description: string;
              inputSchema: object;
              annotations: object;
              execute: (input: unknown) => Promise<unknown>;
            },
            options: { signal: AbortSignal },
          ) => unknown;
        };
      }
    ).modelContext;
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
  const titles: Record<string, { title: string; description: string }> = {
    portfolio: {
      title: 'Cartera',
      description:
        'Posiciones, patrimonio y rentabilidad del conjunto seleccionado.',
    },
    lab: {
      title: 'Laboratorio',
      description:
        'Compara estrategias con datos históricos y costes de ejecución.',
    },
    agent: {
      title: 'Agente IA',
      description: 'Experimentos, evidencia y seguimiento de estrategias.',
    },
    data: {
      title: 'Datos',
      description:
        'Importa precios y movimientos. Consulta su origen y trazabilidad.',
    },
    settings: {
      title: 'Ajustes',
      description:
        'Límites de simulación, proveedores y registro de actividad.',
    },
  };
  return (
    <Tabs
      className="atlas-shell"
      value={tab}
      onValueChange={(v) => setTab(v as Section)}
    >
      <a className="skip-link" href="#main-content">
        Ir al contenido
      </a>
      <header className="topbar">
        <Link href="/" className="brand" aria-label="ATLAS Quant, inicio">
          <span className="brand-mark">
            <Activity size={22} strokeWidth={1.7} />
          </span>
          <span>
            ATLAS <small>QUANT</small>
          </span>
        </Link>
        <TabsList
          className="main-tabs"
          variant="line"
          aria-label="Secciones de ATLAS"
        >
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
          <TabsTrigger ref={dataTab} value="data">
            <FolderInput />
            Datos
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings />
            Ajustes
          </TabsTrigger>
        </TabsList>
        <div className="topbar-right">
          <output
            className={
              'status-dot ' + (connected ? 'connected' : 'disconnected')
            }
          >
            {connected
              ? 'Motor conectado'
              : state || stateQuery.error
                ? 'Motor sin conexión'
                : 'Conectando…'}
          </output>
          <span className="version">v{version}</span>
        </div>
      </header>
      <main className="workspace" id="main-content" tabIndex={-1}>
        <div className="toolbar">
          <div className="dataset-picker">
            <span className="toolbar-label">Conjunto de datos</span>
            <Choice
              label="Conjunto de datos"
              value={datasetId}
              onChange={setDatasetId}
              options={(state?.datasets || []).map((d) => ({
                value: d.id,
                label: d.name,
              }))}
            />
          </div>
          {dataset && (
            <div className="dataset-context">
              <span
                className={
                  'tag ' + (dataset.source_kind === 'synthetic' ? 'amber' : '')
                }
              >
                {dataset.source_kind === 'synthetic'
                  ? 'Datos sintéticos'
                  : 'Datos importados'}
              </span>
              <span className="muted">
                EUR · hasta {date(dataset.manifest.date_max)}
              </span>
            </div>
          )}
          <span className="local-label">Espacio local</span>
        </div>
        <div className="title-row">
          <div>
            <h1>{titles[tab].title}</h1>
            <p className="page-description">{titles[tab].description}</p>
          </div>
          <Button
            variant="outline"
            disabled={busy || !connected}
            onClick={demo}
          >
            <Database />
            {busy ? 'Cargando…' : 'Cargar demostración'}
          </Button>
        </div>
        <div className="notice">
          <ShieldCheck size={17} />
          <span>
            <strong>Análisis y simulación</strong>
            <span className="notice-separator">·</span>
            {!connected
              ? 'Estado de ejecución pendiente de conexión'
              : state?.settings.kill_switch
                ? 'Parada de ejecución activada'
                : 'Simulación bajo reglas habilitada'}
            <span className="notice-secondary">
              {' '}
              · Sin conexión a un bróker
            </span>
          </span>
        </div>
        <QueryStatus label="Estado del motor" query={stateQuery} />
        {navigation.dataset && state && !dataset && (
          <p role="alert" className="error">
            El conjunto de este enlace no está disponible. Selecciona otro
            conjunto.
          </p>
        )}
        {error && (
          <div role="alert" className="error">
            <span>{error}</span>
            <button
              className="dismiss"
              aria-label="Cerrar aviso"
              onClick={() => setError('')}
            >
              ×
            </button>
          </div>
        )}
        <TabsContent keepMounted value="portfolio">
          <PortfolioPanel
            dataset={dataset}
            auditSequence={state?.audit[0]?.seq}
            active={tab === 'portfolio'}
            connected={connected}
            stateLoaded={!!state}
            busy={busy}
            onImport={() => {
              setTab('data');
              dataTab.current?.focus();
            }}
            onDemo={demo}
          />
        </TabsContent>
        <TabsContent keepMounted value="lab">
          <Lab dataset={dataset} onError={setError} />
        </TabsContent>
        <TabsContent keepMounted value="agent">
          {state ? (
            <AgentPanel
              dataset={dataset}
              state={state}
              selectedId={navigation.experiment}
              onSelect={(experiment) => navigate({ experiment })}
              active={tab === 'agent'}
              refresh={refresh}
              onError={setError}
            />
          ) : (
            <output className="empty">
              Esperando el estado de los experimentos…
            </output>
          )}
        </TabsContent>
        <TabsContent keepMounted value="data">
          <DataPanel
            dataset={dataset}
            refresh={refresh}
            selectDataset={setDatasetId}
            onError={setError}
          />
        </TabsContent>
        <TabsContent keepMounted value="settings">
          {state ? (
            <SettingsPanel state={state} refresh={refresh} onError={setError} />
          ) : (
            <output className="empty">Esperando los ajustes del motor…</output>
          )}
        </TabsContent>
        <footer className="footnote">
          <span>ATLAS Quant · v{version} · Guardado en este ordenador</span>
          <span>
            La demo utiliza datos sintéticos. Las conclusiones de IA no
            autorizan operaciones.
          </span>
        </footer>
      </main>
    </Tabs>
  );
}
