import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import {
  dataset,
  experimentResponse,
  mockFetch,
  stateResponse,
} from '@/test/fixtures';
import { AgentPanel } from './agent-panel';

function experiments(count: number) {
  return Array.from({ length: count }, (_, index) =>
    experimentResponse({
      id: `job-${String(index + 1).padStart(4, '0')}`,
    }),
  );
}

describe('Paginación y expediente seleccionado', () => {
  it('abre un ID enlazado fuera de la primera página y conserva el expediente al navegar por la lista', async () => {
    const records = experiments(1000);
    const fetchMock = mockFetch((path) => {
      const record = records.find(
        (item) => path === `/api/experiments/${item.id}`,
      );
      if (!record) throw new Error(`Ruta inesperada ${path}`);
      return record;
    });
    const input = {
      dataset: dataset(),
      state: stateResponse({ experiments: records }),
      refresh: vi.fn(async () => {}),
      onError: vi.fn(),
      onSelect: vi.fn(),
    };
    const { rerender } = render(
      <AgentPanel {...input} selectedId="job-1000" />,
    );
    const report = await screen.findByRole('link', {
      name: 'Exportar informe JSON',
    });
    expect(report.getAttribute('href')).toBe(
      '/api/experiments/job-1000/report',
    );
    expect(
      screen.getByText('951–1000 de 1000 · Página 20 de 20'),
    ).not.toBeNull();
    expect(
      screen
        .getByRole('button', { name: 'Ver experimento A job-1000' })
        .getAttribute('aria-pressed'),
    ).toBe('true');
    expect(screen.getAllByRole('row')).toHaveLength(51);
    const user = userEvent.setup();
    await user.click(
      within(
        screen.getByRole('navigation', { name: 'Paginación de experimentos' }),
      ).getByRole('button', { name: 'Anterior' }),
    );
    expect(
      screen.getByText('901–950 de 1000 · Página 19 de 20'),
    ).not.toBeNull();
    expect(report.getAttribute('href')).toBe(
      '/api/experiments/job-1000/report',
    );
    expect(input.onSelect).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    rerender(<AgentPanel {...input} selectedId="job-0005" />);
    expect(screen.getByText('1–50 de 1000 · Página 1 de 20')).not.toBeNull();
    await user.click(
      within(
        screen.getByRole('navigation', { name: 'Paginación de experimentos' }),
      ).getByRole('button', { name: 'Siguiente' }),
    );
    rerender(<AgentPanel {...input} selectedId="job-1000" />);
    expect(
      screen.getByText('951–1000 de 1000 · Página 20 de 20'),
    ).not.toBeNull();
    rerender(<AgentPanel {...input} selectedId="job-0005" />);
    expect(screen.getByText('1–50 de 1000 · Página 1 de 20')).not.toBeNull();
  });

  it('limita la página cuando una actualización reduce el número de experimentos', () => {
    const records = experiments(120);
    const input = {
      dataset: dataset(),
      refresh: vi.fn(async () => {}),
      onError: vi.fn(),
      active: false,
      selectedId: 'job-0110',
    };
    const { rerender } = render(
      <AgentPanel {...input} state={stateResponse({ experiments: records })} />,
    );
    expect(screen.getByText('101–120 de 120 · Página 3 de 3')).not.toBeNull();
    rerender(
      <AgentPanel
        {...input}
        state={stateResponse({ experiments: records.slice(0, 60) })}
      />,
    );
    expect(screen.getByText('51–60 de 60 · Página 2 de 2')).not.toBeNull();
    expect(screen.getAllByRole('row')).toHaveLength(11);
    expect(
      screen.getByRole('button', { name: 'Ver experimento A job-0060' }),
    ).not.toBeNull();
  });
});
