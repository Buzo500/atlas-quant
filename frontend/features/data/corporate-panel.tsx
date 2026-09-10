'use client';

import { useState } from 'react';
import type {
  CatalogResponse,
  NativeCorporateCatalog as CorporateCatalog,
  NativeCorporatePortfolio,
  CorporatePortfolio,
  NativeCorporateEvent as CorporateEvent,
  CorporateDocuments,
  CorporateDocument,
  PortfolioRecord,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Field, DataTable } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { CorporateEventForm } from './corporate-event-form';
import { CorporateApplicationForm } from './corporate-application-form';
import { CorporateBalances } from './corporate-balances';
import { CorporatePager, eventLabel } from './corporate-shared';

export function CorporateSummary({
  portfolioId,
  revision,
  active,
}: {
  portfolioId: string;
  revision?: number;
  active: boolean;
}) {
  const [offset, setOffset] = useState(0);
  const query = useRead<CorporatePortfolio | NativeCorporatePortfolio>({
    path: `/v2/portfolios/${portfolioId}/corporate-actions?offset=${offset}`,
    revision,
    enabled: active,
  });
  return (
    <section className="panel" aria-label="Derechos y eventos de cartera">
      <h2>Derechos y eventos</h2>
      <QueryStatus label="Derechos y eventos" query={query} />
      {query.data && (
        <>
          <CorporateBalances value={query.data} />
          <CorporatePager
            offset={offset}
            total={query.data.total}
            onChange={setOffset}
          />
        </>
      )}
    </section>
  );
}

export function CorporatePanel({
  catalog,
  portfolio,
  active,
  revision,
  refresh,
  onError,
}: {
  catalog: CatalogResponse;
  portfolio?: PortfolioRecord;
  active: boolean;
  revision?: number;
  refresh: () => Promise<void>;
  onError: (v: string) => void;
}) {
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState('');
  const [day, setDay] = useState('');
  const [cut, setCut] = useState('');
  const [appOffset, setAppOffset] = useState(0);
  const events = useRead<CorporateCatalog>({
    path: `/v2/corporate-events?offset=${offset}`,
    revision,
    enabled: active,
  });
  const native = portfolio?.accounting_policy === 'atlas-accounting-v2';
  const applications = useRead<CorporatePortfolio | NativeCorporatePortfolio>({
    path: portfolio
      ? `/v2/portfolios/${portfolio.id}/corporate-actions?offset=${appOffset}${cut ? `&as_of_date=${cut}` : ''}`
      : null,
    revision: `${revision ?? ''}:${portfolio?.revision ?? ''}`,
    enabled: active && native,
  });
  // Portfolio and rights refresh independently. Initialize the keyed form only
  // from the matching revision; useRead retains older data while refreshing.
  const currentApplications =
    applications.data?.portfolio_id === portfolio?.id &&
    applications.data?.portfolio_revision === portfolio?.revision
      ? applications.data
      : null;
  const selected = events.data?.events.find((event) => event.id === selectedId);
  const refreshAll = async () => {
    await refresh();
    await events.refresh();
    if (native) await applications.refresh();
  };
  return (
    <section className="panel corporate-panel" aria-label="Dividendos y splits">
      <div className="panel-heading">
        <h2>Dividendos y splits</h2>
        <span className="tag neutral">EUR / USD · eventos revisionados</span>
      </div>
      <p className="muted">
        Contrasta la fuente del evento y revisa su efecto en cada cartera. Un
        evento descargado o importado no se aplica automáticamente.
      </p>
      <QueryStatus label="Eventos corporativos" query={events} />
      {events.data && (
        <>
          <DataTable
            heads={[
              'Evento',
              'Fuente / ID externo',
              'Pago',
              'Bruto / ratio',
              'Estado',
              'Acción',
            ]}
            rows={events.data.events.map((event) => [
              eventLabel(event, catalog),
              events
                .data!.sources.filter((source) => source.event_id === event.id)
                .map((source) => `${source.source} · ${source.external_id}`)
                .join(' / '),
              event.payment_date || '—',
              event.gross_per_unit
                ? `${event.gross_per_unit} ${event.currency}/título`
                : `${event.ratio_numerator}:${event.ratio_denominator}`,
              event.cancelled
                ? 'Cancelado'
                : event.verified
                  ? 'Evidencia contrastada'
                  : 'Propuesta pendiente',
              <Button
                key={event.id}
                variant="outline"
                aria-pressed={selectedId === event.id}
                onClick={() => setSelectedId(event.id)}
              >
                Seleccionar evento
              </Button>,
            ])}
            emptyMessage="Importa eventos mediante CSV para revisar sus derechos, cobros o splits."
          />
          <CorporatePager
            offset={offset}
            total={events.data.total}
            onChange={(n) => {
              setOffset(n);
              setSelectedId('');
            }}
          />
          {selected && (
            <EventEvidence
              key={selected.id + ':' + selected.revision}
              event={selected}
            />
          )}
          <CorporateEventForm
            key={`${events.data.revision}:${catalog.revision}:${selectedId}`}
            catalog={catalog}
            events={events.data}
            selected={selected}
            refresh={refreshAll}
            onError={onError}
          />
          {selected &&
            native &&
            portfolio &&
            (currentApplications ? (
              <CorporateApplicationForm
                key={`${portfolio.id}:${portfolio.revision}:${events.data.revision}:${selected.id}`}
                portfolio={portfolio}
                event={selected}
                current={currentApplications}
                refresh={refreshAll}
                onError={onError}
              />
            ) : (
              <output>
                Esperando los derechos actualizados de la cartera para preparar
                la aplicación.
              </output>
            ))}
          {selected && !native && (
            <p>
              Para aplicar eventos D5, selecciona una cartera con libro exacto.
              Las carteras clásicas conservan sus movimientos y convenciones
              originales.
            </p>
          )}
        </>
      )}
      {native && portfolio && (
        <>
          <h3>Aplicaciones a «{portfolio.name}»</h3>
          <form
            className="form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              setCut(day);
              setAppOffset(0);
            }}
          >
            <Field label="Corte de derechos y eventos">
              <Input
                type="date"
                value={day}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) => setDay(e.target.value)}
              />
            </Field>
            <Button type="submit" variant="outline">
              Consultar derechos al corte
            </Button>
          </form>
          <QueryStatus label="Aplicaciones corporativas" query={applications} />
          {applications.data && (
            <>
              <CorporateBalances value={applications.data} />
              <CorporatePager
                offset={appOffset}
                total={applications.data.total}
                onChange={setAppOffset}
              />
            </>
          )}
          <CorporateHistory
            key={portfolio.id + ':' + portfolio.revision}
            portfolioId={portfolio.id}
            revision={revision}
            active={active}
          />
        </>
      )}
      <CorporateHistory revision={revision} active={active} />
    </section>
  );
}

