'use client';

import { useEffect, useRef, useState } from 'react';
import { Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function PerformanceExport({
  portfolioId,
  reportId,
}: {
  portfolioId: string;
  reportId: string;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const pending = useRef<AbortController | null>(null);
  useEffect(
    () => () => {
      pending.current?.abort();
    },
    [portfolioId, reportId],
  );

  async function download() {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setMessage('');
    setError('');
    try {
      const response = await fetch(
        `/api/v2/portfolios/${encodeURIComponent(portfolioId)}/performance/${encodeURIComponent(reportId)}/latex`,
        {
          method: 'POST',
          headers: { 'X-Atlas-Client': 'local-v1' },
          signal: controller.signal,
        },
      );
      if (
        !response.ok ||
        !response.headers.get('content-type')?.includes('application/zip')
      )
        throw new Error(
          response.status === 404
            ? 'El informe guardado ya no está disponible.'
            : 'No se pudo exportar el informe guardado. Puedes volver a intentarlo.',
        );
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `atlas-cartera-latex-${reportId.slice(0, 12)}.zip`;
      document.body.appendChild(link);
      try {
        link.click();
      } finally {
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      setMessage('Fuente LaTeX y datos del informe guardado descargados.');
    } catch (reason) {
      if (!controller.signal.aborted)
        setError(
          reason instanceof Error
            ? reason.message
            : 'No se pudo descargar el informe.',
        );
    } finally {
      if (!controller.signal.aborted) {
        pending.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <div>
      <Button
        variant="outline"
        disabled={busy}
        onClick={() => void download()}
        aria-label="Exportar fuente LaTeX de cartera"
        className="h-auto max-w-full whitespace-normal text-left"
      >
        <Download aria-hidden="true" size={16} />
        {busy ? 'Preparando fuente…' : 'Exportar fuente LaTeX'}
      </Button>
      <p className="muted">
        Incluye el periodo y los resultados guardados. El detalle de posiciones
        no está incluido en este informe. La descarga no necesita TeX instalado.
      </p>
      {message && <output aria-live="polite">{message}</output>}
      {error && (
        <p className="notice" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
