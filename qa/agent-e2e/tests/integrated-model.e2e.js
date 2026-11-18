import { describe, test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { currentFacilityAsset } from './runtime-assets.js';
import { createHash } from 'node:crypto';

const button = (screen, name) => screen.getByRole('button', {name, exact:true});
const detail = {name:'设施详情',exact:true};

describe('统一模型和原方案农业归属', () => {
  test('B1父设施详情引用当前整合场景图片和版本',async({app,screen})=>{
    await app.open();
    await expect(screen.getByRole('status')).toContainText('85对象统一模型');

    await button(screen,'B1 冬季番茄连栋温室 地图选择').click();

    await expect(screen.getByRole('img',{name:'冬季番茄连栋温室的同版Blender模型图',exact:true}))
      .toHaveAttribute('src','../map-viewer/assets/integrated-v3/AGRI_016.png');
    await expect(screen.getByRole('complementary',detail)).toContainText('模型 m14-sensors-integrated-v1');
  });

  test('C1营养液泵按端口介质显示，不误写为控制信号',async({app,screen})=>{
    await app.open();
    await expect(screen.getByRole('status')).toContainText('85对象统一模型');
    await button(screen,'展开实体索引').click();
    await screen.getByRole('searchbox',{name:'搜索设施'}).fill('AGRI_018_NPUMP');

    await button(screen,'营养泵 营养液专用循环泵 AGRI_018_NPUMP').click();

    await expect(screen.getByRole('complementary',detail)).toContainText('营养液 · 入 / 出（候选端口）');
  });

  test('未定义端口的M10设备显示待核，不猜测介质方向',async({app,screen})=>{
    await app.open();
    await expect(screen.getByRole('status')).toContainText('85对象统一模型');
    await button(screen,'展开实体索引').click();
    await screen.getByRole('searchbox',{name:'搜索设施'}).fill('M10_C2_SYSTEM');

    await button(screen,'C2 系统 C2 三换热器 + 提温 + 电输入系统 M10_C2_SYSTEM').click();

    await expect(screen.getByText('端口未定义；介质与方向待核',{exact:true})).toBeVisible();
  });

  test('实体根存在但设备网格缺失时明确失败',async({app,screen,browser})=>{
    const asset=currentFacilityAsset(), manifest=asset.manifest;
    const original=asset.readBytes();
    const oldLength=original.readUInt32LE(12);
    const doc=JSON.parse(original.subarray(20,20+oldLength).toString('utf8'));
    const node=doc.nodes[manifest.entity_nodes.AGRI_016_GH1];
    node.children=[];delete node.mesh;
    const encoded=Buffer.from(JSON.stringify(doc));
    const padded=Buffer.alloc(Math.ceil(encoded.length/4)*4,0x20);encoded.copy(padded);
    const body=Buffer.concat([Buffer.alloc(20),padded,original.subarray(20+oldLength)]);
    body.write('glTF',0);body.writeUInt32LE(2,4);body.writeUInt32LE(body.length,8);
    body.writeUInt32LE(padded.length,12);body.writeUInt32LE(0x4e4f534a,16);
    manifest.sha256=createHash('sha256').update(body).digest('hex');
    await browser.route('**/integrated-asset.json',route=>route.fulfill({status:200,json:manifest}));
    await browser.route(asset.pattern,route=>route.fulfill({status:200,body}));

    await app.open();

    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('No meshes for AGRI_016_GH1');
  });

  for (const [parent, title] of [['AGRI_016','B区番茄'],['AGRI_017','B区草莓']]) {
    test(`${parent}末端从索引聚焦、切底图、返回正确父设施`, async ({app,screen,browser}) => {
      await app.open();
      await expect(screen.getByRole('status')).toContainText('85对象统一模型');
      await button(screen,'展开实体索引').click();
      await screen.getByRole('searchbox',{name:'搜索设施'}).fill(parent+'_GH1');

      await button(screen,`GH1 ${title}温室 GH1 ${parent}_GH1`).click();

      await expect.poll(async()=>browser.evaluate(()=>m9.state.cameraPending)).toEqual(false);
      await expect(screen.getByRole('complementary',detail)).toContainText(parent+'_GH1');
      await expect(screen.getByRole('img',{name:`${title}温室 GH1的同版Blender模型图`,exact:true})).toBeVisible();
      expect(await browser.evaluate(id=>m9.objects[id].meshes.length,parent+'_GH1')).toBeGreaterThan(0);
      const before=await browser.evaluate(()=>({center:m9.snapshot().center,zoom:m9.snapshot().zoom}));
      for (const name of ['卫星','数据 / DEM','标准地图']) await button(screen,name).click();
      expect(await browser.evaluate(()=>({center:m9.snapshot().center,zoom:m9.snapshot().zoom}))).toEqual(before);
      await button(screen,'返回 B 区设施').click();
      expect(await browser.evaluate(()=>m9.state.selected)).toEqual(parent);
      await button(screen,'关闭设施详情').click();
      await expect(screen.getByRole('complementary',detail)).toBeHidden();
    });
  }

  test('B区管段具有可见网格且Escape清除实际材质高亮',async({app,screen,browser})=>{
    await app.open();
    await expect(screen.getByRole('status')).toContainText('85对象统一模型');
    await button(screen,'B1 冬季番茄连栋温室 地图选择').click();
    await button(screen,'设备与回路').click();

    await button(screen,'AGRI_016_EDGE_11 · 热水回路 · 供流').click();

    expect(await browser.evaluate(()=>m9.objects.AGRI_016.meshes.some(m=>m.userData.connectionId==='AGRI_016_EDGE_11' && m.material.emissive.getHex()===0x885500))).toEqual(true);
    await browser.keyboard.press('Escape');
    expect(await browser.evaluate(()=>m9.objects.AGRI_016.meshes.some(m=>m.userData.connectionId==='AGRI_016_EDGE_11' && m.material.emissive.getHex()===0x885500))).toEqual(false);
    await expect(screen.getByRole('region',{name:'设施候选连接',exact:true})).toBeVisible();
  });

  test('统一语义根错配明确失败，不显示空设施成功状态',async({app,screen,browser})=>{
    await browser.route('**/integrated-asset.json',async route=>{
      const response=await route.fetch();const json=await response.json();
      json.entity_nodes.AGRI_016=json.entity_nodes.AGRI_017;
      await route.fulfill({status:200,json});
    });

    await app.open();

    await expect(screen.getByRole('status')).toContainText('加载失败');
    await expect(screen.getByRole('alert')).toContainText('Semantic root mismatch AGRI_016');
  });
});
