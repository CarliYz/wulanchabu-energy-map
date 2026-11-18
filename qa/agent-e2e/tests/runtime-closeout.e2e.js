import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { readFileSync } from 'node:fs';

const button = (screen, name) => screen.getByRole('button', { name, exact: true });
async function ready(app, screen) {
  await app.open();
  await expect(screen.getByRole('status')).toContainText('85对象统一模型');
}
async function choose(screen, id, name) {
  await button(screen, '展开实体索引').click();
  await screen.getByRole('searchbox', { name: '搜索设施' }).fill(id);
  await button(screen, name).click();
}

describe('M16 网页交互收尾', () => {
  test('未选对象时分析不提供未绑定工况与时段', async ({ app, screen }) => {
    await ready(app, screen);

    await button(screen, '分析').click();

    await expect(screen.getByRole('combobox', { name: '选择分析工况' })).toBeDisabled();
    await expect(screen.getByRole('combobox', { name: '选择分析时段' })).toBeDisabled();
    await expect(button(screen, '展开分析')).toBeDisabled();
    await expect(screen.getByRole('region', { name: '决策分析', exact: true })).not.toContainText('synthetic_teaching_not_local');
  });

  test('切到未绑定设施清除上一对象的教学时段', async ({ app, screen }) => {
    await ready(app, screen);
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '分析').click();
    await screen.getByRole('combobox', { name: '选择分析时段' }).selectOption({ value: '7' });
    await button(screen, '展开分析').click();
    await choose(screen, 'AGRI_014', 'A1 种薯组培与原原种温室 AGRI_014');

    const panel = screen.getByRole('region', { name: '决策分析', exact: true });
    await expect(panel).toContainText('AGRI_014');
    await expect(panel).not.toContainText('synthetic_teaching_not_local');
    await expect(screen.getByRole('combobox', { name: '选择分析工况' })).toBeDisabled();
    await expect(screen.getByRole('combobox', { name: '选择分析时段' })).toBeDisabled();
    await expect(button(screen, '展开分析')).toBeDisabled();
    expect(await screen.getByRole('heading', { name: '能量账', exact: true }).isVisible()).toEqual(false);
  });

  test('审计浮层反向Tab留在最后一个可操作按钮', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, '审计').click();

    await browser.keyboard.press('Shift+Tab');

    await expect(button(screen, '导出审计 JSON')).toBeFocused();
  });

  test('审计浮层正向Tab循环后Escape还原入口焦点', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, '审计').click();
    await button(screen, '导出审计 JSON').press('Tab');
    await expect(button(screen, '关闭审计页')).toBeFocused();

    await browser.keyboard.press('Escape');

    await expect(button(screen, '审计')).toBeFocused();
    await expect(screen.getByRole('dialog', { name: '审计与系统状态', exact: true })).toBeHidden();
    expect(await browser.evaluate(() => document.querySelector('header').inert)).toEqual(false);
  });

  test('审计Escape优先关闭当前浮层并保留背景菜单', async ({ app, screen }) => {
    await ready(app, screen);
    await button(screen, '图层').click();
    await button(screen, '审计').press('Enter');
    await expect(screen.getByRole('dialog', { name: '审计与系统状态', exact: true })).toBeVisible();

    await button(screen, '关闭审计页').press('Escape');

    await expect(screen.getByRole('dialog', { name: '审计与系统状态', exact: true })).toBeHidden();
    await expect(screen.getByRole('checkbox', { name: '设施模型与标签', exact: true })).toBeVisible();
    await expect(button(screen, '审计')).toBeFocused();
  });

  test('审计来源加载失败时禁止导出且可以退出', async ({ app, screen, browser }) => {
    await browser.route('**/audit-manifest.json', route => route.fulfill({ status: 503, body: 'source unavailable' }));
    await ready(app, screen);
    await button(screen, '审计').click();
    await expect(screen.getByRole('dialog', { name: '审计与系统状态', exact: true })).toContainText('审计清单加载失败');

    await expect(button(screen, '导出审计 JSON')).toBeDisabled();
    await button(screen, '关闭审计页').click();

    await expect(button(screen, '审计')).toBeFocused();
  });

  test('未绑定对象导出的审计不携带教学分析时段', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '分析').click();
    await choose(screen, 'HUB_011', '热泵 CO₂跨临界热泵枢纽 HUB_011');
    await button(screen, '审计').click();

    const download = await browser.waitForDownload(() => button(screen, '导出审计 JSON').click());

    const payload = JSON.parse(readFileSync(download.absolutePath, 'utf8'));
    expect(payload.selected).toEqual('HUB_011');
    expect(payload.analysis_time).toEqual(null);
  });

  test('来源失败后重新读取可恢复真实审计下载', async ({ app, screen, browser }) => {
    await browser.route('**/audit-manifest.json', route => route.fulfill({ status: 503, body: 'source unavailable' }));
    await ready(app, screen);
    await button(screen, '审计').click();
    await expect(screen.getByRole('dialog', { name: '审计与系统状态', exact: true })).toContainText('审计清单加载失败');
    await browser.unroute('**/audit-manifest.json');

    await button(screen, '重新读取来源').click();
    await expect(button(screen, '导出审计 JSON')).toBeEnabled();
    const download = await browser.waitForDownload(() => button(screen, '导出审计 JSON').click());

    const payload = JSON.parse(readFileSync(download.absolutePath, 'utf8'));
    expect(payload.audit.web_model.sha256).toEqual('aa00fa4c3502197f77851c3a2eb6617875462862c0bbd7351ceeaf4c0cf1869f');
    expect(payload.analysis_time).toEqual(null);
  });

  test('C1审计下载保留所选教学时段和数据性质', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '分析').click();
    await screen.getByRole('combobox', { name: '选择分析时段' }).selectOption({ value: '7' });
    await button(screen, '审计').click();

    const download = await browser.waitForDownload(() => button(screen, '导出审计 JSON').click());

    const payload = JSON.parse(readFileSync(download.absolutePath, 'utf8'));
    expect(payload.selected).toEqual('AGRI_018');
    expect(payload.analysis_status).toEqual('available');
    expect(payload.analysis_time).toEqual({ hour_index: 7, timestamp: null, basis: 'synthetic_teaching_not_local' });
  });

  test('详情分析与审计关键状态无严重无障碍错误', async ({ app, screen, browser }) => {
    await browser.addInitScript(readFileSync(new URL('../../../node_modules/axe-core/axe.min.js', import.meta.url), 'utf8'));
    await ready(app, screen);
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '分析').click();
    await button(screen, '展开分析').click();
    const violations = [];
    for (const [width, height] of [[1440, 900], [1100, 800], [760, 600]]) {
      await browser.setViewport({ width, height });
      violations.push(...await browser.evaluate(async () => (await axe.run()).violations.filter(v => ['critical', 'serious'].includes(v.impact)).map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))));
    }
    await button(screen, '审计').click();
    violations.push(...await browser.evaluate(async () => (await axe.run()).violations.filter(v => ['critical', 'serious'].includes(v.impact)).map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))));

    expect(violations).toEqual([]);
  });

  for (const [width, height] of [[1440, 900], [1100, 800], [760, 600]]) {
    test(`${width}×${height}分析与详情保留独立操作区域`, async ({ app, screen, browser }) => {
      await browser.setViewport({ width, height });
      await ready(app, screen);
      await choose(screen, 'AGRI_018', 'C1 叶菜水培与冷凉种苗 AGRI_018');

      await button(screen, '分析').click();

      const layout = await browser.evaluate(() => {
        const rect = id => document.getElementById(id).getBoundingClientRect();
        const a = rect('analysis-panel'), d = rect('detail'), toolbar = rect('toolbar');
        const footer = document.querySelector('footer').getBoundingClientRect();
        const overlaps = d.width > 0 && d.height > 0 && a.left < d.right && a.right > d.left && a.top < d.bottom && a.bottom > d.top;
        return { overlaps, inWorkspace: a.top >= toolbar.bottom && a.bottom <= footer.top,
          withinViewport: a.left >= 0 && a.right <= innerWidth,
          safe: m9.safeArea().bottom > m9.safeArea().top };
      });
      expect(layout).toEqual({ overlaps: false, inWorkspace: true, withinViewport: true, safe: true });
      await expect(button(screen, '关闭决策分析')).toBeVisible();
      await app.screenshot(`m16-analysis-${width}`);
    });

    test(`${width}×${height}地理复核定位后可分层退出`, async ({ app, screen, browser }) => {
      await browser.setViewport({ width, height });
      await ready(app, screen);
      await button(screen, '地理复核').click();
      await button(screen, '定位复核 pad/AGRI_018/waterbody/relation/7763319').click();
      const visible = await browser.evaluate(() => {
        const point = m9.map.project([113.1844094, 41.0328357]);
        const card = document.getElementById('geo-panel').getBoundingClientRect();
        const toolbar = document.getElementById('toolbar').getBoundingClientRect();
        return point.x > 90 && point.x < innerWidth - 20 && point.y > toolbar.bottom &&
          !(point.x >= card.left && point.x <= card.right && point.y >= card.top && point.y <= card.bottom);
      });

      await browser.keyboard.press('Escape');
      await browser.keyboard.press('Escape');

      expect(visible).toEqual(true);
      await expect(button(screen, '地理复核')).toBeFocused();
      await expect(screen.getByRole('complementary', { name: '地理复核', exact: true })).toBeHidden();
    });
  }
});
