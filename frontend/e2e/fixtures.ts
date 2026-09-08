import { test as base, expect, type Page } from '@playwright/test';
import type { DatasetResponse, StateResponse } from '../lib/api-types';
import { environment } from './environment';

const isolated = environment();

export const test = base.extend<{ networkGuard: void }>({
  networkGuard: [
    async ({ context }, use) => {
      const violations: string[] = [];
      const browserErrors: string[] = [];
      await context.route('**/*', async (route) => {
        const request = route.request();
        const url = new URL(request.url());
        let allowed =
          url.origin === isolated.baseURL &&
          !url.pathname.startsWith('/api/feeds');
        if (
          allowed &&
          request.method() === 'POST' &&
          url.pathname === '/api/experiments'
        ) {
          const body = request.postDataJSON();
          allowed =
            body.provider === 'none' &&
            body.budget_usd === 0 &&
            body.hours === 1 &&
            body.auto_paper === false;
        }
        if (!allowed) {
          violations.push(`${request.method()} ${url.origin}${url.pathname}`);
          await route.abort('blockedbyclient');
        } else {
          // Real HTTP, including failures; no API response is mocked or replaced.
          await route.continue();
        }
      });
      await context.routeWebSocket('**/*', async (socket) => {
        violations.push('Unexpected WebSocket connection');
        await socket.close();
      });
      context.on('page', (page) =>
        page.on('pageerror', (error) => browserErrors.push(error.message)),
      );
      const health = await context.request.get(
        isolated.baseURL + '/api/health',
      );
      expect(health.ok()).toBe(true);
      expect(await health.json()).toMatchObject({
        status: 'ok',
        live_available: false,
      });
      await use();
      await context.setOffline(false);
      expect(
        violations,
        'El navegador intentó salir del entorno E2E o crear una ejecución no autorizada',
      ).toEqual([]);
      expect(browserErrors, 'Errores de ejecución del frontend real').toEqual(
        [],
      );
      const state = await context.request.get(isolated.baseURL + '/api/state');
      expect(state.ok()).toBe(true);
      const actual: StateResponse = await state.json();
      expect(actual.providers.every((provider) => !provider.configured)).toBe(
        true,
      );
      expect(actual.settings.kill_switch).toBe(true);
      for (const job of actual.experiments) {
        expect(job).toMatchObject({
          provider: 'none',
          budget_usd: 0,
          spent_usd: 0,
          reserved_usd: 0,
          auto_paper: false,
          hours: 1,
        });
        expect(job.paper_account).toBeNull();
      }
    },
    { auto: true },
  ],
});
export { expect };

export async function readApi<T>(page: Page, route: string): Promise<T> {
  if (!route.startsWith('/api/') || route.includes('..'))
    throw new Error('Ruta E2E ajena.');
  const response = await page.request.get(isolated.baseURL + route);
  expect(response.ok()).toBe(true);
  return response.json();
}

export async function ensureDemo(page: Page): Promise<DatasetResponse> {
  await page.goto('/');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  let state = await readApi<StateResponse>(page, '/api/state');
  if (!state.datasets.length) {
    const response = page.waitForResponse(
      (reply) =>
        reply.url().endsWith('/api/datasets/demo') &&
        reply.request().method() === 'POST',
    );
    await page
      .getByRole('button', { name: 'Cargar demostración', exact: true })
      .click();
    expect((await response).ok()).toBe(true);
    state = await readApi<StateResponse>(page, '/api/state');
  }
  expect(state.datasets).toHaveLength(1);
  expect(state.datasets[0].source_kind).toBe('synthetic');
  await expect(
    page.getByRole('heading', { name: 'Posiciones', exact: true }),
  ).toBeVisible();
  return state.datasets[0];
}

export async function tab(page: Page, name: string) {
  const target = page.getByRole('tab', { name, exact: true });
  await target.click();
  await expect(target).toHaveAttribute('aria-selected', 'true');
}

export async function select(page: Page, label: string, option: string) {
  await page.getByRole('combobox', { name: label, exact: true }).click();
  await page.getByRole('option', { name: option, exact: true }).click();
}

export async function expectVisibleFocus(page: Page) {
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const active = document.activeElement;
          if (
            !(active instanceof HTMLElement) ||
            active === document.body ||
            !active.isConnected
          )
            return false;
          const box = active.getBoundingClientRect();
          return (
            !active.closest('[hidden],[inert],[aria-hidden="true"]') &&
            getComputedStyle(active).visibility !== 'hidden' &&
            box.width > 0 &&
            box.height > 0
          );
        }),
      {
        message:
          'El foco debe conservarse en un elemento visible tras cambiar la interfaz.',
      },
    )
    .toBe(true);
}
