'use client';

import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import type {
  BookBalance,
  BookDetail,
  BookPreview,
  ReconciliationPreview,
  CatalogResponse,
  BookDocuments,
  BookDocument,
  ReconciliationRow,
  ImportInput,
  ReconciliationInput,
  CorrectionInput,
  PortfolioRecord,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { useAction } from '@/shared/use-action';
import { QueryStatus } from '@/shared/query-status';
import { Choice, DataTable, Field } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { date } from '@/shared/format';
import {
  BookCorporateFields,
  corporateBookInput,
  emptyCorporateDraft,
} from './book-corporate-fields';

const today = () => new Date().toISOString().slice(0, 10);
type Review = BookPreview | ReconciliationPreview;
type Mapping = { reference: string; listing: string };
const scalar = (v: unknown) =>
  typeof v === 'string' || typeof v === 'number' ? String(v) : '—';

function listingLabel(id: string, catalog?: CatalogResponse) {
  const listing = catalog?.listings.find((item) => item.id === id);
  return listing
    ? (catalog?.instruments.find((i) => i.id === listing.instrument_id)?.name ||
        id.slice(0, 8)) +
        ' · ' +
        (listing.market || 'local')
    : id.slice(0, 8);
}

export function ExactBalance({
  value,
  catalog,
}: {
  value: BookBalance;
  catalog?: CatalogResponse;
}) {
  return (
    <div className="book-balance">
      <p>
        <strong>Efectivo: {value.cash} EUR</strong> · Aportaciones netas:{' '}
        {value.net_contributions} EUR · al {date(value.as_of_date)}
      </p>
      <DataTable
        heads={['Cotización', 'Cantidad', 'Coste pendiente (EUR)']}
        numericColumns={[1, 2]}
        rows={value.positions.map((p) => [
          listingLabel(p.listing_id, catalog),
          p.quantity,
          p.cost_basis,
        ])}
        emptyMessage="Sin posiciones abiertas en este corte."
      />
      {value.realized_pnl !== null && (
        <p className="muted">
          Resultado realizado de ventas: {value.realized_pnl} EUR. No representa
          la rentabilidad total de la cartera.
        </p>
      )}
      {value.warnings.map((warning) => (
        <p className="muted" key={warning}>
          {warning}
        </p>
      ))}
    </div>
  );
}

export function BookSummary({
  portfolioId,
  revision,
  active,
}: {
  portfolioId: string;
  revision?: number;
  active: boolean;
}) {
  const query = useRead<BookDetail>({
    path: '/portfolios/' + portfolioId + '/book',
    revision,
    enabled: active,
  });
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Libro contable EUR</h2>
      </div>
      <QueryStatus label="Saldos contables" query={query} />
      {query.data && <ExactBalance value={query.data.balance} />}
      <p className="muted">
        Saldos y cantidades sin usar precios. La valoración y la rentabilidad
        del libro v2 se incorporarán en las siguientes entregas contables.
      </p>
    </section>
  );
}

function Differences({
  rows,
  catalog,
}: {
  rows: ReconciliationRow[];
  catalog: CatalogResponse;
}) {
  return (
    <DataTable
      heads={['Concepto', 'Libro', 'Extracto', 'Diferencia', 'Resultado']}
      numericColumns={[1, 2, 3]}
      rows={rows.map((r) => [
        r.record_type === 'cash'
          ? 'Efectivo EUR'
          : listingLabel(r.listing_id!, catalog),
        r.book,
        r.reference,
        r.difference,
        r.matched ? 'Coincide' : 'Pendiente de resolver',
      ])}
    />
  );
}

function PageButtons({
  offset,
  total,
  limit,
  busy,
  setOffset,
  label,
}: {
  offset: number;
  total: number;
  limit: number;
  busy: boolean;
  setOffset: (n: number) => void;
  label: string;
}) {
  if (total <= limit) return null;
  return (
    <nav className="actions" aria-label={label}>
      <Button
        type="button"
        variant="outline"
        disabled={busy || offset === 0}
        onClick={() => setOffset(Math.max(0, offset - limit))}
      >
        Bloque anterior
      </Button>
      <span>
        {offset + 1}–{Math.min(offset + limit, total)} de {total}
      </span>
      <Button
        type="button"
        variant="outline"
        disabled={busy || offset + limit >= total}
        onClick={() => setOffset(offset + limit)}
      >
        Bloque siguiente
      </Button>
    </nav>
  );
}

