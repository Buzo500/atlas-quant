import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DataPanel } from './data-panel';
import { dataset, deferred } from '@/test/fixtures';

const props = () => ({
  dataset: dataset(),
  refresh: vi.fn(async () => {}),
  selectDataset: vi.fn(),
  onError: vi.fn(),
});
function delayedFile(name = 'prices.csv') {
  const pending = deferred<string>();
  const file = new File(['data'], name, { type: 'text/csv' });
  const read = vi.fn(() => pending.promise);
  Object.defineProperty(file, 'text', { value: read });
  return { file, pending, read };
}
function chooseFile(file: File) {
  fireEvent.change(screen.getByLabelText('Archivo CSV'), {
    target: { files: [file] },
  });
}

describe('Lectura de archivos CSV', () => {
  it('no pisa una edición posterior con una lectura anterior', async () => {
    render(<DataPanel {...props()} />);
    const { file, pending } = delayedFile();
    chooseFile(file);
    fireEvent.change(screen.getByRole('textbox', { name: 'Contenido CSV' }), {
      target: { value: 'edición manual' },
    });
    await act(async () => pending.resolve('archivo anterior'));
    expect(
      (
        screen.getByRole('textbox', {
          name: 'Contenido CSV',
        }) as HTMLTextAreaElement
      ).value,
    ).toBe('edición manual');
  });

  it('descarta la lectura al cambiar el tipo de importación', async () => {
    render(<DataPanel {...props()} />);
    const { file, pending } = delayedFile();
    chooseFile(file);
    const user = userEvent.setup();
    await user.click(screen.getByRole('combobox', { name: 'Tipo de archivo' }));
    await user.click(
      screen.getByRole('option', { name: 'Movimientos de cartera' }),
    );
    await act(async () => pending.resolve('precios antiguos'));
    expect(
      (
        screen.getByRole('textbox', {
          name: 'Contenido CSV',
        }) as HTMLTextAreaElement
      ).value,
    ).toBe('');
  });

  it('conserva el último archivo aunque el anterior termine después', async () => {
    render(<DataPanel {...props()} />);
    const older = delayedFile('older.csv'),
      latest = delayedFile('latest.csv');
    chooseFile(older.file);
    chooseFile(latest.file);
    await act(async () => latest.pending.resolve('último archivo'));
    await act(async () => older.pending.resolve('archivo viejo'));
    expect(
      (
        screen.getByRole('textbox', {
          name: 'Contenido CSV',
        }) as HTMLTextAreaElement
      ).value,
    ).toBe('último archivo');
  });

  it('rechaza archivos de más de 8 MB antes de leerlos', async () => {
    const input = props();
    render(<DataPanel {...input} />);
    const { file, read } = delayedFile();
    Object.defineProperty(file, 'size', { value: 8_000_001 });
    chooseFile(file);
    await waitFor(() =>
      expect(input.onError).toHaveBeenLastCalledWith('Máximo 8 MB.'),
    );
    expect(read).not.toHaveBeenCalled();
  });

  it('no propaga un error de lectura después de desmontarse', async () => {
    const input = props();
    const view = render(<DataPanel {...input} />);
    const { file, pending } = delayedFile();
    chooseFile(file);
    view.unmount();
    await act(async () => pending.reject(new Error('Lectura antigua')));
    expect(input.onError).toHaveBeenCalledTimes(1);
    expect(input.onError).toHaveBeenCalledWith('');
  });
});
