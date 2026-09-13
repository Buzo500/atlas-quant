import { afterEach, expect, it, vi } from 'vitest';
import type { Request } from '@playwright/test';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.resetModules(); });

function request(failure = 'net::ERR_NO_BUFFER_SPACE') {
  return { url: () => 'http://127.0.0.1:3000/_next/static/app.js?private=value',
    method: () => 'GET', resourceType: () => 'script',
    failure: () => ({ errorText: failure }) } as unknown as Request;
}

it('records a failed static asset and socket code without its query', async () => {
  vi.stubEnv('ATLAS_DIAGNOSTIC', '1');
  const log = vi.spyOn(console, 'log').mockImplementation(() => {});
  const { browserStart, browserEvent } = await import('../e2e/diagnostic');
  const asset = request();
  browserStart(asset); browserEvent(asset, 'failed');
  const records = log.mock.calls.map(([line]) => JSON.parse(line));
  expect(records[0]).toMatchObject({ path: '/_next/static/app.js', resource_type: 'script' });
  expect(records[1]).toMatchObject({ code: 'net::ERR_NO_BUFFER_SPACE', event: 'failed', correlation: records[0].correlation });
  expect(JSON.stringify(records)).not.toContain('private');
});

it('never records arbitrary failure descriptions', async () => {
  vi.stubEnv('ATLAS_DIAGNOSTIC', '1');
  const log = vi.spyOn(console, 'log').mockImplementation(() => {});
  const { browserStart, browserEvent } = await import('../e2e/diagnostic');
  const asset = request('unexpected private message');
  browserStart(asset); browserEvent(asset, 'failed');
  expect(JSON.stringify(log.mock.calls)).not.toContain('private');
});

it('does not emit diagnostics in normal runs', async () => {
  vi.stubEnv('ATLAS_DIAGNOSTIC', '0');
  const log = vi.spyOn(console, 'log').mockImplementation(() => {});
  const { browserStart, browserEvent } = await import('../e2e/diagnostic');
  const asset = request();
  expect(browserStart(asset)).toBeUndefined(); browserEvent(asset, 'failed');
  expect(log).not.toHaveBeenCalled();
});
