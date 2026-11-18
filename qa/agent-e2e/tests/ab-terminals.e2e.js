import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';

const detail = { name: '设施详情', exact: true };
const button = (screen, name) => screen.getByRole('button', { name, exact: true });

async function ready(app, screen) {
  await app.open();
  await expect(screen.getByRole('status')).toContainText('A/B 32个设备 / 60端口 / 60连接');
}

describe('A/B 末端候选补模与关系闭环', () => {
  test('A区父设施打开末端设备并可返回上级', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, 'A1 种薯组培与原原种温室 地图选择').click();
    await button(screen, '设备与回路').click();
    await expect(screen.getByRole('region', { name: '设施候选连接', exact: true })).toContainText('A区 末端设备 · 8');

    await button(screen, '板换 隔离板换：仅传热不混水').click();
    await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
    await expect(screen.getByRole('complementary', detail)).toContainText('AGRI_014_HX');
    await expect(screen.getByRole('img', { name: '隔离板换：仅传热不混水的同版Blender模型图', exact: true })).toBeVisible();

    await button(screen, '返回 A 区设施').click();
    await expect(screen.getByRole('complementary', detail)).toContainText('AGRI_014');
    await expect(button(screen, '返回 A 区设施')).toBeHidden();
  });

  test('A区菌房 AHU 保持正确归属和动态端口', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, 'A2 工厂化食用菌 地图选择').click();
    await button(screen, '设备与回路').click();
    await button(screen, 'AHU1 食用菌菌房 AHU1').click();
    await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
    const card = screen.getByRole('complementary', detail);
    await expect(card).toContainText('AGRI_015_AHU1');
    await expect(card).toContainText('A区食用菌 / 菌房空气处理');
    await expect(card).toContainText('热水回路');
    await expect(card).toContainText('二次侧');
  });

  test('A区管段高亮可由 Escape 退出并保留关系面板', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, 'A1 种薯组培与原原种温室 地图选择').click();
    await button(screen, '设备与回路').click();
    await button(screen, 'AGRI_014_EDGE_11 · 热水回路 · 供流').click();

    await browser.keyboard.press('Escape');

    await expect(screen.getByRole('region', { name: '设施候选连接', exact: true })).toBeVisible();
    await expect(button(screen, 'AGRI_014_EDGE_11 · 热水回路 · 供流')).toHaveAttribute('aria-pressed', 'false');
    expect(await browser.evaluate(() => m9.state.connection)).toEqual(null);
  });
});
