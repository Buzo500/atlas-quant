'use client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/lib/api';

type Snapshot<T> = {
  path: string | null;
  data: T | null;
  error: string;
  updatedAt: number | null;
  loading: boolean;
};
const empty = <T>(path: string | null): Snapshot<T> => ({
  path,
  data: null,
  error: '',
  updatedAt: null,
  loading: !!path,
});

/** One authoritative sequence per reader. Late successes and errors are discarded,
 * including transports that complete after receiving abort. */
export function useRead<T>({
  path,
  revision,
  intervalMs,
  enabled = true,
}: {
  path: string | null;
  revision?: string | number;
  intervalMs?: number;
  enabled?: boolean;
}) {
  const [snapshot, setSnapshot] = useState<Snapshot<T>>(() => empty(path));
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const scope = useMemo(() => ({ path, intervalMs }), [path, intervalMs]);
  const activeReader = useRef<{
    scope: typeof scope;
    read: () => Promise<void>;
  } | null>(null);
  const invalidate = useCallback(() => {
    ++sequence.current;
    clearTimeout(timer.current);
    controller.current?.abort();
  }, []);
  const refresh = useCallback(async (): Promise<void> => {
    const { path: resourcePath, intervalMs: pollEvery } = scope;
    // A mutation may finish after the user selects another resource. A captured
    // refresh from that old screen must not cancel or replace the current read.
    if (!resourcePath || activeReader.current?.scope !== scope) return;
    invalidate();
    const current = sequence.current;
    const request = new AbortController();
    controller.current = request;
    queueMicrotask(() => {
      if (current === sequence.current)
        setSnapshot((previous) => ({
          ...(previous.path === resourcePath
            ? previous
            : empty<T>(resourcePath)),
          loading: true,
        }));
    });
    try {
      const data = await api<T>(resourcePath, undefined, request.signal);
      if (current === sequence.current)
        setSnapshot({
          path: resourcePath,
          data,
          error: '',
          updatedAt: Date.now(),
          loading: false,
        });
    } catch (error) {
      if (current === sequence.current)
        setSnapshot((previous) => ({
          ...(previous.path === resourcePath
            ? previous
            : empty<T>(resourcePath)),
          loading: false,
          error: error instanceof Error ? error.message : String(error),
        }));
    } finally {
      // Manual refresh and automatic polling share one completion-based timer.
      // Superseded/aborted readers cannot start another polling loop.
      const reader = activeReader.current;
      if (
        current === sequence.current &&
        reader?.scope === scope &&
        pollEvery &&
        pollEvery > 0
      ) {
        timer.current = setTimeout(() => void reader.read(), pollEvery);
      }
    }
  }, [invalidate, scope]);
  useEffect(() => {
    if (!enabled || !path) return invalidate;
    activeReader.current = { scope, read: refresh };
    // This effect owns an HTTP subscription. Loading and the asynchronous reply
    // belong to that lifecycle; neither is state derived from render props.
    // oxlint-disable-next-line react/react-compiler
    void refresh();
    return () => {
      activeReader.current = null;
      invalidate();
    };
  }, [refresh, invalidate, path, revision, intervalMs, enabled, scope]);
  const value = snapshot.path === path ? snapshot : empty<T>(path);
  return { ...value, loading: enabled && value.loading, refresh, invalidate };
}
