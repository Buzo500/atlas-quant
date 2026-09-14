import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type {
  CorporateCatalog,
  CorporateEvent,
  CorporatePreview,
  CatalogResponse,
} from '@/lib/api-types';
import { CorporateEventForm } from './corporate-event-form';
import { CsvEditor, useCorporateReview } from './corporate-shared';
import {
  corporateBookInput,
  emptyCorporateDraft,
} from './book-corporate-fields';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const request = vi.mocked(api);
const event: CorporateEvent = {
  id: 'event',
  revision: 1,
  listing_id: 'listing',
  event_type: 'dividend',
  effective_date: '2026-01-10',
  payment_date: '2026-01-20',
  available_at: null,
  gross_per_unit: '0.50',
  currency: 'EUR',
  ratio_numerator: null,
  ratio_denominator: null,
  source_reference: 'Fixture',
  verified: true,
  evidence: 'Fuente contrastada',
  cancelled: false,
  created_at: '2026-01-10T00:00:00Z',
  reason: 'Importación',
};
const events: CorporateCatalog = {
  revision: 2,
  catalog_revision: 2,
  events: [event],
  sources: [],
  total: 1,
  offset: 0,
  limit: 100,
};
const catalog: CatalogResponse = {
  revision: 2,
  instruments: [
    {
      id: 'instrument',
      name: 'Activo',
      instrument_type: 'equity',
      source: 'Fixture',
      verified: false,
      codes: [],
    },
  ],
  listings: [
    {
      id: 'listing',
      instrument_id: 'instrument',
      currency: 'EUR',
      market: 'TEST',
      calendar: null,
      verified: false,
    },
  ],
  aliases: [],
};
const preview: CorporatePreview = {
  ...events,
  preview_token: 'a'.repeat(64),
  document_id: 'doc',
  added: 1,
  duplicates: 0,
  committed: false,
};
const refresh = vi.fn(async () => {});
const onError = vi.fn();
beforeEach(() => {
  request.mockReset();
  request.mockResolvedValue(preview);
  refresh.mockClear();
  onError.mockClear();
});

it('edición invalida la previsualización de eventos y conserva disponibilidad desconocida', async () => {
  const user = userEvent.setup();
  render(
    <CorporateEventForm
      catalog={catalog}
      events={events}
      refresh={refresh}
      onError={onError}
    />,
  );
  await user.click(screen.getByText('Importar o revisar eventos'));
  fireEvent.change(screen.getByLabelText('Fuente de eventos'), {
    target: { value: 'Fuente' },
  });
  fireEvent.change(
    screen.getByLabelText('CSV de eventos corporativos', { exact: true }),
    { target: { value: 'CSV original\n' } },
  );
  await user.click(
    screen.getByRole('combobox', {
      name: 'Cotizaciones del evento · destino 1',
    }),
  );
  await user.click(await screen.findByRole('option', { name: /Activo/ }));
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar eventos' }),
  );
  await screen.findByRole('button', { name: 'Confirmar eventos revisados' });
  expect(request.mock.calls[0][1]).toMatchObject({
    csv: 'CSV original\n',
    verified: false,
    mapping: { ASSET: 'listing' },
  });
  fireEvent.change(screen.getByLabelText('Evidencia del evento'), {
    target: { value: 'Nueva evidencia' },
  });
  expect(
    screen.queryByRole('button', { name: 'Confirmar eventos revisados' }),
  ).toBeNull();
  expect(request).toHaveBeenCalledTimes(1);
});

it('un conflicto de confirmación descarta el token sin reintentar ni anunciar guardado', async () => {
  const hook = renderHook(() =>
    useCorporateReview<CorporatePreview>(
      '/corporate-events/imports',
      refresh,
      onError,
    ),
  );
  await act(() => hook.result.current.review({ csv: 'A' }));
  request.mockRejectedValueOnce(new Error('El contexto ha cambiado.'));
  await act(() => hook.result.current.confirm());
  expect(hook.result.current.preview).toBeNull();
  expect(hook.result.current.message).toBe('');
  expect(onError).toHaveBeenLastCalledWith('El contexto ha cambiado.');
  expect(refresh).not.toHaveBeenCalled();
  expect(request).toHaveBeenCalledTimes(2);
});

