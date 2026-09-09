import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type {
  BookDetail,
  BookPreview,
  PortfolioRecord,
  CatalogResponse,
} from '@/lib/api-types';
import { BookWorkspace } from './book-panel';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const request = vi.mocked(api);
const portfolio: PortfolioRecord = {
  id: 'p',
  name: 'Libro de prueba',
  account_id: 'a',
  base_currency: 'EUR',
  accounting_policy: 'atlas-accounting-v2',
  legacy_dataset_id: null,
  revision: 1,
  catalog_revision: 0,
  event_ids: [],
  bindings: [],
};
const catalog: CatalogResponse = {
  revision: 0,
  instruments: [],
  listings: [],
  aliases: [],
};
const book: BookDetail = {
  context: {
    portfolio_id: 'p',
    portfolio_revision: 1,
    catalog_revision: 0,
    accounting_policy: 'atlas-accounting-v2',
    as_of_date: '2026-01-05',
  },
  balance: {
    as_of_date: '2026-01-05',
    cash: '100.00',
    currency: 'EUR',
    net_contributions: '100.00',
    realized_pnl: '0',
    positions: [],
    warnings: [],
  },
  entries: [],
  total: 0,
  offset: 0,
  limit: 100,
  sources: [],
};
const preview: BookPreview = {
  ...book,
  added: 1,
  duplicates: 0,
  historical_insertion: false,
  committed: false,
  preview_token: 'a'.repeat(64),
  document_id: 'd',
};
const props = {
  portfolio,
  catalog,
  active: true,
  refresh: vi.fn(async () => {}),
  onError: vi.fn(),
};
beforeEach(() => {
  request.mockReset();
  props.refresh.mockClear();
  props.onError.mockClear();
  request.mockImplementation(async (path, body) =>
    path.includes('book-documents')
      ? { documents: [], total: 0, offset: 0, limit: 20 }
      : body
        ? preview
        : book,
  );
});

async function openEditor() {
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole('button', { name: 'Revisar un lote o extracto' }),
  );
  fireEvent.change(screen.getByLabelText('Fuente del extracto'), {
    target: { value: 'Fixture' },
  });
  fireEvent.change(screen.getByLabelText('Cuenta de origen'), {
    target: { value: 'DEMO' },
  });
  fireEvent.change(screen.getByLabelText('Contenido del libro o extracto'), {
    target: { value: 'CSV de prueba\n' },
  });
  return user;
}
const writes = () =>
  request.mock.calls.filter(
    ([, body]) =>
      body &&
      typeof body === 'object' &&
      'commit' in body &&
      body.commit === true,
  );

it('editar CSV invalida el token y conserva el texto original del archivo', async () => {
  render(<BookWorkspace {...props} />);
  const user = await openEditor();
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar revisión' }),
  );
  await screen.findByRole('button', { name: 'Confirmar revisión contable' });
  expect(request.mock.calls.find(([, body]) => body)?.[1]).toMatchObject({
    csv: 'CSV de prueba\n',
    commit: false,
  });
  fireEvent.change(screen.getByLabelText('Contenido del libro o extracto'), {
    target: { value: 'Revisado' },
  });
  expect(
    screen.queryByRole('button', { name: 'Confirmar revisión contable' }),
  ).toBeNull();
  expect(writes()).toHaveLength(0);
});

it('conflicto al confirmar descarta el token y no anuncia guardado', async () => {
  request.mockImplementation(async (_path, body) => {
    if (body && typeof body === 'object' && 'commit' in body && body.commit)
      throw new Error('La cartera ha cambiado.');
    return body ? preview : book;
  });
  render(<BookWorkspace {...props} />);
  const user = await openEditor();
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar revisión' }),
  );
  await user.click(
    await screen.findByRole('button', { name: 'Confirmar revisión contable' }),
  );
  await waitFor(() =>
    expect(props.onError).toHaveBeenLastCalledWith('La cartera ha cambiado.'),
  );
  expect(
    screen.queryByRole('button', { name: 'Confirmar revisión contable' }),
  ).toBeNull();
  expect(props.refresh).not.toHaveBeenCalled();
  expect(screen.queryByText(/Revisión guardada/)).toBeNull();
});

