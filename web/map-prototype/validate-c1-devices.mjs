import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = path.join(root, process.argv[2] || 'qc/c1-devices-v1'); fs.mkdirSync(out, { recursive: true });
const graph = JSON.parse(fs.readFileSync(path.join(root, 'web/map-prototype/c1-runtime.json')));
const sha = p => createHash('sha256').update(fs.readFileSync(path.join(root, p))).digest('hex');
const receipt = { command: 'node web/map-prototype/validate-c1-devices.mjs', date: new Date().toISOString(),
  tested_head: spawnSync('git', ['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).stdout.trim(),
  matrix: [], checks: {}, errors: [], product_hashes: {} };
for (const p of ['web/map-prototype/app.mjs','web/map-prototype/facility-index.mjs','web/map-prototype/c1-relations.mjs',
  'web/map-prototype/c1-runtime.json','web/map-prototype/facility-registry.json','web/map-prototype/index.html','web/map-prototype/style.css',
  'web/map-viewer/assets/facilities-v1/facilities.glb', ...graph.objects.map(o=>`web/map-viewer/assets/c1-devices-v1/${o.object_id}.png`)]) receipt.product_hashes[p] = sha(p);
let browser, page;
try {
  const require = createRequire(import.meta.url), {chromium} = require('../../qa/agent-e2e/node_modules/playwright-core');
  browser = await chromium.launch({headless:true}); page = await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror', e=>receipt.errors.push(e.message));
  page.on('console', m=>{ if(m.type()==='error') receipt.errors.push(m.text()); });
  await page.goto('http://127.0.0.1:8767/web/map-prototype/', {waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.m9?.state.ready && m9.snapshot().renderedFrames>0);
  assert.equal(graph.objects.length,11); assert.equal(graph.ports.length,38); assert.equal(graph.connections.length,19);
  async function select(id) {
    if (!await page.locator('#index-panel').isVisible()) await page.locator('#index-toggle').click();
    await page.locator('#entity-search').fill(id); await page.locator(`[data-select="${id}"]`).click();
    await page.waitForFunction(id=>m9.state.selected===id && !m9.state.cameraPending,id);
  }
  for(const width of [1440,1100,760]) {
    await page.setViewportSize({width,height:1000});
    for(const item of graph.objects) {
      const id=item.object_id; await select(id);
      assert.equal(await page.locator('#detail-id').textContent(),id);
      await page.waitForFunction(()=>{const img=document.getElementById('model-preview');return !img.hidden && img.complete && img.naturalWidth===640;});
      const framing=await page.evaluate(id=>{
        const p=m9.projectModelVertices(id);return {area:m9.safeArea(),min:[0,1].map(i=>Math.min(...p.map(p=>p[i]))),max:[0,1].map(i=>Math.max(...p.map(p=>p[i])))};
      },id);
      assert(framing.min[0]>=framing.area.left-3 && framing.max[0]<=framing.area.right+3, `${width}/${id} x framing ${JSON.stringify(framing)}`);
      assert(framing.min[1]>=framing.area.top-3 && framing.max[1]<=framing.area.bottom+3, `${width}/${id} y framing ${JSON.stringify(framing)}`);
      const camera=await page.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom(),elevation:m9.map.getCenterElevation()}));
      for(const view of ['satellite','data','standard']) {
        await page.locator(`[data-view="${view}"]`).click();
        assert.equal(await page.locator('#detail-id').textContent(),id);
        assert.deepEqual(await page.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom(),elevation:m9.map.getCenterElevation()})),camera);
      }
      const point=await page.evaluate(id=>{
        const a=m9.safeArea();
        for(const mesh of m9.objects[id].meshes) {
          const g=mesh.geometry,p=g.attributes.position,ix=g.index,n=ix?ix.count:p.count;
          for(let i=0;i<n;i+=3*Math.max(1,Math.floor(n/600))) {
            const xyz=[0,0,0];
            for(let j=0;j<3;j++){const k=ix?ix.getX(i+j):i+j;xyz[0]+=p.getX(k)/3;xyz[1]+=p.getY(k)/3;xyz[2]+=p.getZ(k)/3;}
            const [x,y]=m9.projectWorld(xyz).map(Math.round);
            if(x>a.left+3 && x<a.right-3 && y>a.top+3 && y<a.bottom-3 && document.elementFromPoint(x,y)?.tagName==='CANVAS' && m9.hitTest(x,y)===id) return [x,y];
          }
        }
        return null;
      },id);
      assert(point,`${width}/${id} has no accessible mesh surface`);
      await page.mouse.click(...point);
      await page.waitForFunction(id=>m9.state.selected===id && !m9.state.cameraPending,id);
      assert.equal(await page.locator('#detail-id').textContent(),id);
      assert.equal(await page.locator(`[data-select="${id}"]`).getAttribute('aria-pressed'),'true');
      await page.locator('#close').click();
      await page.waitForFunction(()=>m9.state.selected==='AGRI_018' && !m9.state.cameraPending);
      assert.equal(await page.locator('#detail-id').textContent(),'AGRI_018');
      await page.locator('#close').click(); assert.equal(await page.locator('#detail').isVisible(),false);
      receipt.matrix.push({width,id,framing,canvas_click:point,tree_canvas_views_parent_exit:'pass'});
    }
    console.log(`Validated ${width}:11 children`);
  }
  await page.setViewportSize({width:1440,height:1000}); await select('AGRI_018');
  await page.locator('#relations-toggle').click();
  assert.equal(await page.locator('[data-edge-row]').count(),19);
  for(const [circuit,count] of [['C1_HEAT',8],['C1_NUTRIENT',7],['C1_CONTROL',4]]) {
    await page.locator(`[data-circuit="${circuit}"]`).click();
    assert.equal(await page.locator('[data-edge-row]').count(),count);
    const ids=await page.locator('[data-edge-row]').evaluateAll(rows=>rows.map(r=>r.dataset.edgeRow));
    assert(ids.every(id=>graph.connections.find(e=>e.connection_id===id).circuit_id===circuit));
  }
  await page.locator('[data-circuit="C1_HEAT"]').click();
  await page.locator('[data-connection="EDGE_014"]').click();
  assert.equal(await page.evaluate(()=>m9.state.connection),'EDGE_014');
  assert(await page.evaluate(()=>m9.scene.children.some(m=>m.userData.connectionId==='EDGE_014' && m.material.emissive?.getHex()===0x885500)));
  await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>m9.state.connection),null);
  assert.equal(await page.locator('#relations-panel').isVisible(),true);
  const viewBefore=await page.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom(),elevation:m9.map.getCenterElevation()}));
  await page.locator('[data-device="AGRI_018_HX"]').click(); await page.waitForFunction(()=>!m9.state.cameraPending);
  await page.locator('#relations-toggle').click();
  assert.equal(await page.locator('[data-port]').count(),4);
  assert.equal(await page.locator('[data-port*="USER"]').count(),2);
  assert((await page.locator('#relations-content').textContent()).includes('预留未接'));
  await page.locator('#parent-facility').click();
  assert.equal(await page.locator('#detail-id').textContent(),'AGRI_018');
  assert.equal(await page.locator('#relations-panel').isVisible(),true);
  assert.deepEqual(await page.evaluate(()=>({center:m9.map.getCenter().toArray(),zoom:m9.map.getZoom(),elevation:m9.map.getCenterElevation()})),viewBefore);
  assert.equal(await page.locator('[data-device="AGRI_018_HX"]').evaluate(e=>e===document.activeElement),true);
  receipt.checks.circuits_ports_highlight_parent_context='pass';
  await page.screenshot({path:path.join(out,'c1-relations.png')});
  await page.locator('[data-device="AGRI_018_PUMP"]').click();await page.waitForFunction(()=>!m9.state.cameraPending);
  await page.locator('#relations-toggle').click();
  await page.getByRole('button',{name:'EDGE_015 终点 调节阀与隔离阀',exact:true}).click();
  await page.waitForFunction(()=>m9.state.selected==='AGRI_018_VALVE' && !m9.state.cameraPending);
  await page.locator('#back-entity').click();
  assert.equal(await page.locator('#detail-id').textContent(),'AGRI_018_PUMP');
  assert.equal(await page.locator('#relations-panel').isVisible(),true);
  assert.equal(await page.getByRole('button',{name:'EDGE_015 终点 调节阀与隔离阀',exact:true}).evaluate(e=>e===document.activeElement),true);
  await page.keyboard.press('Escape');await page.keyboard.press('Escape');
  assert.equal(await page.locator('#detail-id').textContent(),'AGRI_018');
  await page.locator('#overview').click();await page.locator('#pan').click();
  await page.locator('[data-object-id="AGRI_018"]').click();assert.equal(await page.locator('#detail').isVisible(),false);
  await page.keyboard.press('Escape');
  receipt.checks.related_device_history_and_escape='pass';
  assert.deepEqual(await page.evaluate(()=>m9.errors),[]);assert.deepEqual(await page.evaluate(()=>window.m9BootErrors),[]);assert.deepEqual(receipt.errors,[]);
  await page.screenshot({path:path.join(out,'overview.png')});receipt.status='pass';
}catch(error){receipt.status='fail';receipt.failure=error.stack;if(page)await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});}
finally{await browser?.close();receipt.exit_code=receipt.status==='pass'?0:1;fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({status:receipt.status,cases:receipt.matrix.length,checks:receipt.checks,failure:receipt.failure}));process.exitCode=receipt.exit_code;}
