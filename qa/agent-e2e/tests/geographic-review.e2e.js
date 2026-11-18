import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { REVIEW_SOURCE } from '../../../web/map-prototype/geographic-review-source.mjs';

const button = (screen, name) => screen.getByRole('button', { name, exact: true });
const pad = '定位复核 pad/AGRI_018/waterbody/relation/7763319';
async function open(app, screen) {
  await app.open(); await expect(screen.getByRole('status')).toContainText('85对象统一模型');
  await button(screen, '地理复核').click();
  await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toContainText('2814 个地物');
}
describe('公开地理复核', () => {
  test('审计页追踪当前模型和地理来源与工程未决状态', async ({ app, screen }) => {
    await app.open(); await expect(screen.getByRole('status')).toContainText('85对象统一模型');

    await button(screen, '审计').click();

    const audit = screen.getByRole('dialog', { name: '审计与系统状态', exact: true });
    await expect(audit).toContainText('m14-sensors-integrated-v1');
    await expect(audit).toContainText('公开地物复核报告');
    await expect(audit).toContainText('公开地物几何');
    await expect(audit).toContainText('2814');
    await expect(audit).toContainText('独立');
  });
  test('C1场坪相交观察展示来源与独立工程缺口', async ({ app, screen, browser }) => {
    await open(app, screen);

    await button(screen, pad).click();

    const detail = screen.getByRole('region', { name: '地理复核详情', exact: true });
    await expect(detail).toContainText('红海子 · relation/7763319');
    await expect(detail).toContainText('公开几何相交 / 包含');
    await expect(detail).toContainText('blocked');
    await expect(detail).toContainText('61e1bfc2489fc20a');
    expect(await browser.evaluate(() => m9.state.reviewObservation)).toEqual('pad/AGRI_018/waterbody/relation/7763319');
  });
  test('Esc先返回原列表视角和焦点再退出复核', async ({ app, screen, browser }) => {
    await open(app, screen);
    const view = await browser.evaluate(() => ({ center: m9.map.getCenter().toArray(), zoom: m9.map.getZoom(), elevation: m9.map.getCenterElevation() }));
    await button(screen, pad).click();

    await browser.keyboard.press('Escape');

    await expect(button(screen, pad)).toBeFocused();
    expect(await browser.evaluate(() => ({ center: m9.map.getCenter().toArray(), zoom: m9.map.getZoom(), elevation: m9.map.getCenterElevation() }))).toEqual(view);
    await browser.keyboard.press('Escape');
    await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toBeHidden();
    await expect(button(screen, '地理复核')).toBeFocused();
  });
  test('关闭复核恢复进入前的设施详情与回路选择', async ({ app, screen, browser }) => {
    await app.open(); await expect(screen.getByRole('status')).toContainText('85对象统一模型');
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '设备与回路').click(); await button(screen, '营养液回路').click();
    await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
    const view = await browser.evaluate(() => ({ center: m9.map.getCenter().toArray(), zoom: m9.map.getZoom(), elevation: m9.map.getCenterElevation() }));
    await button(screen, '地理复核').click(); await button(screen, pad).click();

    await button(screen, '关闭地理复核').click();

    await expect(screen.getByRole('complementary', { name: '设施详情', exact: true })).toContainText('叶菜水培与冷凉种苗');
    await expect(button(screen, '营养液回路')).toHaveAttribute('aria-pressed', 'true');
    expect(await browser.evaluate(() => ({ center: m9.map.getCenter().toArray(), zoom: m9.map.getZoom(), elevation: m9.map.getCenterElevation() }))).toEqual(view);
  });
  test('三种底图切换保留复核点和公开覆盖层', async ({ app, screen, browser }) => {
    await open(app, screen); await button(screen, pad).click();
    const view = await browser.evaluate(() => ({ center: m9.map.getCenter().toArray(), zoom: m9.map.getZoom() }));

    for (const name of ['卫星', '数据 / DEM', '标准地图']) await button(screen, name).click();

    await expect(screen.getByRole('region', { name: '地理复核详情', exact: true })).toContainText('relation/7763319');
    expect(await browser.evaluate(() => m9.state.reviewObservation)).toEqual('pad/AGRI_018/waterbody/relation/7763319');
    expect(await browser.evaluate(() => m9.map.getLayoutProperty('review-waterbody', 'visibility'))).toEqual('visible');
    expect(await browser.evaluate(() => ({ center: m9.map.getCenter().toArray(), zoom: m9.map.getZoom() }))).toEqual(view);
  });
  test('隐藏水域清除水域复核高亮并允许恢复', async ({ app, screen, browser }) => {
    await open(app, screen); await button(screen, pad).click();

    await screen.getByRole('checkbox', { name: '水域', exact: true }).uncheck();

    await expect(screen.getByRole('region', { name: '地理复核详情', exact: true })).toBeHidden();
    await expect(screen.getByRole('checkbox', { name: '水域', exact: true })).toBeFocused();
    expect(await browser.evaluate(() => m9.state.reviewObservation)).toEqual(null);
    expect(await browser.evaluate(() => m9.map.getLayoutProperty('review-water-fill', 'visibility'))).toEqual('none');
    await screen.getByRole('checkbox', { name: '水域', exact: true }).check();
    await expect(button(screen, pad)).toBeVisible();
  });
  test('搜索空态可以清除并返回完整观察列表', async ({ app, screen }) => {
    await open(app, screen); await screen.getByLabel('搜索地理复核', { exact: true }).fill('不存在的地物 xyz');
    await expect(screen.getByText('没有匹配的观察项，可清除搜索或恢复图层。', { exact: true })).toBeVisible();

    await button(screen, '清除地理复核搜索').click();

    await expect(button(screen, pad)).toBeVisible();
    await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toContainText('293 / 293 条观察');
  });
  test('来源损坏明确失败且允许关闭返回主地图', async ({ app, screen, browser }) => {
    let intercepted = 0;
    await browser.route(`**/${REVIEW_SOURCE.report.url.replace(/^\.\.\/\.\.\//, '')}`, async route => {
      intercepted++;
      const upstream = await route.fetch(); await route.fulfill({ status: 200, body: (await upstream.text()) + ' ', contentType: 'application/json' });
    });
    await app.open(); await expect(screen.getByRole('status')).toContainText('85对象统一模型');

    await button(screen, '地理复核').click();

    await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toContainText('复核数据不可用');
    await expect(button(screen, '重新加载复核数据')).toBeVisible();
    expect(await browser.evaluate(() => m9.geographicReview.snapshot().loaded)).toEqual(false);
    expect(intercepted).toBeGreaterThan(0);
    await button(screen, '关闭地理复核').click();
    await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toBeHidden();
    expect(await browser.evaluate(() => m9.state.ready)).toEqual(true);
  });
  test('从地图复核点点击进入详情', async ({ app, screen, browser }) => {
    await open(app, screen);
    const point = await browser.evaluate(() => {
      const p = m9.map.project([113.1844094, 41.0328357]); return [p.x, p.y];
    });

    await browser.mouse.move(point[0], point[1]); await browser.mouse.down(); await browser.mouse.up();

    await expect(screen.getByRole('region', { name: '地理复核详情', exact: true })).toContainText('AGRI_018 · 模型场坪');
  });
  test('分析入口退出复核并恢复对象上下文', async ({ app, screen }) => {
    await app.open(); await expect(screen.getByRole('status')).toContainText('85对象统一模型');
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '地理复核').click(); await button(screen, pad).click();

    await button(screen, '分析').click();

    await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toBeHidden();
    await expect(screen.getByRole('region', { name: '决策分析', exact: true })).toContainText('叶菜水培与冷凉种苗');
  });
  for (const width of [1440, 1100, 760]) test(`${width}宽度复核聚焦点位于卡片之外且可退出`, async ({ app, screen, browser }) => {
    await browser.setViewport({ width, height: 1000 }); await open(app, screen);

    await button(screen, pad).click();

    const visible = await browser.evaluate(() => {
      const point = m9.map.project([113.1844094, 41.0328357]);
      const card = document.getElementById('geo-panel').getBoundingClientRect();
      const toolbar = document.getElementById('toolbar').getBoundingClientRect();
      return point.x > 90 && point.x < innerWidth - 20 && point.y > toolbar.bottom &&
        !(point.x >= card.left && point.x <= card.right && point.y >= card.top && point.y <= card.bottom);
    });
    expect(visible).toEqual(true);
    await expect(button(screen, '关闭地理复核')).toBeVisible();
    await button(screen, '关闭地理复核').click();
    await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toBeHidden();
  });
});
