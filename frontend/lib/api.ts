/** The backend validates successful responses against the generated contracts. */
export async function api<T = unknown>(path: string, body?: unknown): Promise<T> {
  const response = await fetch('/api' + path, body === undefined
    ? { cache: 'no-store' }
    : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Atlas-Client': 'local-v1' },
        body: JSON.stringify(body) });
  const data: unknown = await response.json();
  if (!response.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : data;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data as T;
}
