import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { currentFacilityAsset } from './runtime-assets.js';

const detail = { name: '设施详情', exact: true };
const button = (screen, name) => screen.getByRole('button', { name, exact: true });

async function ready(app, screen) {
  await app.open();
  await expect(screen.getByRole('status')).toContainText('M10 30个系统设备/角色');
}

describe('M10 系统设备补模与候选关系闭环', () => {
  test('压缩机详情区分站内CO2和独立电输入端口', async ({ app, screen }) => {
    await ready(app, screen);
    await button(screen, '展开实体索引').click();
    await screen.getByRole('searchbox', { name: '搜索设施' }).fill('HUB_011_COMP');
    await button(screen, '压缩机 HUB 压缩机角色端口映射 HUB_011_COMP').click();
    const card = screen.getByRole('complementary', detail);
    await expect(card).toContainText('站内 CO₂ · 入 / 出（候选端口）');
    await expect(card).toContainText('电力 · 入（候选端口）');
  });

  test('候选连接引用缺失端口时明确失败', async ({ app, screen, browser }) => {
    await browser.route('**/m10-system-runtime.json', async route => {
      const response = await route.fetch(); const json = await response.json();
      json.connections[0].from_port_id = 'NONEXISTENT_PORT';
      await route.fulfill({ status: 200, json });
    });
    await app.open();
    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('M10 connection port missing');
  });

  test('PTES 放热回水管段可高亮并逐层退出', async ({ app, screen, browser }) => {
    await app.open();
    await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
    await button(screen, 'PTES PTES池式储热 地图选择').click();
    await button(screen, '查看候选关系').click();

    await button(screen, '高亮管段 M12_B349_PTES_DISCHARGE_RETURN_END').click();

    expect(await browser.evaluate(() => Object.values(m9.objects).some(o => o.meshes.some(m => m.userData.connectionId === 'M12_B349_PTES_DISCHARGE_RETURN_END' && m.material.emissive.getHex() === 0x885500)))).toEqual(true);
    await expect(screen.getByText('STORE_012_DIS_VRETURN:USER:out:flow → STORE_012:USER:in:discharge_return', { exact: true })).toBeVisible();
    await browser.keyboard.press('Escape');
    expect(await browser.evaluate(() => m9.state.connection)).toEqual(null);
    expect(await browser.evaluate(() => Object.values(m9.objects).some(o => o.meshes.some(m => m.userData.connectionId === 'M12_B349_PTES_DISCHARGE_RETURN_END' && m.material.emissive.getHex() === 0x885500)))).toEqual(false);
    await expect(screen.getByRole('region', { name: '设施候选连接', exact: true })).toBeVisible();
    await browser.keyboard.press('Escape');
    await expect(screen.getByRole('region', { name: '设施候选连接', exact: true })).toBeHidden();
    await button(screen, '关闭设施详情').click();
    await expect(screen.getByRole('complementary', detail)).toBeHidden();
  });

  test('C2 系统从索引打开卡片并显示三换热器与提温', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, '展开实体索引').click();
    await screen.getByRole('searchbox', { name: '搜索设施' }).fill('M10_C2_SYSTEM');
    await button(screen, 'C2 系统 C2 三换热器 + 提温 + 电输入系统 M10_C2_SYSTEM').click();

    const card = screen.getByRole('complementary', detail);
    await expect(card).toContainText('M10_C2_SYSTEM');
    await expect(card).toContainText('三台换热器、提温模块、独立电输入');
    await expect(screen.getByRole('img', { name: 'C2 三换热器 + 提温 + 电输入系统的同版Blender模型图', exact: true })).toBeVisible();
    await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
  });

  test('C2 关系面板可进入末端并用 Escape 退出', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, 'C2 秋季低温烘干中心 地图选择').click();
    await button(screen, '查看候选关系').click();
    await expect(screen.getByText('M10 候选设备与回路', { exact: true })).toBeVisible();
    await screen.getByRole('button', { name: '→ 提温', exact: true }).first().click();
    await expect(screen.getByRole('complementary', detail)).toContainText('DRY_019_BOOSTER');
    await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
    await browser.keyboard.press('Escape');
    await expect(screen.getByRole('complementary', detail)).toContainText('DRY_019');
    await expect(screen.getByRole('region', { name: '设施候选连接', exact: true })).toBeVisible();
    await browser.keyboard.press('Escape');
    await expect(screen.getByRole('region', { name: '设施候选连接', exact: true })).toBeHidden();
  });

  test('PTES 系统显示充放热设备并可返回父设施', async ({ app, screen, browser }) => {
    await ready(app, screen);
    await button(screen, '展开实体索引').click();
    await screen.getByRole('searchbox', { name: '搜索设施' }).fill('M10_PTES_SYSTEM');
    await button(screen, 'PTES 系统 PTES 充放热阀泵与控制系统 M10_PTES_SYSTEM').click();
    await expect(screen.getByRole('complementary', detail)).toContainText('M10_PTES_SYSTEM');
    await expect(screen.getByRole('complementary', detail)).toContainText('PTES 充热和放热分列的阀、泵、止回与控制示意');
    await expect(button(screen, '返回 PTES 设施')).toBeVisible();
    await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
  });

  test('条件电锅炉保持候选预留并明确位置待核', async ({ app, screen }) => {
    await ready(app, screen);
    await button(screen, '展开实体索引').click();
    await screen.getByRole('searchbox', { name: '搜索设施' }).fill('BOILER_CAND_001');
    await button(screen, '电锅炉候选 条件绿电电锅炉候选（异常/尖峰） BOILER_CAND_001').click();
    const card = screen.getByRole('complementary', detail);
    await expect(card).toContainText('位置待核');
    await expect(card).toContainText('默认禁用');
    await expect(card).toContainText('不提供数据中心备用电');
  });

  test('统一 GLB 身份损坏时明确加载失败', async ({ app, screen, browser }) => {
    await browser.route(currentFacilityAsset().pattern, route => route.fulfill({ status: 200, body: 'broken M10 GLB' }));
    await app.open();
    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('GLB identity changed');
  });
});
