import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import * as projection from './projection.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(root, 'qc/m9-map');
fs.mkdirSync(output, { recursive: true });
const read = name => fs.readFileSync(path.join(root, name));
const json = name => JSON.parse(read(name));
const sha = name => createHash('sha256').update(read(name)).digest('hex');
const receipt = { command: 'node web/map-prototype/validate.mjs', cwd: root, date: new Date().toISOString(),
  expected_base: '436e65e93c31b9909ec652a73e1ec232769fef6a', checks: {}, limitations: [
    'Conversion self-checks are not independent georegistration.',
    'No independent identifiable control points acquired; C1 water-overlap uncertainty remains.',
    'Relative orthometric height only; no verified geoid-to-ellipsoid conversion.',
    'Candidate route is a 2D overlay, not terrain-draped engineering routing; road offsets/crossings not measured.',
    'C1 c1-dual-loop-v1 replaces the legacy C1 block in this prototype only; no production UI integration, hydraulic calculation or object thermal potential.'
  ] };
function command(cmd, args) {
  const result = spawnSync(cmd, args, { cwd: root, encoding: 'utf8' });
  return { command: [cmd, ...args], exit_code: result.status, stdout: result.stdout, stderr: result.stderr,
    error: result.error?.message };
}
receipt.identity = command('git', ['rev-parse', 'HEAD']);
receipt.branch = command('git', ['branch', '--show-current']);
receipt.tested_head = receipt.identity.stdout.trim();
const identities = ['docs/UI_DESIGN_PLAN_V2.md', 'data/contracts/coordinate-contract.json',
  'data/map-v2/geographic-manifest.json', 'data/map-v2/routes.json', 'data/contracts/fixtures/objects.json',
  'design/m7/README.md', 'web/map-viewer/assets/乌兰察布_真实地理场景_v2.glb',
  'web/map-prototype/app.mjs', 'web/map-prototype/projection.mjs', 'web/map-prototype/index.html',
  'web/map-viewer/assets/c1-v1/AGRI_018.glb', 'web/map-viewer/assets/c1-v1/overview.png',
  'design/m7/map-assets/standard-base.png', 'web/map-prototype/style.css', 'web/map-prototype/asset-bindings.json', 'web/map-prototype/package.json',
  'web/map-prototype/serve.py', 'web/map-prototype/validate.mjs'];
