import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const packageRoot = path.resolve(root, process.argv[2] || 'outputs/能源地图_地理复核演示_20261117');
const output = path.resolve(root, process.argv[3] || 'qc/m13-geographic-ui-v1');
fs.mkdirSync(output, { recursive: true });
const hash = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const receipt = { status: 'fail', exit_code: 1, package_root: packageRoot, date: new Date().toISOString(),
  scope: 'Actual packaged 85-object runtime, 293 observations, C1/P2 water review, three base maps and screen widths, focus, filter, Escape, original context and preview',
  errors: [], checks: {}, runtime_hashes: {} };
let server, browser, page;
try {
  const manifest = JSON.parse(fs.readFileSync(path.join(packageRoot, 'package-manifest.json')));
  for (const [name, digest] of Object.entries(manifest.sha256)) assert.equal(hash(path.join(packageRoot, name)), digest, name);
  for (const [name, digest] of Object.entries(manifest.sha256)) if (/^(web|data|design)\//.test(name) || /^qc\/(m13-geographic-review-v1|m14-sensors-integrated-v1\/geography)\/.+\.(json|geojson)$/.test(name)) receipt.runtime_hashes[name] = digest;
  receipt.checks.package_hashes = Object.keys(manifest.sha256).length;
  server = spawn('python3', ['-u', '-c', `
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import sys
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=sys.argv[1]))
print(server.server_port,flush=True)
server.serve_forever()
`, packageRoot], { stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; server.stderr.on('data', chunk => { log = (log + chunk).slice(-3000); });
  const port = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Package server startup timeout')), 10000);
    server.once('error', error => { clearTimeout(timer); reject(error); });
    server.once('exit', code => { clearTimeout(timer); reject(new Error(`Package server exit ${code}: ${log}`)); });
    server.stdout.once('data', chunk => { clearTimeout(timer); const port = Number(String(chunk).trim());
      if (!Number.isInteger(port) || port < 1 || port > 65535) reject(new Error(`Invalid server port ${chunk}`)); else resolve(port); });
  });
  const require = createRequire(import.meta.url), { chromium } = require('../qa/agent-e2e/node_modules/playwright-core');
  browser = await chromium.launch({ headless: true }); page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', error => receipt.errors.push(error.message));
  page.on('requestfailed', request => receipt.errors.push(`${request.failure()?.errorText}: ${request.url()}`));
  const button = name => page.getByRole('button', { name, exact: true });
  await page.goto(`http://127.0.0.1:${port}/web/map-prototype/`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.m9?.state.ready && m9.snapshot().renderedFrames > 0);
  assert.equal(await page.evaluate(() => Object.keys(m9.objects).length), 85);
  receipt.checks.entities = 85;
  await button('C1 叶菜水培与冷凉种苗 地图选择').click();
  await button('设备与回路').click(); await button('营养液回路').click();
  await page.waitForFunction(() => !m9.state.cameraPending);
  const view = () => page.evaluate(() => ({ center: m9.map.getCenter().toArray(), zoom: m9.map.getZoom(), elevation: m9.map.getCenterElevation() }));
  const original = await view();
  await button('地理复核').click(); await page.waitForFunction(() => m9.geographicReview.snapshot().loaded);
  assert.deepEqual(await page.evaluate(() => m9.geographicReview.snapshot()), { loaded: true, observations: 293, features: 2814 });
  receipt.checks.observations = 293; receipt.checks.features = 2814;
  await button('定位复核 pad/AGRI_018/waterbody/relation/7763319').click();
  assert.match(await page.locator('#geo-properties').textContent(), /公开几何相交 \/ 包含/);
  receipt.checks.sizes = [];
  for (const width of [1440, 1100, 760]) {
    await page.setViewportSize({ width, height: 1000 }); await button('重新定位复核点').click();
    assert.ok(await page.evaluate(() => {
      const point = m9.map.project([113.1844094, 41.0328357]), card = document.getElementById('geo-panel').getBoundingClientRect();
      return point.x > 90 && point.x < innerWidth - 20 && point.y > document.getElementById('toolbar').getBoundingClientRect().bottom &&
        !(point.x >= card.left && point.x <= card.right && point.y >= card.top && point.y <= card.bottom);
    }));
    await page.screenshot({ path: path.join(output, `package-c1-${width}.png`) }); receipt.checks.sizes.push(width);
  }
  await page.setViewportSize({ width: 1440, height: 1000 }); await button('重新定位复核点').click();
  for (const name of ['卫星', '数据 / DEM', '标准地图']) {
    const before = await view(); await button(name).click(); assert.deepEqual(await view(), before);
    assert.equal(await page.evaluate(() => m9.state.reviewObservation), 'pad/AGRI_018/waterbody/relation/7763319');
  }
  await page.keyboard.press('Escape'); await page.getByLabel('搜索地理复核', { exact: true }).fill('P2_V2_RETURN');
  await button('定位复核 route/P2_V2_RETURN/waterbody/relation/7763319').click();
  assert.match(await page.locator('#geo-properties').textContent(), /公开几何相交 \/ 包含/);
  await page.getByRole('checkbox', { name: '水域', exact: true }).uncheck();
  assert.equal(await page.evaluate(() => m9.state.reviewObservation), null);
  await page.getByRole('checkbox', { name: '水域', exact: true }).check();
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#geo-panel').isVisible(), false); assert.deepEqual(await view(), original);
  assert.equal(await page.locator('#detail').isVisible(), true); assert.equal(await page.evaluate(() => m9.state.circuit), 'C1_NUTRIENT');
  receipt.checks.return_to_original_context = 'pass';
  // The restored C1 close-up correctly culls remote labels. Navigate through
  // the visible overview control before selecting the distant storage site.
  await button('全区总览').click();
  await page.waitForFunction(() => !m9.state.cameraPending);
  await button('PTES PTES池式储热 地图选择').click();
  await page.waitForFunction(() => { const image = document.getElementById('model-preview'); return !image.hidden && image.complete && image.naturalWidth > 0; });
  receipt.checks.ptes_preview = 'decoded';
  const integrated = JSON.parse(fs.readFileSync(path.join(packageRoot, 'web/map-prototype/integrated-asset.json')));
  if (integrated.revision === 'm14-sensors-integrated-v1') {
    receipt.scope += '; four agricultural sensor meshes/previews, actual canvas pick and layered exit';
    await button('展开实体索引').click();
    receipt.checks.agricultural_sensors = [];
    const blob = fs.readFileSync(path.resolve(packageRoot, 'web/map-prototype', integrated.asset_url));
    const glb = JSON.parse(blob.subarray(20, 20 + blob.readUInt32LE(12)).toString('utf8'));
    for (const number of ['014', '015', '016', '017']) {
      const id = `AGRI_${number}_SENSOR`;
      await page.getByRole('searchbox', { name: '搜索设施', exact: true }).fill(id);
      await button(`测点 温度/流量测点 ${id}`).click();
      await page.waitForFunction(() => !m9.state.cameraPending);
      const nodes = [];
      const visit = index => { const node = glb.nodes[index]; if (node.mesh !== undefined) nodes.push(node);
        for (const child of node.children || []) visit(child); };
      visit(integrated.entity_nodes[id]);
      assert.equal(nodes.length, 37);
      const expectedVertices = nodes.reduce((sum, node) => sum + glb.meshes[node.mesh].primitives.reduce((n, primitive) =>
        n + glb.accessors[primitive.attributes.POSITION].count, 0), 0);
      const rendered = await page.evaluate(id => ({ batches: m9.objects[id].meshes.length,
        vertices: m9.objects[id].meshes.reduce((n, mesh) => n + mesh.geometry.attributes.position.count, 0) }), id);
      assert.ok(rendered.batches > 0);
      assert.equal(rendered.vertices, expectedVertices, `Batched geometry lost vertices for ${id}`);
      await page.waitForFunction(id => {
        const image = document.getElementById('model-preview');
        return image.src.endsWith(`/${id}.png`) && image.complete && image.naturalWidth === 900;
      }, id);
      assert.match(await page.locator('#detail').textContent(), /未接管/);
      const point = await page.evaluate(id => m9.projectModelVertices(id).find(p =>
        document.elementFromPoint(p[0], p[1])?.tagName === 'CANVAS' && m9.hitTest(p[0], p[1]) === id), id);
      assert.ok(point, `No visible canvas target for ${id}`);
      await page.mouse.click(point[0], point[1]);
      assert.equal(await page.evaluate(() => m9.state.selected), id);
      await page.keyboard.press('Escape');
      assert.equal(await page.evaluate(() => m9.state.selected), `AGRI_${number}`);
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#detail').isVisible(), false);
      receipt.checks.agricultural_sensors.push({ id, source_mesh_nodes: 37, rendered_batches: rendered.batches,
        vertices: rendered.vertices, image: 'decoded', canvas_pick: 'pass', exit: 'parent_then_closed' });
    }
    await page.screenshot({ path: path.join(output, 'package-sensors-final.png') });
  }
  receipt.errors.push(...await page.evaluate(() => [...m9.errors.map(e => `${e.operation}: ${e.message}`), ...m9BootErrors]));
  assert.deepEqual(receipt.errors, []);
  for (const [name, digest] of Object.entries(receipt.runtime_hashes)) assert.equal(hash(path.join(packageRoot, name)), digest, name);
  receipt.status = 'pass'; receipt.exit_code = 0;
} catch (error) { receipt.failure = error.stack; }
finally {
  await browser?.close();
  if (server && server.exitCode === null && server.signalCode === null) { const stopped = once(server, 'exit'); server.kill('SIGTERM'); await stopped; }
  fs.writeFileSync(path.join(output, 'package-browser-verification.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify({ status: receipt.status, checks: receipt.checks, failure: receipt.failure })); process.exitCode = receipt.exit_code;
}
