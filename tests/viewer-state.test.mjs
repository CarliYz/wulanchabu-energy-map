import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { initialViewerState, transition, resultRequestKey } from '../web/map-viewer/viewer-state.mjs';

const objects = new Map(JSON.parse(readFileSync(new URL('../data/contracts/fixtures/objects.json', import.meta.url))).objects.map(x => [x.object_id, x]));
const results = JSON.parse(readFileSync(new URL('../data/contracts/fixtures/results.json', import.meta.url))).results;
const go = (s, type, args = {}) => transition(s, { type, ...args }, objects);

test('default state agrees with the schema-validated fixture', () => {
  const expected = JSON.parse(readFileSync(new URL('../data/contracts/fixtures/viewer-state.json', import.meta.url)));
  assert.deepEqual(initialViewerState(), expected);
});

test('tree/map selection uses exact object_id and preserves caller state', () => {
  const s = initialViewerState();
  const next = go(s, 'select', { objectId: 'AGRI_018', camera: { position: [1, 2, 3] } });
  assert.equal(next.selectedObjectId, 'AGRI_018');
  assert.equal(s.selectedObjectId, null);
  assert.equal(next.cameraHistory.length, 1);
  assert.throws(() => go(s, 'select', { objectId: 'some name' }), /Unknown object_id/);
});

test('view switching preserves selection, camera history and last real base view', () => {
  let s = go(initialViewerState(), 'select', { objectId: 'AGRI_018', camera: { position: [1, 2, 3] } });
  s = go(s, 'set-view', { mode: 'satellite' });
  s = go(s, 'set-view', { mode: 'data' });
  s = go(s, 'return-base');
  assert.equal(s.viewMode, 'satellite');
  assert.equal(s.selectedObjectId, 'AGRI_018');
  assert.equal(s.cameraHistory.length, 1);
});

test('late request cannot replace a new selection, scenario or reselect of same object', () => {
  let s = go(initialViewerState(), 'select', { objectId: 'AGRI_018' });
  s = go(s, 'request-results');
  const oldKey = resultRequestKey(s);
  for (const changed of [
    go(s, 'select', { objectId: 'HUB_011' }),
    go(s, 'set-analysis', { scenarioId: 'MVP_SOURCE_OUTAGE', time: { hour_index: 0, timestamp: null } }),
    go(go(s, 'close-selection'), 'select', { objectId: 'AGRI_018' }),
    go(s, 'request-results'),
  ]) {
    assert.strictEqual(go(changed, 'receive-results', { key: oldKey, rows: results }), changed);
    assert.strictEqual(go(changed, 'fail-results', { key: oldKey }), changed);
  }
});

test('C1 shows missing inputs and never falls back to unbound synthetic results', () => {
  let s = go(initialViewerState(), 'select', { objectId: 'AGRI_018' });
  s = go(s, 'request-results');
  s = go(s, 'receive-results', { key: resultRequestKey(s), rows: results });
  assert.equal(s.resultStatus, 'missing_inputs');
  assert.equal(s.objectResults.length, 1);
  assert.equal(s.objectResults[0].metrics[0].value, null);
});

test('Escape exits exactly one layer in defined order and leaves view intact', () => {
  let s = go(initialViewerState(), 'select', { objectId: 'AGRI_018' });
  s = go(s, 'set-tab', { tab: 'relations' });
  s = go(s, 'set-index', { expanded: true });
  s = go(s, 'set-search', { query: 'C1' });
  s = go(s, 'set-tool', { mode: 'pan' });
  for (const overlay of ['analysis', 'layers', 'audit', 'image']) s = go(s, 'open-overlay', { overlay });
  for (const remaining of [['analysis', 'layers', 'audit'], ['analysis', 'layers'], ['analysis']]) {
    s = go(s, 'escape'); assert.deepEqual(s.overlayStack, remaining);
  }
  s = go(s, 'escape'); assert.equal(s.detailTab, 'properties'); assert.equal(s.selectedObjectId, 'AGRI_018');
  s = go(s, 'escape'); assert.equal(s.selectedObjectId, null);
  s = go(s, 'escape'); assert.deepEqual(s.overlayStack, []);
  s = go(s, 'escape'); assert.equal(s.search, ''); assert.equal(s.indexExpanded, true);
  s = go(s, 'escape'); assert.equal(s.indexExpanded, false);
  s = go(s, 'escape'); assert.equal(s.toolMode, 'free'); assert.equal(s.viewMode, 'standard');
});

test('hiding a selected layer clears stale object data', () => {
  let s = go(initialViewerState(), 'select', { objectId: 'AGRI_018' });
  s = go(s, 'set-layer', { layer: 'agriculture', visible: false, hiddenObjectIds: ['AGRI_018'] });
  assert.equal(s.selectedObjectId, null);
  assert.deepEqual(s.objectResults, []);
});

test('analysis without an identity or time is explicitly rejected', () => {
  assert.throws(() => go(initialViewerState(), 'set-analysis', {
    scenarioId: 'MVP_NORMAL', time: { hour_index: null, timestamp: null },
  }), /Analysis time/);
  for (const hour of [-1, Infinity, 1.5, undefined]) {
    assert.throws(() => go(initialViewerState(), 'set-analysis', {
      scenarioId: 'MVP_NORMAL', time: { hour_index: hour, timestamp: '2026-11-16T00:00:00Z' },
    }), /Analysis time/);
  }
  for (const stamp of ['invalid', '2026-02-31T00:00:00Z', undefined]) {
    assert.throws(() => go(initialViewerState(), 'set-analysis', {
      scenarioId: 'MVP_NORMAL', time: { hour_index: 0, timestamp: stamp },
    }), /Analysis time/);
  }
});
