import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { currentFacilityAsset } from './runtime-assets.js';
import { createHash } from 'node:crypto';

const button = (screen, name) => screen.getByRole('button', { name, exact: true });
async function select(app, screen, id) {
  await app.open();
  await expect(screen.getByRole('status')).toContainText('85对象统一模型');
  await button(screen, '展开实体索引').click();
  await screen.getByRole('searchbox', { name: '搜索设施' }).fill(id);
  await button(screen, `测点 温度/流量测点 ${id}`).click();
}
async function escapeChildToParent(screen, browser, childId) {
  const parentId = childId.replace(/_SENSOR$/, '');
  const indexWasExpanded = await browser.evaluate(() => m9.index.expanded);
  if (indexWasExpanded) {
    const searchHasValue = await browser.evaluate(() => Boolean(document.getElementById('entity-search').value));
    if (searchHasValue) {
      await browser.keyboard.press('Escape');
      expect(await browser.evaluate(() => m9.state.selected)).toEqual(childId);
      expect(await browser.evaluate(() => document.getElementById('entity-search').value)).toEqual('');
    }
    await browser.keyboard.press('Escape');
    expect(await browser.evaluate(() => m9.state.selected)).toEqual(childId);
    expect(await browser.evaluate(() => m9.index.expanded)).toEqual(false);
  }
  await browser.keyboard.press('Escape');
  expect(await browser.evaluate(() => m9.state.selected)).toEqual(parentId);
  await browser.keyboard.press('Escape');
  await expect(screen.getByRole('complementary', { name: '设施详情', exact: true })).toBeHidden();
}

describe('四农业测点网页实体', () => {
  for (const n of ['014', '015', '016', '017']) {
    const id = `AGRI_${n}_SENSOR`;
    test(`${id}具有网格、同ID细节图、聚焦与退出`, async ({ app, screen, browser }) => {
      await select(app, screen, id);
      expect(await browser.evaluate(id => m9.objects[id].meshes.length, id)).toBeGreaterThan(0);
      await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
      const detail = screen.getByRole('complementary', { name: '设施详情', exact: true });
      await expect(detail).toContainText(id);
      await expect(detail).toContainText('未接管');
      await expect(detail).toContainText('m14-sensors-integrated-v1');
      await expect(screen.getByRole('img', { name: '温度/流量测点的同版Blender模型图', exact: true }))
        .toHaveAttribute('src', `../map-viewer/assets/integrated-v3/${id}.png`);
      await expect.poll(async () => browser.evaluate(() => {
        const image = document.getElementById('model-preview'); return image.complete && image.naturalWidth > 0;
      })).toEqual(true);
      const before = await browser.evaluate(() => ({ center: m9.snapshot().center, zoom: m9.snapshot().zoom }));
      for (const name of ['卫星', '数据 / DEM', '标准地图']) await button(screen, name).click();
      expect(await browser.evaluate(() => ({ center: m9.snapshot().center, zoom: m9.snapshot().zoom }))).toEqual(before);
      await button(screen, '关闭设施详情').click();
      await expect(detail).toContainText(`AGRI_${n}`);
      expect(await browser.evaluate(() => m9.state.selected)).toEqual(`AGRI_${n}`);
      await button(screen, '关闭设施详情').click();
      await expect(detail).toBeHidden();
      await button(screen, `测点 温度/流量测点 ${id}`).click();
      await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
      await button(screen, '测点 温度/流量测点 地图选择').click();
      expect(await browser.evaluate(() => m9.state.selected)).toEqual(id);
      await escapeChildToParent(screen, browser, id);
    });
  }
  for (const width of [1440, 1100, 760]) {
    test(`${width}宽度从实际三维仪表网格点击打开同ID卡片`, async ({ app, screen, browser }) => {
      await browser.setViewport({ width, height: 1000 });
      await select(app, screen, 'AGRI_016_SENSOR');
      await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
      const point = await browser.evaluate(() => m9.projectModelVertices('AGRI_016_SENSOR').find(p => {
        const element = document.elementFromPoint(p[0], p[1]);
        return element?.tagName === 'CANVAS' && m9.hitTest(p[0], p[1]) === 'AGRI_016_SENSOR';
      }));
      expect(point).toBeTruthy();
      await browser.mouse.move(point[0], point[1]);
      await browser.mouse.down();
      await browser.mouse.up();
      await expect(screen.getByRole('complementary', { name: '设施详情', exact: true })).toContainText('AGRI_016_SENSOR');
      await escapeChildToParent(screen, browser, 'AGRI_016_SENSOR');
    });
  }
  test('测点实体网格丢失时明确失败', async ({ app, screen, browser }) => {
    const asset = currentFacilityAsset(), manifest = asset.manifest, original = asset.readBytes();
    const length = original.readUInt32LE(12), doc = JSON.parse(original.subarray(20, 20 + length).toString('utf8'));
    doc.nodes[manifest.entity_nodes.AGRI_016_SENSOR].children = [];
    const encoded = Buffer.from(JSON.stringify(doc)), padded = Buffer.alloc(Math.ceil(encoded.length / 4) * 4, 0x20);
    encoded.copy(padded);
    const body = Buffer.concat([Buffer.alloc(20), padded, original.subarray(20 + length)]);
    body.write('glTF', 0); body.writeUInt32LE(2, 4); body.writeUInt32LE(body.length, 8);
    body.writeUInt32LE(padded.length, 12); body.writeUInt32LE(0x4e4f534a, 16);
    manifest.sha256 = createHash('sha256').update(body).digest('hex');
    await browser.route('**/integrated-asset.json', route => route.fulfill({ status: 200, json: manifest }));
    await browser.route(asset.pattern, route => route.fulfill({ status: 200, body }));
    await app.open();
    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('No meshes for AGRI_016_SENSOR');
  });
});
