import { Button } from '@/components/ui/button';
import { dateTime } from '@/shared/format';

export function QueryStatus({
  label,
  query,
}: {
  label: string;
  query: {
    data: unknown;
    error: string;
    loading: boolean;
    updatedAt: number | null;
    refresh: () => Promise<void>;
  };
}) {
  return (
    <div className={'query-status' + (query.error ? ' query-error' : '')}>
      <span role={query.error ? 'alert' : 'status'}>
        {query.error
          ? `${label}: ${query.error} `
          : query.loading
            ? `${query.data ? 'Actualizando' : 'Cargando'} ${label.toLowerCase()}… `
            : ''}
        {query.updatedAt != null &&
          `${query.error || query.loading ? 'Últimos datos disponibles' : 'Última consulta'}: ${dateTime(new Date(query.updatedAt).toISOString())}.`}
      </span>
      {query.error && (
        <Button
          variant="outline"
          size="sm"
          disabled={query.loading}
          onClick={() => void query.refresh()}
        >
          Reintentar {label.toLowerCase()}
        </Button>
      )}
    </div>
  );
}
