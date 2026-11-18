import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { localToWorld } from './projection.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = path.join(root, process.argv[2] || 'qc/facilities-v1'); fs.mkdirSync(out, { recursive: true });
const registry = JSON.parse(fs.readFileSync(path.join(root, 'web/map-prototype/facility-registry.json')));
const sha = p => createHash('sha256').update(fs.readFileSync(path.join(root, p))).digest('hex');
const receipt = { date: new Date().toISOString(), command: 'node web/map-prototype/validate-facilities.mjs',
  tested_head: spawnSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).stdout.trim(),
  product_hashes: {}, matrix: [], errors: [], checks: {}, independent_registration: 'not_run' };
const identities = ['web/map-prototype/app.mjs', 'web/map-prototype/facility-index.mjs', 'web/map-prototype/projection.mjs',
  'web/map-prototype/index.html', 'web/map-prototype/style.css', 'web/map-prototype/facility-registry.json',
  'web/map-prototype/c1-runtime.json', 'web/map-prototype/c1-relations.mjs',
  'web/map-viewer/assets/facilities-v1/facilities.glb', 'data/map-v2/routes.json', 'data/map-v2/geographic-manifest.json'];
for (const item of registry.objects) identities.push(`web/map-viewer/assets/facilities-v1/${item.object_id}.png`);
receipt.product_hashes = Object.fromEntries(identities.map(p => [p, sha(p)]));
let browser, page;
try {
  assert.equal(registry.objects.length, 12);
  assert.equal(registry.sha256, sha('web/map-viewer/assets/facilities-v1/facilities.glb'));
  const require = createRequire(import.meta.url);
  const playwright = require('../../qa/agent-e2e/node_modules/playwright-core');
  browser = await playwright.chromium.launch({ headless: true });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', e => receipt.errors.push({ kind: 'pageerror', message: e.message }));
  page.on('console', m => { if (m.type() === 'error') receipt.errors.push({ kind: 'console', message: m.text() }); });
  await page.goto('http://127.0.0.1:8767/web/map-prototype/', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.m9?.state.ready && m9.snapshot().renderedFrames > 0, null, { timeout: 60000 });
  assert.equal(await page.locator('#index-panel').isVisible(), false);
  assert.equal(await page.locator('#detail').isVisible(), false);
  assert.equal(await page.locator('[data-view="standard"]').getAttribute('aria-pressed'), 'true');
  receipt.checks.default_state = 'pass';
  for (const width of [1440, 1100, 760]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const item of registry.objects) {
      const id = item.object_id;
      if (!await page.locator('#index-panel').isVisible()) await page.locator('#index-toggle').click();
      await page.getByRole('searchbox', { name: '搜索设施' }).fill(id);
      await page.locator(`[data-select="${id}"]`).click();
      await page.waitForFunction(id => m9.state.selected === id && !m9.state.cameraPending, id);
      assert.equal(await page.locator('#detail-id').textContent(), id);
      assert.equal(await page.locator('#detail-name').textContent(), item.name);
      await page.waitForFunction(() => { const img = document.getElementById('model-preview'); return !img.hidden && img.complete && img.naturalWidth > 0; });
      const framed = await page.evaluate(id => {
        const points = m9.projectModelVertices(id), area = m9.safeArea();
        return { area, min: [0,1].map(i => Math.min(...points.map(p => p[i]))), max: [0,1].map(i => Math.max(...points.map(p => p[i]))) };
      }, id);
      assert(framed.min[0] >= framed.area.left - 3 && framed.max[0] <= framed.area.right + 3, `${width}/${id} horizontal framing ${JSON.stringify(framed)}`);
      assert(framed.min[1] >= framed.area.top - 3 && framed.max[1] <= framed.area.bottom + 3, `${width}/${id} vertical framing ${JSON.stringify(framed)}`);
      const before = await page.evaluate(() => m9.snapshot());
      for (const view of ['satellite', 'data', 'standard']) {
        await page.locator(`[data-view="${view}"]`).click();
        assert.equal(await page.locator('#detail-id').textContent(), id);
        const after = await page.evaluate(() => m9.snapshot());
        assert.deepEqual(after.center, before.center); assert.equal(after.zoom, before.zoom);
        assert.equal(after.terrainVisible, view !== 'standard');
      }
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#detail').isVisible(), false);
      assert.equal(await page.evaluate(() => m9.state.selected), null);
      const point = await page.evaluate(world => m9.projectWorld(world), localToWorld(item.model_root_xyz.map((v,i) => v + [0,-45,.1][i])));
      const target = await page.evaluate(([x,y]) => document.elementFromPoint(x,y)?.tagName, point);
      assert.equal(target, 'CANVAS', `${width}/${id} actual model hit blocked by ${target}`);
      await page.mouse.click(...point);
      await page.waitForFunction(id => m9.state.selected === id && !m9.state.cameraPending, id);
      assert.equal(await page.locator('#detail-id').textContent(), id);
      assert.equal(await page.locator(`[data-select="${id}"]`).getAttribute('aria-pressed'), 'true');
      receipt.matrix.push({ width, id, tree_and_canvas: 'pass', framing: framed, click: point, views: 3 });
      if (id === 'HUB_011' || id === 'AGRI_018') await page.screenshot({ path: path.join(out, `${width}-${id}.png`) });
      await page.locator('#close').click();
    }
    console.log(`Validated ${width}: 12 facilities`);
  }
  receipt.checks.twelve_facilities_three_sizes = 'pass';
  await page.setViewportSize({ width: 1440, height: 1000 });
  if (!await page.locator('#index-panel').isVisible()) await page.locator('#index-toggle').click();
  await page.getByRole('searchbox', { name: '搜索设施' }).fill('不存在的设施');
  assert.equal(await page.locator('#empty-index').isVisible(), true);
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('searchbox', { name: '搜索设施' }).inputValue(), '');
  assert.equal(await page.locator('#index-panel').isVisible(), true);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#index-panel').isVisible(), false);
  assert.equal(await page.locator('#index-toggle').evaluate(el => el === document.activeElement), true);
  await page.locator('#index-toggle').click();
  const handle = await page.locator('#index-resize').boundingBox();
  await page.mouse.move(handle.x + 4, handle.y + 20); await page.mouse.down();
  await page.mouse.move(handle.x + 400, handle.y + 20);
  assert.equal(await page.locator('#index-resize').getAttribute('aria-valuenow'), '420');
  await page.keyboard.press('Escape'); await page.mouse.up();
  assert.equal(await page.locator('#index-resize').getAttribute('aria-valuenow'), '288');
  await page.locator('#index-toggle').click();
  receipt.checks.index_search_resize_escape = 'pass';
  await page.locator('#overview').click();
  await page.locator('[data-object-id="HUB_011"]').click();
  await page.waitForFunction(() => !m9.state.cameraPending);
  await page.locator('#relations-toggle').click();
  assert.equal(await page.locator('#relations-panel').isVisible(), true);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#relations-panel').isVisible(), false);
  assert.equal(await page.locator('#detail').isVisible(), true);
  await page.locator('#layers-toggle').click();
  await page.locator('#models').uncheck();
  assert.equal(await page.locator('#detail').isVisible(), false);
  assert.equal(await page.evaluate(() => m9.state.selected), null);
  assert.equal(await page.locator('.facility-label:visible').count(), 0);
  await page.locator('#models').check(); await page.keyboard.press('Escape');
  assert.equal(await page.locator('#layers-panel').isVisible(), false);
  receipt.checks.layers_relations_exit = 'pass';
  const beforeDrag = await page.evaluate(() => m9.snapshot());
  await page.locator('#pan').click();
  await page.mouse.move(700, 400); await page.mouse.down(); await page.mouse.move(850, 440, { steps: 10 }); await page.mouse.up();
  const afterDrag = await page.evaluate(() => m9.snapshot());
  assert.notDeepEqual(afterDrag.center, beforeDrag.center); assert.equal(afterDrag.selected, null);
  await page.keyboard.press('Escape'); assert.equal(await page.locator('#pan').getAttribute('aria-pressed'), 'false');
  receipt.checks.pan_and_exit = 'pass';
  assert.deepEqual(await page.evaluate(() => m9.errors), []);
  assert.deepEqual(await page.evaluate(() => window.m9BootErrors), []);
  assert.deepEqual(receipt.errors, []);
  receipt.status = 'pass';
} catch (error) {
  receipt.status = 'fail'; receipt.failure = error.stack;
  if (page) await page.screenshot({ path: path.join(out, 'failure.png') }).catch(() => {});
} finally {
  await browser?.close();
  receipt.exit_code = receipt.status === 'pass' ? 0 : 1;
  fs.writeFileSync(path.join(out, 'receipt.json'), JSON.stringify(receipt, null, 2));
  console.log(JSON.stringify({ status: receipt.status, cases: receipt.matrix.length, checks: receipt.checks, failure: receipt.failure }));
  process.exitCode = receipt.exit_code;
}
