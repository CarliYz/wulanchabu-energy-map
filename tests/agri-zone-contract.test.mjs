import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const graph = JSON.parse(readFileSync(new URL('../web/map-prototype/ab-terminal-runtime.json', import.meta.url)));

// Original plan: A1 potatoes, A2 mushrooms, B1 tomatoes, B2 strawberries.
test('agricultural terminals belong to the original plan facility and zone', () => {
  const expected = { AGRI_014: 'A区', AGRI_015: 'A区', AGRI_016: 'B区', AGRI_017: 'B区' };
  for (const [id, zone] of Object.entries(expected)) {
    assert.equal(graph.parent_facilities.find(p => p.object_id === id)?.zone, zone, id);
    assert(graph.objects.some(o => o.parent_id === id && o.kind === 'terminal'), `${id} has no terminal`);
  }
});

test('mushroom AHUs never describe tomato or strawberry loads', () => {
  const loads = graph.objects.filter(o => o.parent_id === 'AGRI_015' && o.kind === 'terminal');
  assert.equal(loads.length, 2);
  for (const load of loads) {
    assert.match(load.name, /菌房/);
    assert.doesNotMatch(load.name + load.zone_label, /番茄|草莓|B区/);
  }
});
