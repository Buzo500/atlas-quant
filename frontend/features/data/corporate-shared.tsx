'use client';

import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { useAction } from '@/shared/use-action';
import { Choice, Field } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import type { CorporateEvent, CatalogResponse } from '@/lib/api-types';

export function eventLabel(event: CorporateEvent, catalog: CatalogResponse) {
  const listing = catalog.listings.find((l) => l.id === event.listing_id);
  const name =
    catalog.instruments.find((i) => i.id === listing?.instrument_id)?.name ||
    event.listing_id.slice(0, 8);
  return `${event.event_type === 'dividend' ? 'Dividendo' : 'Split'} · ${name} · ${event.effective_date || 'Fecha pendiente'} · r${event.revision}`;
}

export function useCorporateReview<T extends { preview_token: string }>(
  path: string,
  refresh: () => Promise<void>,
  onError: (s: string) => void,
) {
  const [preview, setPreview] = useState<T | null>(null);
  const [message, setMessage] = useState('');
  const generation = useRef(0);
  const mounted = useRef(true);
  const frozen = useRef<Record<string, unknown> | null>(null);
  const action = useAction(onError);
  useEffect(() => {
    mounted.current = true;
    generation.current++;
    return () => {
      mounted.current = false;
    };
  }, []);
  function invalidate() {
    generation.current++;
    frozen.current = null;
    setPreview(null);
    setMessage('');
  }
  async function review(body: Record<string, unknown>) {
    invalidate();
    const current = generation.current;
    await action.run(async () => {
      try {
        const result = await api<T>(path, body);
        if (!mounted.current || generation.current !== current) return;
        frozen.current = body;
        setPreview(result);
      } catch (error) {
        if (mounted.current && generation.current === current) {
          invalidate();
          throw error;
        }
      }
    });
  }
  async function confirm() {
    if (!preview || !frozen.current) return;
    const body = {
      ...frozen.current,
      commit: true,
      preview_token: preview.preview_token,
    };
    const current = generation.current;
    await action.run(async () => {
      try {
        await api<T>(path, body);
      } catch (error) {
        if (mounted.current && generation.current === current) {
          invalidate();
          throw error;
        }
        return;
      }
      if (!mounted.current || generation.current !== current) return;
      invalidate();
      setMessage('Confirmación guardada con su historial y evidencia.');
      await refresh();
    });
  }
  async function page(offset: number) {
    if (frozen.current) await review({ ...frozen.current, offset });
  }
  return { ...action, preview, message, invalidate, review, confirm, page };
}

export function CsvEditor({
  label,
  value,
  onChange,
  onError,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  onError: (v: string) => void;
}) {
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  return (
    <>
      <Field label={`Archivo · ${label}`}>
        <Input
          type="file"
          accept=".csv,text/csv"
          aria-label={`Archivo · ${label}`}
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const current = ++generation.current;
            onChange('');
            try {
              if (file.size > 8_000_000)
                throw new Error('El archivo supera los 8 MB.');
              const text = new TextDecoder('utf-8', { fatal: true }).decode(
                await file.arrayBuffer(),
              );
              if (generation.current === current) onChange(text);
            } catch {
              if (generation.current === current)
                onError(
                  'No se pudo leer el CSV. Usa UTF-8 y un archivo de hasta 8 MB.',
                );
            }
            e.target.value = '';
          }}
        />
      </Field>
      <Field label={label}>
        <textarea
          className="csv-editor"
          aria-label={label}
          rows={6}
          wrap="off"
          spellCheck={false}
          maxLength={8_000_000}
          value={value}
          onChange={(e) => {
            generation.current++;
            onChange(e.target.value);
          }}
        />
      </Field>
    </>
  );
}

export type MappingRow = { key: string; value: string };
export function MappingFields({
  label,
  rows,
  setRows,
  options,
}: {
  label: string;
  rows: MappingRow[];
  setRows: (v: MappingRow[]) => void;
  options?: { value: string; label: string }[];
}) {
  return (
    <fieldset className="corporate-mapping">
      <legend>{label}</legend>
      {rows.map((row, index) => (
        <div className="form-grid" key={index}>
          <Field label={`${label} · referencia ${index + 1}`}>
            <Input
              value={row.key}
              maxLength={100}
              onChange={(e) =>
                setRows(
                  rows.map((r, i) =>
                    i === index ? { ...r, key: e.target.value } : r,
                  ),
                )
              }
            />
          </Field>
          <Field label={`${label} · destino ${index + 1}`}>
            {options ? (
              <Choice
                label={`${label} · destino ${index + 1}`}
                value={row.value}
                options={options}
                onChange={(value) =>
                  setRows(
                    rows.map((r, i) => (i === index ? { ...r, value } : r)),
                  )
                }
              />
            ) : (
              <Input
                value={row.value}
                maxLength={500}
                onChange={(e) =>
                  setRows(
                    rows.map((r, i) =>
                      i === index ? { ...r, value: e.target.value } : r,
                    ),
                  )
                }
              />
            )}
          </Field>
          <Button
            type="button"
            variant="outline"
            aria-label={`Quitar ${label} ${index + 1}`}
            onClick={() => setRows(rows.filter((_, i) => i !== index))}
          >
            Quitar
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        disabled={rows.length >= 100}
        onClick={() => setRows([...rows, { key: '', value: '' }])}
      >
        Añadir {label.toLowerCase()}
      </Button>
    </fieldset>
  );
}

export function mappingRecord(rows: MappingRow[]) {
  const result: Record<string, string> = Object.create(null);
  for (const row of rows) {
    const key = row.key.trim();
    if (!key || !row.value.trim())
      throw new Error('Completa todas las referencias y sus destinos.');
    if (key in result)
      throw new Error('Una referencia aparece dos veces en el mapeo.');
    result[key] = row.value.trim();
  }
  return result;
}

export function CorporatePager({
  offset,
  total,
  onChange,
}: {
  offset: number;
  total: number;
  onChange: (n: number) => void;
}) {
  if (total <= 100 && offset === 0) return null;
  return (
    <div className="row-actions" aria-label="Bloques de eventos">
      <Button
        variant="outline"
        disabled={!offset}
        onClick={() => onChange(Math.max(0, offset - 100))}
      >
        Bloque anterior
      </Button>
      <span>
        {total
          ? `${offset + 1}–${Math.min(offset + 100, total)} de ${total}`
          : 'Sin registros'}
      </span>
      <Button
        variant="outline"
        disabled={offset + 100 >= total}
        onClick={() => onChange(offset + 100)}
      >
        Bloque siguiente
      </Button>
    </div>
  );
}
