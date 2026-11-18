import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { readFileSync } from 'node:fs';
const graph = JSON.parse(readFileSync(new URL('../../../web/map-prototype/c1-runtime.json', import.meta.url)));
const detail = { name: '设施详情', exact: true };
async function ready(screen) {
  await expect(screen.getByRole('status')).toContainText('C1 11个子设备', { timeout: 30000 });
}

describe('C1子设备与回路', () => {
  for (const item of graph.objects) {
    test(`${item.object_id}从子树打开同版设备卡并可返回C1`, async ({app,screen,browser}) => {
      await app.open();
      await ready(screen);
      await screen.getByRole('button',{name:'展开实体索引',exact:true}).click();
      await screen.getByRole('searchbox',{name:'搜索设施'}).fill(item.object_id);
      await screen.getByRole('button',{name:`${item.short_name} ${item.name} ${item.object_id}`,exact:true}).click();
      await expect.poll(async()=>browser.evaluate(()=>m9.state.cameraPending)).toEqual(false);
      await screen.getByRole('img',{name:`${item.name}的同版Blender模型图`,exact:true}).waitFor();

      await screen.getByRole('button',{name:'返回 C1 设施',exact:true}).click();

      await expect(screen.getByRole('complementary',detail)).toContainText('叶菜水培与冷凉种苗');
      await expect(screen.getByRole('button',{name:'返回 C1 设施',exact:true})).toBeHidden();
    });
  }
  test('热水筛选保留8条同回路连接', async ({app,screen,browser}) => {
    await app.open(); await ready(screen);
    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true}).click();
    await screen.getByRole('button',{name:'设备与回路',exact:true}).click();

    await screen.getByRole('button',{name:'热水回路',exact:true}).click();

    await expect(screen.getByText('8 条拟定内部连接 · 供回方向以端口定义为准',{exact:true})).toBeVisible();
    const circuits=await browser.evaluate(()=>[...document.querySelectorAll('[data-edge-row]')].map(row=>m9.c1.connections.find(e=>e.connection_id===row.dataset.edgeRow).circuit_id));
    expect(circuits).toEqual(Array(8).fill('C1_HEAT'));
  });
  test('Escape先清除管段高亮并保留关系面板', async ({app,screen,browser}) => {
    await app.open(); await ready(screen);
    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true}).click();
    await screen.getByRole('button',{name:'设备与回路',exact:true}).click();
    await screen.getByRole('button',{name:'EDGE_014 · 热水回路 · 供流',exact:true}).click();

    await browser.keyboard.press('Escape');

    await expect(screen.getByRole('region',{name:'设施候选连接',exact:true})).toBeVisible();
    await expect(screen.getByRole('button',{name:'EDGE_014 · 热水回路 · 供流',exact:true})).toHaveAttribute('aria-pressed','false');
    expect(await browser.evaluate(()=>m9.state.connection)).toEqual(null);
  });
  test('子设备近景完整处于浮层外的可见区域', async ({app,screen,browser}) => {
    await app.open(); await ready(screen);
    await screen.getByRole('button',{name:'展开实体索引',exact:true}).click();
    await screen.getByRole('searchbox',{name:'搜索设施'}).fill('AGRI_018_PUMP');

    await screen.getByRole('button',{name:'热水泵 二次热水循环泵 AGRI_018_PUMP',exact:true}).click();
    await expect.poll(async()=>browser.evaluate(()=>m9.state.cameraPending)).toEqual(false);

    const framing=await browser.evaluate(()=>{const a=m9.safeArea();return m9.projectModelVertices('AGRI_018_PUMP').every(([x,y])=>x>=a.left-3&&x<=a.right+3&&y>=a.top-3&&y<=a.bottom+3);});
    expect(framing).toEqual(true);
    await expect(screen.getByRole('img',{name:'二次热水循环泵的同版Blender模型图',exact:true})).toBeVisible();
  });
  test('关闭再打开回路面板不会保留过期的管段选中态', async ({app,screen,browser}) => {
    await app.open(); await ready(screen);
    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true}).click();
    await screen.getByRole('button',{name:'设备与回路',exact:true}).click();
    await screen.getByRole('button',{name:'EDGE_014 · 热水回路 · 供流',exact:true}).click();
    await screen.getByRole('button',{name:'设备与回路',exact:true}).click();

    await screen.getByRole('button',{name:'设备与回路',exact:true}).click();

    await expect(screen.getByRole('button',{name:'EDGE_014 · 热水回路 · 供流',exact:true})).toHaveAttribute('aria-pressed','false');
    expect(await browser.evaluate(()=>m9.state.connection)).toEqual(null);
  });
  test('异版C1关系资产明确加载失败', async ({app,screen,browser}) => {
    await browser.route('**/c1-runtime.json',route=>route.fulfill({status:200,json:{...graph,asset_sha256:'invalid'}}));

    await app.open();

    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('C1 GLB identity mismatch');
  });
});
