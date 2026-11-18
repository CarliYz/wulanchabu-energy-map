// Shared state seam for M9/M10. The existing viewer is migrated in those tickets.
export function initialViewerState() {
  return {
    selectedObjectId: null, selectedCircuitId: null,
    viewMode: 'standard', lastBaseView: 'standard',
    layerVisibility: { energy: true, agriculture: true, pipelines: true, terrain: true },
    cameraHistory: [], detailTab: 'properties',
    analysisScenarioId: 'MVP_NORMAL', analysisTime: { hour_index: 0, timestamp: null },
    overlayStack: [], indexExpanded: false, search: '', toolMode: 'free',
    selectionRevision: 0, resultRequestRevision: 0, resultStatus: 'idle', objectResults: [],
  };
}

function invalidateResults(state) {
  state.resultRequestRevision += 1;
  state.resultStatus = 'idle';
  state.objectResults = [];
}

export function resultRequestKey(state) {
  return {
    objectId: state.selectedObjectId, scenarioId: state.analysisScenarioId,
    time: structuredClone(state.analysisTime), selectionRevision: state.selectionRevision,
    requestRevision: state.resultRequestRevision,
  };
}

export function acceptsResult(state, key) {
  return key.objectId !== null && key.objectId === state.selectedObjectId
    && key.scenarioId === state.analysisScenarioId
    && key.selectionRevision === state.selectionRevision
    && key.requestRevision === state.resultRequestRevision
    && key.time.hour_index === state.analysisTime.hour_index
    && key.time.timestamp === state.analysisTime.timestamp;
}

function closeSelection(state) {
  state.selectedObjectId = null;
  state.selectedCircuitId = null;
  state.detailTab = 'properties';
  state.selectionRevision += 1;
  invalidateResults(state);
}

function validAnalysisTime(time) {
  if (!time || Object.keys(time).sort().join(',') !== 'hour_index,timestamp') return false;
  const hourValid = time.hour_index === null || Number.isInteger(time.hour_index) && time.hour_index >= 0;
  let timestampValid = time.timestamp === null;
  if (typeof time.timestamp === 'string') {
    const match = /^(\d{4})-(\d{2})-(\d{2})T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/i.exec(time.timestamp);
    timestampValid = !!match && Number.isFinite(Date.parse(time.timestamp))
      && Number(match[3]) <= new Date(Date.UTC(Number(match[1]), Number(match[2]), 0)).getUTCDate();
  }
  return hourValid && timestampValid && (time.hour_index !== null || time.timestamp !== null);
}

export function transition(state, action, objects) {
  const next = structuredClone(state);
  switch (action.type) {
    case 'select': {
      if (!objects.has(action.objectId)) throw new Error(`Unknown object_id: ${action.objectId}`);
      if (action.camera) next.cameraHistory.push(structuredClone(action.camera));
      next.selectedObjectId = action.objectId;
      next.selectedCircuitId = null;
      next.detailTab = 'properties';
      next.selectionRevision += 1;
      invalidateResults(next);
      return next;
    }
    case 'close-selection': closeSelection(next); return next;
    case 'set-view':
      if (!['standard', 'satellite', 'data'].includes(action.mode)) throw new Error('Unknown view mode');
      next.viewMode = action.mode;
      if (action.mode !== 'data') next.lastBaseView = action.mode;
      return next;
    case 'return-base': next.viewMode = next.lastBaseView; return next;
    case 'set-analysis':
      if (typeof action.scenarioId !== 'string' || !action.scenarioId.trim()) throw new Error('Analysis scenario is required');
      if (!validAnalysisTime(action.time)) {
        throw new Error('Analysis time requires a valid hour or timestamp');
      }
      next.analysisScenarioId = action.scenarioId;
      next.analysisTime = structuredClone(action.time);
      invalidateResults(next);
      return next;
    case 'request-results':
      if (!next.selectedObjectId) throw new Error('Select an object before requesting results');
      invalidateResults(next);
      next.resultStatus = 'loading';
      return next;
    case 'receive-results': {
      if (!acceptsResult(state, action.key)) return state;
      const rows = action.rows.filter(r => r.binding_status === 'bound'
        && r.object_id === state.selectedObjectId && r.scenario_id === state.analysisScenarioId
        && r.hour_index === state.analysisTime.hour_index && r.timestamp === state.analysisTime.timestamp);
      next.objectResults = rows;
      next.resultStatus = rows.some(r => r.status === 'available') ? 'available' : 'missing_inputs';
      return next;
    }
    case 'fail-results':
      if (!acceptsResult(state, action.key)) return state;
      next.resultStatus = 'error'; next.objectResults = []; return next;
    case 'set-tab':
      if (!['properties', 'relations', 'screenshots'].includes(action.tab)) throw new Error('Unknown detail tab');
      next.detailTab = action.tab; return next;
    case 'open-overlay':
      if (!['analysis', 'layers', 'audit', 'image'].includes(action.overlay)) throw new Error('Unknown overlay');
      next.overlayStack = [...next.overlayStack.filter(x => x !== action.overlay), action.overlay];
      return next;
    case 'close-overlay': next.overlayStack = next.overlayStack.filter(x => x !== action.overlay); return next;
    case 'set-index': next.indexExpanded = action.expanded; return next;
    case 'set-search': next.search = action.query; return next;
    case 'set-tool':
      if (!['free', 'pan', 'rotate'].includes(action.mode)) throw new Error('Unknown tool mode');
      next.toolMode = action.mode; return next;
    case 'set-layer':
      if (!(action.layer in next.layerVisibility)) throw new Error('Unknown layer');
      next.layerVisibility[action.layer] = action.visible;
      if (!action.visible && next.selectedObjectId && action.hiddenObjectIds?.includes(next.selectedObjectId)) closeSelection(next);
      return next;
    case 'escape': {
      // Exit one level, regardless of which lower-priority surface opened last.
      for (const group of [['image', 'audit'], ['layers']]) {
        const top = [...next.overlayStack].reverse().find(x => group.includes(x));
        if (top) { next.overlayStack.splice(next.overlayStack.indexOf(top), 1); return next; }
      }
      if (next.selectedObjectId && next.detailTab !== 'properties') { next.detailTab = 'properties'; return next; }
      if (next.selectedObjectId) { closeSelection(next); return next; }
      if (next.overlayStack.includes('analysis')) { next.overlayStack = next.overlayStack.filter(x => x !== 'analysis'); return next; }
      if (next.search) { next.search = ''; return next; }
      if (next.indexExpanded) { next.indexExpanded = false; return next; }
      next.toolMode = 'free';
      return next;
    }
    default: throw new Error(`Unknown ViewerState action: ${action.type}`);
  }
}
