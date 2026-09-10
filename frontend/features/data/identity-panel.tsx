'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import type {
  CatalogResponse,
  DatasetResponse,
  PortfolioSummary,
  PortfolioDetail,
  PortfolioRecord,
  PriceBinding,
  BindingPreview,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { useAction } from '@/shared/use-action';
import { QueryStatus } from '@/shared/query-status';
import { Field, Choice, DataTable } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { moneyEUR, date } from '@/shared/format';
import { BookWorkspace } from './book-panel';
import { CorporatePanel } from './corporate-panel';
import { MarketWorkspace } from './market-workspace';

export function IdentityPanel({
  portfolios,
  portfolioId,
  selectPortfolio,
  datasets,
  active,
  revision,
  refresh,
  onError,
}: {
  portfolios: PortfolioSummary[];
  portfolioId?: string;
  selectPortfolio: (id: string) => void;
  datasets: DatasetResponse[];
  active: boolean;
  revision?: number;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const catalog = useRead<CatalogResponse>({
    path: '/catalog',
    enabled: active,
    revision,
  });
  const book = useRead<PortfolioDetail>({
    path: portfolioId ? `/portfolios/${portfolioId}` : null,
    enabled: active,
    revision,
  });
  const [name, setName] = useState('');
  const [bookPolicy, setBookPolicy] = useState<
    PortfolioRecord['accounting_policy']
  >('atlas-accounting-v2');
  const action = useAction(onError);
  const refreshAll = async () => {
    await refresh();
    await catalog.refresh();
    await book.refresh();
  };
  return (
    <>
      <section className="panel identity-panel">
        <div className="panel-heading">
          <h2>Cartera y fuentes de valoración</h2>
        </div>
        <p className="muted">
          La cartera conserva su libro al cambiar de precios. El conjunto de la
          cabecera se usa para explorar e investigar.
        </p>
        <Field label="Cartera activa">
          <Choice
            label="Cartera activa"
            value={portfolioId || ''}
            onChange={selectPortfolio}
            options={portfolios.map((p) => ({ value: p.id, label: p.name }))}
          />
        </Field>
        <details className="details">
          <summary>Crear una cartera</summary>
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              void action.run(async () => {
                const created = await api<PortfolioRecord>('/portfolios', {
                  name,
                  accounting_policy: bookPolicy,
                });
                await refresh();
                selectPortfolio(created.id);
                setName('');
              });
            }}
          >
            <Field label="Nombre de cartera">
              <Input
                required
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field label="Formato del libro">
              <Choice
                label="Formato del libro"
                value={bookPolicy}
                onChange={(value) =>
                  setBookPolicy(value as PortfolioRecord['accounting_policy'])
                }
                options={[
                  {
                    value: 'atlas-accounting-v2',
                    label: 'Libro exacto · CSV v2 y conciliación',
                  },
                  {
                    value: 'legacy-eur-v1',
                    label: 'Libro clásico · CSV v1 y gráficos de cartera',
                  },
                ]}
              />
            </Field>
            <Button disabled={action.busy || !name.trim()} type="submit">
              Crear cartera EUR
            </Button>
          </form>
          <p className="muted">
            El libro exacto permite importar y corregir movimientos EUR/USD, y
            valorar su patrimonio en EUR con fuentes explícitas. El libro
            clásico conserva los gráficos y las convenciones anteriores. No se
            cambia la política de carteras existentes.
          </p>
        </details>
        {portfolioId && <QueryStatus label="Libro" query={book} />}
        {book.data && catalog.data && (
          <BookEditor
            key={`${book.data.portfolio.id}:${book.data.portfolio.revision}`}
            detail={book.data}
            catalog={catalog.data}
            datasets={datasets}
            refresh={refreshAll}
            onError={onError}
          />
        )}
      </section>
      {book.data && catalog.data && (
        <BookWorkspace
          key={book.data.portfolio.id + ':' + book.data.portfolio.revision}
          portfolio={book.data.portfolio}
          catalog={catalog.data}
          active={active}
          refresh={refreshAll}
          onError={onError}
        />
      )}
      {catalog.data && (
        <MarketWorkspace
          catalog={catalog.data}
          portfolio={
            book.data && book.data.portfolio.id === portfolioId
              ? book.data.portfolio
              : undefined
          }
          active={active}
          revision={revision}
          refresh={refreshAll}
          onError={onError}
        />
      )}
      {catalog.data && (
        <CorporatePanel
          catalog={catalog.data}
          portfolio={book.data?.portfolio}
          active={active}
          revision={revision}
          refresh={refreshAll}
          onError={onError}
        />
      )}
      <section className="panel identity-panel">
        <div className="panel-heading">
          <h2>Instrumentos y cotizaciones</h2>
        </div>
        <QueryStatus label="Catálogo" query={catalog} />
        {catalog.data && (
          <>
            <p className="muted">
              Catálogo · revisión {catalog.data.revision}. Las identidades
              importadas son locales y no están verificadas.
            </p>
            <DataTable
              heads={[
                'Instrumento',
                'Mercado',
                'Moneda',
                'Símbolos',
                'Identidad',
              ]}
              rows={catalog.data.listings.map((listing) => [
                catalog.data!.instruments.find(
                  (i) => i.id === listing.instrument_id,
                )?.name,
                listing.market || 'Sin verificar',
                listing.currency,
                catalog
                  .data!.aliases.filter((a) => a.listing_id === listing.id)
                  .map((a) => a.symbol)
                  .join(', '),
                <code key="id" title={listing.id}>
                  {listing.id.slice(0, 8)}
                </code>,
              ])}
            />
            <CatalogForms
              catalog={catalog.data}
              refresh={refreshAll}
              onError={onError}
            />
            <details className="details">
              <summary>Vigencia y procedencia de los símbolos</summary>
              <DataTable
                heads={[
                  'Símbolo',
                  'Proveedor',
                  'Desde',
                  'Hasta (exclusivo)',
                  'Fuente',
                ]}
                rows={catalog.data.aliases.map((alias) => [
                  alias.symbol,
                  alias.provider,
                  alias.valid_from
                    ? date(alias.valid_from)
                    : 'Sin límite declarado',
                  alias.valid_to
                    ? date(alias.valid_to)
                    : 'Sin límite declarado',
                  alias.source,
                ])}
              />
            </details>
          </>
        )}
      </section>
    </>
  );
}

