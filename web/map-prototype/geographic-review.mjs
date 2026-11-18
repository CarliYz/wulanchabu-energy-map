import { REVIEW_SOURCE } from './geographic-review-source.mjs';
import { localToLonLat } from './projection.mjs';

const kinds = { highway: '道路', railway: '铁路', waterway: '线状水域', waterbody: '水体面' };
const scopes = { route: '候选线路', anchor: '设施锚点', pad: '模型场坪' };
const empty = () => ({ type: 'FeatureCollection', features: [] });
const feature = (geometry, properties = {}) => ({ type: 'Feature', geometry, properties });
const featureKey = row => `${row.kind}/${row.featureId}`;

export function buildReviewObservations(report) {
  const rows = [];
  function add(subjectId, subjectName, scope, screening) {
    for (const [kind, result] of Object.entries(screening)) {
      const observations = new Map();
      if (result.nearest) observations.set(result.nearest.feature_id, result.nearest);
      for (const candidate of result.candidates) observations.set(candidate.feature_id, candidate);
      for (const point of observations.values()) {
        const intersects = point.relation !== 'outside', near = point.distance_m <= result.threshold_m;
        rows.push({ id: `${scope}/${subjectId}/${kind}/${point.feature_id}`, subjectId, subjectName, scope, kind,
          featureId: point.feature_id, featureName: point.tags.name || point.tags.ref || kinds[kind],
          tags: point.tags, relation: point.relation, distance: point.distance_m, boundaryDistance: point.boundary_distance_m,
          position: point.route_position, featurePosition: point.feature_position, sourceSha256: point.source_sha256,
          statusLabel: intersects ? '公开几何相交 / 包含' : near ? '30m 内邻近' : '30m 内未检出',
          priority: intersects ? (scope === 'pad' ? 0 : kind === 'waterbody' ? 1 : 2) : near ? 3 : 4,
          engineeringStatus: result.engineering_status });
      }
    }
  }
  for (const row of report.route_results) add(row.route_id, row.route_id, 'route', row.public_screening);
  for (const row of report.facility_results) {
    add(row.object_id, row.name, 'anchor', row.public_screening);
    add(row.object_id, row.name, 'pad', { waterbody: row.display_pad.waterbody });
  }
  return rows.sort((a, b) => a.priority - b.priority || a.distance - b.distance || a.id.localeCompare(b.id));
}

export function validateReviewSources(report, features, identity) {
  if (report.source.route_input_sha256 !== identity.routes) throw new Error('Geographic review route identity mismatch');
  if (REVIEW_SOURCE.assetSha256 !== identity.asset) throw new Error('Geographic review model identity mismatch');
  if (report.route_results.length !== 22 || report.facility_results.length !== 12) throw new Error('Geographic review subject count mismatch');
  const keys = new Set();
  for (const item of features.features) {
    const props = item.properties, key = `${props.kind}/${props.id}`;
    if (keys.has(key)) throw new Error(`Duplicate public feature: ${key}`);
    keys.add(key);
    if (props.source_sha256 !== report.source.snapshots[props.kind]?.sha256) throw new Error(`Public source identity mismatch: ${key}`);
  }
  for (const [kind, snapshot] of Object.entries(report.source.snapshots)) {
    if (features.features.filter(item => item.properties.kind === kind).length !== snapshot.elements) throw new Error(`Public feature count mismatch: ${kind}`);
  }
  for (const row of buildReviewObservations(report)) {
    if (!keys.has(featureKey(row))) throw new Error(`Missing public feature: ${featureKey(row)}`);
    if (row.sourceSha256 !== report.source.snapshots[row.kind].sha256) throw new Error(`Observation source identity mismatch: ${row.id}`);
    if (![...row.position, ...row.featurePosition].every(Number.isFinite)) throw new Error(`Invalid observation coordinate: ${row.id}`);
  }
}

