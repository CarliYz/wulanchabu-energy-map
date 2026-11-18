export const ANALYSIS_SOURCE_SHA256 = 'e5819a31bb537a41b357bfccf960240bb918c4c0abea76c648a8705bd98cd603';
export const ANALYSIS_BINDING_SHA256 = '9abdd05a682bed857364fd5c25bb1fc88c1878690e854bc09aa24b59eb70d8f6';
export const ANALYSIS_HOUR_RANGE = { min: 0, max: 23 };

function format(value, unit) {
  return `${Number(value || 0).toFixed(1)} ${unit}`;
}

export function formatMw(value) { return format(value, 'MW'); }
export function formatMwh(value) { return format(value, 'MWh'); }

export function resolveAnalysis({ asset, bindings, objectId, scenarioId = 'normal', hourIndex = null }) {
  const binding = bindings.objects?.[objectId];
  if (!binding || binding.result_status !== 'available') {
    return {
      status: 'unavailable',
      objectId,
      scenarioId,
      binding: binding || null,
      reason: binding?.scope || '当前对象暂无绑定的对象级分析结果。'
    };
  }
  const scenario = bindings.scenarios?.[scenarioId] || bindings.scenarios.normal;
  const resultId = binding.scenario_results?.[scenarioId] || scenario.result_id;
  const rows = (asset.rows || []).filter(row => row.scenario_id === resultId);
  const summary = asset.summary?.[resultId];
  if (!rows.length || !summary) {
    return { status: 'invalid', objectId, scenarioId, reason: `分析资产缺少结果 ${resultId}` };
  }
  const requestedHour = hourIndex === null || hourIndex === undefined
    ? scenarioId === 'storage-depleted'
      ? (rows.find(item => item.storage_end_mwh <= 0)?.hour_index ?? rows.at(-1).hour_index)
      : scenarioId === 'source-outage'
        ? (rows.find(item => item.source_mw === 0)?.hour_index ?? rows[0].hour_index)
        : 14
    : Number(hourIndex);
  if (!Number.isInteger(requestedHour) || requestedHour < ANALYSIS_HOUR_RANGE.min || requestedHour > ANALYSIS_HOUR_RANGE.max) {
    return { status: 'invalid', objectId, scenarioId, reason: `分析时段必须是 ${ANALYSIS_HOUR_RANGE.min}–${ANALYSIS_HOUR_RANGE.max} 的整数小时` };
  }
  const row = rows.find(item => item.hour_index === requestedHour);
  if (!row) return { status: 'invalid', objectId, scenarioId, reason: `分析资产缺少时段 h${requestedHour}` };
  return {
    status: 'available', objectId, scenarioId, scenario, binding, resultId, rows, summary, row,
    time: { hour_index: row.hour_index, timestamp: null, basis: row.time_basis || 'unknown' }
  };
}

export function analysisStatusClass(result) {
  if (result.status === 'invalid') return 'risk';
  if (result.status === 'unavailable') return 'pending';
  return result.scenario?.status || '';
}

export function analysisSummary(result) {
  if (result.status !== 'available') return result.reason;
  const prefix = result.scenario.derived ? '派生分析 · ' : '';
  return `${prefix}h${result.row.hour_index} · 热负荷 ${formatMw(result.row.demand_mw)} · 源热 ${formatMw(result.row.source_mw)} · PTES ${formatMwh(result.row.storage_end_mwh)} · ${result.time.basis}`;
}
