'use client';

import { useState } from 'react';
import type {
  CatalogResponse,
  CorporateCatalog,
  CorporateEvent,
  CorporatePreview,
  CorporateInput,
  CorporateRevisionInput,
} from '@/lib/api-types';
import { Choice, DataTable, Field } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  CsvEditor,
  MappingFields,
  mappingRecord,
  useCorporateReview,
  eventLabel,
  CorporatePager,
  type MappingRow,
} from './corporate-shared';

export function CorporateEventForm({
  catalog,
  events,
  selected,
  refresh,
  onError,
}: {
  catalog: CatalogResponse;
  events: CorporateCatalog;
  selected?: CorporateEvent;
  refresh: () => Promise<void>;
  onError: (v: string) => void;
}) {
  const [mode, setMode] = useState<'import' | 'replace' | 'cancel'>('import');
  const [source, setSource] = useState('');
  const [csv, setCsv] = useState('');
  const [verified, setVerified] = useState(false);
  const [evidence, setEvidence] = useState('');
  const [reason, setReason] = useState('');
  const [mapping, setMapping] = useState<MappingRow[]>([
    { key: 'ASSET', value: '' },
  ]);
  const [aliases, setAliases] = useState<MappingRow[]>([]);
  const [distinct, setDistinct] = useState<MappingRow[]>([]);
  const operation = useCorporateReview<CorporatePreview>(
    mode === 'import'
      ? '/corporate-events/imports'
      : '/corporate-events/revisions',
    refresh,
    onError,
  );
  const change = <T,>(set: (v: T) => void, value: T) => {
    operation.invalidate();
    set(value);
  };
  const options = catalog.listings
    .filter((l) => l.currency === 'EUR')
    .map((l) => ({
      value: l.id,
      label: `${catalog.instruments.find((i) => i.id === l.instrument_id)?.name || l.id.slice(0, 8)} · ${l.market || 'Local'} · ${l.id.slice(0, 8)}`,
    }));
  function submit() {
    try {
      let body: CorporateInput | CorporateRevisionInput;
      if (mode === 'import')
        body = {
          format_id: 'atlas-corporate-events-v1',
          expected_revision: events.revision,
          source,
          csv,
          verified,
          evidence,
          mapping: mappingRecord(mapping),
          event_mapping: mappingRecord(aliases),
          distinct_reasons: mappingRecord(distinct),
        };
      else {
        if (!selected)
          throw new Error('Selecciona un evento para revisar su versión.');
        body = {
          expected_revision: events.revision,
          event_id: selected.id,
          event_revision: selected.revision,
          action: mode,
          reason,
          csv: mode === 'cancel' ? '' : csv,
          mapping: mode === 'cancel' ? {} : mappingRecord(mapping),
          verified: mode !== 'cancel' && verified,
          evidence: mode === 'cancel' ? '' : evidence,
        };
      }
      void operation.review(body);
    } catch (error) {
      onError(error instanceof Error ? error.message : String(error));
    }
  }
  return (
    <details className="details corporate-form">
      <summary>Importar o revisar eventos</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <fieldset disabled={operation.busy}>
          <div className="form-grid">
            <Field label="Operación sobre eventos">
              <Choice
                label="Operación sobre eventos"
                value={mode}
                onChange={(v) => change(setMode, v as typeof mode)}
                options={[
                  { value: 'import', label: 'Importar eventos desde CSV' },
                  ...(selected
                    ? [
                        {
                          value: 'replace',
                          label: 'Crear revisión del evento seleccionado',
                        },
                        {
                          value: 'cancel',
                          label: 'Cancelar el evento seleccionado',
                        },
                      ]
                    : []),
                ]}
              />
            </Field>
            {mode === 'import' && (
              <Field label="Fuente de eventos">
                <Input
                  required
                  maxLength={100}
                  value={source}
                  onChange={(e) => change(setSource, e.target.value)}
                />
              </Field>
            )}
            {mode !== 'import' && (
              <Field label="Motivo de revisión del evento">
                <Input
                  required
                  maxLength={500}
                  value={reason}
                  onChange={(e) => change(setReason, e.target.value)}
                />
              </Field>
            )}
          </div>
          {mode !== 'cancel' && (
            <>
              <p>
                <a href="/api/templates/corporate-events" download>
                  Descargar plantilla de eventos
                </a>
                . Una fila por evento y referencia explícita de cotización. Las
                fechas desconocidas permanecen vacías.
              </p>
              <CsvEditor
                label="CSV de eventos corporativos"
                value={csv}
                onChange={(v) => change(setCsv, v)}
                onError={onError}
              />
              <MappingFields
                label="Cotizaciones del evento"
                rows={mapping}
                setRows={(v) => change(setMapping, v)}
                options={options}
              />
              <div className="form-grid">
                <Field label="Evidencia del evento">
                  <Input
                    required={verified}
                    maxLength={500}
                    value={evidence}
                    onChange={(e) => change(setEvidence, e.target.value)}
                  />
                </Field>
                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={verified}
                    onChange={(e) => change(setVerified, e.target.checked)}
                  />
                  He contrastado la evidencia y los campos declarados
                </label>
              </div>
              <p className="muted">
                Guardar un evento sin verificar lo deja como propuesta. La fecha
                de descarga no acredita cuándo estuvo disponible históricamente.
              </p>
              {mode === 'import' && (
                <details className="details">
                  <summary>Segunda fuente o posibles duplicados</summary>
                  <MappingFields
                    label="Enlaces a evento existente"
                    rows={aliases}
                    setRows={(v) => change(setAliases, v)}
                    options={events.events.map((event) => ({
                      value: event.id,
                      label: eventLabel(event, catalog),
                    }))}
                  />
                  <MappingFields
                    label="Motivos de evento distinto"
                    rows={distinct}
                    setRows={(v) => change(setDistinct, v)}
                  />
                  <p className="muted">
                    Dos fuentes del mismo evento se enlazan a una identidad. Si
                    son distribuciones distintas del mismo día, explica por qué
                    deben conservarse separadas.
                  </p>
                </details>
              )}
            </>
          )}
          {mode === 'cancel' && (
            <p>
              Se conserva el historial. Las aplicaciones a carteras quedarán
              pendientes de revisión; sus movimientos no se anulan
              automáticamente.
            </p>
          )}
          <Button type="submit">Previsualizar eventos</Button>
        </fieldset>
      </form>
      {operation.preview && (
        <section
          className="corporate-preview"
          aria-label="Previsualización de eventos"
        >
          <p>
            {operation.preview.added} eventos nuevos ·{' '}
            {operation.preview.duplicates} duplicados sin efecto · revisión
            propuesta {operation.preview.revision}
          </p>
          <DataTable
            heads={[
              'Evento',
              'Exfecha / efectiva',
              'Pago',
              'Bruto por título / ratio',
              'Evidencia',
            ]}
            rows={operation.preview.events.map((event) => [
              eventLabel(event, catalog),
              event.effective_date || 'Pendiente',
              event.payment_date || '—',
              event.gross_per_unit ??
                `${event.ratio_numerator}:${event.ratio_denominator}`,
              event.cancelled
                ? 'Cancelado'
                : event.verified
                  ? 'Contrastada'
                  : 'Pendiente',
            ])}
          />
          <CorporatePager
            offset={operation.preview.offset}
            total={operation.preview.total}
            onChange={(offset) => void operation.page(offset)}
          />
          <Button
            disabled={operation.busy}
            onClick={() => void operation.confirm()}
          >
            Confirmar eventos revisados
          </Button>
        </section>
      )}
      {operation.message && <output>{operation.message}</output>}
    </details>
  );
}
