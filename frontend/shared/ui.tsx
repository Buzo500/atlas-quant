'use client';
import type { ReactNode } from 'react';
import { Pagination, usePagination } from './pagination';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export function Metric({ title, value }: { title: string; value: string }) {
  return (
    <div className="metric">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Choice({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  label: string;
}) {
  return (
    <Select
      items={options}
      value={value || null}
      onValueChange={(v) => onChange(v || '')}
    >
      <SelectTrigger aria-label={label}>
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
export function DataTable({
  heads,
  rows,
  numericColumns = [],
  emptyMessage = 'No hay registros para mostrar.',
}: {
  heads: string[];
  rows: ReactNode[][];
  numericColumns?: number[];
  emptyMessage?: string;
}) {
  const pagination = usePagination(rows.length);
  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            {heads.map((h, i) => (
              <TableHead
                key={h}
                scope="col"
                className={numericColumns.includes(i) ? 'numeric' : undefined}
              >
                {h}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.slice(pagination.start, pagination.end).map((r, i) => (
            <TableRow key={pagination.start + i}>
              {r.map((c, j) => (
                <TableCell
                  key={j}
                  className={numericColumns.includes(j) ? 'numeric' : undefined}
                >
                  {c}
                </TableCell>
              ))}
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={heads.length} className="table-empty">
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <Pagination pagination={pagination} />
    </>
  );
}