function listingOptions(catalog: CatalogResponse) {
  return catalog.listings.map((listing) => ({
    value: listing.id,
    label: `${catalog.instruments.find((i) => i.id === listing.instrument_id)?.name || listing.id} · ${listing.market || 'local'} · ${listing.currency} · ${listing.id.slice(0, 8)}`,
  }));
}

function BookEditor({
  detail,
  catalog,
  datasets,
  refresh,
  onError,
}: {
  detail: PortfolioDetail;
  catalog: CatalogResponse;
  datasets: DatasetResponse[];
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [bindings, setBindings] = useState<PriceBinding[]>(
    detail.portfolio.bindings,
  );
  const [preview, setPreview] = useState<BindingPreview | null>(null);
  const [message, setMessage] = useState('');
  const action = useAction(onError);
  const set = (next: PriceBinding[]) => {
    setBindings(next);
    setPreview(null);
    setMessage('');
  };
  const edit = (index: number, patch: Partial<PriceBinding>) =>
    set(bindings.map((b, i) => (i === index ? { ...b, ...patch } : b)));
  const submit = (commit: boolean) =>
    void action.run(async () => {
      try {
        const result = await api<BindingPreview>(
          `/portfolios/${detail.portfolio.id}/bindings`,
          {
            bindings,
            commit,
            preview_token: commit ? preview?.preview_token : undefined,
          },
        );
        if (commit) {
          setPreview(null);
          setMessage('Fuentes guardadas. Los movimientos se conservan.');
          await refresh();
        } else setPreview(result);
      } catch (error) {
        setPreview(null);
        throw error;
      }
    });
  return (
    <>
      <p className="muted">
        {detail.entries.length} movimientos · revisión{' '}
        {detail.portfolio.revision} · EUR
      </p>
      <details className="details">
        <summary>Configurar fuentes de precios</summary>
        <p className="muted">
          Elige la cotización y su serie expresamente. La versión elegida queda
          fijada hasta que confirmes otro cambio.
        </p>
        {bindings.map((binding, index) => {
          const dataset = datasets.find((d) => d.id === binding.dataset_id);
          if (!dataset && binding.dataset_id)
            return (
              <fieldset
                className="binding-row"
                key={index}
                disabled={action.busy}
              >
                <legend>Fuente {index + 1}</legend>
                <p>
                  {binding.symbol} · versión {binding.dataset_version} ·{' '}
                  <code>{binding.dataset_id.slice(0, 12)}</code>
                </p>
                <p className="muted">
                  Serie nativa fijada. Consulta su evidencia o elige otra
                  versión en Precios y tipos de cambio.
                </p>
                <Button
                  variant="outline"
                  onClick={() => set(bindings.filter((_, i) => i !== index))}
                >
                  Quitar fuente {index + 1}
                </Button>
              </fieldset>
            );
          const versions = datasets.map((d) => ({
            value: `${d.id}:${d.version}`,
            label: `${d.name} · v${d.version}`,
          }));
          if (dataset && dataset.version !== binding.dataset_version)
            versions.push({
              value: `${dataset.id}:${binding.dataset_version}`,
              label: `${dataset.name} · v${binding.dataset_version} (fijada)`,
            });
          return (
            <fieldset
              className="binding-row"
              key={index}
              disabled={action.busy}
            >
              <legend>Fuente {index + 1}</legend>
              <div className="form-grid">
                <Field label={`Cotización ${index + 1}`}>
                  <Choice
                    label={`Cotización ${index + 1}`}
                    value={binding.listing_id}
                    onChange={(listing_id) => edit(index, { listing_id })}
                    options={listingOptions(catalog)}
                  />
                </Field>
                <Field label={`Precios ${index + 1}`}>
                  <Choice
                    label={`Precios ${index + 1}`}
                    value={
                      binding.dataset_id
                        ? `${binding.dataset_id}:${binding.dataset_version}`
                        : ''
                    }
                    options={versions}
                    onChange={(value) => {
                      const [dataset_id, version] = value.split(':');
                      edit(index, {
                        dataset_id,
                        dataset_version: Number(version),
                        symbol: '',
                      });
                    }}
                  />
                </Field>
                <Field label={`Símbolo de precios ${index + 1}`}>
                  <Choice
                    label={`Símbolo de precios ${index + 1}`}
                    value={binding.symbol}
                    onChange={(symbol) => edit(index, { symbol })}
                    options={(dataset?.manifest.symbols || []).map(
                      (symbol) => ({ value: symbol, label: symbol }),
                    )}
                  />
                </Field>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => set(bindings.filter((_, i) => i !== index))}
                >
                  Quitar fuente {index + 1}
                </Button>
              </div>
            </fieldset>
          );
        })}
        <div className="actions">
          <Button
            variant="outline"
            disabled={action.busy || bindings.length >= 100}
            onClick={() =>
              set([
                ...bindings,
                {
                  listing_id: '',
                  dataset_id: '',
                  dataset_version: 1,
                  symbol: '',
                },
              ])
            }
          >
            Añadir fuente
          </Button>
          <Button
            disabled={
              action.busy ||
              bindings.some((b) => !b.listing_id || !b.dataset_id || !b.symbol)
            }
            onClick={() => submit(false)}
          >
            Previsualizar fuentes
          </Button>
        </div>
        {preview && (
          <output className="notice vertical">
            <strong>
              Valor con estas fuentes:{' '}
              {preview.value ? moneyEUR(preview.value.nav) : 'No disponible'}
            </strong>
            <span>
              {detail.entries.length} movimientos conservados ·{' '}
              {bindings.length} fuentes
            </span>
            <Button disabled={action.busy} onClick={() => submit(true)}>
              Confirmar fuentes
            </Button>
          </output>
        )}
        {message && <output>{message}</output>}
      </details>
      <details className="details">
        <summary>Consultar movimientos</summary>
        <DataTable
          heads={[
            'Fecha',
            'Orden del día',
            'Tipo',
            'Símbolo original',
            'Cantidad',
            'Importe',
            'ID original',
          ]}
          rows={detail.entries.map((entry) => [
            date(entry.date),
            entry.day_sequence,
            scalar(entry.event.kind),
            scalar(entry.event.symbol),
            scalar(entry.event.quantity),
            scalar(entry.event.amount),
            scalar(entry.event.id),
          ])}
        />
      </details>
    </>
  );
}

