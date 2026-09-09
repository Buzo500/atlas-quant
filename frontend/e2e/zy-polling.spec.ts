import { test, expect, ensureDemo, tab } from './fixtures';

test('sondeo del estado conserva la ficha de precios en pantalla estrecha', async ({
  page,
}, testInfo) => {
  await ensureDemo(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await tab(page, 'Datos');
  const plot = page.locator('.price-chart-svg');
  await expect(plot).toBeVisible();
  await plot.scrollIntoViewIfNeeded();
  const anchor = await plot.evaluate((element) => {
    const wick = element.querySelector<SVGLineElement>(
      '.price-rise line, .price-fall line',
    )!;
    const point = new DOMPoint(
      wick.x1.baseVal.value,
      (wick.y1.baseVal.value + wick.y2.baseVal.value) / 2,
    ).matrixTransform((element as SVGSVGElement).getScreenCTM()!);
    return { x: point.x, y: point.y };
  });
  await page.mouse.move(anchor.x, anchor.y);
  await expect(page.getByRole('tooltip')).toBeVisible();
  const before = await plot.boundingBox();
  await page.waitForResponse((reply) => reply.url().endsWith('/api/state'));
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  await testInfo.attach('poll-layout.json', {
    body: JSON.stringify({ before, after: await plot.boundingBox() }),
    contentType: 'application/json',
  });
  await expect(page.getByRole('tooltip')).toBeVisible();
});
