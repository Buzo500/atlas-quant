/** Immutable daily-price read: the dataset version is always explicit. */
export function datasetPricesPath(
  id: string,
  version: number,
  symbol: string,
  range: { start?: string; end?: string } = {},
): string {
  if (!id || !symbol || !Number.isInteger(version) || version < 1)
    throw new Error(
      'Selecciona un conjunto, una versión positiva y un activo.',
    );
  const query = new URLSearchParams({ version: String(version), symbol });
  if (range.start) query.set('start', range.start);
  if (range.end) query.set('end', range.end);
  return `/datasets/${encodeURIComponent(id)}/prices?${query}`;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function detailMessage(data: unknown): string | undefined {
  if (!data || typeof data !== 'object' || !('detail' in data)) return;
  const detail: unknown = data.detail;
  if (typeof detail === 'string') return detail;
  // Validation errors may include the rejected CSV or prompt. Only expose the
  // location and explanation, never serialize a complete request or response.
  if (Array.isArray(detail))
    return detail
      .map((item: unknown) => {
        if (!item || typeof item !== 'object' || !('msg' in item))
          return 'Campo no válido';
        const location =
          'loc' in item && Array.isArray(item.loc)
            ? item.loc
                .filter(
                  (part: unknown) =>
                    typeof part === 'string' && part !== 'body',
                )
                .join(' · ')
            : '';
        return `${location ? location + ': ' : ''}${String(item.msg)}`;
      })
      .slice(0, 5)
      .join('. ');
}

/** Successful responses are validated by the backend against generated contracts.
 * Reads are cancellable. Mutations are never retried automatically. */
export async function api<T = unknown>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(
      '/api' + path,
      body === undefined
        ? { cache: 'no-store', signal }
        : {
            method: 'POST',
            signal,
            headers: {
              'Content-Type': 'application/json',
              'X-Atlas-Client': 'local-v1',
            },
            body: JSON.stringify(body),
          },
    );
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(
      body === undefined
        ? 'No se pudo conectar con el motor. Comprueba que ATLAS está iniciado.'
        : 'No se pudo confirmar el resultado de la operación. Actualiza los datos antes de volver a intentarlo.',
    );
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(
      body === undefined
        ? 'El motor no devolvió una respuesta válida. Vuelve a consultar.'
        : 'La respuesta no permite confirmar la operación. Actualiza los datos antes de repetirla.',
      response.status,
    );
  }
  if (!response.ok)
    throw new ApiError(
      detailMessage(data) ||
        `El motor rechazó la solicitud (${response.status}).`,
      response.status,
    );
  return data as T;
}
