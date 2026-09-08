'use client';

import { useEffect, useRef, useState } from 'react';
import { Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { moneyEUR, number } from '@/shared/format';
import type { DatasetResponse, LedgerResponse } from '@/lib/api-types';

/** The parent keys this confirmation by dataset revision and CSV edit revision. */
export function LedgerImport({
  dataset,
  csv,
  refresh,
  onError,
}: {
  dataset: DatasetResponse | undefined;
  csv: string;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [preview, setPreview] = useState<LedgerResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const active = useRef(true);
  const inFlight = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);

  async function submit(commit: boolean) {
    if (!dataset || !csv || inFlight.current || (commit && !preview)) return;
    inFlight.current = true;
    setBusy(true);
    setMessage('');
    onError('');
    try {
      const result = await api<LedgerResponse>(
        `/datasets/${dataset.id}/ledger`,
        {
          csv,
          commit,
          ...(commit ? { preview_token: preview?.preview_token } : {}),
        },
      );
      if (!active.current) return;
      if (commit) {
        setPreview(null);
        setMessage(
          `${result.added} movimientos añadidos; ${result.duplicates} duplicados omitidos.`,
        );
        await refresh();
      } else {
        setPreview(result);
      }
    } catch (error) {
      if (active.current) {
        // A failed or uncertain commit always requires a fresh review.
        setPreview(null);
        onError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      inFlight.current = false;
      if (active.current) setBusy(false);
    }
  }

  return (
    <>
      <div className="actions">
        <Button
          disabled={busy || !dataset || !csv}
          onClick={() => void submit(false)}
        >
          {busy ? 'Validando…' : 'Previsualizar movimientos'}
        </Button>
        <a className="text-link" href="/api/templates/ledger" download>
          <Download size={15} />
          Plantilla CSV
        </a>
      </div>
      {preview && !preview.committed && (
        <div className="notice vertical">
          <strong>
            {number(preview.added, { maximumFractionDigits: 0 })} nuevos ·{' '}
            {number(preview.duplicates, { maximumFractionDigits: 0 })}{' '}
            duplicados
          </strong>
          <span>
            {dataset?.name} · versión {dataset?.version}
          </span>
          <span>Valor resultante: {moneyEUR(preview.portfolio.nav)}</span>
          <Button disabled={busy} onClick={() => void submit(true)}>
            Confirmar importación
          </Button>
        </div>
      )}
      {message && <output className="success">{message}</output>}
    </>
  );
}
