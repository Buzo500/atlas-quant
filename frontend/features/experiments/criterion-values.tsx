import { number } from '@/shared/format';

export function CriterionValues({
  actual,
  required,
}: {
  actual: unknown;
  required: unknown;
}) {
  const values = [
    { label: 'Actual', value: actual },
    { label: 'Requerido', value: required },
  ];
  const isStructured = (value: unknown) =>
    value !== null && typeof value === 'object';
  const primitives = values.filter(({ value }) => !isStructured(value));
  const structured = values.filter(({ value }) => isStructured(value));
  const format = (value: unknown) => {
    if (value == null) return 'Sin dato';
    if (typeof value === 'boolean') return value ? 'Sí' : 'No';
    if (typeof value === 'number') {
      return number(value, { maximumFractionDigits: 6 });
    }
    return typeof value === 'string'
      ? value
      : (JSON.stringify(value) ?? 'Sin dato');
  };
  return (
    <>
      {primitives.length > 0 && (
        <small>
          {primitives.map(({ label, value }, index) => (
            <span key={label}>
              {index > 0 ? ' · ' : ''}
              {label}: {format(value)}
            </span>
          ))}
        </small>
      )}
      {structured.length > 0 && (
        <details className="details criterion-data">
          <summary>Ver datos del criterio</summary>
          {structured.map(({ label, value }) => (
            <div key={label}>
              <strong>{label}</strong>
              <pre>{JSON.stringify(value, null, 2)}</pre>
            </div>
          ))}
        </details>
      )}
    </>
  );
}