export function BookWorkspace({
  portfolio,
  catalog,
  active,
  refresh,
  onError,
}: {
  portfolio: PortfolioRecord;
  catalog: CatalogResponse;
  active: boolean;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [draftDay, setDraftDay] = useState(today);
  const [day, setDay] = useState(today);
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState(false);
  const [documentsRevision, setDocumentsRevision] = useState(0);
  const query = useRead<BookDetail>({
    path:
      '/portfolios/' +
      portfolio.id +
      '/book?as_of_date=' +
      day +
      '&offset=' +
      offset,
    revision: portfolio.revision,
    enabled: active,
  });
  const refreshAll = async () => {
    await refresh();
    await query.refresh();
    setDocumentsRevision((value) => value + 1);
  };
  return (
    <section className="panel book-workspace" aria-label="Libro y conciliación">
      <div className="panel-heading">
        <h2>Libro y conciliación</h2>
        <span className="tag neutral">EUR · revisión {portfolio.revision}</span>
      </div>
      <p className="muted">
        Comprueba efectivo y cantidades contra un extracto. Guardar diferencias
        no modifica el libro ni acredita la calidad de los precios.
      </p>
      <form
        className="form-grid"
        onSubmit={(event) => {
          event.preventDefault();
          setDay(draftDay);
          setOffset(0);
        }}
      >
        <Field label="Fecha de corte del libro">
          <Input
            type="date"
            required
            max={today()}
            value={draftDay}
            onChange={(e) => setDraftDay(e.target.value)}
          />
        </Field>
        <Button type="submit">Consultar libro al corte</Button>
      </form>
      <QueryStatus label="Libro exacto" query={query} />
      {query.data && (
        <>
          <ExactBalance value={query.data.balance} catalog={catalog} />
          <details className="details">
            <summary>Movimientos efectivos del corte</summary>
            <DataTable
              heads={[
                'Fecha',
                'Orden',
                'Tipo',
                'Cotización',
                'ID externo/original',
                'Cantidad',
                'Bruto/importe',
                'Comisión',
              ]}
              rows={query.data.entries.map((entry) => [
                date(entry.date),
                entry.day_sequence,
                scalar(entry.event.kind),
                entry.listing_id
                  ? listingLabel(entry.listing_id, catalog)
                  : '—',
                scalar(entry.event.external_id ?? entry.event.id),
                scalar(entry.event.quantity),
                scalar(entry.event.gross_amount ?? entry.event.amount),
                scalar(entry.event.fee_amount ?? entry.event.fee),
              ])}
            />
            <PageButtons
              offset={offset}
              total={query.data.total}
              limit={100}
              busy={query.loading}
              setOffset={setOffset}
              label="Bloques de movimientos"
            />
          </details>
          <Button
            variant="outline"
            onClick={() => setEditing(!editing)}
            aria-expanded={editing}
          >
            Revisar un lote o extracto
          </Button>
          {editing && (
            <BookReview
              key={portfolio.id + ':' + portfolio.revision}
              portfolio={portfolio}
              catalog={catalog}
              entries={query.data.entries}
              sources={query.data.sources}
              refresh={refreshAll}
              onError={onError}
            />
          )}
        </>
      )}
      <BookHistory
        portfolio={portfolio}
        active={active}
        catalog={catalog}
        revision={documentsRevision}
      />
    </section>
  );
}

function BookReview({
  portfolio,
  catalog,
  entries,
  sources,
  refresh,
  onError,
}: {
  portfolio: PortfolioRecord;
  catalog: CatalogResponse;
  entries: BookDetail['entries'];
  sources: BookDetail['sources'];
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const native = portfolio.accounting_policy === 'atlas-accounting-v2';
  const [mode, setMode] = useState(native ? 'import' : 'reconciliation');
  const [source, setSource] = useState(sources[0]?.source || '');
  const [account, setAccount] = useState(sources[0]?.source_account || '');
  const [day, setDay] = useState(today);
  const [csv, setCsv] = useState('');
  const [mapping, setMapping] = useState<Mapping[]>([]);
  const [explanations, setExplanations] = useState<
    { id: string; note: string }[]
  >([]);
  const [complete, setComplete] = useState(false);
  const [eventId, setEventId] = useState('');
  const [correction, setCorrection] = useState('void');
  const [reason, setReason] = useState('');
  const [corporate, setCorporate] = useState(emptyCorporateDraft);
  const [preview, setPreview] = useState<Review | null>(null);
  const [message, setMessage] = useState('');
  const mounted = useRef(true);
  const action = useAction(onError);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const invalidate = () => {
    setPreview(null);
    setMessage('');
  };
  const voiding = mode === 'correction' && correction === 'void';
  const options = catalog.listings
    .filter((item) => item.currency === 'EUR')
    .map((item) => ({
      value: item.id,
      label: listingLabel(item.id, catalog) + ' · ' + item.id.slice(0, 8),
    }));

  function body(
    commit: boolean,
    offset = 0,
  ): ImportInput | ReconciliationInput | CorrectionInput {
    if (
      !voiding &&
      (new Set(mapping.map((m) => m.reference.trim())).size !==
        mapping.length ||
        mapping.some((m) => !m.reference.trim() || !m.listing))
    )
      throw new Error(
        'Cada referencia necesita una cotización y no puede repetirse.',
      );
    if (
      !voiding &&
      mode !== 'reconciliation' &&
      (new Set(explanations.map((e) => e.id.trim())).size !==
        explanations.length ||
        explanations.some((e) => !e.id.trim() || !e.note.trim()))
    )
      throw new Error('Cada explicación necesita un ID distinto y un motivo.');
    const reviewed = {
      expected_revision: portfolio.revision,
      commit,
      preview_token: commit ? preview?.preview_token : undefined,
      offset,
      limit: 100,
    };
    const mapped = Object.fromEntries(
      mapping.map((m) => [m.reference.trim(), m.listing]),
    );
    const gross = Object.fromEntries(
      explanations.map((e) => [e.id.trim(), e.note.trim()]),
    );
    if (mode === 'correction')
      return {
        ...reviewed,
        event_id: eventId,
        action: correction as 'void' | 'replace',
        reason,
        csv: voiding ? '' : csv,
        mapping: voiding ? {} : mapped,
        gross_explanations: voiding ? {} : gross,
        ...corporateBookInput(corporate, voiding),
      };
    const common = {
      ...reviewed,
      source,
      source_account: account,
      as_of_date: day,
      csv,
      mapping: mapped,
    };
    if (mode === 'reconciliation') {
      if (!complete)
        throw new Error(
          'Declara que el extracto contiene el efectivo y todas las posiciones de esa cuenta al corte.',
        );
      return {
        ...common,
        format_id: 'atlas-statement-v2',
        complete_statement: true,
      };
    }
    return {
      ...common,
      format_id: 'atlas-ledger-v2',
      gross_explanations: gross,
      ...corporateBookInput(corporate, false),
    };
  }

  function submit(commit: boolean, offset = 0) {
    if (commit && !preview) return;
    void action.run(async () => {
      setMessage('');
      try {
        const route =
          mode === 'import'
            ? 'imports'
            : mode === 'correction'
              ? 'corrections'
              : 'reconciliations';
        const result = await api<Review>(
          '/portfolios/' + portfolio.id + '/' + route,
          body(commit, offset),
        );
        if (!mounted.current) return;
        if (commit) {
          setPreview(null);
          setMessage(
            'Revisión guardada. Consulta el libro y el historial actualizados.',
          );
          await refresh();
        } else setPreview(result);
      } catch (error) {
        if (mounted.current) setPreview(null);
        throw error;
      }
    });
  }

  return (
    <div className="book-review">
      {!native && (
        <p className="notice">
          Esta cartera conserva el libro heredado. Puedes conciliar su extracto;
          la importación v2 y las correcciones requieren crear una cartera con
          libro v2.
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(false);
        }}
      >
        <fieldset disabled={action.busy}>
          <legend>Preparar revisión</legend>
          <div className="form-grid">
            <Field label="Tipo de revisión">
              <Choice
                label="Tipo de revisión"
                value={mode}
                options={
                  native
                    ? [
                        { value: 'import', label: 'Movimientos CSV v2' },
                        {
                          value: 'reconciliation',
                          label: 'Extracto de referencia',
                        },
                        {
                          value: 'correction',
                          label: 'Corrección de movimiento',
                        },
                      ]
                    : [
                        {
                          value: 'reconciliation',
                          label: 'Extracto de referencia',
                        },
                      ]
                }
                onChange={(v) => {
                  setMode(v);
                  setCsv('');
                  setMapping([]);
                  setExplanations([]);
                  setCorporate(emptyCorporateDraft());
                  setComplete(false);
                  invalidate();
                }}
              />
            </Field>
            {mode !== 'correction' && (
              <>
                <Field label="Fuente del extracto">
                  <Input
                    required
                    maxLength={100}
                    value={source}
                    onChange={(e) => {
                      setSource(e.target.value);
                      invalidate();
                    }}
                    placeholder="Nombre estable de la fuente"
                  />
                </Field>
                <Field label="Cuenta de origen">
                  <Input
                    required
                    maxLength={100}
                    value={account}
                    onChange={(e) => {
                      setAccount(e.target.value);
                      invalidate();
                    }}
                    placeholder="Identificador de la cuenta del extracto"
                  />
                </Field>
                <Field label="Fecha del lote o extracto">
                  <Input
                    type="date"
                    required
                    max={today()}
                    value={day}
                    onChange={(e) => {
                      setDay(e.target.value);
                      invalidate();
                    }}
                  />
                </Field>
              </>
            )}
            {mode === 'correction' && (
              <>
                <Field label="Movimiento a corregir">
                  <Choice
                    label="Movimiento a corregir"
                    value={eventId}
                    options={entries.map((entry) => ({
                      value: String(entry.event.id),
                      label:
                        date(entry.date) +
                        ' · ' +
                        scalar(entry.event.kind) +
                        ' · ' +
                        scalar(entry.event.external_id),
                    }))}
                    onChange={(v) => {
                      setEventId(v);
                      invalidate();
                    }}
                  />
                </Field>
                <Field label="Acción de corrección">
                  <Choice
                    label="Acción de corrección"
                    value={correction}
                    options={[
                      {
                        value: 'void',
                        label: 'Anular conservando el original',
                      },
                      {
                        value: 'replace',
                        label: 'Sustituir con una fila CSV v2',
                      },
                    ]}
                    onChange={(v) => {
                      setCorrection(v);
                      invalidate();
                    }}
                  />
                </Field>
                <Field label="Motivo de corrección">
                  <Input
                    required
                    minLength={3}
                    maxLength={500}
                    value={reason}
                    onChange={(e) => {
                      setReason(e.target.value);
                      invalidate();
                    }}
                  />
                </Field>
              </>
            )}
          </div>
          {!voiding && (
            <>
              <p className="muted">
                {mode === 'reconciliation'
                  ? 'Una fila cash EUR y todas las posiciones al mismo cierre. Una posición omitida se declara cero.'
                  : 'Movimientos en EUR, incluidos cobros de dividendos y splits revisados. ID externo y secuencia por fecha obligatorios; FX está pendiente.'}
              </p>
              <a
                className="text-link"
                href={
                  '/api/templates/' +
                  (mode === 'reconciliation'
                    ? 'book-statement'
                    : 'book-movements')
                }
                download
              >
                Descargar plantilla{' '}
                {mode === 'reconciliation' ? 'de extracto' : 'de movimientos'}{' '}
                v2
              </a>
              <Field label="Archivo de libro o extracto">
                <Input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    invalidate();
                    void action.run(async () => {
                      if (file.size > 8_000_000)
                        throw new Error('El archivo supera 8 MB.');
                      const contents = new TextDecoder('utf-8', {
                        fatal: true,
                        ignoreBOM: true,
                      }).decode(await file.arrayBuffer());
                      if (mounted.current) {
                        setCsv(contents);
                        setPreview(null);
                      }
                    });
                  }}
                />
              </Field>
              <Field label="Contenido del libro o extracto">
                <textarea
                  aria-label="Contenido del libro o extracto"
                  required
                  className="book-csv"
                  value={csv}
                  maxLength={8_000_000}
                  onChange={(e) => {
                    setCsv(e.target.value);
                    invalidate();
                  }}
                  spellCheck={false}
                />
              </Field>
              <details
                className="details"
                open={mapping.length > 0 ? true : undefined}
              >
                <summary>Mapeo de referencias a cotizaciones</summary>
                <p className="muted">
                  Copia cada listing_ref usado en el archivo y elige su
                  cotización. No se identifican activos por parecido del ticker.
                </p>
                {mapping.map((m, index) => (
                  <div className="form-grid" key={index}>
                    <Field label={'Referencia CSV ' + (index + 1)}>
                      <Input
                        required
                        value={m.reference}
                        maxLength={100}
                        onChange={(e) => {
                          setMapping(
                            mapping.map((old, i) =>
                              i === index
                                ? { ...old, reference: e.target.value }
                                : old,
                            ),
                          );
                          invalidate();
                        }}
                      />
                    </Field>
                    <Field label={'Cotización CSV ' + (index + 1)}>
                      <Choice
                        label={'Cotización CSV ' + (index + 1)}
                        value={m.listing}
                        options={options}
                        onChange={(v) => {
                          setMapping(
                            mapping.map((old, i) =>
                              i === index ? { ...old, listing: v } : old,
                            ),
                          );
                          invalidate();
                        }}
                      />
                    </Field>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setMapping(mapping.filter((_, i) => i !== index));
                        invalidate();
                      }}
                    >
                      Quitar referencia {index + 1}
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  disabled={mapping.length >= 100}
                  onClick={() => {
                    setMapping([...mapping, { reference: '', listing: '' }]);
                    invalidate();
                  }}
                >
                  Añadir referencia CSV
                </Button>
              </details>
              {mode !== 'reconciliation' && (
                <details className="details">
                  <summary>Explicar diferencias del importe bruto</summary>
                  <p className="muted">
                    Solo si el bruto del extracto difiere de cantidad × precio
                    redondeado al céntimo. Se conserva el importe declarado y tu
                    explicación.
                  </p>
                  {explanations.map((entry, index) => (
                    <div className="form-grid" key={index}>
                      <Field label={'ID de explicación ' + (index + 1)}>
                        <Input
                          required
                          maxLength={100}
                          value={entry.id}
                          onChange={(e) => {
                            setExplanations(
                              explanations.map((old, i) =>
                                i === index
                                  ? { ...old, id: e.target.value }
                                  : old,
                              ),
                            );
                            invalidate();
                          }}
                        />
                      </Field>
                      <Field label={'Explicación del bruto ' + (index + 1)}>
                        <Input
                          required
                          maxLength={500}
                          value={entry.note}
                          onChange={(e) => {
                            setExplanations(
                              explanations.map((old, i) =>
                                i === index
                                  ? { ...old, note: e.target.value }
                                  : old,
                              ),
                            );
                            invalidate();
                          }}
                        />
                      </Field>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setExplanations(
                            explanations.filter((_, i) => i !== index),
                          );
                          invalidate();
                        }}
                      >
                        Quitar explicación {index + 1}
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setExplanations([...explanations, { id: '', note: '' }]);
                      invalidate();
                    }}
                  >
                    Añadir explicación
                  </Button>
                </details>
              )}
            </>
          )}
          {mode === 'reconciliation' && (
            <label className="book-declaration">
              <input
                type="checkbox"
                checked={complete}
                onChange={(e) => {
                  setComplete(e.target.checked);
                  invalidate();
                }}
              />{' '}
              El extracto incluye el efectivo y todas las posiciones de esta
              cuenta al cierre elegido.
            </label>
          )}
          {native && mode !== 'reconciliation' && (
            <BookCorporateFields
              value={corporate}
              voiding={voiding}
              onChange={(value) => {
                setCorporate(value);
                invalidate();
              }}
            />
          )}
          <Button
            type="submit"
            disabled={
              action.busy ||
              (mode === 'correction' && !eventId) ||
              (mode === 'reconciliation' && !complete)
            }
          >
            {action.busy ? 'Revisando…' : 'Previsualizar revisión'}
          </Button>
        </fieldset>
      </form>
      {preview && (
        <section
          className="notice vertical"
          aria-label="Previsualización contable"
        >
          <strong>
            {'differences' in preview
              ? preview.status === 'matched'
                ? 'El extracto coincide'
                : 'Hay diferencias pendientes'
              : preview.added +
                ' nuevos · ' +
                preview.duplicates +
                ' duplicados'}
          </strong>
          {'historical_insertion' in preview &&
            preview.historical_insertion && (
              <p>
                Se ha reconstruido el orden completo, incluida la historia
                posterior. Revisa los movimientos antes de confirmar.
              </p>
            )}
          <ExactBalance value={preview.balance} catalog={catalog} />
          {'differences' in preview ? (
            <Differences rows={preview.differences} catalog={catalog} />
          ) : (
            <DataTable
              heads={[
                'Fecha',
                'Orden',
                'ID externo',
                'Tipo',
                'Cantidad',
                'Bruto',
                'Comisión',
                'Explicación',
              ]}
              rows={preview.entries.map((e) => [
                date(e.date),
                e.day_sequence,
                scalar(e.event.external_id),
                scalar(e.event.kind),
                scalar(e.event.quantity),
                scalar(e.event.gross_amount),
                scalar(e.event.fee_amount),
                scalar(e.event.gross_explanation),
              ])}
            />
          )}
          <PageButtons
            offset={preview.offset}
            total={preview.total}
            limit={preview.limit}
            busy={action.busy}
            setOffset={(n) => submit(false, n)}
            label="Bloques de previsualización"
          />
          <p>
            {mode === 'reconciliation'
              ? 'Guardar conserva la evidencia y las diferencias. No crea movimientos de ajuste.'
              : 'Confirmar modifica el libro de ' +
                portfolio.name +
                ' y conserva su historial.'}
          </p>
          <Button
            type="button"
            disabled={action.busy}
            focusableWhenDisabled={action.busy}
            onClick={() => submit(true)}
          >
            Confirmar revisión contable
          </Button>
        </section>
      )}
      {message && <output>{message}</output>}
    </div>
  );
}

