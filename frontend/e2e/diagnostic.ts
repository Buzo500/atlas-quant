// Opt-in isolated E2E metadata only. Never record bodies, queries or credentials.
import type { Request } from '@playwright/test';
export const diagnostic = process.env.ATLAS_DIAGNOSTIC === '1';
let sequence = 0;
const starts = new WeakMap<Request, { correlation: string; start: number }>();
export const correlation = () => `client-${process.pid}-${++sequence}`;
export function trace(event: string, fields: Record<string, unknown>) {
  if (diagnostic)
    console.log(
      JSON.stringify({
        diag: 'client',
        utc: new Date().toISOString(),
        event,
        ...fields,
      }),
    );
}
export function browserStart(request: Request) {
  if (!diagnostic) return undefined;
  const value = { correlation: correlation(), start: performance.now() };
  starts.set(request, value);
  trace('start', {
    correlation: value.correlation,
    transport: 'browser',
    method: request.method(),
    path: new URL(request.url()).pathname,
    resource_type: request.resourceType(),
  });
  return value.correlation;
}
export function browserEvent(request: Request, event: string, status?: number) {
  const value = starts.get(request);
  const failure = event === 'failed' ? request.failure()?.errorText : undefined;
  if (value)
    trace(event, {
      correlation: value.correlation,
      ms: performance.now() - value.start,
      status,
      code: failure && /^net::ERR_[A-Z0-9_]+$/.test(failure) ? failure : undefined,
    });
}
