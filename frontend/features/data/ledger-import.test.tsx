import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DataPanel } from '@/app/workbench';
import { api } from '@/lib/api';
import {
  dataset as datasetResponse,
  deferred,
  portfolioResponse,
} from '@/test/fixtures';

vi.mock('@/lib/api', async (original) => ({
  ...(await original<typeof import('@/lib/api')>()),
  api: vi.fn(),
}));
const request = vi.mocked(api);
const reply = () => ({
  added: 1,
  duplicates: 0,
  total: 1,
  committed: false,
  portfolio: portfolioResponse(),
  preview_token: 'a'.repeat(64),
});
const props = () => ({
  // These tests isolate ledger requests; price reads have their own component
  // coverage and are exercised together with imports by the real E2E suite.
  active: false,
  dataset: datasetResponse(),
  refresh: vi.fn(async () => {}),
  selectDataset: vi.fn(),
  onError: vi.fn(),
});

async function editLedger() {
  const user = userEvent.setup();
  screen.getByRole('combobox', { name: 'Tipo de archivo' }).focus();
  await user.keyboard('{ArrowDown}');
  await user.click(
    await screen.findByRole('option', { name: 'Movimientos de cartera' }),
  );
  fireEvent.change(screen.getByRole('textbox', { name: 'Contenido CSV' }), {
    target: { value: 'csv-reviewed' },
  });
  return user;
}

describe('Confirmación de movimientos', () => {
  beforeEach(() => {
    request.mockReset();
  });
  it.each(['confirm', 'other-field', 'hidden-panel'] as const)(
    'mantiene un foco útil después de confirmar y actualizar la versión: %s',
    async (focus) => {
      const pending = deferred<unknown>();
      request
        .mockResolvedValueOnce(reply())
        .mockImplementationOnce(() => pending.promise);
      const input = props();
      let version = 1;
      let active = true;
      const view = () => (
        <>
          <div hidden={!active}>
            <DataPanel {...input} dataset={datasetResponse('a', version)} />
          </div>
          <input aria-label="Otro campo" />
        </>
      );
      const { rerender } = render(view());
      input.refresh.mockImplementation(async () => {
        version = 2;
        rerender(view());
      });
      const user = await editLedger();
      await user.click(
        screen.getByRole('button', { name: 'Previsualizar movimientos' }),
      );
      (
        await screen.findByRole('button', { name: 'Confirmar importación' })
      ).focus();
      await user.keyboard('{Enter}');
      const other = screen.getByRole('textbox', { name: 'Otro campo' });
      if (focus !== 'confirm') other.focus();
      if (focus === 'hidden-panel') {
        active = false;
        rerender(view());
      }
      await act(async () => pending.resolve({ ...reply(), committed: true }));
      await waitFor(() => expect(input.refresh).toHaveBeenCalledOnce());
      expect(request).toHaveBeenLastCalledWith('/datasets/a/ledger', {
        csv: 'csv-reviewed',
        commit: true,
        preview_token: 'a'.repeat(64),
      });
      expect(document.activeElement).toBe(
        focus === 'confirm'
          ? screen.getByRole('textbox', { name: 'Contenido CSV' })
          : other,
      );
      if (active)
        expect(
          screen.getByText('1 movimientos añadidos; 0 duplicados omitidos.'),
        ).not.toBeNull();
    },
  );

  it('conserva el mensaje de éxito cuando el refresh remonta la revisión del ledger', async () => {
    request
      .mockResolvedValueOnce(reply())
      .mockResolvedValueOnce({ ...reply(), committed: true });
    const input = props();
    const { rerender } = render(<DataPanel {...input} />);
    input.refresh.mockImplementation(async () => {
      rerender(<DataPanel {...input} dataset={datasetResponse('a', 2)} />);
    });
    const user = await editLedger();
    await user.click(
      screen.getByRole('button', { name: 'Previsualizar movimientos' }),
    );
    await user.click(
      await screen.findByRole('button', { name: 'Confirmar importación' }),
    );
    await waitFor(() => expect(input.refresh).toHaveBeenCalledOnce());
    expect(
      screen.getByText('1 movimientos añadidos; 0 duplicados omitidos.'),
    ).not.toBeNull();
  });

  it('confirma el CSV revisado con el token del servidor', async () => {
    request
      .mockResolvedValueOnce(reply())
      .mockResolvedValueOnce({ ...reply(), committed: true });
    const input = props();
    render(<DataPanel {...input} />);
    const user = await editLedger();
    await user.click(
      screen.getByRole('button', { name: 'Previsualizar movimientos' }),
    );
    await user.click(
      await screen.findByRole('button', { name: 'Confirmar importación' }),
    );
    expect(request).toHaveBeenLastCalledWith(
      `/datasets/${input.dataset.id}/ledger`,
      {
        csv: 'csv-reviewed',
        commit: true,
        preview_token: 'a'.repeat(64),
      },
    );
    await waitFor(() => expect(input.refresh).toHaveBeenCalledOnce());
    expect(
      screen.queryByRole('button', { name: 'Confirmar importación' }),
    ).toBeNull();
  });

  it.each(['dataset', 'version', 'csv'])(
    'exige otra revisión al cambiar %s',
    async (change) => {
      request.mockResolvedValue(reply());
      const input = props();
      const view = render(<DataPanel {...input} />);
      const user = await editLedger();
      await user.click(
        screen.getByRole('button', { name: 'Previsualizar movimientos' }),
      );
      await screen.findByRole('button', { name: 'Confirmar importación' });
      if (change === 'csv')
        fireEvent.change(
          screen.getByRole('textbox', { name: 'Contenido CSV' }),
          {
            target: { value: 'other-csv' },
          },
        );
      else
        view.rerender(
          <DataPanel
            {...input}
            dataset={{
              ...input.dataset,
              ...(change === 'dataset' ? { id: 'other' } : { version: 2 }),
            }}
          />,
        );
      expect(
        screen.queryByRole('button', { name: 'Confirmar importación' }),
      ).toBeNull();
      expect(request).toHaveBeenCalledTimes(1);
    },
  );

  it('descarta una previsualización que termina después de editar el CSV', async () => {
    let resolve!: (value: unknown) => void;
    request.mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    render(<DataPanel {...props()} />);
    const user = await editLedger();
    await user.click(
      screen.getByRole('button', { name: 'Previsualizar movimientos' }),
    );
    fireEvent.change(screen.getByRole('textbox', { name: 'Contenido CSV' }), {
      target: { value: 'new-csv' },
    });
    await act(async () => resolve(reply()));
    expect(
      screen.queryByRole('button', { name: 'Confirmar importación' }),
    ).toBeNull();
  });

  it('retira una confirmación rechazada para pedir otra previsualización', async () => {
    request
      .mockResolvedValueOnce(reply())
      .mockRejectedValueOnce(new Error('La previsualización ha cambiado.'));
    const input = props();
    render(<DataPanel {...input} />);
    const user = await editLedger();
    await user.click(
      screen.getByRole('button', { name: 'Previsualizar movimientos' }),
    );
    await user.click(
      await screen.findByRole('button', { name: 'Confirmar importación' }),
    );
    await waitFor(() =>
      expect(input.onError).toHaveBeenLastCalledWith(
        'La previsualización ha cambiado.',
      ),
    );
    expect(
      screen.queryByRole('button', { name: 'Confirmar importación' }),
    ).toBeNull();
    expect(input.refresh).not.toHaveBeenCalled();
  });
});