function BookHistory({
  portfolio,
  active,
  catalog,
  revision,
}: {
  portfolio: PortfolioRecord;
  active: boolean;
  catalog: CatalogResponse;
  revision: number;
}) {
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState('');
  const query = useRead<BookDocuments>({
    path:
      '/portfolios/' +
      portfolio.id +
      '/book-documents?offset=' +
      offset +
      '&limit=20',
    revision: portfolio.revision + ':' + revision,
    enabled: active && open,
  });
  const detail = useRead<BookDocument>({
    path: selected
      ? '/portfolios/' + portfolio.id + '/book-documents/' + selected
      : null,
    revision: portfolio.revision + ':' + revision,
    enabled: active && open,
  });
  return (
    <details
      className="details"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>Historial de lotes, extractos y correcciones</summary>
      <QueryStatus label="Historial contable" query={query} />
      {query.data && (
        <>
          <DataTable
            heads={[
              'Tipo',
              'Corte',
              'Fuente / cuenta',
              'Revisión',
              'Resultado',
              'Contexto',
              'Detalle',
            ]}
            rows={query.data.documents.map((d) => [
              d.kind === 'import'
                ? 'Importación'
                : d.kind === 'correction'
                  ? 'Corrección'
                  : 'Conciliación',
              date(d.as_of_date),
              d.source + ' / ' + d.source_account,
              d.portfolio_revision,
              d.status === 'matched'
                ? 'Coincide'
                : d.status === 'differences'
                  ? 'Diferencias'
                  : 'Registrado',
              d.current ? 'Corte vigente' : 'Corte histórico',
              <Button
                variant="outline"
                key={d.id}
                onClick={() => setSelected(d.id)}
              >
                Ver documento {d.id.slice(0, 8)}
              </Button>,
            ])}
          />
          <PageButtons
            offset={offset}
            total={query.data.total}
            limit={20}
            busy={query.loading}
            setOffset={setOffset}
            label="Bloques de historial"
          />
        </>
      )}
      {selected && <QueryStatus label="Documento contable" query={detail} />}
      {detail.data && (
        <div className="book-document">
          <p>
            Documento de {detail.data.source} · {detail.data.source_account} ·
            revisión {detail.data.portfolio_revision}.{' '}
            {detail.data.current
              ? 'Coincide con la revisión actual.'
              : 'Conserva un corte histórico.'}
          </p>
          <ExactBalance value={detail.data.balance} catalog={catalog} />
          <Differences rows={detail.data.differences} catalog={catalog} />
          {typeof detail.data.evidence.reason === 'string' && (
            <p>Motivo: {detail.data.evidence.reason}</p>
          )}
          <a
            className="text-link"
            href={
              '/api/portfolios/' + portfolio.id + '/book-documents/' + selected
            }
            download
          >
            Descargar evidencia JSON
          </a>
        </div>
      )}
    </details>
  );
}
