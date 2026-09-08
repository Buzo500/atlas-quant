'use client';
import { useCallback, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { dateTime } from '@/shared/format';

export function QueryStatus({
  label,
  query,
}: {
  label: string;
  query: {
    data: unknown;
    error: string;
    loading: boolean;
    updatedAt: number | null;
    refresh: () => Promise<void>;
  };
}) {
  const [retrying, setRetrying] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const phase = query.error
    ? 'error'
    : query.loading && query.data == null
      ? 'initial'
      : 'ready';
  const [notice, setNotice] = useState({
    label,
    phase,
    attempt,
    text: phase === 'initial' ? `Cargando ${label.toLowerCase()}…` : '',
  });
  // Remember meaningful transitions, not the changing polling timestamp.
  // Updating this snapshot during render avoids an effect announcing stale props.
  if (
    notice.label !== label ||
    notice.phase !== phase ||
    notice.attempt !== attempt
  ) {
    let text = '';
    if (phase === 'initial') text = `Cargando ${label.toLowerCase()}…`;
    else if (notice.label === label && notice.attempt !== attempt)
      text = query.error
        ? `${label}: el reintento ha fallado. ${query.error}`
        : `${label}: consulta actualizada.`;
    else if (
      notice.label === label &&
      notice.phase === 'error' &&
      phase === 'ready'
    )
      text = `${label}: conexión recuperada.`;
    else if (
      notice.label === label &&
      notice.phase === 'initial' &&
      phase === 'ready'
    )
      text = `${label}: datos cargados.`;
    setNotice({ label, phase, attempt, text });
  }
  const summary = useRef<HTMLSpanElement | null>(null);
  const retryButton = useRef<HTMLButtonElement | null>(null);
  const setRetryButton = useCallback((node: HTMLButtonElement | null) => {
    const previous = retryButton.current;
    if (!node && previous && previous === document.activeElement) {
      const target = summary.current;
      queueMicrotask(() => {
        // The button can disappear on recovery, including automatic recovery.
        // Do not move focus if the whole panel left the page or focus moved on.
        if (
          target?.isConnected &&
          !target.closest('[hidden], [inert]') &&
          document.activeElement === document.body
        )
          target.focus();
      });
    }
    retryButton.current = node;
  }, []);
  async function retry() {
    if (retrying || query.loading) return;
    setRetrying(true);
    try {
      await query.refresh();
    } finally {
      setRetrying(false);
      setAttempt((value) => value + 1);
    }
  }
  return (
    <div className={'query-status' + (query.error ? ' query-error' : '')}>
      <span ref={summary} tabIndex={-1}>
        <span className="sr-only">{label}. </span>
        {query.error
          ? `${label}: ${query.error} `
          : query.loading
            ? `${query.data ? 'Actualizando' : 'Cargando'} ${label.toLowerCase()}… `
            : ''}
        {query.updatedAt != null &&
          `${query.error || query.loading ? 'Últimos datos disponibles' : 'Última consulta'}: ${dateTime(new Date(query.updatedAt).toISOString())}.`}
      </span>
      <output aria-live="polite" aria-atomic="true" className="sr-only">
        {retrying ? `Reintentando ${label.toLowerCase()}…` : notice.text}
      </output>
      <span role="alert" aria-atomic="true" className="sr-only">
        {query.error ? `${label}: ${query.error}` : ''}
      </span>
      {query.error && (
        <Button
          ref={setRetryButton}
          variant="outline"
          size="sm"
          disabled={query.loading || retrying}
          focusableWhenDisabled
          onClick={() => void retry()}
        >
          Reintentar {label.toLowerCase()}
        </Button>
      )}
    </div>
  );
}
