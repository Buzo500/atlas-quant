import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import { useRead } from './use-read';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const request = vi.mocked(api);
type Payload = { label: string };

function deferred() {
  let resolve!: (value: Payload) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<Payload>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

describe('Lecturas vigentes y caché por recurso', () => {
  beforeEach(() => {
    request.mockReset();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-08T12:00:00Z'));
  });
  afterEach(() => vi.useRealTimers());

  it.each(['success', 'error'])(
    'descarta un %s tardío al cambiar de recurso',
    async (outcome) => {
      const old = deferred(),
        next = deferred();
      request
        .mockReturnValueOnce(old.promise)
        .mockReturnValueOnce(next.promise);
      const { result, rerender } = renderHook(
        ({ path }) => useRead<Payload>({ path }),
        {
          initialProps: { path: '/first' },
        },
      );
      const firstSignal = request.mock.calls[0][2];
      rerender({ path: '/second' });
      expect(firstSignal?.aborted).toBe(true);
      expect(result.current.data).toBeNull();
      await act(async () => next.resolve({ label: 'second' }));
      const fresh = result.current;
      await act(async () => {
        if (outcome === 'success') old.resolve({ label: 'stale' });
        else old.reject(new Error('stale failure'));
      });
      expect(result.current).toBe(fresh);
      expect(result.current.data).toEqual({ label: 'second' });
      expect(result.current.error).toBe('');
    },
  );

  it('no muestra la caché de otro recurso, ni si el nuevo falla', async () => {
    const old = deferred(),
      next = deferred();
    request.mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
    const { result, rerender } = renderHook(
      ({ path }) => useRead<Payload>({ path }),
      {
        initialProps: { path: '/first' },
      },
    );
    await act(async () => old.resolve({ label: 'first' }));
    expect(result.current.updatedAt).not.toBeNull();
    rerender({ path: '/second' });
    expect(result.current.data).toBeNull();
    expect(result.current.updatedAt).toBeNull();
    await act(async () => next.reject(new Error('not available')));
    expect(result.current.data).toBeNull();
    expect(result.current.updatedAt).toBeNull();
    expect(result.current.error).toBe('not available');
  });

  it('un refresh capturado por un control antiguo no interfiere con el nuevo recurso', async () => {
    const old = deferred(),
      current = deferred();
    request
      .mockReturnValueOnce(old.promise)
      .mockReturnValueOnce(current.promise);
    const { result, rerender } = renderHook(
      ({ path }) => useRead<Payload>({ path }),
      {
        initialProps: { path: '/experiments/first' },
      },
    );
    const refreshAfterOldControl = result.current.refresh;
    rerender({ path: '/experiments/second' });
    const currentSignal = request.mock.calls[1][2];
    await act(async () => refreshAfterOldControl());
    expect(request).toHaveBeenCalledTimes(2);
    expect(currentSignal?.aborted).toBe(false);
    await act(async () => current.resolve({ label: 'second' }));
    await act(async () => old.resolve({ label: 'first' }));
    expect(result.current.data).toEqual({ label: 'second' });
  });

  it.each(['success', 'error'])(
    'descarta un %s anterior a refresh',
    async (outcome) => {
      const old = deferred(),
        current = deferred();
      request
        .mockReturnValueOnce(old.promise)
        .mockReturnValueOnce(current.promise);
      const { result } = renderHook(() => useRead<Payload>({ path: '/same' }));
      const oldSignal = request.mock.calls[0][2];
      act(() => {
        void result.current.refresh();
      });
      expect(oldSignal?.aborted).toBe(true);
      await act(async () => current.resolve({ label: 'refreshed' }));
      await act(async () => {
        if (outcome === 'success') old.resolve({ label: 'stale' });
        else old.reject(new Error('stale failure'));
      });
      expect(result.current.data).toEqual({ label: 'refreshed' });
      expect(result.current.error).toBe('');
    },
  );

  it('invalida la solicitud al cambiar de revisión del mismo recurso', async () => {
    const old = deferred(),
      current = deferred();
    request
      .mockReturnValueOnce(old.promise)
      .mockReturnValueOnce(current.promise);
    const { result, rerender } = renderHook(
      ({ revision }) => useRead<Payload>({ path: '/same', revision }),
      {
        initialProps: { revision: 1 },
      },
    );
    rerender({ revision: 2 });
    expect(request.mock.calls[0][2]?.aborted).toBe(true);
    await act(async () => current.resolve({ label: 'revision 2' }));
    await act(async () => old.resolve({ label: 'revision 1' }));
    expect(result.current.data).toEqual({ label: 'revision 2' });
  });

  it('conserva la última lectura del mismo recurso con error y recupera al reintentar', async () => {
    const initial = deferred(),
      failed = deferred(),
      recovered = deferred();
    request
      .mockReturnValueOnce(initial.promise)
      .mockReturnValueOnce(failed.promise)
      .mockReturnValueOnce(recovered.promise);
    const { result } = renderHook(() => useRead<Payload>({ path: '/same' }));
    await act(async () => initial.resolve({ label: 'cached' }));
    const lastSuccess = result.current.updatedAt;
    await act(async () => vi.advanceTimersByTime(1000));
    act(() => {
      void result.current.refresh();
    });
    await act(async () => failed.reject(new Error('offline')));
    expect(result.current.data).toEqual({ label: 'cached' });
    expect(result.current.error).toBe('offline');
    expect(result.current.updatedAt).toBe(lastSuccess);
    expect(result.current.loading).toBe(false);
    act(() => {
      void result.current.refresh();
    });
    expect(result.current.error).toBe('offline');
    await act(async () => recovered.resolve({ label: 'recovered' }));
    expect(result.current.data).toEqual({ label: 'recovered' });
    expect(result.current.error).toBe('');
    expect(result.current.updatedAt).toBeGreaterThan(lastSuccess!);
  });

  it('invalida y descarta una respuesta aunque el transporte ignore abort', async () => {
    const pending = deferred();
    request.mockReturnValueOnce(pending.promise);
    const { result } = renderHook(() => useRead<Payload>({ path: '/same' }));
    act(() => result.current.invalidate());
    expect(request.mock.calls[0][2]?.aborted).toBe(true);
    const before = result.current;
    await act(async () => pending.resolve({ label: 'aborted' }));
    expect(result.current).toBe(before);
    expect(result.current.data).toBeNull();
  });

  it('no sondea de nuevo ni cancela una lectura lenta por vencer el intervalo', async () => {
    const pending = deferred(),
      next = deferred();
    request
      .mockReturnValueOnce(pending.promise)
      .mockReturnValueOnce(next.promise);
    const { unmount } = renderHook(() =>
      useRead<Payload>({ path: '/same', intervalMs: 1000 }),
    );
    await act(async () => vi.advanceTimersByTime(10_000));
    expect(request).toHaveBeenCalledTimes(1);
    expect(request.mock.calls[0][2]?.aborted).toBe(false);
    await act(async () => pending.resolve({ label: 'done' }));
    await act(async () => vi.advanceTimersByTime(999));
    expect(request).toHaveBeenCalledTimes(1);
    await act(async () => vi.advanceTimersByTime(1));
    expect(request).toHaveBeenCalledTimes(2);
    unmount();
  });

  it('reinicia el intervalo después de una lectura manual lenta', async () => {
    const initial = deferred(),
      manual = deferred(),
      next = deferred();
    request
      .mockReturnValueOnce(initial.promise)
      .mockReturnValueOnce(manual.promise)
      .mockReturnValueOnce(next.promise);
    const { result, unmount } = renderHook(() =>
      useRead<Payload>({ path: '/same', intervalMs: 1000 }),
    );
    await act(async () => initial.resolve({ label: 'initial' }));
    await act(async () => vi.advanceTimersByTime(500));
    act(() => {
      void result.current.refresh();
    });
    await act(async () => vi.advanceTimersByTime(3000));
    expect(request).toHaveBeenCalledTimes(2);
    expect(request.mock.calls[1][2]?.aborted).toBe(false);
    await act(async () => manual.resolve({ label: 'manual' }));
    await act(async () => vi.advanceTimersByTime(1000));
    expect(request).toHaveBeenCalledTimes(3);
    unmount();
  });

  it('una lectura sustituida no programa otro sondeo mientras la vigente sigue pendiente', async () => {
    const old = deferred(),
      manual = deferred();
    request
      .mockReturnValueOnce(old.promise)
      .mockReturnValueOnce(manual.promise);
    const { result, unmount } = renderHook(() =>
      useRead<Payload>({ path: '/same', intervalMs: 1000 }),
    );
    act(() => {
      void result.current.refresh();
    });
    await act(async () => old.resolve({ label: 'old' }));
    await act(async () => vi.advanceTimersByTime(1000));
    expect(request).toHaveBeenCalledTimes(2);
    expect(request.mock.calls[1][2]?.aborted).toBe(false);
    unmount();
  });

  it.each(['success', 'error'])(
    'al desmontar descarta un %s y detiene el polling',
    async (outcome) => {
      const pending = deferred();
      request.mockReturnValueOnce(pending.promise);
      const { result, unmount } = renderHook(() =>
        useRead<Payload>({ path: '/same', intervalMs: 1000 }),
      );
      const before = result.current;
      unmount();
      expect(request.mock.calls[0][2]?.aborted).toBe(true);
      await act(async () => before.refresh());
      await act(async () => {
        if (outcome === 'success') pending.resolve({ label: 'late' });
        else pending.reject(new Error('late failure'));
      });
      await act(async () => vi.advanceTimersByTime(10_000));
      expect(result.current).toBe(before);
      expect(request).toHaveBeenCalledTimes(1);
    },
  );

  it('no lee sin ruta o si está deshabilitado', () => {
    const { result, rerender } = renderHook(
      ({ path, enabled }) => useRead<Payload>({ path, enabled }),
      {
        initialProps: { path: null as string | null, enabled: true },
      },
    );
    rerender({ path: '/disabled', enabled: false });
    expect(request).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
  });
});
