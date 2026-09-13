import { readFile } from 'node:fs/promises';
import { test, expect } from './fixtures';

test('v0.6 retrospectivo: revisión, descarga, reapertura y reserva excluida', async ({
  page,
}, info) => {
  const days = Array.from(
    { length: 14 },
    (_, i) => `2025-01-${String(i + 1).padStart(2, '0')}`,
  );
  const closes = [10, 10, 10, 12, 10, 8, 8, 10, 10, 10, 12, 10, 8, 8];
  const csv =
    'date,open,high,low,close,volume,dividends,splits\n' +
    days
      .map((day, i) => {
        const open = i === 6 || i === 13 ? 8 : 10;
        return [
          day,
          open,
          Math.max(open, closes[i]),
          Math.min(open, closes[i]),
          closes[i],
          100,
          0,
          0,
        ].join(',');
      })
      .join('\n') +
    '\n';
  await page.goto('/?tab=lab');
  await page
    .getByText('Investigación retrospectiva con supuestos', { exact: true })
    .click();
  const panel = page.locator('.retrospective-panel');
  for (const [label, value] of [
    ['Símbolo retrospectivo', 'TEST'],
    ['Identificador del instrumento / ISIN', 'TEST_ASSET'],
    ['Mercado retrospectivo', 'TEST'],
    ['Reserva desde', days[7]],
    ['Procedencia de los precios', 'Fixture ficticio'],
    ['Fuente del calendario', 'Calendario ficticio'],
    ['Revisión de dividendos y splits', 'Sin eventos en el fixture ficticio'],
    ['Media rápida retrospectiva', '2'],
    ['Media lenta retrospectiva', '3'],
    ['Capital inicial EUR', '1000'],
    ['Comisión proporcional (pb)', '0'],
    ['Deslizamiento (pb)', '0'],
  ])
    await panel.getByLabel(label, { exact: true }).fill(value);
  await panel
    .getByLabel('Archivo de precios retrospectivos (CSV, máximo 2 MB)', {
      exact: true,
    })
    .setInputFiles({
      name: 'prices.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csv),
    });
  await expect(
    panel.getByRole('textbox', { name: 'CSV retrospectivo', exact: true }),
  ).toHaveValue(csv);
  await panel
    .getByLabel('Archivo de calendario (una fecha por línea)', { exact: true })
    .setInputFiles({
      name: 'calendar.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(days.join('\n')),
    });
  const freeze = panel.getByRole('button', {
    name: 'Congelar y revisar protocolo',
  });
  await expect(freeze).toBeDisabled();
  await panel.getByRole('checkbox', { name: /Acepto los horarios/ }).check();
  await freeze.click();
  await expect(
    panel.getByRole('region', { name: 'Contexto retrospectivo congelado' }),
  ).toBeVisible();
  const result = panel.getByRole('region', {
    name: 'Resultado retrospectivo de desarrollo',
    exact: true,
  });
  await expect(result).toHaveCount(0);
  const calculate = panel.getByRole('button', {
    name: 'Calcular desarrollo retrospectivo',
  });
  await expect(calculate).toBeDisabled();
  const reviewed = panel.getByRole('checkbox', {
    name: /He revisado el protocolo congelado/,
  });
  await reviewed.focus();
  await page.keyboard.press('Space');
  await page.keyboard.press('Tab');
  await expect(calculate).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(
    result.getByRole('cell', { name: '800,00 €', exact: true }),
  ).toBeVisible();
  await expect(
    result.getByRole('cell', { name: '801,00 €', exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByText('Sin calcular · precios excluidos', { exact: true }),
  ).toBeVisible();
  const downloadEvent = page.waitForEvent('download');
  await panel.getByRole('button', { name: 'Descargar informe JSON' }).click();
  const downloaded = await downloadEvent;
  const json = await readFile((await downloaded.path())!, 'utf8');
  const report = JSON.parse(json);
  expect(report.result.holdout.evaluated).toBe(false);
  expect(report.frozen.rows).toHaveLength(7);
  expect(
    report.frozen.rows.every((row: { date: string }) => row.date < days[7]),
  ).toBe(true);
  expect(
    report.result.development.metrics.map(
      (m: { final_nav_eur: string }) => m.final_nav_eur,
    ),
  ).toEqual(['800', '801', '1000']);
  const zipEvent = page.waitForEvent('download');
  await panel
    .getByRole('button', { name: 'Exportar paquete JSON/CSV' })
    .click();
  const zipped = await zipEvent;
  expect(
    (await readFile((await zipped.path())!)).subarray(0, 4).toString('hex'),
  ).toBe('504b0304');
  await page.reload();
  await page
    .getByText('Investigación retrospectiva con supuestos', { exact: true })
    .click();
  await expect(result).toHaveCount(0);
  await panel
    .getByLabel('Informe retrospectivo guardado', { exact: true })
    .setInputFiles({
      name: 'report.json',
      mimeType: 'application/json',
      buffer: Buffer.from(json),
    });
  await expect(
    result.getByRole('cell', { name: '800,00 €', exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByText(`Informe: ${report.report_hash}`, { exact: true }),
  ).toBeVisible();
  await page
    .getByText('Investigación retrospectiva con supuestos', { exact: true })
    .click();
  await page
    .getByText('Investigación retrospectiva con supuestos', { exact: true })
    .click();
  await expect(result).toBeVisible();
  for (const width of [565, 1366, 3440]) {
    await page.setViewportSize({ width, height: width === 3440 ? 1440 : 1000 });
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      )
      .toBe(true);
    await result.scrollIntoViewIfNeeded();
    await page.screenshot({
      path: info.outputPath(`retrospective-${width}.png`),
    });
  }
});
