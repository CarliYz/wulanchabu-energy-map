import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { readFileSync } from 'node:fs';
import { currentFacilityAsset } from './runtime-assets.js';
const registry = JSON.parse(readFileSync(new URL('../../../web/map-prototype/facility-registry.json', import.meta.url)));
const detail = {name:'设施详情',exact:true};

describe('完整父设施地图交互', () => {
  for (const item of registry.objects) {
    test(`${item.object_id}从索引聚焦并打开对应模型卡`, async ({app,screen,browser}) => {
      await app.open();
      await screen.getByRole('status').waitFor({state:'visible'});
      await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
      await screen.getByRole('button',{name:'展开实体索引',exact:true}).click();
      await screen.getByRole('searchbox',{name:'搜索设施'}).fill(item.object_id);

      await screen.getByRole('button',{name:`${item.short_name} ${item.name} ${item.object_id}`,exact:true}).click();
      await screen.getByRole('complementary',detail).waitFor();

      await expect(screen.getByRole('complementary',detail)).toContainText(item.object_id);
      await expect(screen.getByRole('img',{name:`${item.name}的同版Blender模型图`,exact:true})).toBeVisible();
      await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
      await expect(screen.getByRole('complementary',detail)).toContainText('未知；无绑定对象结果');
    });
  }
  test('三视图切换保持同设施与视角',async ({app,screen,browser}) => {
    await app.open();
    await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true}).click();
    await screen.getByRole('complementary',detail).waitFor();
    await expect.poll(async () => browser.evaluate(() => m9.state.cameraPending)).toEqual(false);
    const before=await browser.evaluate(() => m9.snapshot());

    await screen.getByRole('button',{name:'卫星',exact:true}).click();
    await screen.getByRole('button',{name:'数据 / DEM',exact:true}).click();
    await screen.getByRole('button',{name:'返回底图',exact:true}).click();

    await expect(screen.getByRole('button',{name:'卫星',exact:true})).toHaveAttribute('aria-pressed','true');
    const after=await browser.evaluate(() => m9.snapshot());
    expect(after.center).toEqual(before.center);expect(after.zoom).toEqual(before.zoom);
    await expect(screen.getByRole('complementary',detail)).toContainText('AGRI_018');
  });
  test('搜索无结果可以用Escape清空并收回索引',async ({app,screen,browser}) => {
    await app.open();
    await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
    await screen.getByRole('button',{name:'展开实体索引',exact:true}).click();
    await screen.getByRole('searchbox',{name:'搜索设施'}).fill('不存在');
    await screen.getByText('没有匹配的设施',{exact:true}).waitFor();

    await browser.keyboard.press('Escape');
    await browser.keyboard.press('Escape');

    await expect(screen.getByRole('button',{name:'展开实体索引',exact:true})).toBeFocused();
    await expect(screen.getByRole('region',{name:'实体索引内容',exact:true})).toBeHidden();
  });
  test('关闭设施卡恢复地图入口焦点',async ({app,screen}) => {
    await app.open();
    await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true}).click();
    await screen.getByRole('complementary',detail).waitFor();

    await screen.getByRole('button',{name:'关闭设施详情',exact:true}).click();

    await expect(screen.getByRole('complementary',detail)).toBeHidden();
    await expect(screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true})).toBeFocused();
  });
  test('隐藏模型清除设施选择并关闭卡片',async ({app,screen}) => {
    await app.open();
    await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true}).click();
    await screen.getByRole('complementary',detail).waitFor();
    await screen.getByRole('button',{name:'图层',exact:true}).click();

    await screen.getByRole('checkbox',{name:'设施模型与标签',exact:true}).uncheck();

    await expect(screen.getByRole('complementary',detail)).toBeHidden();
    await expect(screen.getByRole('status')).toContainText('选择已清除');
  });
  test('损坏设施资产明确加载失败',async ({app,screen,browser}) => {
    await browser.route(currentFacilityAsset().pattern, route => route.fulfill({status:200,body:'broken GLB'}));

    await app.open();

    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('GLB identity changed');
  });
  test('小手模式不会通过地图标签打开详情',async ({app,screen}) => {
    await app.open();
    await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
    await screen.getByRole('button',{name:'小手平移',exact:true}).click();

    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 地图选择',exact:true}).click();

    await expect(screen.getByRole('complementary',detail)).toBeHidden();
  });
  test('折叠分组后关闭详情会把焦点交还分组',async ({app,screen}) => {
    await app.open();
    await expect(screen.getByRole('status')).toContainText('已载入12个主要设施');
    await screen.getByRole('button',{name:'展开实体索引',exact:true}).click();
    await screen.getByRole('searchbox',{name:'搜索设施'}).fill('AGRI_018');
    await screen.getByRole('button',{name:'C1 叶菜水培与冷凉种苗 AGRI_018',exact:true}).click();
    await screen.getByText('C 区 · 水培 / 秋烘',{exact:true}).click();

    await screen.getByRole('button',{name:'关闭设施详情',exact:true}).click();

    await expect(screen.getByText('C 区 · 水培 / 秋烘',{exact:true})).toBeFocused();
  });
});
