import * as THREE from 'three';
import { createWorkspaceLayout } from './workspace-layout.mjs?v=m16-closeout-1';
import { createFacilityIndex } from './facility-index.mjs?v=c1-devices-1';
import { CIRCUITS, renderC1Relations } from './c1-relations.mjs?v=c1-devices-1';
import { renderABRelations } from './ab-relations.mjs?v=m9-ab-terminals-1';
import { renderM10Relations } from './m10-relations.mjs?v=m10-system-devices-1';
import { validateSystemGraph } from './m10-graph.mjs?v=m12-connected-1';
import { createGeographicReview } from './geographic-review.mjs?v=m13-geographic-review-1';
import { ROUTES_SHA256, ROUTE_STYLES, routeStyle, flowCoordinates, createEnergyNetwork, renderEnergyStory, renderNetworkRelations, renderRouteDetail } from './energy-network.mjs?v=energy-paths-2';
import { ANALYSIS_SOURCE_SHA256, ANALYSIS_BINDING_SHA256, resolveAnalysis, analysisStatusClass, analysisSummary, formatMw, formatMwh } from './analysis-runtime.mjs?v=m10-object-analysis-2';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { ORIGIN, MERCATOR_ORIGIN, WORLD_SCALE, glbToLocal, glbToWorld, localToLonLat, localToWorld } from './projection.mjs';

const $ = id => document.getElementById(id);
const workspace = createWorkspaceLayout();
const auditBackground = new Map();
const state = { view: 'standard', previousMap: 'standard', selected: null, ready: false,
  independent_registration: 'not_run', modelVisible: true, routesVisible: true, route: null, circuit: 'all', connection: null,
  scenario: 'normal', analysisHour: 14, analysisOpen: false, analysisExpanded: false, auditOpen: false,
  reviewOpen: false, reviewObservation: null };
const errors = [], events = [], objects = {}, labels = {}, pickables = [], terrain = [];
const scene = new THREE.Scene(), camera = new THREE.Camera(), raycaster = new THREE.Raycaster();
let map, renderer, clipMatrix, registry, c1, ab, m10, index, network, analysisBindings, analysisAsset, auditManifest, geographicReview,
  loadedFrames = 0, focusToken = 0, selectionEntry;
