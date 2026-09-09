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
  portfolioId,
  portfolioName,
  csv,
  refresh,
  onError,
  onMessage,
  onConfirmationRemoved,
}: {
  dataset: DatasetResponse | undefined;
  portfolioId?: string;
  portfolioName?: string;
  csv: string;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
  onMessage: (message: string) => void;
  onConfirmationRemoved: (button: HTMLButtonElement | null) => void;
}) {
  const [preview, setPreview] = useState<LedgerResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const confirmButton = useRef<HTMLButtonElement | null>(null);
  const active = useRef(true);
  const inFlight = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);

  async function submit(commit: boolean) {
    if (
      (!dataset && !portfolioId) ||
      !csv ||
      inFlight.current ||
      (commit && !preview)
    )
      return;
    inFlight.current = true;
    setBusy(true);
    onMessage('');
    onError('');
    try {
      const result = await api<LedgerResponse>(
        portfolioId
          ? `/portfolios/${portfolioId}/ledger`
          : `/datasets/${dataset!.id}/ledger`,
        {
          csv,
          commit,
          ...(commit ? { preview_token: preview?.preview_token } : {}),
        },
      );
      if (!active.current) return;
      if (commit) {
        onConfirmationRemoved(confirmButton.current);
        setPreview(null);
        onMessage(
          `${result.added} movimientos añadidos; ${result.duplicates} duplicados omitidos.`,
        );
        await refresh();
      } else {
        setPreview(result);
      }
    } catch (error) {
      if (active.current) {
        // A failed or uncertain commit always requires a fresh review.
        if (commit) onConfirmationRemoved(confirmButton.current);
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
          disabled={busy || (!dataset && !portfolioId) || !csv}
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
            {portfolioId
              ? portfolioName
              : `${dataset?.name} · versión ${dataset?.version}`}
          </span>
          <span>Valor resultante: {moneyEUR(preview.portfolio.nav)}</span>
          <Button
            ref={confirmButton}
            disabled={busy}
            focusableWhenDisabled={busy}
            onClick={() => void submit(true)}
          >
            Confirmar importación
          </Button>
        </div>
      )}
    </>
  );
}