it('confirmar dos veces en el mismo turno envía una sola copia del cuerpo revisado', async () => {
  const hook = renderHook(() =>
    useCorporateReview<CorporatePreview>('/events', refresh, onError),
  );
  await act(() =>
    hook.result.current.review({ csv: 'Original', source: 'Fixture' }),
  );
  let finish!: (v: unknown) => void;
  request.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  let pending!: Promise<void>;
  act(() => {
    pending = hook.result.current.confirm();
    void hook.result.current.confirm();
  });
  expect(request).toHaveBeenCalledTimes(2);
  expect(request.mock.calls[1][1]).toEqual({
    csv: 'Original',
    source: 'Fixture',
    commit: true,
    preview_token: preview.preview_token,
  });
  await act(async () => {
    finish(preview);
    await pending;
  });
  expect(refresh).toHaveBeenCalledTimes(1);
});

it.each(['success', 'error'])(
  'una respuesta tardía %s no recupera una previsualización invalidada',
  async (outcome) => {
    let finish!: (v: unknown) => void;
    let fail!: (e: Error) => void;
    request.mockImplementationOnce(
      () =>
        new Promise((resolve, reject) => {
          finish = resolve;
          fail = reject;
        }),
    );
    const hook = renderHook(() =>
      useCorporateReview<CorporatePreview>('/events', refresh, onError),
    );
    let pending!: Promise<void>;
    act(() => {
      pending = hook.result.current.review({ csv: 'A' });
    });
    act(() => hook.result.current.invalidate());
    await act(async () => {
      if (outcome === 'success') finish(preview);
      else fail(new Error('Error anterior'));
      await pending;
    });
    expect(hook.result.current.preview).toBeNull();
    expect(onError).not.toHaveBeenCalledWith('Error anterior');
  },
);

it('desmontar el formulario durante una confirmación no refresca otra cartera', async () => {
  const hook = renderHook(() =>
    useCorporateReview<CorporatePreview>('/events', refresh, onError),
  );
  await act(() => hook.result.current.review({ csv: 'A' }));
  let finish!: (v: unknown) => void;
  request.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  let pending!: Promise<void>;
  act(() => {
    pending = hook.result.current.confirm();
  });
  hook.unmount();
  await act(async () => {
    finish(preview);
    await pending;
  });
  expect(refresh).not.toHaveBeenCalled();
});

it('un archivo que acaba de leerse tarde no sustituye el CSV editado a mano', async () => {
  const change = vi.fn();
  let finish!: (v: ArrayBuffer) => void;
  const file = new File(['fixture'], 'eventos.csv', { type: 'text/csv' });
  Object.defineProperty(file, 'arrayBuffer', {
    value: () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  });
  render(
    <CsvEditor label="Eventos" value="" onChange={change} onError={onError} />,
  );
  fireEvent.change(screen.getByLabelText('Archivo · Eventos'), {
    target: { files: [file] },
  });
  fireEvent.change(screen.getByLabelText('Eventos', { exact: true }), {
    target: { value: 'Editado' },
  });
  await act(async () => {
    finish(new TextEncoder().encode('Viejo').buffer);
  });
  await waitFor(() => expect(change).toHaveBeenLastCalledWith('Editado'));
});

it('el lote transmite evidencia y revisiones conjuntas y rechaza IDs repetidos', () => {
  const draft = emptyCorporateDraft();
  draft.mapping = [{ key: 'DIV', value: 'event' }];
  draft.payments = [{ key: 'payment', value: 'Extracto' }];
  draft.reviews = [
    {
      id: 'event',
      review: {
        event_revision: 2,
        day_sequence: 10,
        evidence: 'Cantidad contrastada',
        eligible_quantity: '100',
      },
    },
  ];
  expect(corporateBookInput(draft, false)).toMatchObject({
    corporate_mapping: { DIV: 'event' },
    unaccredited_payments: { payment: 'Extracto' },
    corporate_reviews: { event: { event_revision: 2 } },
  });
  expect(corporateBookInput(draft, true)).toEqual({
    corporate_reviews: { event: draft.reviews[0].review },
  });
  draft.reviews.push(draft.reviews[0]);
  expect(() => corporateBookInput(draft, false)).toThrow(
    /ID de evento distinto/,
  );
});
