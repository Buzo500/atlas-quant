'use client';
import type {
  DatasetResponse,
  PortfolioResponse,
  PortfolioDetail,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import {
  moneyEUR as money,
  percent as pct,
  number,
  date,
} from '@/shared/format';
import { Metric, DataTable } from '@/shared/ui';
import { Curve } from '@/components/atlas/curve';
import { Wallet } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { qualityLabel } from '@/shared/quality';
import { BookSummary } from '@/features/data/book-panel';

export function PortfolioPanel({
  dataset,
  portfolioId,
  portfolioRevision,
  portfolioName,
  auditSequence,
  active,
  connected,
  stateLoaded,
  busy,
  onImport,
  onDemo,
}: {
  dataset: DatasetResponse | undefined;
  portfolioId?: string;
  portfolioRevision?: number;
  portfolioName?: string;
  auditSequence?: number;
  active: boolean;
  connected: boolean;
  stateLoaded: boolean;
  busy: boolean;
  onImport: () => void;
  onDemo: () => Promise<void>;
}) {
  const portfolioQuery = useRead<PortfolioResponse | PortfolioDetail>({
    path: portfolioId
      ? `/portfolios/${portfolioId}`
      : dataset
        ? '/datasets/' + dataset.id + '/portfolio'
        : null,
    revision: `${portfolioId ? portfolioRevision : dataset?.version}:${auditSequence}`,
    enabled: active,
  });
  const detail =
    portfolioQuery.data && 'value' in portfolioQuery.data
      ? portfolioQuery.data
      : null;
  const portfolio = detail
    ? detail.value
    : (portfolioQuery.data as PortfolioResponse | null);
  const identity = portfolioId || dataset?.id;
  const nativeBook =
    detail?.portfolio.accounting_policy === 'atlas-accounting-v2';
  return (
    <>
      {(dataset || portfolioId) && (
        <QueryStatus label="Cartera" query={portfolioQuery} />
      )}
      {portfolioId && (
        <p className="muted">
          {portfolioName || 'Cartera'} · revisión{' '}
          {detail?.context.portfolio_revision ?? portfolioRevision} ·{' '}
          {nativeBook
            ? 'Libro contable EUR v2'
            : 'Fuentes de valoración configuradas en Datos'}
        </p>
      )}
      {detail?.portfolio.accounting_policy === 'atlas-accounting-v2' &&
        portfolioId && (
          <BookSummary
            portfolioId={portfolioId}
            revision={portfolioRevision}
            active={active}
          />
        )}
      {detail?.status === 'unavailable' &&
        detail.portfolio.accounting_policy !== 'atlas-accounting-v2' && (
          <output className="notice">
            {detail.warnings.join(' ')} El libro se conserva; revisa sus fuentes
            en Datos.
          </output>
        )}
      {!!detail?.quality?.length && (
        <p className="notice">
          Valoración heredada al {date(detail.quality[0].end)}. Calidad de sus
          precios:{' '}
          {detail.quality
            .map(
              (q) => `${q.symbol}: ${qualityLabel[q.capabilities.valuation]}`,
            )
            .join(' · ')}
          . Esta lectura conserva la política EUR original; no acredita
          conciliación ni rentabilidad definitiva.
        </p>
      )}
      {!nativeBook && (
        <div className="stats portfolio-stats">
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
      )}
      {portfolio?.curve?.length ? (
        <div className="portfolio-layout">
          <section className="panel positions-panel">
            <div className="panel-heading">
              <div>
                <h2>Posiciones</h2>
                <p className="muted">Distribución actual de activos</p>
              </div>
              <span className="tag neutral">
                {portfolio.positions.length} activos
              </span>
            </div>
            <DataTable
              key={identity}
              heads={[
                'Activo',
                'Cantidad',
                'Último precio',
                'Valor',
                'Peso',
                'P&L no realizado',
              ]}
              numericColumns={[1, 2, 3, 4, 5]}
              emptyMessage="No hay posiciones abiertas en esta cartera."
              rows={portfolio.positions.map((p) => [
                <strong className="symbol" key="symbol">
                  {p.symbol}
                </strong>,
                number(p.quantity, {
                  maximumFractionDigits: 6,
                }),
                <span key="price">
                  {money(p.price)}
                  <time className="price-date" dateTime={p.price_date}>
                    {p.price_date &&
                    p.price_date < (portfolio.curve.at(-1)?.date ?? '')
                      ? 'Precio anterior · '
                      : ''}
                    {date(p.price_date)}
                  </time>
                </span>,
                money(p.market_value),
                pct(p.weight),
                <span
                  key="pnl"
                  className={p.unrealized_pnl >= 0 ? 'positive' : 'negative'}
                >
                  {money(p.unrealized_pnl)}
                </span>,
              ])}
            />
            <div className="table-summary">
              <span>Aportaciones netas</span>
              <strong>{money(portfolio.net_contributions)}</strong>
            </div>
          </section>
          <section className="panel portfolio-curve">
            <div className="panel-heading">
              <div>
                <h2>Evolución del patrimonio</h2>
                <p className="muted">Valoración diaria · EUR</p>
              </div>
            </div>
            <Curve
              key={`${identity}:${detail?.context.portfolio_revision ?? dataset?.version}`}
              data={portfolio.curve}
            />
          </section>
        </div>
      ) : detail?.status === 'unavailable' ? null : (dataset || portfolioId) &&
        (portfolioQuery.loading || portfolioQuery.error) ? (
        <section className="panel empty">
          <h2>
            {portfolioQuery.loading
              ? 'Cargando cartera…'
              : 'No se pudo consultar la cartera'}
          </h2>
          <p>
            Los movimientos se mostrarán cuando termine una consulta correcta.
          </p>
        </section>
      ) : (
        <section className="panel">
          <div className="empty">
            <Wallet size={32} />
            <h2>
              {!connected && !stateLoaded
                ? 'Conectando con ATLAS'
                : dataset
                  ? 'Importa tus movimientos'
                  : 'Empieza con un conjunto de datos'}
            </h2>
            <p>
              {dataset
                ? 'Añade depósitos, compras y otros movimientos desde Datos para construir tu cartera.'
                : 'Explora tres activos ficticios con la demostración o importa tu historial de precios y operaciones.'}
            </p>
            <div className="actions centered">
              <Button onClick={onImport}>Importar datos</Button>
              <Button
                variant="outline"
                disabled={busy || !connected}
                onClick={onDemo}
              >
                Explorar demo
              </Button>
            </div>
          </div>
        </section>
      )}
      {portfolio && portfolio.warnings.length > 0 && (
        <details className="details valuation-notes">
          <summary>
            Convenciones de valoración{' '}
            <span className="muted">({portfolio.warnings.length})</span>
          </summary>
          <ul>
            {portfolio.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
