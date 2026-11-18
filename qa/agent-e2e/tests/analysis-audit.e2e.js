import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';

const button = (screen, name) => screen.getByRole('button', { name, exact: true });
const detail = { name: '设施详情', exact: true };
const analysis = { name: '决策分析', exact: true };
const audit = { name: '审计与系统状态', exact: true };

async function ready(app, screen) {
  await app.open();
  await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
}

describe('M10 对象级分析与 M11 来源审计', () => {
  test('打开和关闭分析面板有明确退出与焦点恢复', async ({ app, screen }) => {
    await ready(app, screen);

    await button(screen, '分析').click();
    await expect(screen.getByRole('region', analysis)).toBeVisible();
    await expect(screen.getByRole('region', analysis)).toContainText('请选择一个设施');

    await button(screen, '关闭决策分析').click();

    await expect(screen.getByRole('region', analysis)).toBeHidden();
    await expect(button(screen, '分析')).toBeFocused();
  });

  test('AGRI_018 绑定同对象结果并可切换源退出工况', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await expect(screen.getByRole('complementary', detail)).toBeVisible();

    await button(screen, '分析').click();
    const panel = screen.getByRole('region', analysis);
    await expect(panel).toContainText('叶菜水培与冷凉种苗 · AGRI_018');
    await expect(panel).toContainText('正常工况');
    await expect(panel).toContainText('h14');

    await button(screen, '展开分析').click();
    await expect(panel).toContainText('能量账');
    await expect(panel).toContainText('近端直供 + 余热入库');

    await screen.getByRole('combobox', { name: '选择分析工况' }).selectOption({ value: 'source-outage' });
    await expect(panel).toContainText('源退出');
    await expect(panel).toContainText('PTES 放热补峰');
    await expect.poll(async () => browser.evaluate(() => m9.state.scenario)).toEqual('source-outage');

    await screen.getByRole('combobox', { name: '选择分析时段' }).selectOption({ value: '7' });
    await expect(panel).toContainText('h7');
    await expect.poll(async () => browser.evaluate(() => m9.state.analysisHour)).toEqual(7);

    await browser.keyboard.press('Escape');
    await expect(panel).toBeVisible();
    await expect(screen.getByText('展开分析', { exact: true })).toBeVisible();
    await browser.keyboard.press('Escape');
    await expect(panel).toBeHidden();
    await expect(button(screen, '分析')).toBeFocused();
  });

  test('分析结果按对象、工况和时段同步，派生耗尽保持边界说明', async ({ app, screen }) => {
    await ready(app, screen);
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '分析').click();
    const panel = screen.getByRole('region', analysis);
    await screen.getByRole('combobox', { name: '选择分析工况' }).selectOption({ value: 'storage-depleted' });
    await expect(panel).toContainText('储能耗尽（派生）');
    await expect(panel).toContainText('h5');
    await expect(panel).toContainText('不是新的求解结果');
  });

  test('HUB_011 没有绑定结果时保持对象级空态', async ({ app, screen }) => {
    await ready(app, screen);
    await button(screen, '热泵 CO₂跨临界热泵枢纽 地图选择').click();
    await button(screen, '分析').click();

    const panel = screen.getByRole('region', analysis);
    await expect(panel).toContainText('CO₂跨临界热泵枢纽 · HUB_011');
    await expect(panel).toContainText('暂无绑定');
    await expect(panel).not.toContainText('近端直供 + 余热入库');
  });

  test('切换到未绑定对象时收起旧对象的展开分析状态', async ({ app, screen }) => {
    await ready(app, screen);
    await button(screen, 'C1 叶菜水培与冷凉种苗 地图选择').click();
    await button(screen, '分析').click();
    await button(screen, '展开分析').click();
    await expect(screen.getByText('能量账', { exact: true })).toBeVisible();

    await button(screen, '展开实体索引').click();
    await screen.getByRole('searchbox', { name: '搜索设施' }).fill('HUB_011');
    await button(screen, '热泵 CO₂跨临界热泵枢纽 HUB_011').click();

    const panel = screen.getByRole('region', analysis);
    await expect(panel).toContainText('暂无绑定');
    await expect(button(screen, '展开分析')).toHaveAttribute('aria-expanded', 'false');
  });

  test('审计页回读版本、模型、来源与限制，并由 Escape 关闭', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, '审计').click();

    const panel = screen.getByRole('dialog', audit);
    await expect(panel).toBeVisible();
    await expect(panel).toContainText('codex/energy-map-v2');
    await expect(panel).toContainText('facilities.glb');
    await expect(panel).toContainText('合成教学数据');
    await expect(panel).toContainText('OpenStreetMap');
    await expect(panel).toContainText('逐项来源清单');
    await expect(panel).toContainText('网页运行时');
    await expect(panel).toContainText('时间绑定');

    await screen.getByRole('button', { name: '重新读取来源', exact: true }).click();
    await expect(panel).toContainText('codex/energy-map-v2');

    await browser.keyboard.press('Escape');
    await expect(panel).toBeHidden();
    await expect(button(screen, '审计')).toBeFocused();
  });

  test('审计清单加载失败时显示明确失败态', async ({ app, screen, browser }) => {
    await browser.route('**/audit-manifest.json', route => route.fulfill({ status: 503, body: 'audit unavailable' }));
    await ready(app, screen);
    await button(screen, '审计').click();

    const panel = screen.getByRole('dialog', audit);
    await expect(panel).toContainText('审计清单加载失败');
    await expect(panel).toContainText('来源待核');

    await browser.keyboard.press('Escape');
    await expect(panel).toBeHidden();
  });
});
