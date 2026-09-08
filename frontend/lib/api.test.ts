import { describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './api';

describe('Transporte HTTP local', () => {
  it('lee sin caché y propaga la señal de cancelación', async () => {
    const controller = new AbortController();
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' })),
    );
    await expect(api('/state', undefined, controller.signal)).resolves.toEqual({
      status: 'ok',
    });
    expect(fetch).toHaveBeenCalledWith('/api/state', {
      cache: 'no-store',
      signal: controller.signal,
    });
  });

  it('envía una mutación una sola vez con cabecera local y el cuerpo exacto', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ accepted: true })),
    );
    await api('/settings', { kill_switch: true });
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith(
      '/api/settings',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Atlas-Client': 'local-v1',
        },
        body: '{"kill_switch":true}',
      }),
    );
  });

  it('describe el fallo de red sin divulgar el error interno', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('SECRET transport trace'));
    const error = await api('/state').catch((cause: unknown) => cause);
    expect(error).toBeInstanceOf(ApiError);
    expect(String(error)).toContain('No se pudo conectar con el motor');
    expect(String(error)).not.toContain('SECRET');
    expect(fetch).toHaveBeenCalledOnce();
  });

  it.each(['network', 'invalid-json'])(
    'no reintenta una escritura de resultado desconocido tras %s',
    async (failure) => {
      if (failure === 'network')
        vi.mocked(fetch).mockRejectedValue(new TypeError('offline'));
      else
        vi.mocked(fetch).mockResolvedValue(
          new Response('<html>SECRET</html>', { status: 502 }),
        );
      const error = await api('/datasets/a/ledger', { csv: 'SECRET' }).catch(
        (cause: unknown) => cause,
      );
      expect(error).toBeInstanceOf(ApiError);
      expect(String(error)).toContain('confirmar');
      expect(String(error)).toContain('Actualiza los datos');
      expect(String(error)).not.toContain('SECRET');
      expect(fetch).toHaveBeenCalledOnce();
    },
  );

  it('muestra un error legible para JSON inválido de lectura', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('<html>SECRET</html>', { status: 502 }),
    );
    const error = await api('/state').catch((cause: unknown) => cause);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(502);
    expect(String(error)).toContain('respuesta válida');
    expect(String(error)).not.toContain('SECRET');
  });

  it('resume un 422 sin exponer input, contexto ni el cuerpo de la petición', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            {
              loc: ['body', 'csv'],
              msg: 'Field required',
              type: 'missing',
              input: 'SECRET CSV',
              ctx: { error: 'SECRET context' },
            },
            {
              loc: ['body', 'hours'],
              msg: 'Input should be greater than 0',
              input: 'SECRET hours',
            },
          ],
        }),
        { status: 422 },
      ),
    );
    const error = await api('/experiments', { prompt: 'SECRET prompt' }).catch(
      (cause: unknown) => cause,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(422);
    expect(String(error)).toContain('csv: Field required');
    expect(String(error)).toContain('hours: Input should be greater than 0');
    expect(String(error)).not.toContain('SECRET');
    expect(fetch).toHaveBeenCalledOnce();
  });

  it('limita el número de errores de validación y tolera entradas malformadas', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            null,
            {},
            { msg: 'error 3' },
            { msg: 'error 4' },
            { msg: 'error 5' },
            { msg: 'error 6' },
          ],
        }),
        { status: 422 },
      ),
    );
    await expect(api('/experiments')).rejects.toThrow(
      'Campo no válido. Campo no válido. error 3. error 4. error 5',
    );
  });

  it('usa el estado HTTP si no hay un detalle interpretable', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: { input: 'SECRET' } }), {
        status: 503,
      }),
    );
    await expect(api('/state')).rejects.toThrow(
      'El motor rechazó la solicitud (503).',
    );
  });

  it('preserva la cancelación durante fetch', async () => {
    const controller = new AbortController();
    const aborted = new DOMException('cancelled', 'AbortError');
    vi.mocked(fetch).mockImplementation(async () => {
      controller.abort();
      throw aborted;
    });
    await expect(api('/state', undefined, controller.signal)).rejects.toBe(
      aborted,
    );
  });

  it('preserva la cancelación durante la lectura del cuerpo JSON', async () => {
    const controller = new AbortController();
    const aborted = new DOMException('cancelled', 'AbortError');
    const response = new Response('{}');
    vi.spyOn(response, 'json').mockImplementation(async () => {
      controller.abort();
      throw aborted;
    });
    vi.mocked(fetch).mockResolvedValue(response);
    await expect(api('/state', undefined, controller.signal)).rejects.toBe(
      aborted,
    );
  });
});
