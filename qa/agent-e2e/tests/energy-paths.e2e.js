import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
const button = (screen, name) => screen.getByRole('button',{name,exact:true});
async function c1(app,screen) {
  await app.open(); await expect(screen.getByRole('status')).toContainText('C1 11个子设备');
  await button(screen,'C1 叶菜水培与冷凉种苗 地图选择').click();
  await button(screen,'设备与回路').click();
}
describe('源端与分区能源路径', () => {
  test('经历关联线路后关闭设施卡仍回到最初地图标签', async ({app,screen}) => {
    await c1(app,screen); await button(screen,'查看线路 AGRI_018_SUPPLY').click();
    await button(screen,'返回上个对象').click();

    await button(screen,'关闭设施详情').click();

    await expect(button(screen,'C1 叶菜水培与冷凉种苗 地图选择')).toBeFocused();
  });
  test('B区仅显示本区温室用热关系', async ({app,screen}) => {
    await app.open(); await expect(screen.getByRole('status')).toContainText('C1 11个子设备');
    await button(screen,'B1 冬季番茄连栋温室 地图选择').click();

    await button(screen,'设备与回路').click();

    const region=screen.getByRole('region',{name:'设施候选连接',exact:true});
    await expect(region).toContainText('二期 · B 区用户分支');
    await expect(region).not.toContainText('C1');
  });
  test('C1供水可沿干线追到热泵并逐级返回原入口', async ({app,screen,browser}) => {
    await c1(app,screen);
    await button(screen,'查看线路 AGRI_018_SUPPLY').click();
    await button(screen,'查看线路 P2_V2_SUPPLY').click();
    await button(screen,'定位设备 HUB_011').click();
    await button(screen,'返回上个实体').click();
    await button(screen,'返回上个对象').click();

    await button(screen,'返回上个对象').click();

    await expect(screen.getByRole('complementary',{name:'设施详情',exact:true})).toContainText('叶菜水培与冷凉种苗');
    await expect(button(screen,'查看线路 AGRI_018_SUPPLY')).toBeFocused();
    expect(await browser.evaluate(()=>m9.state.route)).toEqual(null);
  });
  test('C1能源解释纵切保留源侧热泵与PTES并列关系', async ({app,screen}) => {
    await c1(app,screen);

    const region=screen.getByRole('region',{name:'设施候选连接',exact:true});
    await expect(region).toContainText('能源解释纵切');
    await expect(region).toContainText('PTES · 并列调节支路');
    await expect(region).toContainText('站内 CO₂ · 闭合循环');
    await button(screen,'能源路径定位 HUB_011 · 用户侧热水 · 反查上游').click();
    await button(screen,'查看候选关系').click();

    await expect(screen.getByRole('region',{name:'设施候选连接',exact:true})).toContainText('DC1 源侧水');
    await expect(button(screen,'定位设备 STORE_012')).toBeVisible();
  });
  test('返回C1同时恢复回路筛选与相机高程', async ({app,screen,browser}) => {
    await c1(app,screen); await button(screen,'营养液回路').click();
    await expect.poll(async()=>browser.evaluate(()=>m9.state.cameraPending)).toEqual(false);
    const view=await browser.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom(),elevation:m9.map.getCenterElevation()}));
    await button(screen,'查看线路 AGRI_018_RETURN').click();

    await browser.keyboard.press('Escape');

    await expect(button(screen,'营养液回路')).toHaveAttribute('aria-pressed','true');
    expect(await browser.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom(),elevation:m9.map.getCenterElevation()}))).toEqual(view);
    await expect(button(screen,'查看线路 AGRI_018_RETURN')).toBeFocused();
  });
  test('三视图保持选中线路与视角', async ({app,screen,browser}) => {
    await c1(app,screen); await button(screen,'查看线路 P2_V2_SUPPLY').click();
    const view=await browser.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom()}));

    await button(screen,'卫星').click();

    await expect(screen.getByRole('complementary',{name:'线路详情',exact:true})).toContainText('P2_V2_SUPPLY');
    expect(await browser.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom()}))).toEqual(view);
    expect(await browser.evaluate(()=>m9.map.getFilter('route-selected'))).toEqual(['==',['get','route_id'],'P2_V2_SUPPLY']);
  });
  test('隐藏线路清除路线详情和高亮', async ({app,screen,browser}) => {
    await c1(app,screen); await button(screen,'查看线路 P2_V2_SUPPLY').click();
    await button(screen,'图层').click();

    await screen.getByLabel('候选供回线',{exact:true}).uncheck();

    await expect(screen.getByRole('complementary',{name:'线路详情',exact:true})).toBeHidden();
    expect(await browser.evaluate(()=>m9.state.route)).toEqual(null);
    expect(await browser.evaluate(()=>m9.map.getLayoutProperty('route-selected','visibility'))).toEqual('none');
  });
  test('进入小手模式退出线路卡和线路高亮', async ({app,screen,browser}) => {
    await c1(app,screen); await button(screen,'查看线路 AGRI_018_SUPPLY').click();
    await button(screen,'小手平移').click();

    await expect(screen.getByRole('complementary',{name:'线路详情',exact:true})).toBeHidden();
    expect(await browser.evaluate(()=>m9.state.route)).toEqual(null);
    expect(await browser.evaluate(()=>m9.map.getFilter('route-selected'))).toEqual(['==',['get','route_id'],'']);
    await expect(button(screen,'小手平移')).toHaveAttribute('aria-pressed','true');
  });
  test('多级线路进入小手模式回到设施并清空路线状态', async ({app,screen,browser}) => {
    await c1(app,screen); await button(screen,'查看线路 AGRI_018_SUPPLY').click();
    await button(screen,'查看线路 P2_V2_SUPPLY').click();
    await button(screen,'小手平移').click();

    await expect(screen.getByRole('complementary',{name:'线路详情',exact:true})).toBeHidden();
    await expect(screen.getByRole('complementary',{name:'设施详情',exact:true})).toContainText('叶菜水培与冷凉种苗');
    expect(await browser.evaluate(()=>m9.state.route)).toEqual(null);
    expect(await browser.evaluate(()=>m9.map.getFilter('route-selected'))).toEqual(['==',['get','route_id'],'']);
    await expect(button(screen,'小手平移')).toHaveAttribute('aria-pressed','true');
  });
  test('从上游线路进入枢纽后再进小手模式不会恢复旧路线', async ({app,screen,browser}) => {
    await c1(app,screen); await button(screen,'查看线路 AGRI_018_SUPPLY').click();
    await button(screen,'查看线路 P2_V2_SUPPLY').click();
    await button(screen,'定位设备 HUB_011').click();

    await button(screen,'小手平移').click();

    await expect(screen.getByRole('complementary',{name:'线路详情',exact:true})).toBeHidden();
    await expect(screen.getByRole('complementary',{name:'设施详情',exact:true})).toContainText('CO₂跨临界热泵枢纽');
    expect(await browser.evaluate(()=>({route:m9.state.route, history:m9.events.filter(event=>event.operation==='exitRoutesForPan').length}))).toEqual({route:null,history:1});
    expect(await browser.evaluate(()=>m9.map.getFilter('route-selected'))).toEqual(['==',['get','route_id'],'']);

    await button(screen,'小手平移').click();
    await button(screen,'关闭设施详情').click();
    await expect(button(screen,'展开实体索引')).toBeFocused();
    await expect(screen.getByRole('complementary',{name:'线路详情',exact:true})).toBeHidden();
  });
  test('隐藏线路后返回端点不会恢复已隐藏线路', async ({app,screen,browser}) => {
    await c1(app,screen); await button(screen,'查看线路 AGRI_018_SUPPLY').click();
    await button(screen,'查看线路 P2_V2_SUPPLY').click();
    await button(screen,'定位设备 HUB_011').click(); await button(screen,'图层').click();

    await screen.getByLabel('候选供回线',{exact:true}).uncheck();
    await button(screen,'返回上个实体').click();

    await expect(screen.getByRole('complementary',{name:'设施详情',exact:true})).toContainText('叶菜水培与冷凉种苗');
    expect(await browser.evaluate(()=>m9.state.route)).toEqual(null);
    expect(await screen.getByLabel('候选供回线',{exact:true}).isChecked()).toEqual(false);
    await expect(screen.getByRole('complementary',{name:'线路详情',exact:true})).toBeHidden();
  });
  test('PTES原回水不冒充已确认放热线路', async ({app,screen}) => {
    await app.open(); await expect(screen.getByRole('status')).toContainText('C1 11个子设备');
    await button(screen,'PTES PTES池式储热 地图选择').click();
    await button(screen,'查看候选关系').click();

    await button(screen,'查看线路 PTES_RETURN').click();

    const card=screen.getByRole('complementary',{name:'线路详情',exact:true});
    await expect(card).toContainText('用户水 · 储热支路返回枢纽');
    await expect(card).toContainText('不等于已确认放热线');
  });
  test('A区一期显示独立隔离直供', async ({app,screen}) => {
    await app.open(); await expect(screen.getByRole('status')).toContainText('C1 11个子设备');
    await button(screen,'A1 种薯组培与原原种温室 地图选择').click();
    await button(screen,'设备与回路').click();

    await button(screen,'查看线路 AGRI_014_SUPPLY').click();

    const card=screen.getByRole('complementary',{name:'线路详情',exact:true});
    await expect(card).toContainText('一期近端直供候选');
    await expect(card).toContainText('不表示必须经过二期 CO₂ 压缩机');
  });
  test('异版线路来源明确拒绝加载', async ({app,screen,browser}) => {
    await browser.route('**/data/map-v2/routes.json',r=>r.fulfill({status:200,json:{routes:[]}}));

    await app.open();

    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('Route identity mismatch');
  });
});