export function createGeographicReview({ map, json, identity, state, trace, fail, currentView, safeArea, suspend, resume }) {
  const $ = id => document.getElementById(id);
  let report, rows = [], features, entryView, listView, entryFocus, listScroll = 0, loading;
  const layerIds = [];
  const groups = () => ({ highway: $('geo-roads').checked, railway: $('geo-rail').checked,
    waterway: $('geo-water').checked, waterbody: $('geo-water').checked });
  function addLayer(layer, before) { map.addLayer(layer, before); layerIds.push(layer.id); }
  function initializeLayers() {
    if (map.getSource('public-review')) return;
    map.addSource('public-review', { type: 'geojson', data: features });
    const pads = report.facility_results.map(row => feature({ type: 'Polygon', coordinates: [row.display_pad.ring_local_xy.map(localToLonLat)] }, { subjectId: row.object_id }));
    map.addSource('review-pads', { type: 'geojson', data: { type: 'FeatureCollection', features: pads } });
    map.addSource('review-points', { type: 'geojson', data: { type: 'FeatureCollection', features: rows.map(row => feature({ type: 'Point', coordinates: row.position }, { id: row.id, kind: row.kind, priority: row.priority })) } });
    map.addSource('review-highlight', { type: 'geojson', data: empty() });
    map.addSource('review-focus', { type: 'geojson', data: empty() });
    addLayer({ id: 'review-water-fill', type: 'fill', source: 'public-review', filter: ['==', ['get', 'kind'], 'waterbody'], paint: { 'fill-color': '#3b9ec3', 'fill-opacity': .25 } }, 'route-outline');
    for (const [kind, color, width] of [['highway', '#596d76', 2], ['railway', '#86688f', 3], ['waterway', '#2785aa', 3], ['waterbody', '#2785aa', 2]]) {
      addLayer({ id: `review-${kind}`, type: 'line', source: 'public-review', filter: ['==', ['get', 'kind'], kind], paint: { 'line-color': color, 'line-width': width, 'line-opacity': .85 } }, 'route-outline');
    }
    addLayer({ id: 'review-pads', type: 'line', source: 'review-pads', paint: { 'line-color': '#aa5e43', 'line-width': 2, 'line-dasharray': [3, 2] } });
    addLayer({ id: 'review-points', type: 'circle', source: 'review-points', paint: { 'circle-radius': 5, 'circle-color': ['case', ['<', ['get', 'priority'], 3], '#b7563c', '#387a99'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } });
    addLayer({ id: 'review-highlight', type: 'line', source: 'review-highlight', paint: { 'line-color': '#b04b30', 'line-width': 5, 'line-opacity': .95 } });
    addLayer({ id: 'review-focus-line', type: 'line', source: 'review-focus', filter: ['==', ['geometry-type'], 'LineString'], paint: { 'line-color': '#b04b30', 'line-width': 3, 'line-dasharray': [2, 2] } });
    addLayer({ id: 'review-focus-point', type: 'circle', source: 'review-focus', filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-radius': 9, 'circle-color': '#f7d493', 'circle-stroke-color': '#963e2a', 'circle-stroke-width': 3 } });
  }
  function updateLayers() {
    const allowed = groups(), visible = state.reviewOpen;
    for (const id of layerIds) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
    if (!layerIds.length) return;
    for (const kind of Object.keys(kinds)) map.setLayoutProperty(`review-${kind}`, 'visibility', visible && allowed[kind] ? 'visible' : 'none');
    map.setLayoutProperty('review-water-fill', 'visibility', visible && allowed.waterbody ? 'visible' : 'none');
    map.setFilter('review-points', ['in', ['get', 'kind'], ['literal', Object.keys(kinds).filter(kind => allowed[kind])]]);
    map.setLayoutProperty('review-pads', 'visibility', visible && allowed.waterbody ? 'visible' : 'none');
  }
  function clearHighlight() {
    state.reviewObservation = null;
    map.getSource('review-highlight')?.setData(empty()); map.getSource('review-focus')?.setData(empty());
    $('geo-list-view').hidden = false; $('geo-observation').hidden = true;
  }
  function renderList() {
    const query = $('geo-search').value.trim().toLowerCase(), kind = $('geo-kind').value, allowed = groups();
    const filtered = rows.filter(row => allowed[row.kind] && (kind === 'all' || row.kind === kind) &&
      `${row.subjectId} ${row.subjectName} ${row.featureId} ${row.featureName} ${scopes[row.scope]}`.toLowerCase().includes(query));
    $('geo-count').textContent = `${filtered.length} / ${rows.length} 条观察 · 22 条线 / 12 个设施 / 12 个场坪`;
    $('geo-list').replaceChildren(...filtered.map(row => {
      const button = document.createElement('button'); button.dataset.observation = row.id;
      button.setAttribute('aria-label', `定位复核 ${row.id}`);
      const title = document.createElement('span'); title.textContent = `${row.subjectId} · ${scopes[row.scope]} / ${kinds[row.kind]}`;
      const copy = document.createElement('small'); copy.textContent = `${row.featureName} · ${row.statusLabel} · ${row.distance.toFixed(1)}m`;
      button.append(title, copy); button.onclick = () => select(row.id); return button;
    }));
    $('geo-empty').hidden = filtered.length > 0;
  }
  async function load() {
    $('geo-load-state').textContent = '正在校验公开复核数据…'; $('geo-retry').hidden = true;
    try {
      const [data, geometry] = await Promise.all([json(REVIEW_SOURCE.report.url, REVIEW_SOURCE.report.sha256), json(REVIEW_SOURCE.features.url, REVIEW_SOURCE.features.sha256)]);
      await Promise.all([json('./facility-registry.json', data.source.facility_registry_sha256),
        json('../../data/map-v2/geographic-manifest.json', data.source.geographic_manifest_sha256)]);
      validateReviewSources(data, geometry, identity);
      report = data; features = geometry; rows = buildReviewObservations(data); initializeLayers(); updateLayers(); renderList();
      $('geo-load-state').textContent = `2026-11-17 OSM 快照 · ${features.features.length} 个地物 · 28 个水体（含 3 个关系）`;
      trace('reviewLoad', { outcome: 'pass', features: features.features.length, observations: rows.length });
    } catch (error) {
      fail('review/load', error); $('geo-load-state').textContent = `复核数据不可用：${error.message}`;
      $('geo-retry').hidden = false; trace('reviewLoad', { outcome: 'fail', message: error.message });
    } finally { loading = null; }
  }
  function focusRow(row) {
    const area = safeArea(), panel = $('geo-panel').getBoundingClientRect();
    const right = innerWidth <= 850 ? area.right : Math.min(area.right, panel.left - 20);
    const bottom = innerWidth <= 850 ? Math.min(area.bottom, panel.top - 16) : area.bottom;
    map.setCenterElevation(0);
    const bounds = [0, 1].map(index => [Math.min(row.position[index], row.featurePosition[index]), Math.max(row.position[index], row.featurePosition[index])]);
    map.fitBounds([[bounds[0][0], bounds[1][0]], [bounds[0][1], bounds[1][1]]], { duration: 0, maxZoom: 17, pitch: 0, bearing: 0,
      padding: { top: area.top + 10, bottom: innerHeight - bottom + 10, left: area.left + 10, right: innerWidth - right + 10 } });
    trace('reviewFocus', { observation: row.id, position: row.position });
  }
  function select(id) {
    const row = rows.find(row => row.id === id); if (!row) throw new Error(`Unknown review observation ${id}`);
    if (!state.reviewObservation) { listView = currentView(); listScroll = $('geo-list').scrollTop; }
    state.reviewObservation = id; $('geo-list-view').hidden = true; $('geo-observation').hidden = false;
    $('geo-title').textContent = `${row.subjectId} · ${scopes[row.scope]}`;
    const values = [['对象', row.subjectName], ['公开地物', `${row.featureName} · ${row.featureId}`], ['观察结果', row.statusLabel],
      ['最短距离', `${row.distance.toFixed(3)} m（近似）`], ['距边界', `${row.boundaryDistance.toFixed(3)} m（近似）`],
      ['观察位置', row.position.map(x => x.toFixed(7)).join(', ')], ['几何关系', row.relation],
      ['范围', `${scopes[row.scope]}；模型场坪不是现场建筑占地`], ['工程判定', 'blocked · 独立测量与工程核验未执行'],
      ['数据日期', report.source.retrieved_at], ['来源 SHA256', row.sourceSha256],
      ['地物标签', Object.entries(row.tags).map(([key, value]) => `${key}=${value}`).join(' · ')]];
    $('geo-properties').replaceChildren(...values.flatMap(([key, value]) => {
      const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = key; dd.textContent = value; return [dt, dd];
    }));
    const selectedFeature = features.features.find(f => `${f.properties.kind}/${f.properties.id}` === featureKey(row));
    const highlighted = [selectedFeature];
    if (row.scope === 'pad') highlighted.push(feature({ type: 'Polygon', coordinates: [report.facility_results.find(f => f.object_id === row.subjectId).display_pad.ring_local_xy.map(localToLonLat)] }));
    map.getSource('review-highlight').setData({ type: 'FeatureCollection', features: highlighted });
    map.getSource('review-focus').setData({ type: 'FeatureCollection', features: [feature({ type: 'Point', coordinates: row.position }), feature({ type: 'LineString', coordinates: [row.position, row.featurePosition] })] });
    focusRow(row); $('geo-back').focus(); trace('reviewSelect', { observation: id });
  }
  function back() {
    const old = state.reviewObservation; clearHighlight();
    if (listView) map.jumpTo(listView);
    $('geo-list').scrollTop = listScroll;
    [...$('geo-list').querySelectorAll('button')].find(button => button.dataset.observation === old)?.focus();
    trace('reviewBack');
  }
  function close({ restoreView = true, restoreFocus = true } = {}) {
    if (!state.reviewOpen) return;
    clearHighlight(); state.reviewOpen = false; updateLayers(); $('geo-panel').hidden = true;
    $('geo-toggle').setAttribute('aria-expanded', 'false'); resume();
    if (restoreView && entryView) map.jumpTo(entryView);
    if (restoreFocus) (entryFocus?.isConnected ? entryFocus : $('geo-toggle')).focus();
    trace('reviewClose', { restoreView });
  }
  async function open() {
    if (state.reviewOpen) { close(); return; }
    entryView = currentView(); entryFocus = document.activeElement; suspend();
    state.reviewOpen = true; $('geo-panel').hidden = false; $('geo-toggle').setAttribute('aria-expanded', 'true');
    clearHighlight(); updateLayers(); $('geo-search').focus(); trace('reviewOpen');
    if (!report) { loading ||= load(); await loading; }
  }
  $('geo-toggle').onclick = open; $('geo-close').onclick = () => close(); $('geo-back').onclick = back;
  $('geo-refocus').onclick = () => focusRow(rows.find(row => row.id === state.reviewObservation));
  $('geo-retry').onclick = () => { loading ||= load(); };
  $('geo-search').oninput = renderList; $('geo-kind').onchange = renderList;
  $('geo-clear-search').onclick = () => { $('geo-search').value = ''; renderList(); $('geo-search').focus(); };
  for (const id of ['geo-roads', 'geo-rail', 'geo-water']) $(id).onchange = () => {
    if (state.reviewObservation && !groups()[rows.find(row => row.id === state.reviewObservation).kind]) back();
    updateLayers(); renderList(); $(id).focus(); trace('reviewLayers', { groups: groups() });
  };
  return { close, open, escape() { if (!state.reviewOpen) return false; if (state.reviewObservation) back(); else close(); return true; },
    pick(point) {
      if (!state.reviewOpen || !map.getLayer('review-points')) return false;
      const hits = map.queryRenderedFeatures([[point.x - 8, point.y - 8], [point.x + 8, point.y + 8]], { layers: ['review-points'] });
      const row = hits.map(hit => rows.find(row => row.id === hit.properties.id)).filter(Boolean).sort((a,b) => a.priority - b.priority)[0];
      if (!row) return false; select(row.id); return true;
    }, snapshot: () => ({ loaded: !!report, observations: rows.length, features: features?.features.length || 0 }) };
}
