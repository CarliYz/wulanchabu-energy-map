import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { flowCoordinates } from './energy-network.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = path.join(root, process.argv[2] || 'qc/energy-paths-v1/matrix'); fs.mkdirSync(out, { recursive: true });
const routes = JSON.parse(fs.readFileSync(path.join(root, 'data/map-v2/routes.json'))).routes;
const receipt = { command: `node web/map-prototype/validate-energy-paths.mjs ${process.argv[2] || ''}`, date: new Date().toISOString(),
  tested_head: spawnSync('git', ['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).stdout.trim(), matrix: [], checks: {}, errors: [], product_hashes: {} };
for (const file of ['web/map-prototype/app.mjs','web/map-prototype/energy-network.mjs','web/map-prototype/index.html',
  'web/map-prototype/style.css','data/map-v2/routes.json','web/map-prototype/facility-registry.json','web/map-prototype/c1-runtime.json',
  'web/map-prototype/ab-terminal-runtime.json','web/map-prototype/ab-relations.mjs',
  'web/map-prototype/m10-system-runtime.json','web/map-prototype/m10-relations.mjs','web/map-prototype/m10-graph.mjs',
  'web/map-prototype/asset-bindings.json','web/map-prototype/integrated-asset.json',
  'web/map-prototype/audit-manifest.json',
  path.relative(root, path.resolve(root, 'web/map-prototype', JSON.parse(fs.readFileSync(path.join(root,'web/map-prototype/integrated-asset.json'))).asset_url))]) receipt.product_hashes[file] = createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex');
let browser, page, server;
try {
  // Own this server: e2e runs may stop the shared 8767 service at any time.
  server = spawn('python3', ['-u', '-c', `
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import sys
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=sys.argv[1]))
print(server.server_port, flush=True)
server.serve_forever()
`, root], {stdio:['ignore','pipe','pipe']});
  let serverLog=''; server.stderr.on('data', chunk=>{serverLog=(serverLog+chunk).slice(-4000);});
  const port = await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Matrix server did not start within 10s')),10000);
    server.once('error',error=>{clearTimeout(timer);reject(error);});
    server.once('exit',code=>{clearTimeout(timer);reject(new Error(`Matrix server exited ${code}: ${serverLog}`));});
    server.stdout.once('data',chunk=>{clearTimeout(timer);const port=Number(String(chunk).trim());
      if(!Number.isInteger(port)||port<1||port>65535)reject(new Error(`Invalid matrix server port: ${chunk}`));else resolve(port);});
  });
  receipt.server={ownership:'matrix_process',pid:server.pid,url:`http://127.0.0.1:${port}/web/map-prototype/`};
  const require = createRequire(import.meta.url), {chromium} = require('../../qa/agent-e2e/node_modules/playwright-core');
  browser = await chromium.launch({headless:true}); page = await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror', e=>receipt.errors.push(e.message));
  page.on('console', m=>{if(m.type()==='error')receipt.errors.push(m.text());});
  page.on('requestfailed', request=>receipt.errors.push(`${request.failure()?.errorText}: ${request.url()}`));
  await page.goto(receipt.server.url,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.m9?.state.ready && m9.snapshot().renderedFrames>0);
  const view = () => page.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom(),pitch:m9.map.getPitch(),bearing:m9.map.getBearing(),elevation:m9.map.getCenterElevation()}));
  async function select(id) {
    if (!await page.locator('#index-panel').isVisible()) await page.locator('#index-toggle').click();
    await page.locator('#entity-search').fill(id); await page.locator(`[data-select="${id}"]`).click();
    await page.waitForFunction(()=>!m9.state.cameraPending);
    await page.locator('#relations-toggle').click();
  }
  for (const width of [1440,1100,760]) {
    await page.setViewportSize({width,height:1000});
    for (const route of routes) {
      const id=route.route_id;
      const parent = id.startsWith('P2_') ? 'HUB_011' : id.startsWith('PTES') ? 'STORE_012' : id.match(/^(?:AGRI|DRY|DC)_\d+/)[0];
      await select(parent); const entryView=await view();
      await page.getByRole('button',{name:`查看线路 ${id}`,exact:true}).click();
      assert.equal(await page.locator('#route-id').textContent(),id);
      assert.equal(await page.locator('#detail').isVisible(),false);
      assert.deepEqual(await page.evaluate(()=>m9.map.getFilter('route-selected')),['==',['get','route_id'],id]);
      const coordinates=await page.evaluate(id=>m9.map.getSource('routes')._data.features.find(f=>f.properties.route_id===id).geometry.coordinates,id);
      assert.equal(coordinates.length,flowCoordinates(route).length);
      const routeView=await view();
      for (const mode of ['satellite','data','standard']) {
        await page.locator(`[data-view="${mode}"]`).click(); assert.deepEqual(await view(),routeView);
        assert.equal(await page.locator('#route-id').textContent(),id);
      }
      // Test the actual route at map level, away from facility surfaces and UI.
      const candidate=await page.evaluate(id=>{
        const a=m9.safeArea(),geometry=m9.map.getSource('routes')._data.features.find(f=>f.properties.route_id===id).geometry.coordinates;
        for(let i=0;i<geometry.length-1;i++) for(const t of [.5,.25,.75,0]) {
          const p=geometry[i].map((n,k)=>n*(1-t)+geometry[i+1][k]*t), q=m9.map.project(p);
          const x=Math.round(q.x),y=Math.round(q.y);
          if(x<a.left+5&&x<a.right)continue;
          if(x<=a.left+5||x>=a.right-5||y<=a.top+5||y>=a.bottom-5||document.elementFromPoint(x,y)?.tagName!=='CANVAS'||m9.hitTest(x,y))continue;
          const hits=m9.map.queryRenderedFeatures([[x-5,y-5],[x+5,y+5]],{layers:['route-lines']});
          if(hits.some(h=>h.properties.route_id===id)) return [x,y];
        }
        return null;
      },id);
      assert(candidate,`${width}/${id}: no accessible route pixel`);
      // Closing restores the facility camera; return to the saved route camera
      // only to reproduce the same actual pointer target, without selecting it.
      await page.locator('#route-back').click(); assert.equal(await page.locator('#detail-id').textContent(),parent);
      assert.deepEqual(await view(),entryView);
      assert.equal(await page.getByRole('button',{name:`查看线路 ${id}`,exact:true}).evaluate(el=>el===document.activeElement),true);
      await page.locator('#close').click();
      await page.evaluate(v=>m9.map.jumpTo(v),routeView); await page.waitForFunction(()=>!m9.map.isMoving());
      await page.mouse.click(...candidate);
      const picker=await page.locator('#route-picker').isVisible();
      if(picker) await page.getByRole('button',{name:`选择重叠线路 ${id}`,exact:true}).click();
      assert.equal(await page.locator('#route-detail').isVisible(),true);
      assert.equal(await page.evaluate(()=>m9.state.route),id);
      assert.equal(await page.locator('#route-id').textContent(),id);
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#route-detail').isVisible(),false);
      assert.equal(await page.evaluate(()=>m9.state.route),null);
      assert.equal(await page.locator('canvas.maplibregl-canvas').evaluate(el=>el===document.activeElement),true);
      receipt.matrix.push({width,id,canvas_click:candidate,overlap_picker:picker,views_history_exit:'pass'});
    }
    console.log(`Validated ${width}: ${routes.length} route journeys`);
  }
  await page.setViewportSize({width:1440,height:1000}); await select('HUB_011');
  assert.match(await page.locator('#relations-content').textContent(),/蒸发器 → 压缩机（电输入）→ 气冷器 → 节流阀 → 蒸发器/);
  await page.getByRole('button',{name:'查看线路 P2_V2_SUPPLY',exact:true}).click();
  await page.screenshot({path:path.join(out,'p2-supply.png')});
  await page.locator('[data-view="satellite"]').click(); await page.screenshot({path:path.join(out,'p2-satellite.png')});
  await page.locator('[data-view="data"]').click(); await page.screenshot({path:path.join(out,'p2-dem.png')});
  receipt.checks.route_flow_orientation_and_source='pass';
  assert.deepEqual(await page.evaluate(()=>m9.errors),[]);assert.deepEqual(await page.evaluate(()=>m9BootErrors),[]);assert.deepEqual(receipt.errors,[]);
  receipt.completed_product_hashes = {};
  for (const [file,sha] of Object.entries(receipt.product_hashes)) {
    receipt.completed_product_hashes[file] = createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex');
    assert.equal(receipt.completed_product_hashes[file],sha,`Input changed during route matrix: ${file}`);
  }
  receipt.checks.unchanged_product_identity='pass';
  receipt.status='pass';
} catch(error) {receipt.status='fail';receipt.failure=error.stack;if(page) await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});}
finally {
  await browser?.close();
  if(server&&server.exitCode===null&&server.signalCode===null){const stopped=once(server,'exit');server.kill('SIGTERM');await stopped;}
  receipt.exit_code=receipt.status==='pass'?0:1;
  fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify({status:receipt.status,cases:receipt.matrix.length,failure:receipt.failure}));process.exitCode=receipt.exit_code;
}
