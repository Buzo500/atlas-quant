'use client';

import { useState } from 'react';
import type {
  CorporateApplicationInput,
  NativeCorporateApplicationPreview as CorporateApplicationPreview,
  NativeCorporateEvent as CorporateEvent,
  NativeCorporatePortfolio,
  CorporatePortfolio,
  CorporateReview,
  NativeBookDetail as BookDetail,
  PortfolioRecord,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Field, Choice, DataTable } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { CorporatePager, useCorporateReview } from './corporate-shared';
import { CorporateBalances } from './corporate-balances';

const columns =
  'external_id,date,day_sequence,kind,listing_ref,quantity,unit_price,gross_amount,currency,fee_amount,fee_currency,tax_amount,tax_currency,fx_to_amount,fx_to_currency,ratio_numerator,ratio_denominator,corporate_event_ref'.split(
    ',',
  );
const quote = (value: string) =>
  /[",\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
const scalar = (value: unknown) =>
  typeof value === 'string' || typeof value === 'number' ? String(value) : '—';

export function CorporateApplicationForm({
  portfolio,
  event,
  current,
  refresh,
  onError,
}: {
  portfolio: PortfolioRecord;
  event: CorporateEvent;
  current?: CorporatePortfolio | NativeCorporatePortfolio;
  refresh: () => Promise<void>;
  onError: (v: string) => void;
}) {
  const applied = current?.applications.find((a) => a.event_id === event.id);
  const [mode, setMode] = useState(
    event.event_type === 'dividend' ? 'right' : 'create',
  );
  const [source, setSource] = useState(applied?.source || '');
  const [account, setAccount] = useState(applied?.source_account || '');
  const [quantity, setQuantity] = useState(applied?.eligible_quantity || '');
  const [sequence, setSequence] = useState(String(applied?.day_sequence || 10));
  const [evidence, setEvidence] = useState('');
  const [discrepancy, setDiscrepancy] = useState('');
  const [override, setOverride] = useState('');
  const [grossReason, setGrossReason] = useState('');
  const [fraction, setFraction] = useState('');
  const [external, setExternal] = useState('');
  const [day, setDay] = useState(
    event.event_type === 'split'
      ? event.effective_date || ''
      : event.payment_date || '',
  );
  const [movementSequence, setMovementSequence] = useState('10');
  const [gross, setGross] = useState('');
  const [fee, setFee] = useState('0.00');
  const [tax, setTax] = useState('0.00');
  const [movement, setMovement] = useState('');
  const [reason, setReason] = useState('');
  const [entryOffset, setEntryOffset] = useState(0);
  const book = useRead<BookDetail>({
    path: `/v2/portfolios/${portfolio.id}/book?offset=${entryOffset}&limit=100`,
    revision: portfolio.revision,
    enabled: mode === 'link',
  });
  const operation = useCorporateReview<CorporateApplicationPreview>(
    `/v2/portfolios/${portfolio.id}/corporate-actions`,
    refresh,
    onError,
  );
  const change = <T,>(set: (v: T) => void, value: T) => {
    operation.invalidate();
    set(value);
  };
  function input(
    label: string,
    value: string,
    set: (s: string) => void,
    required = false,
    type = 'text',
  ) {
    return (
      <Field label={label}>
        <Input
          aria-label={label}
          type={type}
          required={required}
          value={value}
          maxLength={type === 'text' ? 500 : undefined}
          onChange={(e) => change(set, e.target.value)}
        />
      </Field>
    );
  }
  function submit() {
    const review: CorporateReview = {
      event_revision: event.revision,
      day_sequence: Number(sequence),
      evidence,
      eligible_quantity: event.event_type === 'dividend' ? quantity : null,
      discrepancy_reason: discrepancy,
      gross_amount: override || null,
      gross_explanation: grossReason,
      fraction_evidence: fraction,
    };
    let csv = '';
    if (mode === 'create') {
      const values: Record<string, string> = {
        external_id: external,
        date: day,
        day_sequence:
          event.event_type === 'split' ? sequence : movementSequence,
        kind: event.event_type === 'dividend' ? 'dividend_payment' : 'split',
        listing_ref: 'ASSET',
        currency: event.currency,
        corporate_event_ref: 'EVENT',
      };
      if (event.event_type === 'dividend')
        Object.assign(values, {
          gross_amount: gross,
          fee_amount: fee,
          fee_currency: event.currency,
          tax_amount: tax,
          tax_currency: event.currency,
        });
      else
        Object.assign(values, {
          ratio_numerator: String(event.ratio_numerator),
          ratio_denominator: String(event.ratio_denominator),
        });
      csv = `${columns.join(',')}\n${columns.map((key) => quote(values[key] || '')).join(',')}\n`;
    }
    const body: CorporateApplicationInput = {
      expected_revision: portfolio.revision,
      event_id: event.id,
      source,
      source_account: account,
      action: mode === 'cancel' ? 'cancel' : 'review',
      review: mode === 'cancel' ? null : review,
      reason: mode === 'cancel' ? reason : '',
      movement_id: mode === 'link' ? movement || null : null,
      csv,
    };
    void operation.review(body);
  }
  const eligible = event.verified && !event.cancelled && !!event.effective_date;
  return (
    <section
      className="corporate-form"
      aria-label="Aplicación del evento a cartera"
    >
      <h3>Aplicar a «{portfolio.name}»</h3>
      <p>
        {event.event_type === 'dividend'
          ? `Dividendo de ${event.gross_per_unit} ${event.currency} por título · exfecha ${event.effective_date || 'pendiente'}`
          : `Split ${event.ratio_numerator}:${event.ratio_denominator} · fecha ${event.effective_date || 'pendiente'}`}{' '}
        · revisión {event.revision}
      </p>
      {!eligible && (
        <output>
          La aplicación requiere evidencia verificada, fecha efectiva conocida y
          evento vigente.
        </output>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <fieldset disabled={operation.busy}>
          <div className="form-grid">
            <Field label="Acción en la cartera">
              <Choice
                label="Acción en la cartera"
                value={mode}
                onChange={(v) => change(setMode, v)}
                options={[
                  ...(event.event_type === 'dividend'
                    ? [
                        {
                          value: 'right',
                          label: 'Reconocer o revisar el derecho',
                        },
                      ]
                    : []),
                  {
                    value: 'create',
                    label:
                      event.event_type === 'dividend'
                        ? 'Crear cobro revisado'
                        : 'Crear movimiento de split',
                  },
                  { value: 'link', label: 'Enlazar movimiento existente' },
                  ...(applied
                    ? [
                        {
                          value: 'cancel',
                          label: 'Cancelar aplicación sin movimiento vinculado',
                        },
                      ]
                    : []),
                ]}
              />
            </Field>
            {input('Fuente del movimiento', source, setSource, true)}
            {input(
              'Cuenta de origen del movimiento',
              account,
              setAccount,
              true,
            )}
          </div>
          {mode === 'cancel' ? (
            <>
              {input(
                'Motivo de cancelación de la aplicación',
                reason,
                setReason,
                true,
              )}
              <p>
                Si hay un movimiento vinculado, primero revisa su anulación en
                Libro y conciliación. Cancelar un derecho no elimina un cobro o
                split.
              </p>
            </>
          ) : (
            <>
              <div className="form-grid">
                {event.event_type === 'dividend' &&
                  input(
                    'Cantidad elegible acreditada',
                    quantity,
                    setQuantity,
                    true,
                  )}
                {input(
                  'Secuencia del derecho o split',
                  sequence,
                  setSequence,
                  true,
                  'number',
                )}
                {input(
                  'Evidencia de elegibilidad y orden',
                  evidence,
                  setEvidence,
                  true,
                )}
              </div>
              <p className="muted">
                La secuencia expresa el orden económico del día. Una cantidad
                elegible se acredita en exfecha; no se toma del saldo actual.
              </p>
              <details className="details">
                <summary>Diferencias o fracciones acreditadas</summary>
                <div className="form-grid">
                  {event.event_type === 'dividend' ? (
                    <>
                      {input(
                        'Motivo de diferencia de cantidad elegible',
                        discrepancy,
                        setDiscrepancy,
                      )}
                      {input(
                        'Bruto del derecho declarado (opcional)',
                        override,
                        setOverride,
                      )}
                      {input(
                        'Evidencia de diferencia del bruto',
                        grossReason,
                        setGrossReason,
                      )}
                    </>
                  ) : (
                    input(
                      'Evidencia de fracción conservada por la cuenta',
                      fraction,
                      setFraction,
                    )
                  )}
                </div>
              </details>
              {mode === 'create' && (
                <div className="form-grid">
                  {input(
                    'ID externo del nuevo movimiento',
                    external,
                    setExternal,
                    true,
                  )}
                  {input(
                    'Fecha del nuevo movimiento',
                    day,
                    setDay,
                    true,
                    'date',
                  )}
                  {event.event_type === 'dividend' && (
                    <>
                      {input(
                        'Secuencia del cobro',
                        movementSequence,
                        setMovementSequence,
                        true,
                        'number',
                      )}
                      {input(
                        `Bruto del cobro ${event.currency}`,
                        gross,
                        setGross,
                        true,
                      )}
                      {input(
                        `Retención del cobro ${event.currency}`,
                        tax,
                        setTax,
                        true,
                      )}
                      {input(
                        `Comisión del cobro ${event.currency}`,
                        fee,
                        setFee,
                        true,
                      )}
                    </>
                  )}
                </div>
              )}
              {mode === 'link' && (
                <>
                  <QueryStatus label="Movimientos para enlazar" query={book} />
                  <Field label="Movimiento existente">
                    <Choice
                      label="Movimiento existente"
                      value={movement}
                      onChange={(v) => change(setMovement, v)}
                      options={(book.data?.entries || [])
                        .filter(
                          (e) =>
                            e.event.kind ===
                            (event.event_type === 'dividend'
                              ? 'dividend_payment'
                              : 'split'),
                        )
                        .map((e) => ({
                          value: String(e.event.id),
                          label: `${e.date} · ${scalar(e.event.external_id)} · ${scalar(e.event.gross_amount ?? 'split')}`,
                        }))}
                    />
                  </Field>
                  {input(
                    'ID interno de movimiento (si está en otro bloque)',
                    movement,
                    setMovement,
                    true,
                  )}
                  <div className="row-actions">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={!entryOffset}
                      onClick={() =>
                        setEntryOffset(Math.max(0, entryOffset - 100))
                      }
                    >
                      Movimientos anteriores
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={
                        !book.data || entryOffset + 100 >= book.data.total
                      }
                      onClick={() => setEntryOffset(entryOffset + 100)}
                    >
                      Movimientos siguientes
                    </Button>
                  </div>
                  <p className="muted">
                    Enlazar conserva el efectivo ya registrado. Se contrastan
                    cuenta, cotización, fecha e importe.
                  </p>
                </>
              )}
            </>
          )}
          <Button type="submit" disabled={mode !== 'cancel' && !eligible}>
            Previsualizar aplicación
          </Button>
        </fieldset>
      </form>
      {operation.preview && (
        <section
          className="corporate-preview"
          aria-label="Previsualización de aplicación"
        >
          <p>
            Propuesta para la revisión {operation.preview.portfolio_revision}.
            Los cambios se guardarán juntos al confirmar.
          </p>
          <CorporateBalances value={operation.preview} />
          {event.event_type === 'split' && (
            <DataTable
              heads={[
                'Cotización',
                'Cantidad resultante',
                `Coste total conservado ${event.currency}`,
              ]}
              numericColumns={[1, 2]}
              rows={operation.preview.balance.positions.map((p) => [
                p.listing_id.slice(0, 8),
                p.quantity,
                p.cost_basis,
              ])}
            />
          )}
          <CorporatePager
            offset={operation.preview.offset}
            total={operation.preview.total}
            onChange={(offset) => void operation.page(offset)}
          />
          <Button
            disabled={operation.busy}
            onClick={() => void operation.confirm()}
          >
            Confirmar aplicación revisada
          </Button>
        </section>
      )}
      {operation.message && <output>{operation.message}</output>}
    </section>
  );
}