const viewHistory = [];
const entityHistory = [];
function fail(operation, error) {
  const entry = { operation, message: String(error?.message || error) };
  errors.push(entry); $('errors').textContent = errors.map(e => `${e.operation}: ${e.message}`).join(' | ');
  console.error('m9', entry);
}
function trace(operation, detail = {}) {
  events.push({ operation, view: state.view, selected: state.selected, circuit: state.circuit, connection: state.connection, route: state.route, at: performance.now(), ...detail });
  $('state').textContent = `view=${state.view} · selected=${state.selected || 'none'} · registration=not_run`;
}
function renderHourlyChart(rows) {
  $('hourly-chart').replaceChildren(...rows.map(row => {
    const group = document.createElement('span'); group.className = 'chart-group';
    group.title = `h${row.hour_index} · 源热 ${formatMw(row.source_mw)} · 热负荷 ${formatMw(row.demand_mw)}${row.unserved_mw > 0 ? ` · 未供热 ${formatMw(row.unserved_mw)}` : ''}`;
    const source = document.createElement('i'); source.className = 'bar';
    const demand = document.createElement('i'); demand.className = row.unserved_mw > 0 ? 'bar risk' : 'bar demand';
    const max = Math.max(1, ...rows.flatMap(item => [item.source_mw, item.demand_mw]));
    source.style.height = `${Math.max(3, row.source_mw / max * 100)}%`;
    demand.style.height = `${Math.max(3, row.demand_mw / max * 100)}%`;
    group.append(source, demand); return group;
  }));
}
function resetAnalysisExpanded() {
  state.analysisExpanded = false;
  $('analysis-expand').textContent = '展开分析';
  $('analysis-expand').setAttribute('aria-expanded', 'false');
}
function renderAnalysis() {
  const status = $('analysis-status'), empty = $('analysis-empty'), body = $('analysis-body');
  const id = state.selected;
  // Start from an unbound state so no previous object's time or controls leak.
  $('analysis-time-state').textContent = '时段未绑定';
  for (const name of ['analysis-scenario', 'analysis-hour', 'analysis-expand']) $(name).disabled = true;
  $('analysis-scenario').value = state.scenario;
  $('analysis-hour').value = String(state.analysisHour);
  $('analysis-object').textContent = id ? `${objects[id]?.contract?.name || id} · ${id}` : '请选择一个设施';
  if (!id || !analysisBindings || !analysisAsset) {
    status.className = 'analysis-status pending'; status.textContent = '待绑定';
    $('analysis-summary').textContent = '选择设施后显示对象级结果；未绑定对象保持空态。';
    empty.textContent = '当前对象暂无绑定的对象级分析结果。'; empty.classList.remove('error'); empty.hidden = false;
    body.hidden = true; $('analysis-limits').textContent = ''; resetAnalysisExpanded(); return;
  }
  const result = resolveAnalysis({ asset: analysisAsset, bindings: analysisBindings, objectId: id, scenarioId: state.scenario, hourIndex: state.analysisHour });
  status.className = `analysis-status ${analysisStatusClass(result)}`;
  if (result.status !== 'available') {
    status.textContent = result.status === 'invalid' ? '来源错误' : '待绑定';
    $('analysis-summary').textContent = result.reason;
    empty.textContent = result.status === 'unavailable' ? `暂无绑定：${result.reason}` : result.reason;
    empty.classList.toggle('error', result.status === 'invalid'); empty.hidden = false;
    body.hidden = true; $('analysis-limits').textContent = result.binding?.limits?.join('；') || ''; resetAnalysisExpanded(); return;
  }
  status.textContent = result.scenario.label;
  for (const name of ['analysis-scenario', 'analysis-hour', 'analysis-expand']) $(name).disabled = false;
  $('analysis-summary').textContent = analysisSummary(result);
  $('analysis-time-state').textContent = `h${result.time.hour_index} · ${result.time.basis}`;
  empty.hidden = true;
  body.hidden = !state.analysisExpanded;
  $('analysis-expand').textContent = state.analysisExpanded ? '收起分析' : '展开分析';
  $('analysis-expand').setAttribute('aria-expanded', String(state.analysisExpanded));
  const summary = result.summary, row = result.row;
  $('energy-balance-value').textContent = `${formatMwh(summary.source_mwh)} → ${formatMwh(summary.delivered_mwh)}`;
  $('energy-balance-copy').textContent = `未供热 ${formatMwh(summary.unserved_mwh)} · 残差 ${formatMwh(summary.thermal_residual_mwh)} · 合成教学数据`;
  $('storage-value').textContent = formatMwh(row.storage_end_mwh);
  $('storage-copy').textContent = row.storage_end_mwh <= 0 ? '库存已耗尽' : row.discharge_mw > 0 ? '当前正在放热' : row.charge_mw > 0 ? '当前正在充热' : '库存保持';
  $('recommendation-value').textContent = result.scenario.recommendation;
  $('recommendation-copy').textContent = result.scenario.reason;
  $('analysis-limits').textContent = `${result.binding.limits.join('；')}；当前绑定时段：h${result.time.hour_index}（${result.time.basis}）`;
  renderHourlyChart(result.rows);
}
function setAnalysisOpen(open, focus = false) {
  if (open) geographicReview?.close({ restoreFocus: false });
  if (open && innerWidth <= 850) index.setExpanded(false);
  state.analysisOpen = open; $('analysis-panel').hidden = !open;
  document.body.classList.toggle('analysis-open', open);
  workspace.sync();
  $('analysis-open').setAttribute('aria-expanded', String(open));
  $('analysis-open').dataset.analysisOpen = String(open);
  if (open) { renderAnalysis(); if (focus) $('analysis-panel').focus(); }
  else { state.analysisExpanded = false; $('analysis-expand').setAttribute('aria-expanded', 'false'); $('analysis-open').focus(); }
  trace(open ? 'openAnalysis' : 'closeAnalysis');
}
function setAnalysisExpanded(expanded) {
  state.analysisExpanded = expanded; renderAnalysis(); trace(expanded ? 'expandAnalysis' : 'collapseAnalysis');
}
function renderAudit() {
  if (!auditManifest) return;
  const model = auditManifest.web_model, analysis = auditManifest.analysis;
  $('audit-code').innerHTML = `分支 <code>${auditManifest.branch}</code><br>运行版本 <code>${auditManifest.runtime_revision}</code><br>需求 <code>${auditManifest.requirement_revision}</code>`;
  $('audit-blender').innerHTML = `${auditManifest.blender.version} · ${auditManifest.blender.render_engine}<br>场景 <code>${auditManifest.blender.scene_name}</code><br>BLEND <code>${auditManifest.blender.scene_file}</code><br>BLEND SHA <code>${auditManifest.blender.scene_file_sha256.slice(0, 16)}…</code><br>GLB <code>${model.path}</code><br>GLB SHA <code>${model.sha256.slice(0, 16)}…</code>`;
  $('audit-map-source').innerHTML = `设施注册表 <code>${auditManifest.sources.facility_registry_path}</code><br>注册表 SHA <code>${auditManifest.sources.facility_registry_sha256.slice(0, 16)}…</code><br>线路 <code>${auditManifest.sources.routes_path}</code><br>线路 SHA <code>${auditManifest.sources.routes_sha256.slice(0, 16)}…</code><br>DEM：${model.terrain_source}<br>卫星：${model.satellite_source}`;
  $('audit-analysis-source').innerHTML = `绑定 <code>${analysis.binding_sha256.slice(0, 16)}…</code><br>结果源 <code>${analysis.source_sha256.slice(0, 16)}…</code><br>基线：${analysis.basis}<br>时间绑定：${analysis.time_binding || '未声明'}`;
  const sourceHost = $('audit-sources'); sourceHost.replaceChildren();
  for (const source of auditManifest.source_inventory || []) {
    const row = document.createElement('div'); row.className = 'audit-source-row';
    const status = document.createElement('span'); status.className = `audit-source-status ${source.status || 'pending'}`; status.textContent = source.status_label || source.status || '待核';
    const copy = document.createElement('span'); copy.innerHTML = `<strong>${source.label}</strong><br><code>${source.path}</code><br>版本 ${source.version || '未声明'} · SHA <code title="${source.sha256 || ''}">${(source.sha256 || 'unknown').slice(0, 16)}…</code>`;
    row.append(status, copy); sourceHost.append(row);
  }
  $('audit-status-pills').innerHTML = `<span class="verified">已核验 · ${auditManifest.status_counts.verified}</span><span class="candidate">候选 · ${auditManifest.status_counts.candidate}</span><span class="pending">待核 · ${auditManifest.status_counts.pending}</span>`;
  $('audit-limitations').replaceChildren(...auditManifest.limitations.map(item => { const li = document.createElement('li'); li.textContent = item; return li; }));
}
async function loadAuditManifest() {
  auditManifest = null;
  $('audit-export').disabled = true; $('audit-refresh').disabled = true;
  $('audit-code').textContent = '正在重新读取来源…';
  try { auditManifest = await json('./audit-manifest.json'); renderAudit(); $('audit-export').disabled = false; }
  catch (error) {
    auditManifest = null;
    fail('audit/load', error); $('audit-code').textContent = '审计清单加载失败，不能把当前状态视为已核验。';
    $('audit-blender').textContent = '当前无法确认 Blender / GLB 版本。'; $('audit-map-source').textContent = '当前无法确认地图与线路来源。';
    $('audit-analysis-source').textContent = '当前无法确认分析绑定来源。'; $('audit-sources').textContent = '逐项来源清单加载失败；不能把旧版本来源当作当前证据。'; $('audit-status-pills').innerHTML = '<span class="pending">来源待核</span>';
    $('audit-limitations').replaceChildren(Object.assign(document.createElement('li'), { textContent: error.message }));
  } finally { $('audit-refresh').disabled = false; }
}
function setAuditOpen(open) {
  if (open) geographicReview?.close({ restoreFocus: false });
  if (open && !state.auditOpen) {
    for (const element of document.body.children) {
      if (element === $('audit-panel') || element === $('audit-backdrop') || element.tagName === 'SCRIPT') continue;
      auditBackground.set(element, element.inert); element.inert = true;
    }
  } else if (!open) {
    for (const [element, inert] of auditBackground) element.inert = inert;
    auditBackground.clear();
  }
  state.auditOpen = open; $('audit-panel').hidden = !open; $('audit-backdrop').hidden = !open;
  $('audit-toggle').setAttribute('aria-expanded', String(open));
  if (open) { renderAudit(); $('audit-panel').focus(); } else $('audit-toggle').focus();
  trace(open ? 'openAudit' : 'closeAudit');
}
function exportAudit() {
  if (!auditManifest) return;
  const analysis = state.selected ? resolveAnalysis({ asset: analysisAsset, bindings: analysisBindings, objectId: state.selected, scenarioId: state.scenario, hourIndex: state.analysisHour }) : null;
  const payload = { audit: auditManifest, analysis_bindings: analysisBindings, selected: state.selected, scenario: state.scenario,
    analysis_status: analysis?.status || 'unavailable',
    analysis_time: analysis?.status === 'available' ? { hour_index: analysis.time.hour_index, timestamp: null, basis: analysis.time.basis } : null };
  const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  link.download = `energy-map-audit-${auditManifest.runtime_revision}.json`; link.click(); URL.revokeObjectURL(link.href); trace('exportAudit');
}
async function json(url, expectedHash) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  const raw = await response.text();
  if (expectedHash) {
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw)))].map(x => x.toString(16).padStart(2, '0')).join('');
    if (digest !== expectedHash) throw new Error(`Route identity mismatch: ${url}`);
  }
  return JSON.parse(raw);
}
function setView(view) {
  if (!['standard', 'satellite', 'data'].includes(view)) throw new Error(`Unknown view: ${view}`);
  if (view !== 'data') state.previousMap = view;
  state.view = view;
  map.setLayoutProperty('osm', 'visibility', view === 'standard' ? 'visible' : 'none');
  for (const mesh of terrain) {
    mesh.visible = view !== 'standard';
    mesh.material = view === 'satellite' ? mesh.userData.satellite : mesh.userData.dem;
  }
  document.querySelectorAll('[data-view]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.view === view)));
  $('return-view').hidden = view !== 'data';
  $('legend').textContent = {
    standard: '真实 OSM 区域底图 · z12 归档栅格，放大不增加街道精度 · 区域外空白',
    satellite: '原 GLB 内嵌 EOxCloudless Sentinel-2 2024 · 每顶点重投影 · 覆盖范围外为空白',
    data: 'DEM 高程信息：浅灰 1279.5 → 深灰 1522.0 m EGM2008 · 约40m网格 · 热潜力/实时工况：未知'
  }[view];
  trace('setView'); map.triggerRepaint();
}
function paintSelection() {
  for (const mesh of pickables) {
    const selected = mesh.userData.objectId === state.selected || objects[mesh.userData.objectId].contract.parent_id === state.selected;
    const activeEdge = state.connection && mesh.userData.connectionId === state.connection;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach(mat => { if (mat.emissive) mat.emissive.setHex(activeEdge ? 0x885500 : selected ? 0x51320c : 0x000000); });
  }
  if (map?.getLayer('route-selected')) {
    map.setFilter('route-selected', ['==', ['get', 'route_id'], state.route || '']);
    map.setFilter('route-flow-selected', ['==', ['get', 'route_id'], state.route || '']);
  }
  for (const [id, label] of Object.entries(labels)) label.setAttribute('aria-pressed', String(state.selected === id));
  map.triggerRepaint();
}
function renderRelations() {
  $('relations-content').replaceChildren();
  renderEnergyStory($('relations-content'), network, state.selected, navigateNetwork);
  const parentId = objects[state.selected]?.contract.parent_id || state.selected;
  const isC1 = parentId === 'AGRI_018';
  const isAB = ab &&
    (ab.parent_facilities.some(item => item.object_id === parentId) || ab.objects.some(item => item.object_id === state.selected));
  if (isC1) {
    if (state.selected === 'AGRI_018') {
      const external = document.createElement('section');
      renderExternalRelations(external, state.selected); $('relations-content').append(external);
    }
    const internal = document.createElement('div'); $('relations-content').append(internal);
    renderC1Relations(internal, c1, state.selected, state.circuit, state.connection,
      (id, trigger) => navigateEntity(id, trigger), id => {
        state.connection = id; paintSelection(); renderRelations();
        const target = id ? document.querySelector(`[data-connection="${id}"]`) : document.querySelector(`[data-circuit="${state.circuit}"]`);
        target?.focus(); trace('selectConnection');
      }, circuit => {
        state.circuit = circuit; state.connection = null; paintSelection(); renderRelations();
        document.querySelector(`[data-circuit="${circuit}"]`)?.focus(); trace('filterCircuit');
      });
    return;
  }
  if (isAB) {
    if (state.selected === parentId) {
      const external = document.createElement('section');
      renderExternalRelations(external, state.selected); $('relations-content').append(external);
    }
    const internal = document.createElement('div'); $('relations-content').append(internal);
    renderABRelations(internal, ab, state.selected, state.circuit, state.connection,
      (id, trigger) => navigateEntity(id, trigger), id => {
        state.connection = id; paintSelection(); renderRelations();
        const target = id ? document.querySelector(`[data-connection="${id}"]`) : document.querySelector(`[data-circuit="${state.circuit}"]`);
        target?.focus(); trace('selectABConnection');
      }, circuit => {
        state.circuit = circuit; state.connection = null; paintSelection(); renderRelations();
        document.querySelector(`[data-circuit="${circuit}"]`)?.focus(); trace('filterABCircuit');
      });
    return;
  }
  const isM10 = m10 && m10.objects.some(item => item.object_id === state.selected || item.parent_id === state.selected);
  if (isM10) {
    if (state.selected === parentId || !objects[state.selected]?.contract.parent_id) {
      const external = document.createElement('section');
      renderExternalRelations(external, state.selected); $('relations-content').append(external);
    }
    const internal = document.createElement('div'); $('relations-content').append(internal);
    renderM10Relations(internal, m10, state.selected, (id, trigger) => navigateEntity(id, trigger), state.connection, id => {
      state.connection = id; paintSelection(); renderRelations();
      const target = id ? document.querySelector(`[data-connection="${id}"]`) : $('relations-toggle');
      target?.focus(); trace('selectM10Connection');
    });
    return;
  }
  renderExternalRelations($('relations-content'), state.selected);
}
function renderExternalRelations(host, id) {
  renderNetworkRelations(host, network, id, navigateNetwork);
}
function navigateNetwork(target, trigger) {
  if (target.kind === 'route') navigateRoute(target.id, trigger);
  else if (target.kind === 'facility') navigateEntity(target.id, trigger);
}
function captureEntity(trigger) {
  return { id: state.selected, route: state.route, view: currentView(), circuit: state.circuit,
    connection: state.connection, relations: !$('relations-panel').hidden, scroll: (state.route ? $('route-detail') : $('detail')).scrollTop,
    selectionEntry,
    triggerId: trigger?.dataset.device || trigger?.dataset.networkTarget,
    triggerLabel: trigger?.getAttribute('aria-label') };
}
function navigateRoute(id, trigger) {
  entityHistory.push(captureEntity(trigger)); selectionEntry = trigger; selectRoute(id);
}
function selectRoute(id, focus = true) {
  const route = network.describe(id);
  selectObject(null, false); state.route = id;
  if (!state.routesVisible) {
    state.routesVisible = true; $('routes').checked = true;
    for (const layer of ['route-outline', 'route-lines', 'route-selected', 'route-flow-selected']) map.setLayoutProperty(layer, 'visibility', 'visible');
    trace('revealRoutes');
  }
  $('route-detail').hidden = false;
  $('route-name').textContent = route.label;
  $('route-id').textContent = id;
  $('route-back').hidden = !entityHistory.length;
  renderRouteDetail($('route-content'), network, id, navigateNetwork);
  $('route-detail').scrollTop = 0;
  paintSelection();
  if (focus) focusRoute(id);
  trace('selectRoute');
}
function focusRoute(id) {
  focusToken++; state.cameraPending = false; rememberView(); map.setCenterElevation(0);
  const points = network.describe(id).sampled_xyz.map(localToLonLat);
  const bounds = new maplibregl.LngLatBounds(); points.forEach(point => bounds.extend(point));
  const area = safeArea();
  map.fitBounds(bounds, { duration: 0, maxZoom: 17, pitch: 0, bearing: 0,
    padding: { top: area.top + 20, bottom: innerHeight - area.bottom + 20, left: area.left + 20, right: innerWidth - area.right + 20 } });
  trace('focusRoute');
}
function backEntity() {
  const entry = entityHistory.pop(); if (entry) restoreEntity(entry);
}
function closeRoute() {
  if (entityHistory.length) { backEntity(); return; }
  selectObject(null, false);
  if (selectionEntry === map.getCanvas()) map.getCanvas().focus();
  else $('overview').focus();
  trace('closeRoute');
}
function exitRoutesForPan() {
  const entry = [...entityHistory].reverse().find(item => !item.route);
  entityHistory.length = 0;
  if (state.selected && !state.route) {
    // Navigating from a route into a facility leaves route entries behind,
    // but the facility is the user's current context and must stay selected.
    $('back-entity').hidden = true;
    paintSelection();
  } else if (entry) restoreEntity(entry);
  else {
    selectObject(null, false);
    if (selectionEntry === map.getCanvas()) map.getCanvas().focus();
    else $('overview').focus();
  }
  trace('exitRoutesForPan');
}
function closeRoutePicker(restore = false) {
  $('route-picker').hidden = true;
  if (restore) map.getCanvas().focus();
}
function openRoutePicker(ids, point) {
  const host = $('route-picker-list'); host.replaceChildren();
  for (const id of ids) {
    const route = network.describe(id), button = document.createElement('button');
    button.textContent = `${id} · ${route.label}`;
    button.setAttribute('aria-label', `选择重叠线路 ${id}`);
    button.onclick = () => { closeRoutePicker(); entityHistory.length = 0; selectionEntry = map.getCanvas(); selectRoute(id); };
    host.append(button);
  }
  $('route-picker').style.left = `${Math.max(96, Math.min(point.x, innerWidth - 330))}px`;
  $('route-picker').style.top = `${Math.max($('toolbar').getBoundingClientRect().bottom + 8, Math.min(point.y, innerHeight - 380))}px`;
  $('route-picker').hidden = false; host.querySelector('button').focus();
  trace('chooseOverlappingRoute', { candidates: ids });
}
function currentView() {
  return { center: map.getCenter().toArray(), zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing(), elevation: map.getCenterElevation() };
}
function navigateEntity(id, trigger) {
  entityHistory.push(captureEntity(trigger));
  selectionEntry = trigger; selectObject(id);
}
function parentLabel(parentId) {
  if (parentId === 'AGRI_018') return '返回 C1 设施';
  if (['AGRI_014', 'AGRI_015'].includes(parentId)) return '返回 A 区设施';
  if (['AGRI_016', 'AGRI_017'].includes(parentId)) return '返回 B 区设施';
  return `返回 ${objects[parentId]?.contract?.short_name || parentId} 设施`;
}
function relationLabel(circuitId) {
  if (CIRCUITS[circuitId]) return CIRCUITS[circuitId];
  if (circuitId?.endsWith('_CONTROL')) return '控制信号';
  if (circuitId?.endsWith('_HEAT')) return '热水回路';
  return circuitId || '见候选关系';
}
function objectContext(objectId) {
  const object = objects[objectId]?.contract;
  const parentId = object?.parent_id;
  const parent = parentId ? objects[parentId]?.contract : null;
  return { object, parentId, parent };
}
function objectPortSummary(objectId) {
  const ports = [c1, ab, m10].flatMap(graph => graph?.ports || [])
    .filter(port => port.object_id === objectId);
  if (!ports.length) return '端口未定义；介质与方向待核';
  const media = { water: '水', nutrient: '营养液', signal: '控制信号', control: '控制信号', electricity: '电力', co2: '站内 CO₂' };
  const directions = { in: '入', out: '出', bidirectional: '双向' };
  return [...new Set(ports.map(port => port.medium))].map(medium => {
    const values = [...new Set(ports.filter(port => port.medium === medium).map(port => port.direction))].sort();
    return `${media[medium] || medium} · ${values.map(value => directions[value] || value).join(' / ')}（候选端口）`;
  }).join('；');
}
function restoreEntity(entry) {
  if (entry.route) selectRoute(entry.route, false);
  else selectObject(entry.id, false);
  map.jumpTo(entry.view);
  selectionEntry = entry.selectionEntry;
  state.circuit = entry.circuit; state.connection = entry.connection;
  if (!entry.route && entry.id) {
    $('relations-panel').hidden = !entry.relations;
    $('relations-toggle').setAttribute('aria-expanded', String(entry.relations)); renderRelations();
  }
  paintSelection();
  const host = entry.route ? $('route-detail') : $('detail'); host.scrollTop = entry.scroll;
  const trigger = [...host.querySelectorAll('button')].find(button => entry.triggerLabel && button.getAttribute('aria-label') === entry.triggerLabel) ||
    [...host.querySelectorAll('[data-device], [data-network-target]')].find(button => (button.dataset.device || button.dataset.networkTarget) === entry.triggerId);
  (trigger || $(entry.route ? 'route-focus' : 'relations-toggle')).focus(); trace('restoreEntity');
}
function enterObject(id, trigger) {
  entityHistory.length = 0; selectionEntry = trigger; selectObject(id);
}
function selectObject(id, focus = true) {
  geographicReview?.close({ restoreView: false, restoreFocus: false });
  if (id !== null && !objects[id]) throw new Error(`Unknown facility ${id}`);
  focusToken++; state.cameraPending = false;
  state.selected = id; state.route = null; $('route-detail').hidden = true; closeRoutePicker();
  state.circuit = 'all'; state.connection = null;
  index?.select(id);
  if (id && innerWidth <= 850) index?.setExpanded(false);
  if (id) setModels(true);
  $('relations-panel').hidden = true; $('relations-toggle').setAttribute('aria-expanded', 'false');
  paintSelection();
  $('detail').hidden = !id;
  const context = id ? objectContext(id) : { object: null, parentId: null, parent: null };
  $('parent-facility').hidden = !context.parentId;
  if (context.parentId) $('parent-facility').textContent = parentLabel(context.parentId);
  $('back-entity').hidden = !entityHistory.length;
  if (id) {
    $('relations-content').replaceChildren();
    const obj = objects[id], feature = obj.feature, parent = context.parent;
    $('detail-name').textContent = obj.contract.name; $('detail-id').textContent = id;
    const parentName = parent ? `${parent.short_name || context.parentId} · ${parent.name}` : null;
    const values = [
      ['经纬度', localToLonLat(feature.xyz).map(n => n.toFixed(7)).join(', ')],
      ['位置来源', feature.properties.source || '历史方案种子；精度待核'],
      ['状态', obj.contract.installation_status || '候选规划 · 位置与接入待核'],
      ['规划面积', obj.contract.planning_area ? `${obj.contract.planning_area.min}–${obj.contract.planning_area.max} m²` : '未知 / 待核'],
      ['示意场坪面积', obj.contract.model_footprint_m2 === null ? '未知 / 待核' : `${obj.contract.model_footprint_m2} m²`],
      ...(obj.contract.zone_label ? [['所属分区', obj.contract.zone_label]] : []),
      [context.parentId ? '所属设施' : 'DEM地表高程', context.parentId ? parentName : `${(feature.xyz[2] + ORIGIN[2]).toFixed(2)} m EGM2008（粗网格）`],
      [context.parentId ? '模型参考高程' : '模型场坪高程', `${(obj.contract.model_root_xyz[2] + ORIGIN[2]).toFixed(2)} m EGM2008（示意抬坪）`],
      ['回路', obj.contract.circuits?.map(relationLabel).join(' / ') || '见候选关系'],
      ...(context.parentId ? [['介质 / 方向', objectPortSummary(id)]] : []),
      ['热潜力 / 实测值', '未知；无绑定对象结果'], ['独立配准', 'not_run']
    ];
    $('properties').replaceChildren(...values.flatMap(([key, value]) => {
      const dt = document.createElement('dt'), dd = document.createElement('dd');
      dt.textContent = key; dd.textContent = value; return [dt, dd];
    }));
    $('description').textContent = obj.contract.description;
    $('gaps').textContent = obj.contract.gaps.join('；');
    $('position-note').textContent = context.parentId === 'AGRI_018'
      ? 'C1原坐标保留；临水/覆盖水域的疑点仍待独立核验。'
      : context.parentId ? `${parentName} 的候选末端补模；地理配准、施工连接和水力参数仍待核。`
        : '代表模型不等于现场实测建筑；选址与接入条件尚待核验。';
    $('focus').textContent = context.parentId ? '聚焦此设备' : '聚焦整座设施';
    const hasInternalRelations = id === 'AGRI_018' || context.parentId === 'AGRI_018' ||
      ab?.parent_facilities.some(item => item.object_id === (context.parentId || id));
    $('relations-toggle').textContent = hasInternalRelations ? '设备与回路' : '查看候选关系';
    const terminalPreview = ab?.zones.find(zone => zone.parent_id === id);
    const systemPreview = m10?.parent_previews?.[id];
    $('model-revision').textContent = `模型 ${systemPreview?.model_revision || (terminalPreview ? ab.revision : obj.contract.model_revision)} · 非厂家施工模型`;
    $('model-preview').hidden = true; $('preview-status').textContent = '模型图正在加载…';
    $('model-preview').onload = () => { $('model-preview').hidden = false; $('preview-status').textContent = ''; };
    $('model-preview').onerror = () => { $('model-preview').hidden = true; $('preview-status').textContent = '同版模型图未取得'; };
    $('model-preview').src = systemPreview?.preview_url || terminalPreview?.preview_url || obj.contract.preview_url;
    $('model-preview').alt = `${obj.contract.name}的同版Blender模型图`;
    renderRelations(); $('detail').scrollTop = 0;
    if (focus) focusObject(id);
  }
  renderAnalysis(); trace('selectObject'); map.triggerRepaint();
}
function rememberView() {
  viewHistory.push(currentView());
  if (viewHistory.length > 30) viewHistory.shift(); $('back-view').disabled = false;
}
function safeArea() {
  return workspace.safeArea();
}
function setModels(visible) {
  state.modelVisible = visible; $('models').checked = visible;
  pickables.forEach(mesh => { mesh.visible = visible; }); updateLabels();
}
async function focusObject(id) {
  const token = ++focusToken; state.cameraPending = true;
  const b = objects[id].localBounds;
  const corners = [[b.min.x, b.min.y], [b.min.x, b.max.y], [b.max.x, b.min.y], [b.max.x, b.max.y]].map(localToLonLat);
  const sw = [Math.min(...corners.map(p => p[0])), Math.min(...corners.map(p => p[1]))];
  const ne = [Math.max(...corners.map(p => p[0])), Math.max(...corners.map(p => p[1]))];
  rememberView();
  const area = safeArea();
  // The custom scene's vertical datum is relative to ORIGIN[2]. A close
  // camera aimed at map zero would descend below this model's raised pad.
  map.setCenterElevation(objects[id].contract.parent_id ? (b.min.z + b.max.z) / 2 : 0);
  map.fitBounds([sw, ne], { duration: 0, maxZoom: objects[id].contract.parent_id ? 21 : 17, pitch: 42, bearing: 0,
    padding: { top: area.top, bottom: innerHeight - area.bottom, left: area.left, right: innerWidth - area.right } });
  for (let attempt = 0; attempt < 5; attempt++) {
    await new Promise(resolve => { map.once('render', resolve); map.triggerRepaint(); });
    if (token !== focusToken) return;
    const target = safeArea();
    const vertices = objects[id].meshes.flatMap(mesh => {
      const box=mesh.geometry.boundingBox, points=[];
      for(const x of [box.min.x,box.max.x]) for(const y of [box.min.y,box.max.y]) for(const z of [box.min.z,box.max.z]){
        const p=new THREE.Vector3(x,y,z).applyMatrix4(clipMatrix);
        points.push([(p.x+1)/2*innerWidth,(1-p.y)/2*innerHeight]);
      }
      return points;
    });
    const min=[0,1].map(i=>Math.min(...vertices.map(p=>p[i]))), max=[0,1].map(i=>Math.max(...vertices.map(p=>p[i])));
    const scale=Math.min(1,(target.right-target.left)/(max[0]-min[0]),(target.bottom-target.top)/(max[1]-min[1]));
    const dx=(min[0]+max[0]-target.left-target.right)/2, dy=(min[1]+max[1]-target.top-target.bottom)/2;
    if(scale>=.999 && Math.hypot(dx,dy)<1) break;
    if(scale<1) map.setZoom(map.getZoom()+Math.log2(scale*.96));
    map.panBy([dx,dy],{duration:0});
  }
  if (token === focusToken) {state.cameraPending=false;trace('focusSettled');}
}
function updateLabels() {
  if (!clipMatrix) return;
  const candidates = [];
  for (const [id, object] of Object.entries(objects)) {
    const p = new THREE.Vector3(...localToWorld(object.contract.parent_id ? object.contract.model_root_xyz : object.feature.xyz)).applyMatrix4(clipMatrix);
    const label = labels[id];
    label.hidden = !state.modelVisible || p.z < -1 || p.z > 1 || (!!object.contract.parent_id && state.selected !== id);
    label.classList.toggle('compact', map.getZoom() < 14 && state.selected !== id);
    if (!label.hidden) candidates.push({ id, object, label, x: (p.x + 1) / 2 * innerWidth, y: (1 - p.y) / 2 * innerHeight });
  }
  // Facility labels are DOM overlays rather than map symbols, so MapLibre's
  // collision handling cannot protect their hit areas. Keep the selected
  // label at its anchor and move later colliding labels by a small deterministic
  // vertical offset. This preserves every facility's click target when a
  // candidate asset sits on top of a parent facility in screen space.
  const priority = item => (state.selected === item.id ? 0 : item.object.contract.parent_id ? 2 : 1);
  candidates.sort((a, b) => priority(a) - priority(b) || a.id.localeCompare(b.id));
  const placed = [];
  for (const item of candidates) {
    const width = item.label.offsetWidth || (item.label.classList.contains('compact') ? 72 : 180);
    const height = item.label.offsetHeight || 28;
    const offsets = [0, -height - 6, height + 6, -2 * (height + 6), 2 * (height + 6), -3 * (height + 6), 3 * (height + 6)];
    const overlaps = (left, top) => placed.some(box => left < box.right && left + width > box.left && top < box.bottom && top + height > box.top);
    let top = item.y - height * 1.15;
    for (const offset of offsets) {
      const candidateTop = item.y - height * 1.15 + offset;
      const left = item.x - width / 2;
      if (!overlaps(left, candidateTop)) { top = candidateTop; break; }
    }
    item.label.style.left = `${item.x}px`;
    item.label.style.top = `${top + height * 1.15}px`;
    placed.push({ left: item.x - width / 2, right: item.x + width / 2, top, bottom: top + height });
  }
}
function transformMesh(source, objectId) {
  const geometry = source.geometry.clone(); geometry.applyMatrix4(source.matrixWorld);
  const pos = geometry.attributes.position;
  const localBounds = new THREE.Box3(), colors = [];
  for (let i = 0; i < pos.count; i++) {
    const glb = [pos.getX(i), pos.getY(i), pos.getZ(i)], local = glbToLocal(glb);
    localBounds.expandByPoint(new THREE.Vector3(...local));
    const world = glbToWorld(glb); pos.setXYZ(i, ...world);
    if (!objectId) {
      const grey = THREE.MathUtils.clamp(0.91 - (local[2] + ORIGIN[2] - 1279.5) / (1522 - 1279.5) * .45, .3, .95);
      colors.push(grey, grey + .015, grey + .01);
    }
  }
  // Reprojection reflects north into Mercator south; reverse triangle winding.
  if (geometry.index) {
    const ix = geometry.index;
    for (let i = 0; i < ix.count; i += 3) { const b = ix.getX(i + 1); ix.setX(i + 1, ix.getX(i + 2)); ix.setX(i + 2, b); }
  } else {
    const index = Array.from({ length: pos.count }, (_, i) => i);
    for (let i = 0; i < index.length; i += 3) [index[i + 1], index[i + 2]] = [index[i + 2], index[i + 1]];
    geometry.setIndex(index);
  }
  geometry.computeVertexNormals(); geometry.computeBoundingSphere(); geometry.computeBoundingBox();
  const cloneMaterial = mat => { const clone = mat.clone(); clone.side = THREE.DoubleSide; clone.userData.sourceUuid = mat.uuid; return clone; };
  const material = Array.isArray(source.material) ? source.material.map(cloneMaterial) : cloneMaterial(source.material);
  const mesh = new THREE.Mesh(geometry, material); mesh.userData.objectId = objectId;
  mesh.userData.connectionId = source.userData.connection_id || null;
  if (objectId) { objects[objectId].meshes.push(mesh); objects[objectId].localBounds.union(localBounds); pickables.push(mesh); }
  else {
    const original = Array.isArray(source.material) ? source.material[0] : source.material;
    if (!original.map) throw new Error('Existing EOx terrain texture missing');
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    mesh.userData.satellite = new THREE.MeshBasicMaterial({ map: original.map, side: THREE.DoubleSide });
    mesh.userData.dem = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide });
    mesh.material = mesh.userData.dem; mesh.visible = false; terrain.push(mesh);
  }
  scene.add(mesh); return mesh;
}
function castAt(x, y) {
  const ndc = new THREE.Vector3(x / map.getCanvas().clientWidth * 2 - 1,
    1 - y / map.getCanvas().clientHeight * 2, -1);
  const inv = clipMatrix.clone().invert(), near = ndc.clone().applyMatrix4(inv);
  const far = ndc.clone().setZ(1).applyMatrix4(inv);
  raycaster.set(near, far.sub(near).normalize());
  return raycaster.intersectObjects(pickables, false)[0]?.object.userData.objectId || null;
}
function hitTest(x, y) {
  if (!state.modelVisible || !clipMatrix) return null;
  const direct = castAt(x, y);
  if (objects[direct]?.contract.parent_id) return direct;
  // Thin schematic headers can be subpixel at facility scale. A two CSS
  // pixel target tolerance keeps them selectable without altering geometry.
  if (map.getZoom() >= 16) {
    for (const radius of [1, 2]) for (const [dx,dy] of [[radius,0],[-radius,0],[0,radius],[0,-radius]]) {
      const near = castAt(x+dx, y+dy);
      if (objects[near]?.contract.parent_id && (!direct || objects[near].contract.parent_id === direct)) return near;
    }
  }
  return direct;
}
async function boot() {
  if (!globalThis.maplibregl) throw new Error('Pinned MapLibre dependency unavailable');
  const [geo, contract, binding, routes, coordinate, graph, bindings, results, abGraph, m10Graph, integrated] = await Promise.all([
    json('../../data/map-v2/geographic-manifest.json'), json('./facility-registry.json'),
    json('./asset-bindings.json'), json('../../data/map-v2/routes.json', ROUTES_SHA256), json('../../data/contracts/coordinate-contract.json'), json('./c1-runtime.json'),
    json('./analysis-bindings.json', ANALYSIS_BINDING_SHA256), json('../map-viewer/assets/analysis-results.json', ANALYSIS_SOURCE_SHA256), json('./ab-terminal-runtime.json'), json('./m10-system-runtime.json'), json('./integrated-asset.json')
  ]);
  registry = contract; c1 = graph; ab = abGraph; m10 = m10Graph; analysisBindings = bindings; analysisAsset = results; network = createEnergyNetwork(routes.routes, registry.objects);
  if (c1.asset_sha256 !== registry.sha256) throw new Error('C1 GLB identity mismatch');
  if (ab.objects.length !== 32 || ab.ports.length !== 60 || ab.connections.length !== 60) throw new Error('A/B runtime contract count mismatch');
  validateSystemGraph(m10, registry.objects.map(o => o.object_id));
  const entities = [...registry.objects, ...c1.objects, ...ab.objects, ...m10.objects];
  if (new Set(entities.map(item => item.object_id)).size !== entities.length ||
      Object.keys(integrated.entity_nodes).length !== entities.length) throw new Error('Integrated entity identity mismatch');
  if (JSON.stringify(coordinate.origin_utm_egm2008_m) !== JSON.stringify(ORIGIN)) throw new Error('Origin identity mismatch');
  map = new maplibregl.Map({ container: 'map', center: [113.207, 41.014], zoom: 12.5, pitch: 0, bearing: 0,
    minZoom: 10, maxZoom: 21, maxPitch: 60, renderWorldCopies: false,
    canvasContextAttributes: { antialias: true, preserveDrawingBuffer: true },
    style: { version: 8, sources: { osm: { type: 'image', url: '../../design/m7/map-assets/standard-base.png',
      coordinates: [[113.12,41.054],[113.29,41.054],[113.29,40.974],[113.12,40.974]] } }, layers: [
      { id: 'background', type: 'background', paint: { 'background-color': '#edf0ee' } },
      { id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-opacity': .55 } }
    ] } });
  map.on('error', event => fail('map/source', event.error));
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
  map.addControl(new maplibregl.ScaleControl(), 'bottom-left');
  await new Promise(resolve => map.once('style.load', resolve));
  map.setCenterClampedToGround(false);
  scene.add(new THREE.AmbientLight(0xffffff, 2));
  const sunlight = new THREE.DirectionalLight(0xffffff, 3); sunlight.position.set(-500, -500, 1000); scene.add(sunlight);
  async function loadAsset(asset) {
  const modelResponse = await fetch(asset.asset_url);
  if (!modelResponse.ok) throw new Error(`GLB HTTP ${modelResponse.status}`);
  const bytes = await modelResponse.arrayBuffer();
  const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
  if (digest !== asset.sha256) throw new Error(`GLB identity changed: ${digest}`);
  return new GLTFLoader().parseAsync(bytes, new URL('../map-viewer/assets/', location.href).href);
  }
  const [gltf, facilities] = await Promise.all([
    loadAsset(binding), loadAsset(integrated)
  ]);
  gltf.scenes[binding.scene_index].updateMatrixWorld(true); facilities.scene.updateMatrixWorld(true);
  for (const entry of entities) {
    const id = entry.object_id;
    objects[id] = { feature: geo.features.find(f => f.id === id) || { xyz: entry.model_root_xyz, properties: { source: '同版GLB相对模型位置；非现场实测' } }, contract: entry,
      meshes: [], localBounds: new THREE.Box3() };
    const label = document.createElement('button'); label.className = 'facility-label'; label.dataset.objectId = id;
    const short = document.createElement('b'), full = document.createElement('span');
    short.textContent = entry.short_name; full.textContent = entry.name; label.append(short, full);
    label.setAttribute('aria-label', `${entry.short_name} ${entry.name} 地图选择`); label.title = entry.name;
    label.setAttribute('aria-pressed', 'false');
    label.onclick = () => { if (!state.panMode) enterObject(id, label); };
    $('map').append(label); labels[id] = label;
  }
  for (const entry of entities) {
    const id = entry.object_id;
    if (!Number.isInteger(integrated.entity_nodes[id])) throw new Error(`Integrated root missing ${id}`);
    const root = await facilities.parser.getDependency('node', integrated.entity_nodes[id]);
    if ((root.userData.object_id || root.userData.asset_id) !== id) throw new Error(`Semantic root mismatch ${id}`);
  }
  // Traverse the combined asset once so nested equipment is never duplicated.
  facilities.scene.traverse(child => {
    if (!child.isMesh) return;
    let owner = child;
    while (owner && !objects[owner.userData.object_id || owner.userData.asset_id]) owner = owner.parent;
    const ownerId = owner?.userData.object_id || owner?.userData.asset_id;
    if (!ownerId) throw new Error(`Integrated mesh owner missing: ${child.name}`);
    transformMesh(child, ownerId);
  });
  for (const entry of entities) {
    const id = entry.object_id;
    if (!objects[id].meshes.length) {
      if (!integrated.semantic_only_entities?.includes(id)) throw new Error(`No meshes for ${id}`);
      // Only explicitly declared measurement points may lack geometry.
      const point = new THREE.Vector3(...objects[id].contract.model_root_xyz);
      objects[id].localBounds.set(point, point);
      continue;
    }
    // The innermost entity and connection are batching boundaries for picking/highlight.
    const batches = new Map();
    for (const mesh of objects[id].meshes) {
      const material = Array.isArray(mesh.material) ? null : mesh.material;
      const key = material ? `${mesh.userData.connectionId}|${material.userData.sourceUuid}|${Object.keys(mesh.geometry.attributes).sort()}|${!!mesh.geometry.index}` : mesh.uuid;
      if (!batches.has(key)) batches.set(key, []); batches.get(key).push(mesh);
    }
    objects[id].meshes = [];
    for (const batch of batches.values()) {
      if (batch.length === 1) { objects[id].meshes.push(batch[0]); continue; }
      const merged = mergeGeometries(batch.map(m => m.geometry));
      if (!merged) throw new Error(`Geometry batching failed ${id}`);
      merged.computeBoundingBox(); merged.computeBoundingSphere();
      const mesh = new THREE.Mesh(merged, batch[0].material); mesh.userData = { ...batch[0].userData };
      for (const old of batch) { scene.remove(old); pickables.splice(pickables.indexOf(old), 1); old.geometry.dispose(); }
      scene.add(mesh); pickables.push(mesh); objects[id].meshes.push(mesh);
    }
  }
  for (const entry of c1.objects) {
    const parent = objects[entry.parent_id], child = objects[entry.object_id];
    parent.meshes.push(...child.meshes); parent.localBounds.union(child.localBounds);
  }
  for (const entry of ab.objects) {
    const parent = objects[entry.parent_id], child = objects[entry.object_id];
    parent.meshes.push(...child.meshes); parent.localBounds.union(child.localBounds);
  }
  for (const entry of m10.objects) {
    const parent = entry.parent_id ? objects[entry.parent_id] : null, child = objects[entry.object_id];
    if (parent && child) { parent.meshes.push(...child.meshes); parent.localBounds.union(child.localBounds); }
  }
  index = createFacilityIndex({ objects: entities }, enterObject, ids => {
    rememberView(); selectObject(null, false);
    entityHistory.length = 0; map.setCenterElevation(0);
    const bounds = new maplibregl.LngLatBounds();
    ids.forEach(id => bounds.extend(localToLonLat(objects[id].feature.xyz)));
    const area = safeArea();
    map.fitBounds(bounds, { duration: 0, maxZoom: 14.5, pitch: 0, bearing: 0,
      padding: { top: area.top + 60, bottom: innerHeight - area.bottom + 80, left: area.left + 100, right: innerWidth - area.right + 100 } });
  });
  $('scope-note').textContent = `已接入 ${registry.objects.length} / 12 个主要设施 · C1、A/B 末端与 M10 系统候选补模`;
  const terrainNode = await gltf.parser.getDependency('node', binding.terrain_node);
  terrainNode.traverse(node => { if (node.isMesh) transformMesh(node, null); });
  const worldMatrix = new THREE.Matrix4().makeTranslation(...MERCATOR_ORIGIN)
    .multiply(new THREE.Matrix4().makeScale(WORLD_SCALE, WORLD_SCALE, WORLD_SCALE));
  const customLayer = { id: 'corridor-glb', type: 'custom', renderingMode: '3d',
    onAdd(_map, gl) {
      renderer = new THREE.WebGLRenderer({ canvas: map.getCanvas(), context: gl, antialias: true });
      renderer.autoClear = false;
    },
    render(_gl, args) {
      clipMatrix = new THREE.Matrix4().fromArray(args.defaultProjectionData.mainMatrix).multiply(worldMatrix);
      camera.projectionMatrix.copy(clipMatrix); camera.projectionMatrixInverse.copy(clipMatrix).invert();
      renderer.resetState();
      // Initialize Three's active viewport before the glass transmission pass, including after resize.
      renderer.setViewport(0, 0, _gl.drawingBufferWidth, _gl.drawingBufferHeight);
      renderer.render(scene, camera); updateLabels(); loadedFrames++;
    }
  };
  map.addLayer(customLayer);
  const zoneFeatures = geo.features.filter(f => f.type === 'Polygon').map(f => ({ type: 'Feature',
    properties: { id: f.id, color: ({ZONE_AGRIA:'#e8a148',ZONE_AGRIB:'#5d92c5',ZONE_AGRIC:'#9c7cba',ZONE_DCZONE:'#61a88a',ZONE_CITY:'#8b9298',ZONE_NEWAREA:'#c29266'})[f.id] },
    geometry: { type: 'Polygon', coordinates: f.xyz.map(ring => ring.map(localToLonLat)) } }));
  map.addSource('zones', { type:'geojson', data:{type:'FeatureCollection',features:zoneFeatures} });
  map.addLayer({ id:'zone-fill', type:'fill', source:'zones', paint:{'fill-color':['get','color'],'fill-opacity':.12} }, 'corridor-glb');
  map.addLayer({ id:'zone-outline', type:'line', source:'zones', paint:{'line-color':['get','color'],'line-width':2,'line-dasharray':[3,2]} }, 'corridor-glb');
  const features = routes.routes.map(r => ({type:'Feature', properties:{route_id:r.route_id,
    style: routeStyle(r), status:'candidate_unverified'},
    geometry:{type:'LineString',coordinates:flowCoordinates(r).map(localToLonLat)}}));
  const routeColors = ['match', ['get', 'style'], ...Object.entries(ROUTE_STYLES).flatMap(([id, value]) => [id, value.color]), '#ffffff'];
  map.addSource('routes', { type: 'geojson', data: { type: 'FeatureCollection', features } });
  map.addLayer({ id: 'route-outline', type: 'line', source: 'routes', paint: {
    'line-color': '#344750', 'line-width': 8, 'line-opacity': .8, 'line-dasharray': [2, 2] } });
  map.addLayer({ id: 'route-lines', type: 'line', source: 'routes', paint: {
    'line-color': routeColors, 'line-width': 5, 'line-dasharray': [2, 2] } });
  map.addLayer({ id: 'route-selected', type: 'line', source: 'routes', filter: ['==', ['get', 'route_id'], ''], paint: {
    'line-color': '#f5ce4f', 'line-width': 10, 'line-opacity': .8, 'line-gap-width': 5 } });
  // A local raster icon avoids a new glyph/font dependency. Rotates with the
  // flow-ordered GeoJSON; the arrows express topology, never live flow.
  const arrowCanvas = document.createElement('canvas'); arrowCanvas.width = 32; arrowCanvas.height = 24;
  const arrow = arrowCanvas.getContext('2d'); arrow.strokeStyle = '#23343f'; arrow.lineWidth = 4;
  arrow.beginPath(); arrow.moveTo(5, 12); arrow.lineTo(26, 12); arrow.moveTo(16, 3); arrow.lineTo(27, 12); arrow.lineTo(16, 21); arrow.stroke();
  map.addImage('flow-arrow', arrow.getImageData(0, 0, 32, 24));
  map.addLayer({ id: 'route-flow-selected', type: 'symbol', source: 'routes', filter: ['==', ['get', 'route_id'], ''], layout: {
    'symbol-placement': 'line', 'symbol-spacing': 95, 'icon-image': 'flow-arrow', 'icon-size': .65,
    'icon-rotation-alignment': 'map', 'icon-keep-upright': false, 'icon-allow-overlap': true } });
  geographicReview = createGeographicReview({ map, json, state, trace, fail, currentView, safeArea,
    identity: { routes: ROUTES_SHA256, asset: integrated.sha256 },
    suspend() {
      focusToken++; state.cameraPending = false; closeRoutePicker();
      panMode(false);
      if (state.auditOpen) setAuditOpen(false);
      if (state.analysisOpen) setAnalysisOpen(false);
      $('detail').hidden = true; $('route-detail').hidden = true;
    },
    resume() { $('detail').hidden = !state.selected; $('route-detail').hidden = !state.route; }
  });
  // Routes are a 2D map overlay. Their DEM/port heights are not engineering registration.
  map.on('click', event => {
    if (state.panMode || !clipMatrix || event.originalEvent.target.closest('button')) return;
    if (geographicReview.pick(event.point)) return;
    const id = hitTest(event.point.x, event.point.y);
    trace('pick', { point: [event.point.x, event.point.y], hit: id });
    if (id) { enterObject(id, map.getCanvas()); return; }
    if (state.routesVisible) {
      const { x, y } = event.point;
      const hits = map.queryRenderedFeatures([[x-5,y-5],[x+5,y+5]], { layers: ['route-lines'] });
      const ids = [...new Set(hits.map(hit => hit.properties.route_id))];
      if (ids.length > 1) openRoutePicker(ids, event.point);
      else if (ids.length) { entityHistory.length = 0; selectionEntry = map.getCanvas(); selectRoute(ids[0]); }
    }
  });
  document.querySelectorAll('[data-view]').forEach(el => el.onclick = () => setView(el.dataset.view));
  $('return-view').onclick = () => setView(state.previousMap);
  $('analysis-open').onclick = () => setAnalysisOpen(true, true);
  $('analysis-close').onclick = () => setAnalysisOpen(false);
  $('analysis-expand').onclick = () => setAnalysisExpanded(!state.analysisExpanded);
  $('analysis-scenario').onchange = event => {
    state.scenario = event.target.value;
    state.analysisHour = { normal: 14, 'source-outage': 0, 'storage-depleted': 5 }[state.scenario] ?? 14;
    renderAnalysis(); trace('setAnalysisScenario', { scenario: state.scenario, hourIndex: state.analysisHour });
  };
  $('analysis-hour').onchange = event => {
    state.analysisHour = Number(event.target.value);
    renderAnalysis(); trace('setAnalysisHour', { scenario: state.scenario, hourIndex: state.analysisHour });
  };
  $('audit-toggle').onclick = () => setAuditOpen(true);
  $('audit-close').onclick = () => setAuditOpen(false);
  $('audit-backdrop').onclick = () => setAuditOpen(false);
  $('audit-refresh').onclick = () => loadAuditManifest();
  $('audit-export').onclick = exportAudit;
  function closeDetail() {
    if (objects[state.selected]?.contract.parent_id) { returnParent(); return; }
    if (entityHistory.length) { backEntity(); return; }
    const old = state.selected; selectObject(null, false);
    if (selectionEntry?.isConnected && !selectionEntry.closest('details:not([open]), [hidden]') && selectionEntry.getClientRects().length) selectionEntry.focus();
    else index.focus(old);
  }
  function returnParent() {
    const parent = objects[state.selected].contract.parent_id;
    const position = entityHistory.findLastIndex(entry => entry.id === parent);
    if (position >= 0) { const entry = entityHistory[position]; entityHistory.splice(position); restoreEntity(entry); }
    else { entityHistory.length = 0; selectObject(parent); index.focus(parent); }
  }
  $('close').onclick = closeDetail;
  $('parent-facility').onclick = returnParent;
  $('back-entity').onclick = backEntity;
  $('route-back').onclick = backEntity;
  $('route-close').onclick = closeRoute;
  $('route-focus').onclick = () => focusRoute(state.route);
  $('route-picker-close').onclick = () => closeRoutePicker(true);
  $('focus').onclick = () => focusObject(state.selected);
  $('relations-toggle').onclick = () => {
    const open = $('relations-panel').hidden; $('relations-panel').hidden = !open;
    $('relations-toggle').setAttribute('aria-expanded', String(open));
    if (!open) { state.connection = null; paintSelection(); renderRelations(); }
  };
  $('overview').onclick = () => {
    rememberView(); entityHistory.length = 0; selectObject(null, false);
    map.jumpTo({ center: [113.207, 41.014], zoom: 12.5, pitch: 0, bearing: 0, elevation: 0 });
  };
  $('project-home').onclick = () => $('overview').click();
  $('back-view').onclick = () => {
    const previous = viewHistory.pop(); if (!previous) return;
    focusToken++; state.cameraPending = false; map.jumpTo(previous); $('back-view').disabled = !viewHistory.length;
  };
  function layers(open, restore = false) {
    $('layers-panel').hidden = !open; $('layers-toggle').setAttribute('aria-expanded', String(open));
    if (restore) $('layers-toggle').focus();
  }
  $('layers-toggle').onclick = () => layers($('layers-panel').hidden);
  $('layers-close').onclick = () => layers(false, true);
  document.addEventListener('pointerdown', e => { if (!e.target.closest('#layers-panel, #layers-toggle')) layers(false); });
  $('models').onchange = event => {
    setModels(event.target.checked);
    if (!state.modelVisible) { entityHistory.length = 0; selectObject(null, false); $('status').textContent = '设施已隐藏；选择已清除。可用同一开关恢复。'; }
    else $('status').textContent = '已载入12个主要设施 · C1 双回路 v1 · A/B 末端候选补模 · 方案位置待核';
    trace('setModels'); map.triggerRepaint();
  };
  $('routes').onchange = event => {
    state.routesVisible = event.target.checked;
    closeRoutePicker();
    if (!state.routesVisible) {
      // A hidden route must not remain in the back stack and reappear when an
      // endpoint card is restored later.
      for (let i = entityHistory.length - 1; i >= 0; i--) {
        if (entityHistory[i].route) entityHistory.splice(i, 1);
      }
    }
    if (!state.routesVisible && state.route) { entityHistory.length = 0; selectObject(null, false); $('routes').focus(); }
    for (const id of ['route-outline', 'route-lines', 'route-selected', 'route-flow-selected']) map.setLayoutProperty(id, 'visibility', state.routesVisible ? 'visible' : 'none');
    trace('setRoutes');
  };
  $('zones').onchange = event => {
    for (const id of ['zone-fill', 'zone-outline']) map.setLayoutProperty(id, 'visibility', event.target.checked ? 'visible' : 'none');
  };
  function panMode(on) {
    if (on) {
      closeRoutePicker();
      if (state.route || entityHistory.some(entry => entry.route)) exitRoutesForPan();
    }
    state.panMode = on; $('pan').setAttribute('aria-pressed', String(on)); map.getCanvas().style.cursor = on ? 'grab' : '';
  }
  $('pan').onclick = () => panMode(!state.panMode);
  $('angle').onclick = () => { rememberView(); map.jumpTo({pitch:map.getPitch() > 1 ? 0 : 42}); };
  map.on('pitchend', () => $('angle').setAttribute('aria-pressed', String(map.getPitch() > 1)));
  document.addEventListener('keydown', event => {
    if (state.auditOpen && event.key === 'Tab') {
      const panel = $('audit-panel');
      const controls = [...panel.querySelectorAll('button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), [tabindex="0"]')].filter(el => el.getClientRects().length);
      const first = controls[0], last = controls.at(-1), active = document.activeElement;
      if (!controls.length) { event.preventDefault(); panel.focus(); }
      else if (event.shiftKey && (active === first || active === panel || !panel.contains(active))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (active === last || active === panel || !panel.contains(active))) { event.preventDefault(); first.focus(); }
      return;
    }
    if (event.key !== 'Escape') return;
    if (state.auditOpen) { setAuditOpen(false); return; }
    if (index.resizing) { index.escape(); return; }
    if (!$('route-picker').hidden) closeRoutePicker(true);
    else if (!$('layers-panel').hidden) layers(false, true);
    else if (geographicReview.escape()) {}
    else if (state.analysisOpen && state.analysisExpanded) setAnalysisExpanded(false);
    else if (state.analysisOpen) setAnalysisOpen(false);
    else if (state.connection) { state.connection = null; paintSelection(); renderRelations(); document.querySelector(`[data-circuit="${state.circuit}"]`)?.focus(); }
    else if (!$('relations-panel').hidden) { $('relations-panel').hidden = true; $('relations-toggle').setAttribute('aria-expanded','false'); $('relations-toggle').focus(); }
    else if (state.route) closeRoute();
    else if (state.selected) closeDetail();
    else if (index.escape()) {}
    else panMode(false);
  });
  state.ready = true; setView('standard');
  $('status').textContent = `已载入12个主要设施 · C1 11个子设备 / 38端口 / 19内部连接 · A/B 32个设备 / 60端口 / 60连接 · M10 ${m10.objects.length}个系统设备/角色 / ${m10.ports.length}端口 / ${m10.connections.length}候选连接 · ${entities.length}对象统一模型 · 源位置待核 · 独立配准 not_run`;
  renderAnalysis(); loadAuditManifest();
  window.m9 = { map, state, errors, events, objects, scene, binding, registry, c1, ab, m10, network, analysisBindings, analysisAsset, auditManifest, geographicReview, index, safeArea, selectObject, focusObject, setView, hitTest,
    snapshot: () => ({ ...state, center: map.getCenter().toArray(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch(),
      renderedFrames: loadedFrames, modelMeshes: pickables.length, rendererViewport: renderer?.getViewport(new THREE.Vector4()).toArray(), drawingBuffer: renderer?.getDrawingBufferSize(new THREE.Vector2()).toArray(), rendererCalls: renderer?.info.render.calls,
      terrainVisible: terrain.some(t => t.visible), errors: [...errors],
      anchors: Object.fromEntries(Object.entries(objects).map(([id, o]) => [id, localToWorld(o.feature.xyz)])) }),
    projectWorld: world => { const p = new THREE.Vector3(...world).applyMatrix4(clipMatrix);
      return [(p.x + 1) / 2 * innerWidth, (1 - p.y) / 2 * innerHeight]; },
    projectModelVertices: id => objects[id].meshes.flatMap(mesh => {
      const p = mesh.geometry.attributes.position, result = [];
      for (let i = 0; i < p.count; i += Math.max(1, Math.floor(p.count / 100))) result.push(window.m9.projectWorld([p.getX(i), p.getY(i), p.getZ(i)]));
      return result;
    }) };
  map.triggerRepaint(); trace('ready');
}
boot().catch(error => { $('status').textContent = '加载失败 · 原型未就绪'; fail('boot', error); });
