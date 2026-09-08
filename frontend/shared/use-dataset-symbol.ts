import { useState } from 'react';
import type { DatasetResponse } from '@/lib/api-types';

export function useDatasetSymbol(dataset: DatasetResponse | undefined) {
  const [selections, setSelections] = useState<Record<string, string>>({});
  const symbols = dataset?.manifest.symbols ?? [];
  const selected = dataset ? selections[dataset.id] : undefined;
  const symbol =
    selected && symbols.includes(selected) ? selected : (symbols[0] ?? '');
  const setSymbol = (value: string) => {
    if (dataset)
      setSelections((current) => ({ ...current, [dataset.id]: value }));
  };
  return { symbols, symbol, setSymbol };
}
