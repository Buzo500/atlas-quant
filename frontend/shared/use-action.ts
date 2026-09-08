import { useEffect, useRef, useState } from 'react';

/** A click starts at most one mutation; leaving a panel only suppresses UI feedback. */
export function useAction(onError: (message: string) => void) {
  const [busy, setBusy] = useState(false);
  const mounted = useRef(true);
  const inFlight = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function run(action: () => Promise<void>) {
    if (inFlight.current || !mounted.current) return;
    inFlight.current = true;
    setBusy(true);
    onError('');
    try {
      await action();
    } catch (error) {
      if (mounted.current)
        onError(error instanceof Error ? error.message : String(error));
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return { busy, run };
}
