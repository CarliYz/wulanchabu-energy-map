import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const runtime = JSON.parse(readFileSync(new URL('../web/map-prototype/ab-terminal-runtime.json', import.meta.url)));
const glb = readFileSync(new URL(runtime.asset_url, new URL('../web/map-prototype/', import.meta.url)));

test('A/B runtime contract matches the exported GLB and candidate counts', () => {
  assert.equal(runtime.asset_sha256, createHash('sha256').update(glb).digest('hex'));
  assert.equal(runtime.asset_format, 'glTF Binary v2');
  assert.equal(runtime.objects.length, 32);
  assert.equal(runtime.ports.length, 60);
  assert.equal(runtime.connections.length, 60);
  assert.deepEqual(runtime.parent_facilities.map(item => item.object_id), ['AGRI_014', 'AGRI_015', 'AGRI_016', 'AGRI_017']);
  assert(runtime.objects.every(item => item.installation_status.includes('候选规划')));
  assert(runtime.connections.every(item => item.status === 'candidate_unverified'));
  assert(runtime.zones.every(item => Object.values(item.semantic_root_nodes).every(value => Number.isInteger(value))));
});

test('A/B connection endpoints resolve to declared ports and entities', () => {
  const objectIds = new Set(runtime.objects.map(item => item.object_id));
  const portIds = new Set(runtime.ports.map(item => item.port_id));
  for (const connection of runtime.connections) {
    assert(objectIds.has(connection.from_object_id));
    assert(objectIds.has(connection.to_object_id));
    assert(portIds.has(connection.from_port_id));
    assert(portIds.has(connection.to_port_id));
  }
});
