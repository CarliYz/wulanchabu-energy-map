import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { ROUTES_SHA256, createEnergyNetwork, flowCoordinates, routeStyle } from '../web/map-prototype/energy-network.mjs';
const bytes = readFileSync(new URL('../data/map-v2/routes.json', import.meta.url));
const routes = JSON.parse(bytes).routes;
const facilities = JSON.parse(readFileSync(new URL('../web/map-prototype/facility-registry.json', import.meta.url))).objects;
const network = createEnergyNetwork(routes, facilities);
test('关系绑定固定来源、22条线路及其具名端点', () => {
  assert.equal(createHash('sha256').update(bytes).digest('hex'), ROUTES_SHA256);
  assert.equal(network.routes.length, 22);
  for (const route of routes) {
    const result = network.describe(route.route_id);
    assert.equal(result.from.id, route.flow_from); assert.equal(result.to.id, route.flow_to);
    assert.notEqual(result.from.name, undefined); assert.notEqual(result.to.name, undefined);
    assert.equal(result.geometry_length_m, route.geometry_length_m);
  }
});
test('所有回水箭头从显式flow_from出发，原线点序不改', () => {
  for (const route of routes) {
    const before = JSON.stringify(route.sampled_xyz), coords = flowCoordinates(route);
    const expected = route.geometry_start_node === route.flow_from ? route.sampled_xyz[0] : route.sampled_xyz.at(-1);
    assert.deepEqual(coords[0], expected); assert.equal(JSON.stringify(route.sampled_xyz), before);
  }
  assert.equal(network.describe('AGRI_018_RETURN').to.kind, 'route');
  assert.equal(network.describe('P2_V2_RETURN').from.kind, 'interface');
});
test('A区一期说明隔离直供，不强制经过二期CO₂压缩机', () => {
  for (const id of ['AGRI_014','AGRI_015']) {
    assert.match(network.context(id).title, /一期/);
    assert.match(network.context(id).text, /不依赖二期/);
    assert.match(network.describe(id + '_SUPPLY').explanation, /只换热、不混水/);
  }
});
test('PTES_RETURN保留返回语义，充放支路不串联到全体用户', () => {
  assert.equal(routeStyle(routes.find(r => r.route_id === 'PTES_RETURN')), 'storage_return');
  assert.match(network.describe('PTES_RETURN').label, /返回枢纽/);
  assert.match(network.context('STORE_012').text, /放热.*待核/);
  assert.equal(network.describe('P2_V2_SUPPLY').from.id, 'HUB_011');
});
test('三个回路、电输入和独立科研边界可解释', () => {
  assert.match(network.context('HUB_011').text, /电输入/);
  assert.match(network.context('HUB_011').text, /CO₂ 不沿城市或农业管线输送/);
  assert.equal(network.related('DEMO_013').length, 0);
  assert.deepEqual(network.context('DEMO_013').links, []);
  assert.match(network.context('DRY_019').text, /45℃.*不能直接产生50–55℃/);
});
test('C1仍是后续预留，短支线长度不代表源端全程', () => {
  const route = network.describe('AGRI_018_SUPPLY');
  assert.equal(route.phase, 'future_candidate');
  assert.equal(route.geometry_length_m, 94.31950671212817);
  assert.match(network.context('AGRI_018').text, /一次侧仍预留未接/);
});
test('B区关系描述绑定本区设施，不继承C1营养液说明', () => {
  for (const id of ['AGRI_016','AGRI_017']) {
    const context=network.context(id);
    assert.match(context.title,/B 区/);assert.doesNotMatch(context.text,/C1|营养液/);
    assert.match(context.text,new RegExp(facilities.find(o=>o.object_id===id).name));
  }
});
test('未知端点、阶段与矛盾流向明确拒绝', () => {
  assert.throws(() => createEnergyNetwork([{...routes[0],flow_from:'missing'}],facilities),/Unbound/);
  assert.throws(() => createEnergyNetwork([{...routes[0],phase:'live'}],facilities),/Unknown route semantics/);
  assert.throws(() => flowCoordinates({...routes[0],geometry_start_node:'other'}),/mismatch/);
  assert.throws(() => network.describe('missing'),/Unknown route/);
});
