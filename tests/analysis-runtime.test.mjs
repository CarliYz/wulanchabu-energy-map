import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolveAnalysis } from '../web/map-prototype/analysis-runtime.mjs';

const bindings = JSON.parse(await readFile(new URL('../web/map-prototype/analysis-bindings.json', import.meta.url)));
const asset = JSON.parse(await readFile(new URL('../web/map-viewer/assets/analysis-results.json', import.meta.url)));

test('analysis binds the selected object, scenario, and hour', () => {
  const result = resolveAnalysis({ asset, bindings, objectId: 'AGRI_018', scenarioId: 'normal', hourIndex: 7 });
  assert.equal(result.status, 'available');
  assert.equal(result.row.hour_index, 7);
  assert.equal(result.time.hour_index, 7);
  assert.equal(result.time.basis, 'synthetic_teaching_not_local');
});

test('derived storage depletion chooses its first depleted hour when no hour is provided', () => {
  const result = resolveAnalysis({ asset, bindings, objectId: 'AGRI_018', scenarioId: 'storage-depleted' });
  assert.equal(result.status, 'available');
  assert.equal(result.row.hour_index, 5);
  assert.equal(result.scenario.derived, true);
});

test('unbound objects stay empty even when a valid hour is requested', () => {
  const result = resolveAnalysis({ asset, bindings, objectId: 'HUB_011', scenarioId: 'normal', hourIndex: 7 });
  assert.equal(result.status, 'unavailable');
  assert.match(result.reason, /没有绑定/);
});

test('invalid analysis hours are rejected explicitly', () => {
  const result = resolveAnalysis({ asset, bindings, objectId: 'AGRI_018', scenarioId: 'normal', hourIndex: 24 });
  assert.equal(result.status, 'invalid');
  assert.match(result.reason, /0–23/);
});