it('doble clic confirma una vez y bloquea la edición durante la petición', async () => {
  let finish!: (value: unknown) => void;
  request.mockImplementation(async (_path, body) => {
    if (body && typeof body === 'object' && 'commit' in body && body.commit)
      return new Promise((resolve) => {
        finish = resolve;
      });
    return body ? preview : book;
  });
  render(<BookWorkspace {...props} />);
  const user = await openEditor();
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar revisión' }),
  );
  await user.dblClick(
    await screen.findByRole('button', { name: 'Confirmar revisión contable' }),
  );
  expect(writes()).toHaveLength(1);
  expect(
    screen.getByLabelText('Contenido del libro o extracto').closest('fieldset')
      ?.disabled,
  ).toBe(true);
  expect(writes()[0][1]).toMatchObject({
    preview_token: preview.preview_token,
    expected_revision: 1,
  });
  await act(async () => finish({ ...preview, committed: true }));
  await waitFor(() => expect(props.refresh).toHaveBeenCalledTimes(1));
});

it('cambiar de cartera descarta una confirmación tardía de la cartera anterior', async () => {
  let finish!: (value: unknown) => void;
  request.mockImplementation(async (_path, body) => {
    if (body && typeof body === 'object' && 'commit' in body && body.commit)
      return new Promise((resolve) => {
        finish = resolve;
      });
    return body ? preview : book;
  });
  const view = render(<BookWorkspace key="p" {...props} />);
  const user = await openEditor();
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar revisión' }),
  );
  await user.click(
    await screen.findByRole('button', { name: 'Confirmar revisión contable' }),
  );
  view.rerender(
    <BookWorkspace
      key="other"
      {...props}
      portfolio={{ ...portfolio, id: 'other' }}
    />,
  );
  await act(async () => finish({ ...preview, committed: true }));
  expect(props.refresh).not.toHaveBeenCalled();
  expect(screen.queryByText(/Revisión guardada/)).toBeNull();
});

it('cartera heredada solo ofrece extractos y exige declarar su integridad', async () => {
  render(
    <BookWorkspace
      {...props}
      portfolio={{ ...portfolio, accounting_policy: 'legacy-eur-v1' }}
    />,
  );
  const user = await openEditor();
  const button = screen.getByRole('button', { name: 'Previsualizar revisión' });
  expect(button.hasAttribute('disabled')).toBe(true);
  await user.click(screen.getByRole('combobox', { name: 'Tipo de revisión' }));
  expect(
    screen.queryByRole('option', { name: 'Movimientos CSV v2' }),
  ).toBeNull();
  await user.keyboard('{Escape}');
  await user.click(screen.getByRole('checkbox'));
  await user.click(button);
  await waitFor(() =>
    expect(request.mock.calls.find(([, body]) => body)?.[1]).toMatchObject({
      complete_statement: true,
      format_id: 'atlas-statement-v2',
    }),
  );
});

it('guardar extracto refresca historial aunque la revisión del libro no cambie', async () => {
  request.mockImplementation(async (path, body) =>
    path.includes('book-documents')
      ? { documents: [], total: 0, offset: 0, limit: 20 }
      : body
        ? { ...preview, differences: [], status: 'matched' }
        : book,
  );
  render(
    <BookWorkspace
      {...props}
      portfolio={{ ...portfolio, accounting_policy: 'legacy-eur-v1' }}
    />,
  );
  const user = await openEditor();
  await user.click(
    screen.getByText('Historial de lotes, extractos y correcciones'),
  );
  await waitFor(() =>
    expect(
      request.mock.calls.filter(([path]) => path.includes('book-documents')),
    ).toHaveLength(1),
  );
  await user.click(screen.getByRole('checkbox'));
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar revisión' }),
  );
  await user.click(
    await screen.findByRole('button', { name: 'Confirmar revisión contable' }),
  );
  await waitFor(() =>
    expect(
      request.mock.calls.filter(([path]) => path.includes('book-documents')),
    ).toHaveLength(2),
  );
  expect(writes()).toHaveLength(1);
});
