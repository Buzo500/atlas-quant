'use client';
import { Input } from '@/components/ui/input';
import { Field } from '@/shared/ui';

export const DEFAULT_COSTS = {
  initial_cash: 10000,
  commission_bps: 5,
  slippage_bps: 5,
  minimum_fee: 1.25,
  max_position_weight: 0.25,
};
export function CostForm({
  costs,
  setCosts,
}: {
  costs: typeof DEFAULT_COSTS;
  setCosts: (c: typeof DEFAULT_COSTS) => void;
}) {
  return (
    <div className="form-grid costs">
      {Object.entries({
        initial_cash: 'Capital simulado (€)',
        commission_bps: 'Comisión (pb)',
        slippage_bps: 'Deslizamiento (pb)',
        minimum_fee: 'Comisión mínima (€)',
        max_position_weight: 'Peso máximo (0–1)',
      }).map(([key, label]) => (
        <Field key={key} label={label}>
          <Input
            type="number"
            min={key === 'initial_cash' ? 100 : 0}
            step={key === 'max_position_weight' ? '.05' : '.25'}
            max={key === 'max_position_weight' ? 1 : undefined}
            value={costs[key as keyof typeof costs]}
            onChange={(e) =>
              setCosts({ ...costs, [key]: Number(e.target.value) })
            }
          />
        </Field>
      ))}
    </div>
  );
}
