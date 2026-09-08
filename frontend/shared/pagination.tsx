'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { number } from './format';
import './pagination.css';

const PAGE_SIZE = 50;

/** Selection changes reveal that record; browsing pages does not select records. */
export function usePagination(
  total: number,
  selectionKey?: string,
  selectionIndex = -1,
) {
  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);
  const selectedPage = Math.max(0, Math.floor(selectionIndex / PAGE_SIZE));
  const [cursor, setCursor] = useState({ selectionKey, page: selectedPage });
  const page = Math.min(
    lastPage,
    cursor.selectionKey === selectionKey ? cursor.page : selectedPage,
  );
  // Adjust before children render. Returning to a previously selected ID must
  // not restore an unrelated manually browsed page saved for that old selection.
  if (cursor.selectionKey !== selectionKey || cursor.page !== page) {
    setCursor({ selectionKey, page });
  }
  const start = page * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, total);
  return {
    total,
    page,
    lastPage,
    start,
    end,
    setPage: (next: number) =>
      setCursor({ selectionKey, page: Math.max(0, Math.min(lastPage, next)) }),
  };
}

export function Pagination({
  pagination,
  label = 'registros',
}: {
  pagination: ReturnType<typeof usePagination>;
  label?: string;
}) {
  const { total, page, lastPage, start, end, setPage } = pagination;
  if (total <= PAGE_SIZE) return null;
  return (
    <nav className="table-pagination" aria-label={`Paginación de ${label}`}>
      <Button
        variant="outline"
        size="sm"
        disabled={page === 0}
        onClick={() => setPage(page - 1)}
      >
        Anterior
      </Button>
      <output aria-live="polite">
        {number(start + 1)}–{number(end)} de {number(total)} · Página{' '}
        {number(page + 1)} de {number(lastPage + 1)}
      </output>
      <Button
        variant="outline"
        size="sm"
        disabled={page === lastPage}
        onClick={() => setPage(page + 1)}
      >
        Siguiente
      </Button>
    </nav>
  );
}
