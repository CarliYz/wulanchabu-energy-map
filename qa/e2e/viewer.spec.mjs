import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function pointerClick(page, selector) {
  const item = page.locator(selector);
  const box = await item.boundingBox();
  expect(box, `${selector} visible`).toBeTruthy();
  const p = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  expect(await item.evaluate((el, p) => el.contains(document.elementFromPoint(p.x, p.y)), p), `${selector} not obstructed`).toBe(true);
  await page.mouse.click(p.x, p.y);
}

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toBeHidden({ timeout: 30000 });
  await expect(page.locator('#status')).not.toHaveText('加载中');
});

test('真实指针可展开索引，选C区并聚焦', async ({ page }) => {
  await pointerClick(page, '#collapse-tree');
  await pointerClick(page, '.location[data-id="AGRI_018"]');
  await expect(page.locator('#map-viewport')).toHaveAttribute('data-selected-id', 'AGRI_018');
  await expect(page.locator('#map-viewport')).toHaveAttribute('data-focused-id', 'AGRI_018');
  await expect(page.locator('#detail-id')).toHaveText('AGRI_018');
  await pointerClick(page, '#collapse-tree');
  await expect(page.locator('#toolbar')).toHaveClass(/collapsed/);
});

test('新需求：顶部三视图都可点击并返回标准地图', async ({ page }) => {
  await pointerClick(page, '#map-satellite');
  await expect(page.locator('#map-satellite')).toHaveClass(/active/);
  await expect(page.getByRole('button', { name: /数据图层/ })).toBeVisible();
  await page.getByRole('button', { name: /数据图层/ }).click();
  await pointerClick(page, '#map-standard');
  await expect(page.locator('#map-standard')).toHaveClass(/active/);
});

test('新需求：Escape关闭审计并归还焦点', async ({ page }) => {
  await pointerClick(page, '#audit-toggle');
  await expect(page.locator('#audit-panel')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#audit-panel')).toBeHidden();
  await expect(page.locator('#audit-toggle')).toBeFocused();
});

test('新需求：设施详情默认隐藏，点选显示并可关闭', async ({ page }) => {
  await expect(page.locator('#details')).toBeHidden();
  await pointerClick(page, '#collapse-tree');
  await pointerClick(page, '.location[data-id="AGRI_018"]');
  await expect(page.locator('#details')).toBeVisible();
  await page.getByRole('button', { name: '关闭设施详情', exact: true }).click();
  await expect(page.locator('#details')).toBeHidden();
});

test('审计 WCAG 缺陷并输出可复核结果', async ({ page }, testInfo) => {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  await testInfo.attach('axe-report', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  expect(result.violations.filter(v => ['critical', 'serious'].includes(v.impact))).toEqual([]);
});
