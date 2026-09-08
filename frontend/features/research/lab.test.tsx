import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Lab, ResearchResult } from '@/app/workbench';
import { api } from '@/lib/api';
import { dataset, deferred, researchResponse } from '@/test/fixtures';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const request = vi.mocked(api);

describe('Identidad de una comparación del Laboratorio', () => {
  beforeEach(() => request.mockReset());

  it('presenta los datos y parámetros confirmados por el motor', async () => {
    const result = researchResponse();
    request.mockResolvedValueOnce(result);
    render(<Lab dataset={dataset()} onError={vi.fn()} />);
    const user = userEvent.setup();
    await user.click(
      screen.getByRole('button', { name: 'Ejecutar comparación' }),
    );
    const context = await screen.findByRole('region', {
      name: 'Contexto de la ejecución',
    });
    expect(
      within(context).getByRole('heading', { name: 'A · Datos a' }),
    ).toBeTruthy();
    expect(context.textContent).toContain('Versión 1');
    expect(context.textContent).toContain('01/01/2026 → 07/09/2026');
    expect(screen.queryByText('Resultado de otra configuración')).toBeNull();
    await user.click(
      within(context).getByText('Parámetros y trazabilidad de la ejecución'),
    );
    expect(context.textContent).toContain(result.execution.id);
    expect(context.textContent).toContain(result.data_hash);
    expect(request).toHaveBeenCalledWith('/research', {
      dataset_id: 'a',
      symbol: 'A',
      costs: result.execution.costs,
    });
  });

  it.each(['symbol', 'costs', 'dataset', 'version', 'hash'])(
    'conserva y etiqueta el resultado al cambiar %s',
    async (change) => {
      const result = researchResponse();
      request.mockResolvedValueOnce(result);
      const original = dataset();
      const onError = vi.fn();
      const view = render(<Lab dataset={original} onError={onError} />);
      const user = userEvent.setup();
      await user.click(
        screen.getByRole('button', { name: 'Ejecutar comparación' }),
      );
      await screen.findByRole('region', { name: 'Contexto de la ejecución' });
      if (change === 'symbol') {
        await user.click(screen.getByRole('combobox', { name: 'Activo' }));
        await user.click(screen.getByRole('option', { name: 'B' }));
      } else if (change === 'costs') {
        fireEvent.change(
          screen.getByRole('spinbutton', { name: 'Capital simulado (€)' }),
          { target: { value: '20000' } },
        );
      } else {
        const changed =
          change === 'dataset'
            ? dataset('b')
            : change === 'version'
              ? dataset('a', 2)
              : dataset('a', 1, {
                  manifest: { ...original.manifest, sha256: 'b'.repeat(64) },
                });
        view.rerender(<Lab dataset={changed} onError={onError} />);
      }
      expect(screen.getByText('Resultado de otra configuración')).toBeTruthy();
      const context = screen.getByRole('region', {
        name: 'Contexto de la ejecución',
      });
      expect(
        within(context).getByRole('heading', { name: 'A · Datos a' }),
      ).toBeTruthy();
      expect(context.textContent).toContain('Versión 1');
      expect(request).toHaveBeenCalledTimes(1);
      expect(onError).not.toHaveBeenCalledWith(
        expect.stringContaining('Error'),
      );
    },
  );

  it('explica un cambio durante el cálculo y atribuye la respuesta a la petición original', async () => {
    const pending = deferred<ReturnType<typeof researchResponse>>();
    request.mockImplementationOnce(() => pending.promise);
    const onError = vi.fn();
    const view = render(<Lab dataset={dataset()} onError={onError} />);
    const user = userEvent.setup();
    await user.click(
      screen.getByRole('button', { name: 'Ejecutar comparación' }),
    );
    fireEvent.change(
      screen.getByRole('spinbutton', { name: 'Comisión (pb)' }),
      { target: { value: '9' } },
    );
    view.rerender(<Lab dataset={dataset('b', 3)} onError={onError} />);
    expect(
      screen.getByText(/El formulario ha cambiado durante el cálculo/),
    ).toBeTruthy();
    expect(screen.getByText('Calculando A · Datos a')).toBeTruthy();
    await act(async () => pending.resolve(researchResponse()));
    expect(screen.getByText('Resultado de otra configuración')).toBeTruthy();
    const context = screen.getByRole('region', {
      name: 'Contexto de la ejecución',
    });
    expect(
      within(context).getByRole('heading', { name: 'A · Datos a' }),
    ).toBeTruthy();
    expect(
      (
        screen.getByRole('spinbutton', {
          name: 'Comisión (pb)',
        }) as HTMLInputElement
      ).value,
    ).toBe('9');
    expect(request).toHaveBeenCalledWith(
      '/research',
      expect.objectContaining({
        dataset_id: 'a',
        costs: expect.objectContaining({ commission_bps: 5 }),
      }),
    );
  });

  it('muestra la versión realmente leída por el motor aunque el formulario aún tenga otra', async () => {
    const response = researchResponse();
    response.execution = {
      ...response.execution,
      dataset_version: 2,
      dataset_name: 'Nombre del servidor',
    };
    request.mockResolvedValueOnce(response);
    render(<Lab dataset={dataset()} onError={vi.fn()} />);
    const user = userEvent.setup();
    await user.click(
      screen.getByRole('button', { name: 'Ejecutar comparación' }),
    );
    const context = await screen.findByRole('region', {
      name: 'Contexto de la ejecución',
    });
    expect(
      within(context).getByRole('heading', { name: 'A · Nombre del servidor' }),
    ).toBeTruthy();
    expect(context.textContent).toContain('Versión 2');
    expect(screen.getByText('Resultado de otra configuración')).toBeTruthy();
  });

  it('mantiene compatible la investigación persistida de experimentos sin metadatos nuevos', () => {
    const response = researchResponse();
    const { execution: _execution, ...historical } = response;
    render(<ResearchResult result={historical} />);
    expect(
      screen.getByRole('heading', { name: 'Resultado fuera de muestra' }),
    ).toBeTruthy();
    expect(
      screen.queryByRole('region', { name: 'Contexto de la ejecución' }),
    ).toBeNull();
  });
});
