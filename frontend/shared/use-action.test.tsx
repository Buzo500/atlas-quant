import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { deferred } from '@/test/fixtures';
import { useAction } from './use-action';

describe('Acciones de escritura', () => {
  it('un doble clic en el mismo ciclo solo ejecuta una operación', async () => {
    const pending = deferred<void>();
    const action = vi.fn(() => pending.promise);
    const onError = vi.fn();
    const hook = renderHook(() => useAction(onError));
    act(() => {
      void hook.result.current.run(action);
      void hook.result.current.run(action);
    });
    expect(action).toHaveBeenCalledTimes(1);
    expect(hook.result.current.busy).toBe(true);
    await act(async () => pending.resolve());
    expect(hook.result.current.busy).toBe(false);
  });

  it('termina la operación autorizada sin mostrar errores en un panel desmontado', async () => {
    const pending = deferred<void>();
    const onError = vi.fn();
    const hook = renderHook(() => useAction(onError));
    act(() => {
      void hook.result.current.run(() => pending.promise);
    });
    hook.unmount();
    await act(async () => pending.reject(new Error('Respuesta tardía')));
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith('');
  });
});