function scalar(value: unknown) {
  return typeof value === 'string' || typeof value === 'number'
    ? String(value)
    : '—';
}

function CatalogForms({
  catalog,
  refresh,
  onError,
}: {
  catalog: CatalogResponse;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [name, setName] = useState('');
  const [type, setType] = useState('unknown');
  const [instrumentId, setInstrumentId] = useState('');
  const [currency, setCurrency] = useState('EUR');
  const [market, setMarket] = useState('');
  const [listingId, setListingId] = useState('');
  const [symbol, setSymbol] = useState('');
  const [provider, setProvider] = useState('csv');
  const [source, setSource] = useState('Declaración del usuario');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [message, setMessage] = useState('');
  const action = useAction(onError);
  const add = (kind: string, values: object) =>
    void action.run(async () => {
      setMessage('');
      try {
        await api(`/catalog/${kind}`, {
          expected_revision: catalog.revision,
          ...values,
        });
        setMessage('Registro añadido al catálogo.');
      } finally {
        await refresh();
      }
    });
  return (
    <details className="details">
      <summary>Añadir instrumentos, cotizaciones o símbolos</summary>
      <p className="muted">
        Primero registra el instrumento, después su cotización y por último los
        símbolos con su vigencia. Un código o nombre coincidente no fusiona
        registros.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          add('instruments', { name, instrument_type: type, source });
        }}
      >
        <div className="form-grid">
          <Field label="Nombre del instrumento">
            <Input
              required
              value={name}
              maxLength={100}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Field label="Tipo de instrumento">
            <Choice
              label="Tipo de instrumento"
              value={type}
              onChange={setType}
              options={[
                { value: 'unknown', label: 'Sin clasificar' },
                { value: 'equity', label: 'Acción' },
                { value: 'ETF', label: 'ETF' },
              ]}
            />
          </Field>
          <Field label="Procedencia de la identidad">
            <Input
              required
              minLength={3}
              maxLength={500}
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={action.busy}>
            Registrar instrumento
          </Button>
        </div>
      </form>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          add('listings', {
            instrument_id: instrumentId,
            currency,
            market: market.trim() || null,
          });
        }}
      >
        <div className="form-grid">
          <Field label="Instrumento para cotización">
            <Choice
              label="Instrumento para cotización"
              value={instrumentId}
              onChange={setInstrumentId}
              options={catalog.instruments.map((i) => ({
                value: i.id,
                label: `${i.name} · ${i.id.slice(0, 8)}`,
              }))}
            />
          </Field>
          <Field label="Mercado declarado">
            <Input
              value={market}
              maxLength={50}
              placeholder="Vacío si se desconoce"
              onChange={(e) => setMarket(e.target.value)}
            />
          </Field>
          <Field label="Moneda de cotización">
            <Choice
              label="Moneda de cotización"
              value={currency}
              onChange={setCurrency}
              options={[
                { value: 'EUR', label: 'EUR' },
                { value: 'USD', label: 'USD · solo catálogo' },
              ]}
            />
          </Field>
          <Button type="submit" disabled={action.busy || !instrumentId}>
            Registrar cotización
          </Button>
        </div>
      </form>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          add('aliases', {
            listing_id: listingId,
            symbol,
            provider,
            source,
            valid_from: from || null,
            valid_to: to || null,
          });
        }}
      >
        <div className="form-grid">
          <Field label="Cotización para símbolo">
            <Choice
              label="Cotización para símbolo"
              value={listingId}
              onChange={setListingId}
              options={listingOptions(catalog)}
            />
          </Field>
          <Field label="Símbolo del proveedor">
            <Input
              required
              maxLength={50}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
            />
          </Field>
          <Field label="Proveedor del símbolo">
            <Input
              required
              maxLength={100}
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            />
          </Field>
          <Field label="Vigente desde">
            <Input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
          </Field>
          <Field label="Vigente hasta (exclusivo)">
            <Input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={action.busy || !listingId}>
            Registrar símbolo
          </Button>
        </div>
      </form>
      {message && <output>{message}</output>}
    </details>
  );
}
