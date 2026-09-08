import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { DataTable } from './ui';

const rows = (count: number) =>
  Array.from({ length: count }, (_, index) => [
    `Activo ${index + 1}`,
    index + 1,
  ]);

describe('Paginación de tablas', () => {
  it('mantiene una tabla corta completa sin controles innecesarios', () => {
    render(<DataTable heads={['Activo', 'Cantidad']} rows={rows(50)} />);
    expect(screen.getAllByRole('row')).toHaveLength(51);
    expect(screen.getByRole('cell', { name: 'Activo 50' })).not.toBeNull();
    expect(screen.queryByRole('navigation')).toBeNull();
  });

  it('limita el DOM, muestra el total y permite alcanzar las últimas filas con teclado', async () => {
    const user = userEvent.setup();
    render(<DataTable heads={['Activo', 'Cantidad']} rows={rows(120)} />);
    expect(screen.getAllByRole('row')).toHaveLength(51);
    expect(screen.queryByRole('cell', { name: 'Activo 51' })).toBeNull();
    expect(screen.getByText('1–50 de 120 · Página 1 de 3')).not.toBeNull();
    expect(
      screen.getByRole('button', { name: 'Anterior' }).hasAttribute('disabled'),
    ).toBe(true);
    screen.getByRole('button', { name: 'Siguiente' }).focus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('cell', { name: 'Activo 51' })).not.toBeNull();
    await user.keyboard('{Enter}');
    expect(screen.getByText('101–120 de 120 · Página 3 de 3')).not.toBeNull();
    expect(screen.getByRole('cell', { name: 'Activo 120' })).not.toBeNull();
    expect(screen.getAllByRole('row')).toHaveLength(21);
    expect(
      screen
        .getByRole('button', { name: 'Siguiente' })
        .hasAttribute('disabled'),
    ).toBe(true);
    screen.getByRole('button', { name: 'Anterior' }).focus();
    await user.keyboard(' ');
    expect(screen.getByText('51–100 de 120 · Página 2 de 3')).not.toBeNull();
  });

  it('ajusta una página que deja de existir tras actualizar el conjunto', async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <DataTable heads={['Activo', 'Cantidad']} rows={rows(120)} />,
    );
    await user.click(screen.getByRole('button', { name: 'Siguiente' }));
    await user.click(screen.getByRole('button', { name: 'Siguiente' }));
    rerender(<DataTable heads={['Activo', 'Cantidad']} rows={rows(60)} />);
    expect(screen.getByText('51–60 de 60 · Página 2 de 2')).not.toBeNull();
    expect(screen.getByRole('cell', { name: 'Activo 60' })).not.toBeNull();
    expect(screen.getAllByRole('row')).toHaveLength(11);
    rerender(<DataTable heads={['Activo', 'Cantidad']} rows={[]} />);
    expect(
      screen.getByRole('cell', { name: 'No hay registros para mostrar.' }),
    ).not.toBeNull();
    expect(screen.queryByRole('navigation')).toBeNull();
    rerender(<DataTable heads={['Activo', 'Cantidad']} rows={rows(120)} />);
    expect(screen.getByText('1–50 de 120 · Página 1 de 3')).not.toBeNull();
  });
});
