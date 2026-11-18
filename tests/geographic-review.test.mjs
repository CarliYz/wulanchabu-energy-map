import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { REVIEW_SOURCE } from '../web/map-prototype/geographic-review-source.mjs';
import { buildReviewObservations, validateReviewSources } from '../web/map-prototype/geographic-review.mjs';

const base = new URL('../web/map-prototype/', import.meta.url);
const report = JSON.parse(fs.readFileSync(new URL(REVIEW_SOURCE.report.url, base)));
const features = JSON.parse(fs.readFileSync(new URL(REVIEW_SOURCE.features.url, base)));

test('review keeps every route, anchor, pad and nearby feature without moving input geometry', () => {
  const original = JSON.stringify(report), rows = buildReviewObservations(report);
  assert.equal(new Set(rows.filter(r => r.scope === 'route').map(r => r.subjectId)).size, 22);
  assert.equal(new Set(rows.filter(r => r.scope === 'anchor').map(r => r.subjectId)).size, 12);
  assert.equal(new Set(rows.filter(r => r.scope === 'pad').map(r => r.subjectId)).size, 12);
  assert.equal(new Set(rows.map(r => r.id)).size, rows.length);
  for (const route of report.route_results) for (const [kind, result] of Object.entries(route.public_screening)) {
    for (const candidate of result.candidates) assert.ok(rows.some(r => r.subjectId === route.route_id && r.kind === kind && r.featureId === candidate.feature_id));
  }
  assert.equal(JSON.stringify(report), original);
});

test('C1 anchor and model-pad water observations stay distinct and are never called engineered crossings', () => {
  const rows = buildReviewObservations(report);
  const anchor = rows.find(r => r.subjectId === 'AGRI_018' && r.scope === 'anchor' && r.kind === 'waterbody');
  const pad = rows.find(r => r.subjectId === 'AGRI_018' && r.scope === 'pad' && r.featureId === 'relation/7763319');
  assert.equal(anchor.relation, 'outside'); assert.equal(anchor.distance, 6.262);
  assert.equal(pad.distance, 0); assert.match(pad.statusLabel, /相交/);
  assert.notEqual(anchor.id, pad.id);
  assert.ok(rows.find(r => r.subjectId === 'P2_V2_RETURN' && r.featureId === 'relation/7763319').statusLabel.includes('相交'));
  assert.equal(pad.engineeringStatus, 'blocked');
});

test('runtime review rejects changed model, route, missing water relation and untraceable feature', () => {
  const identity = { routes: report.source.route_input_sha256, asset: REVIEW_SOURCE.assetSha256 };
  assert.doesNotThrow(() => validateReviewSources(report, features, identity));
  assert.throws(() => validateReviewSources(report, features, { ...identity, routes: 'changed' }), /route/i);
  assert.throws(() => validateReviewSources(report, features, { ...identity, asset: 'changed' }), /model/i);
  const missing = structuredClone(features); missing.features = missing.features.filter(f => f.properties.id !== 'relation/7763319');
  assert.throws(() => validateReviewSources(report, missing, identity), /feature|count/i);
  const corrupt = structuredClone(features); corrupt.features[0].properties.source_sha256 = 'changed';
  assert.throws(() => validateReviewSources(report, corrupt, identity), /source/i);
});