receipt.sha256 = Object.fromEntries(identities.map(p => [p, sha(p)]));
receipt.syntax = ['app.mjs', 'projection.mjs', 'validate.mjs'].map(p => command('node', ['--check', `web/map-prototype/${p}`]));
try {
  assert.equal(command('git',['merge-base','--is-ancestor',receipt.expected_base,receipt.tested_head]).exit_code,0);
  assert(['codex/energy-m9-runtime','codex/energy-map-v2'].includes(receipt.branch.stdout.trim()));
  assert(receipt.syntax.every(r => r.exit_code === 0));
  const contract = json('data/contracts/coordinate-contract.json'), geo = json('data/map-v2/geographic-manifest.json');
  assert.deepEqual(contract.origin_utm_egm2008_m, projection.ORIGIN);
  assert.deepEqual(projection.glbToLocal([1, 2, 3]), [1, -3, 2]);
  const binding = json('web/map-prototype/asset-bindings.json');
  assert.equal(binding.sha256, receipt.sha256['web/map-viewer/assets/乌兰察布_真实地理场景_v2.glb']);
  const glb = read('web/map-viewer/assets/乌兰察布_真实地理场景_v2.glb');
  const document = JSON.parse(glb.subarray(20, 20 + glb.readUInt32LE(12)).toString());
  const sceneNodes = new Set(document.scenes[binding.scene_index].nodes);
  for (const value of Object.values(binding.objects)) {
    value.node_indices.forEach((index, i) => { assert(sceneNodes.has(index)); assert.equal(document.nodes[index].name, value.node_names[i]); });
  }
  assert.equal(binding.objects.AGRI_018.replacement.sha256, sha('web/map-viewer/assets/c1-v1/AGRI_018.glb'));
  receipt.checks.identity_axis_bindings_syntax = 'pass';
  // The tolerance was set before browser/registration measurements. It is numerical only.
  receipt.numerical_tolerance_m = .01;
  receipt.conversion_checks = contract.projection_self_checks.map(control => {
    const forward = projection.forward(control.lonlat), reverse = projection.inverse(control.utm);
    const back = projection.forward(reverse);
    const forward_error_m = Math.hypot(...forward.map((v, i) => v - control.utm[i]));
    const roundtrip_error_m = Math.hypot(...back.map((v, i) => v - control.utm[i]));
    assert(forward_error_m < .01 && roundtrip_error_m < .01);
    return { input: control, forward_error_m, roundtrip_error_m, independent: false };
  });
  receipt.axes_1m = [[0, 0, 0], ...['HUB_011', 'AGRI_018'].map(id => geo.features.find(f => f.id === id).xyz)].map(local => {
    const origin = projection.localToWorld(local);
    const axes = [[1, 0, 0], [0, 1, 0], [0, 0, 1]].map(delta => {
      const vertex = projection.localToWorld(local.map((v, i) => v + delta[i]));
      return vertex.map((v, i) => v - origin[i]);
    });
    return { local, lonlat: projection.localToLonLat(local), axes_mercator_origin_m: axes,
      mercator_grid_north_angle_degrees: Math.atan2(axes[1][0], -axes[1][1]) * 180 / Math.PI };
  });
  const origin = projection.localToWorld([0, 0, 0]);
  const east = projection.localToWorld([1, 0, 0]).map((v, i) => v - origin[i]);
  const north = projection.localToWorld([0, 1, 0]).map((v, i) => v - origin[i]);
  const samples = [geo.features.find(f => f.id === 'AGRI_018').xyz,
    ...[[geo.utm_bounds[0], geo.utm_bounds[1]], [geo.utm_bounds[2], geo.utm_bounds[3]]]
      .map(p => [p[0] - projection.ORIGIN[0], p[1] - projection.ORIGIN[1], 0])];
  receipt.global_affine_residuals_m = samples.map(local => {
    const exact = projection.localToWorld(local);
    return { local, horizontal_residual_m: Math.hypot(...[0, 1].map(i => exact[i] - (origin[i] + east[i] * local[0] + north[i] * local[1]))) };
  });
  receipt.checks.projection_self_check = 'pass';
} catch (error) {
  receipt.checks.local_validation = 'fail'; receipt.local_error = error.stack;
}
receipt.checks.independent_registration = 'not_run';
receipt.independent_control_points = [];
receipt.registration_tolerance_m = null;
receipt.registration_tolerance_reason = 'No independent controls or their accuracy; no engineering tolerance inferred from a 40m mesh.';
receipt.checks.browser = 'not_run';
receipt.browser = { url: 'http://127.0.0.1:8767/web/map-prototype/', screenshots: [], console_errors: [], console_warnings: [], page_errors: [], request_failures: [] };
let browser;
try {
  const candidates = [process.env.M9_PLAYWRIGHT_MODULE,
    '/Users/ianlee/Documents/ChatGPT/ai工程/energy-innovation-3d/qa/node_modules/playwright',
    '/path/to/wulanchabu-energy-map/qa/node_modules/playwright',
    '/path/to/wulanchabu-energy-map/node_modules/playwright'].filter(Boolean);
  const modulePath = candidates.find(p => fs.existsSync(path.join(p, 'package.json')));
  if (!modulePath) throw new Error('Existing main-repo Playwright module not found; set M9_PLAYWRIGHT_MODULE');
  const require = createRequire(import.meta.url), playwright = require(modulePath);
  receipt.browser.playwright_module = modulePath;
  receipt.browser.playwright_version = require(path.join(modulePath, 'package.json')).version;
  browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('console', msg => { if (msg.type() === 'error') receipt.browser.console_errors.push(msg.text()); if(msg.type()==='warning')receipt.browser.console_warnings.push(msg.text()); });
  page.on('pageerror', error => receipt.browser.page_errors.push(error.message));
  page.on('requestfailed', request => receipt.browser.request_failures.push({ url: request.url(), error: request.failure() }));
  await page.goto(receipt.browser.url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForFunction(() => window.m9?.state.ready && window.m9.snapshot().renderedFrames > 0, null, { timeout: 45000 });
  await page.locator('[data-select="AGRI_018"]').click();
  await page.waitForFunction(() => !m9.state.cameraPending);
  assert.equal(await page.locator('#detail-id').innerText(), 'AGRI_018');
  receipt.browser.slices = [];
  for (const pitch of [0, 45]) for (const zoom of [12.5, 14, 16]) {
    await page.evaluate(({ pitch, zoom }) => window.m9.map.jumpTo({ pitch, zoom }), { pitch, zoom });
    const before = await page.evaluate(() => window.m9.snapshot());
    const canvasHashes = [];
    for (const view of ['standard', 'satellite', 'data']) {
      await page.locator(`[data-view="${view}"]`).click();
      await page.evaluate(() => new Promise(resolve => { window.m9.map.once('render', resolve); window.m9.map.triggerRepaint(); }));
      const after = await page.evaluate(() => window.m9.snapshot());
      for (const property of ['center', 'zoom', 'pitch', 'bearing', 'selected', 'anchors']) assert.deepEqual(after[property], before[property]);
      assert.equal(after.terrainVisible, view !== 'standard');
      assert(after.rendererCalls > 0);
      const canvas = await page.evaluate(() => window.m9.map.getCanvas().toDataURL());
      canvasHashes.push(createHash('sha256').update(canvas).digest('hex'));
      receipt.browser.slices.push({ view, pitch, zoom, snapshot: after });
      if (pitch === 45 && zoom === 14) {
        const screenshot = `browser-${view}.png`;
        await page.screenshot({ path: path.join(output, screenshot) }); receipt.browser.screenshots.push(screenshot);
      }
    }
    assert.equal(new Set(canvasHashes).size, 3, 'The actual map canvas must change between all three views');
  }
  await page.locator('#return-view').click();
  assert.equal((await page.evaluate(() => window.m9.snapshot())).view, 'satellite');
  const camera = await page.evaluate(() => window.m9.snapshot());
  await page.keyboard.press('Escape');
  assert(await page.locator('#detail').isHidden());
  assert.equal(await page.evaluate(() => window.m9.state.selected), null);
  assert.deepEqual((await page.evaluate(() => window.m9.snapshot())).center, camera.center);
  // Same-ID entrance through a visible map label, then exercise close and actual mesh raycast.
  await page.locator('[data-object-id="AGRI_018"]').click();
  await page.waitForFunction(() => !m9.state.cameraPending);
  assert.equal(await page.locator('#detail-id').innerText(), 'AGRI_018');
  const points = await page.evaluate(() => window.m9.projectModelVertices('AGRI_018'));
  const modelPoint = [0, 1].map(axis => (Math.min(...points.map(p => p[axis])) + Math.max(...points.map(p => p[axis]))) / 2);
  assert(modelPoint, 'Whole-facility focus must leave real model vertices in the unobstructed map');
  assert(points.every(([x, y]) => x > 250 && x < 1050 && y > 160 && y < 780),
    'Every sampled mesh vertex must fit safely outside the panels');
  receipt.browser.visible_model_measurement = { sampled_vertices: points.length, visible_point: modelPoint,
    min: [Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1]))],
    max: [Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1]))], independent_georegistration: false };
  await page.locator('#close').click();
  await page.mouse.click(...modelPoint);
  await page.waitForFunction(() => !m9.state.cameraPending);
  assert.equal(await page.locator('#detail-id').innerText(), 'AGRI_018');
  assert(await page.locator('#detail').isVisible());
  await page.locator('#models').uncheck();
  assert.equal(await page.evaluate(() => window.m9.state.selected), null);
  assert(await page.locator('[data-object-id="AGRI_018"]').isHidden());
  await page.locator('#models').check();
  receipt.browser.responsive = [];
  for (const size of [{width:1440,height:1000},{width:1100,height:900},{width:760,height:900}]) {
    await page.setViewportSize(size);
    await page.locator('[data-select="AGRI_018"]').click();
    await page.evaluate(() => new Promise(resolve => {m9.map.once('render',resolve);m9.map.triggerRepaint()}));
    await page.waitForFunction(() => !m9.state.cameraPending);
    const bounds = await page.locator('#detail').boundingBox();
    const vertices = await page.evaluate(() => m9.projectModelVertices('AGRI_018'));
    assert(bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= size.width && bounds.y + bounds.height <= size.height);
    const headerBottom=await page.locator('header').evaluate(el=>el.getBoundingClientRect().bottom);
    const clear = vertices.every(([x,y]) => x > (size.width <= 850 ? 12 : 232) && x < (size.width <= 850 ? size.width - 12 : bounds.x) && y > headerBottom+12 && y < (size.width <= 850 ? bounds.y : size.height - 160));
    if(!clear){receipt.browser.responsive_failure={size,bounds,min:[0,1].map(i=>Math.min(...vertices.map(p=>p[i]))),max:[0,1].map(i=>Math.max(...vertices.map(p=>p[i])))};await page.screenshot({path:path.join(output,'responsive-failure.png')});}
    assert(clear, `Whole model must remain clear of panels at ${size.width}`);
    await page.keyboard.press('Escape');
    assert(await page.locator('#detail').isHidden());
    assert(await page.locator('[data-select="AGRI_018"]').evaluate(el => el === document.activeElement));
    receipt.browser.responsive.push({viewport:size,detail:bounds,whole_model_clear:clear,escape:'pass'});
  }
  assert.deepEqual(await page.evaluate(() => window.m9BootErrors), []);
  assert.deepEqual(receipt.browser.page_errors, []);
  assert.deepEqual(receipt.browser.console_errors, []);
  assert(!receipt.browser.console_warnings.some(m=>m.includes('GL_INVALID_FRAMEBUFFER_OPERATION')));
  receipt.checks.browser = 'pass';
  // Corrupt the actual GLB response: loading must fail visibly before parsing.
  const broken = await browser.newPage({viewport:{width:1440,height:1000}});
  await broken.route('**/c1-v1/AGRI_018.glb', async route => {
    const bytes=Buffer.from(read('web/map-viewer/assets/c1-v1/AGRI_018.glb'));bytes[bytes.length-1]^=1;
    await route.fulfill({status:200,contentType:'model/gltf-binary',body:bytes});
  });
  await broken.goto(receipt.browser.url);
  await broken.waitForFunction(() => document.getElementById('status').textContent.includes('加载失败'));
  assert.match(await broken.locator('#errors').innerText(), /GLB identity changed/);
  assert.equal(await broken.evaluate(() => window.m9?.state.ready ?? false),false);
  assert(await broken.locator('#detail').isHidden());
  receipt.browser.corrupt_asset_failure = {status:'pass',ready:false,message:await broken.locator('#errors').innerText()};
  await broken.close();
} catch (error) {
  receipt.checks.browser = /Permission denied|Operation not permitted|not found|ERR_CONNECTION_REFUSED|Target page.*closed/.test(error.message) ? 'blocked' : 'fail';
  receipt.browser.error = error.stack;
} finally { if (browser) await browser.close(); }
const failed = Object.values(receipt.checks).includes('fail');
receipt.status = failed ? 'fail' : receipt.checks.browser === 'pass' ? 'pass_with_registration_not_run' : 'blocked';
receipt.exit_code = failed ? 1 : receipt.checks.browser === 'pass' ? 0 : 2;
fs.writeFileSync(path.join(output, 'validation.json'), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt, null, 2));
process.exitCode = receipt.exit_code;
