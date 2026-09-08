import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { environment } from './e2e/environment';

const isolated = environment();
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  outputDir: path.join(isolated.run, 'browser-artifacts'),
  reporter: [
    ['list'],
    ['json', { outputFile: path.join(isolated.run, 'playwright.json') }],
    ['junit', { outputFile: path.join(isolated.run, 'playwright.xml') }],
  ],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: isolated.baseURL,
    viewport: { width: 1440, height: 1000 },
    headless: true,
    serviceWorkers: 'block',
    locale: 'es-ES',
    timezoneId: 'Europe/Madrid',
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: { args: ['--disable-background-networking'] },
  },
});