function EventEvidence({ event }: { event: CorporateEvent }) {
  const [draft, setDraft] = useState(String(event.revision));
  const [version, setVersion] = useState(event.revision);
  const query = useRead<CorporateEvent>({
    path: `/v2/corporate-events/${event.id}/versions/${version}`,
  });
  const value = query.data || event;
  return (
    <details className="details">
      <summary>Identidad y evidencia del evento seleccionado</summary>
      <p className="mono">{event.id}</p>
      <form
        className="form-grid"
        onSubmit={(e) => {
          e.preventDefault();
          setVersion(Number(draft));
        }}
      >
        <Field label="Revisión histórica del evento">
          <Input
            type="number"
            min={1}
            max={event.revision}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </Field>
        <Button type="submit" variant="outline">
          Consultar revisión del evento
        </Button>
      </form>
      <QueryStatus label="Evidencia del evento" query={query} />
      <p>
        Revisión {value.revision} · {value.source_reference}
      </p>
      <p>{value.evidence || 'Evidencia pendiente de contrastar.'}</p>
      <p>
        Disponibilidad histórica: {value.available_at || 'Sin acreditar'} ·
        Fecha efectiva: {value.effective_date || 'Desconocida'} · Motivo:{' '}
        {value.reason}
      </p>
    </details>
  );
}

function CorporateHistory({
  portfolioId,
  revision,
  active,
}: {
  portfolioId?: string;
  revision?: number;
  active: boolean;
}) {
  const [offset, setOffset] = useState(0);
  const [document, setDocument] = useState('');
  const [open, setOpen] = useState(false);
  const path = portfolioId
    ? `/portfolios/${portfolioId}/corporate-documents`
    : '/corporate-documents';
  const query = useRead<CorporateDocuments>({
    path: `${path}?offset=${offset}`,
    revision,
    enabled: active && open,
  });
  const detail = useRead<CorporateDocument>({
    path: document ? `${path}/${document}` : null,
    enabled: active && open,
  });
  function download() {
    if (!detail.data) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(detail.data, null, 2)], {
        type: 'application/json',
      }),
    );
    const link = window.document.createElement('a');
    link.href = url;
    link.download = `atlas-evento-${detail.data.id}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <details
      className="details"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>
        {portfolioId
          ? 'Historial de aplicaciones y evidencia'
          : 'Historial de importaciones y revisiones de eventos'}
      </summary>
      <QueryStatus label="Historial corporativo" query={query} />
      {query.data && (
        <>
          <DataTable
            heads={['Fecha', 'Operación', 'Evidencia']}
            rows={query.data.documents.map((doc) => [
              doc.created_at,
              doc.kind,
              <Button
                variant="outline"
                key={doc.id}
                onClick={() => setDocument(doc.id)}
              >
                Consultar evidencia
              </Button>,
            ])}
          />
          <CorporatePager
            offset={offset}
            total={query.data.total}
            onChange={setOffset}
          />
        </>
      )}
      {document && <QueryStatus label="Documento corporativo" query={detail} />}
      {detail.data && (
        <div>
          <p>
            {detail.data.kind} · {detail.data.created_at}
          </p>
          <Button variant="outline" onClick={download}>
            Descargar evidencia JSON
          </Button>
        </div>
      )}
    </details>
  );
}
