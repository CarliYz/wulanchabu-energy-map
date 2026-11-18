import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

const require = createRequire(import.meta.url);
const { chromium } = require('../qa/agent-e2e/node_modules/playwright-core');
const output = path.resolve('qc/m15-figma-runtime-sync-v1/runtime');
fs.mkdirSync(output, { recursive: true });
const receipt = { status: 'fail', purpose: 'Current runtime visual references for Figma, not a new full product regression', viewport: [1440,900], checks: [], errors: [] };
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width:1440,height:900 } });
  page.on('pageerror', e => receipt.errors.push(e.message));
  await page.goto('http://127.0.0.1:8768/web/map-prototype/', { waitUntil:'domcontentloaded' });
  await page.waitForFunction(() => window.m9?.state.ready && m9.snapshot().renderedFrames > 0);
  const button = name => page.getByRole('button', { name, exact:true });
  const capture = async name => {
    await page.waitForFunction(() => !m9.state.cameraPending);
    await page.screenshot({ path:path.join(output, name+'-full.png') });
    const style = await page.addStyleTag({ content:'body > header,body > nav,body > aside,body > section,body > footer,#audit-backdrop{visibility:hidden!important}' });
    await page.screenshot({ path:path.join(output, name+'-map.png') });
    await style.evaluate(el=>el.remove());
    receipt.checks.push({ name, state:await page.evaluate(()=>({ selected:m9.state.selected,view:m9.state.view,review:m9.state.reviewObservation,circuit:m9.state.circuit })), map_sha256:createHash('sha256').update(fs.readFileSync(path.join(output,name+'-map.png'))).digest('hex') });
    if (['05-c1','06-c1-relations','09-sensor','10-parent-a1','11-geographic-list','12-geographic-detail','14-analysis-empty'].includes(name)) {
      const context=await page.evaluate(()=>({selected:m9.state.selected,review:m9.state.reviewObservation,circuit:m9.state.circuit}));
      for (const [label,suffix] of [['卫星','satellite'],['数据 / DEM','dem']]) {
        await button(label).click();
        assert.deepEqual(await page.evaluate(()=>({selected:m9.state.selected,review:m9.state.reviewObservation,circuit:m9.state.circuit})),context);
        await capture(name+'-'+suffix);
      }
      await button('标准地图').click();
    }
  };
  await capture('01-standard');
  await button('卫星').click(); await capture('03-satellite');
  await button('数据 / DEM').click(); await capture('04-dem');
  await button('标准地图').click();
  await button('C1 叶菜水培与冷凉种苗 地图选择').click();
  await capture('05-c1');
  receipt.c1_detail=await page.locator('#detail').innerText();
  await button('设备与回路').click(); await button('营养液回路').click();
  await capture('06-c1-relations');
  await button('地理复核').click();
  await page.waitForFunction(()=>m9.geographicReview.snapshot().loaded);
  await capture('11-geographic-list');
  await button('定位复核 pad/AGRI_018/waterbody/relation/7763319').click();
  await capture('12-geographic-detail');
  receipt.geographic_detail=await page.locator('#geo-properties').innerText();
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  assert.equal(await page.locator('#geo-panel').isVisible(),false);
  await button('全区总览').click();
  await page.waitForFunction(()=>!m9.state.cameraPending);
  await button('A1 种薯组培与原原种温室 地图选择').click();
  await capture('10-parent-a1');
  receipt.parent_detail=await page.locator('#detail').innerText();
  await button('展开实体索引').click();
  await page.getByRole('searchbox',{name:'搜索设施',exact:true}).fill('AGRI_014_SENSOR');
  await button('测点 温度/流量测点 AGRI_014_SENSOR').click();
  await page.waitForFunction(()=>{const i=document.getElementById('model-preview');return i.complete&&i.naturalWidth===900;});
  await capture('09-sensor');
  receipt.sensor_detail=await page.locator('#detail').innerText();
  assert.match(receipt.sensor_detail,/未接管/);
  await page.keyboard.press('Escape');
  assert.equal(await page.evaluate(()=>m9.state.selected),'AGRI_014');
  await button('分析').click();
  await capture('14-analysis-empty');
  receipt.analysis_empty=await page.locator('#analysis-panel').innerText();
  assert.equal(await page.locator('#analysis-empty').isVisible(),true);
  assert.deepEqual(receipt.errors,[]);
  receipt.status='pass';
} catch(error) { receipt.failure=error.stack; process.exitCode=1; }
finally { await browser.close();fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt)); }
