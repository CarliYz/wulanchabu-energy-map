import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateSystemGraph } from '../web/map-prototype/m10-graph.mjs';

const graph = () => JSON.parse(readFileSync(new URL('../web/map-prototype/m10-system-runtime.json', import.meta.url)));
const parents = JSON.parse(readFileSync(new URL('../web/map-prototype/facility-registry.json', import.meta.url))).objects.map(o => o.object_id);

test('candidate system accepts declared compatible ports', () => {
  assert.doesNotThrow(() => validateSystemGraph(graph(), parents));
});
test('missing endpoint cannot yield a ready system', () => {
  const data = graph(); data.connections[0].from_port_id = 'missing';
  assert.throws(() => validateSystemGraph(data, parents), /connection port missing/);
});
test('a water pipe cannot be connected to a power socket', () => {
  const data = graph(); const edge = data.connections.find(e => e.medium === 'water');
  data.ports.find(p => p.port_id === edge.to_port_id).medium = 'electricity';
  assert.throws(() => validateSystemGraph(data, parents), /incompatible connection/);
});
test('the viewer never accepts PTES as an executable controller', () => {
  const data = graph(); data.ptes.execution_allowed = true;
  assert.throws(() => validateSystemGraph(data, parents), /candidate mode invalid/);
});
