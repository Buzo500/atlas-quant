import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { dataset } from '@/test/fixtures';
import { useDatasetSymbol } from './use-dataset-symbol';

describe('Activo seleccionado por conjunto', () => {
  it('sustituye un activo eliminado por el primero disponible', () => {
    const original = dataset();
    const hook = renderHook(({ input }) => useDatasetSymbol(input), {
      initialProps: { input: original },
    });
    act(() => hook.result.current.setSymbol('B'));
    hook.rerender({
      input: {
        ...original,
        version: 2,
        manifest: { ...original.manifest, symbols: ['A'] },
      },
    });
    expect(hook.result.current.symbol).toBe('A');
  });

  it('recupera la elección de cada conjunto sin almacenarla fuera de la sesión', () => {
    const original = dataset();
    const hook = renderHook(({ input }) => useDatasetSymbol(input), {
      initialProps: { input: original },
    });
    act(() => hook.result.current.setSymbol('B'));
    hook.rerender({ input: dataset('other') });
    expect(hook.result.current.symbol).toBe('A');
    hook.rerender({ input: original });
    expect(hook.result.current.symbol).toBe('B');
  });
});
