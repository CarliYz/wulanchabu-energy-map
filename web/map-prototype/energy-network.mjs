export const ROUTES_SHA256 = 'b1f5544c37c4b574913a6fed18709b9382dbc98ddb0acfb6c5112d53c22fba83';
export const PHASES = { source_candidate: '源侧汇集候选', P1_candidate: '一期近端直供候选',
  P2_candidate: '二期提温候选', future_candidate: '后续预留候选', storage_candidate: '储热支路候选' };
export const ROUTE_STYLES = {
  source_supply: { label: '源侧水 · 取热去程', color: '#adede2' },
  source_return: { label: '源侧水 · 返回源端', color: '#6fb4c6' },
  user_supply: { label: '用户水 · 供水', color: '#f2bb84' },
  user_return: { label: '用户水 · 回水', color: '#98ddec' },
  storage_charge: { label: '用户水 · 储热支路充热去程', color: '#ead49a' },
  storage_return: { label: '用户水 · 储热支路返回枢纽', color: '#c7b8e8' }
};

export function routeStyle(route) {
  if (route.route_id === 'PTES_CHARGE') return 'storage_charge';
  if (route.route_id === 'PTES_RETURN') return 'storage_return';
  return `${route.circuit === 'source_water' ? 'source' : 'user'}_${route.route_id.endsWith('RETURN') ? 'return' : 'supply'}`;
}

// The original geometry is stored station→user even for most return pipes.
// Use explicit flow endpoints, never the order in which vertices were drawn.
export function flowCoordinates(route) {
  const forward = route.geometry_start_node === route.flow_from && route.geometry_end_node === route.flow_to;
  const reverse = route.geometry_start_node === route.flow_to && route.geometry_end_node === route.flow_from;
  if (!forward && !reverse) throw new Error(`Route flow/geometry mismatch: ${route.route_id}`);
  return reverse ? [...route.sampled_xyz].reverse() : [...route.sampled_xyz];
}

export function createEnergyNetwork(routes, facilities) {
  const entities = new Map(facilities.map(o => [o.object_id, o]));
  const edges = new Map(routes.map(r => [r.route_id, r]));
  if (edges.size !== routes.length) throw new Error('Duplicate route ID');
  const city = { id: 'CITY_INTERFACE_V2', name: '城市拟接入接口', kind: 'interface' };
  function endpoint(id) {
    if (entities.has(id)) return { id, name: entities.get(id).name, kind: 'facility' };
    if (edges.has(id)) return { id, name: id === 'P2_V2_SUPPLY' ? '二期用户供水干线' : id === 'P2_V2_RETURN' ? '二期用户回水干线' : `${id} · ${ROUTE_STYLES[routeStyle(edges.get(id))].label}`, kind: 'route' };
    if (id === city.id) return city;
    throw new Error(`Unbound route endpoint: ${id}`);
  }
  for (const route of routes) {
    if (!PHASES[route.phase] || !['source_water', 'user_water'].includes(route.circuit)) throw new Error(`Unknown route semantics: ${route.route_id}`);
    if (!Number.isFinite(route.geometry_length_m) || route.geometry_length_m <= 0 || route.sampled_xyz.length < 2) throw new Error(`Invalid route geometry: ${route.route_id}`);
    endpoint(route.flow_from); endpoint(route.flow_to); flowCoordinates(route);
  }
  function describe(id) {
    const route = edges.get(id);
    if (!route) throw new Error(`Unknown route: ${id}`);
    const style = ROUTE_STYLES[routeStyle(route)];
    let explanation;
    if (route.phase === 'P1_candidate') explanation = '一期近端隔离换热直供 A 区。线路几何从枢纽场址出发，表示独立板换与用户水边界，不表示必须经过二期 CO₂ 压缩机。源水与用户水只换热、不混水。';
    else if (route.phase === 'source_candidate') explanation = '数据中心余热候选水路；源端独立冷却安全通道仍需保留。取热接口、可用功率与合同未落实；不能把教学源池赋给具名机房。';
    else if (route.phase === 'storage_candidate') explanation = 'PTES 为并列调节支路，用户供水可直接从枢纽进入干线。原表只给充热去程和返回枢纽，放热阀序、温区与接入拓扑待核；PTES_RETURN 不等于已确认放热线。';
    else explanation = '二期热泵将源侧余热经站内 CO₂ 制冷循环传给独立用户水。B 区、C 区及城市分别分支，不串联混水；C 区为后续预留，尚未接入。85℃是报告目标，不是当前实测。';
    return { ...route, style: routeStyle(route), label: style.label, from: endpoint(route.flow_from), to: endpoint(route.flow_to),
      phase_label: PHASES[route.phase], explanation, status: '候选 · 接口、路网与穿越待核 · 无实际流量',
      source: `方案线路表 candidate-v2 / ${id}；工程方案第5–6节` };
  }
  function related(id) { return routes.filter(r => r.flow_from === id || r.flow_to === id).map(r => describe(r.route_id)); }
  function context(id) {
    if (id === 'DEMO_013') return { title: 'A 区独立科研', text: 'CO₂ 冷热与土壤跨季储热属于独立科研范围，未自动接入商业主热网。', links: [] };
    if (id === 'STORE_012') return { title: 'PTES · 并列储热支路', text: '充热与返回按原表展示；放热功能有规划，但路径与阀序待核。50万m³是规划体积，不能据此宣布保供时长。', links: ['PTES_CHARGE', 'PTES_RETURN', 'HUB_011', 'P2_V2_SUPPLY'] };
    if (['AGRI_014', 'AGRI_015'].includes(id)) return { title: '一期 · A 区近端隔离直供', text: '约45℃源水是方案假设，经隔离板换向独立用户水传热；不依赖二期 CO₂ 压缩机，温级匹配与接口仍待核。', links: [id + '_SUPPLY', id + '_RETURN', 'HUB_011', 'DC_004', 'DC_005', 'DC_006'] };
    if (id === 'HUB_011') return { title: '源区 → 隔离直供 / 二期提温', text: '源侧水、站内 CO₂、用户水分成三个回路。站内：蒸发器 → 压缩机（电输入）→ 气冷器 → 节流阀 → 蒸发器。CO₂ 不沿城市或农业管线输送；A 区一期由隔离板换直供。', links: ['DC_004', 'DC_005', 'DC_006', 'AGRI_014_SUPPLY', 'AGRI_015_SUPPLY', 'P2_V2_SUPPLY', 'P2_V2_RETURN', 'STORE_012'] };
    if (id.startsWith('DC_')) return { title: '源端 · 取热与冷却分开', text: '候选源水汇入枢纽换热边界，利用后返回源端；保留数据中心自身冷却。余热能力、出水温度和交付均待实测。', links: [id + '_SOURCE', id + '_SOURCE_RETURN', 'HUB_011'] };
    const text = id === 'DRY_019' ? '秋季低温烘干采用后续候选支线。45℃源水不能直接产生50–55℃热风，需单独核对提温与电输入。' :
      id === 'AGRI_018' ? '用户供回支线分别接二期干线，经独立换热进入区内回路。C1 一次侧仍预留未接；热水与营养液各自循环。PTES 为并列调节支路。' :
      `${entities.get(id).name}的供回支线分别接二期用户干线，经本区独立换热向温室供热。本区末端温控、接口及工况待核；PTES 为并列调节支路。`;
    return { title: id === 'AGRI_018' || id === 'DRY_019' ? '后续预留 · C 区用户分支' : '二期 · B 区用户分支', text,
      links: [id + '_SUPPLY', id + '_RETURN', 'P2_V2_SUPPLY', 'P2_V2_RETURN', 'HUB_011', 'STORE_012'] };
  }
  return { routes, endpoint, describe, related, context, has: id => edges.has(id) };
}

function el(tag, text, className) {
  const node = document.createElement(tag); if (text) node.textContent = text; if (className) node.className = className; return node;
}
function link(network, id, navigate, prefix = '') {
  const target = network.endpoint(id), button = el('button', prefix + target.name);
  button.dataset.networkTarget = id;
  button.setAttribute('aria-label', `${target.kind === 'route' ? '查看线路' : '定位设备'} ${id}`);
  if (target.kind === 'interface') { button.disabled = true; button.textContent += ' · 未建实体'; }
  else button.onclick = () => navigate(target, button);
  return button;
}

const ENERGY_STORIES = {
  AGRI_018: {
    title: '能源解释纵切',
    lead: '从 C1 二次水向上回查到热泵用户侧；源侧和 PTES 是并列候选支路，不把它们画成一条必经串联。',
    lanes: [
      { title: '用户侧热水 · 反查上游', description: 'C1 通过候选用户侧干线接到热泵用户侧，C1 外接仍是预留。', steps: [
        ['AGRI_018', 'C1 二次热水'], ['AGRI_018_SUPPLY', 'C1 用户侧供水支线'], ['P2_V2_SUPPLY', '二期用户供水干线'], ['HUB_011', '热泵用户侧']
      ] },
      { title: 'PTES · 并列调节支路', description: 'PTES 只表达充热/返回接口；放热阀序和调度条件待核。', steps: [
        ['HUB_011', '热泵用户侧'], ['PTES_CHARGE', 'PTES 充热'], ['STORE_012', 'PTES 池式储热'], ['PTES_RETURN', 'PTES 返回枢纽']
      ] },
      { title: '源侧余热 · 候选入口', description: '数据中心源水与用户水经隔离换热；源端自身冷却通道仍需保留。', steps: [
        ['DC_004_SOURCE', 'DC1 源侧水'], ['DC_005_SOURCE', 'DC2 源侧水'], ['DC_006_SOURCE', 'DC3 源侧水']
      ] },
      { title: '站内 CO₂ · 闭合循环', description: '蒸发器 → 压缩机 → 气冷器 → 节流阀 → 蒸发器；CO₂ 只在热泵站内循环，不沿城市或农业管线输送。', steps: [] }
    ]
  },
  HUB_011: {
    title: '热泵能源关系',
    lead: '热泵枢纽把源侧水、站内 CO₂ 和用户侧水分开表达；电输入只属于站内压缩机。',
    lanes: [
      { title: '用户侧水 · C1 示例', description: '用户侧热水经二期干线进入 C1；其他 B/C 分支仍按候选关系分别展示。', steps: [
        ['HUB_011', '热泵用户侧'], ['P2_V2_SUPPLY', '二期用户供水干线'], ['AGRI_018_SUPPLY', 'C1 用户侧供水支线'], ['AGRI_018', 'C1 二次热水']
      ] },
      { title: 'PTES · 并列调节', description: '充热与返回是独立支路，不等于所有用户热量都必须经过储热。', steps: [
        ['HUB_011', '热泵用户侧'], ['PTES_CHARGE', 'PTES 充热'], ['STORE_012', 'PTES 池式储热'], ['PTES_RETURN', 'PTES 返回枢纽']
      ] },
      { title: '源侧水 · 三个候选来源', description: '候选源侧水进入枢纽换热边界，余热能力、温度和交付尚待实测。', steps: [
        ['DC_004_SOURCE', 'DC1 源侧水'], ['DC_005_SOURCE', 'DC2 源侧水'], ['DC_006_SOURCE', 'DC3 源侧水']
      ] },
      { title: 'CO₂ 与电输入 · 仅站内', description: '蒸发器、压缩机、气冷器和节流阀组成站内闭环；不生成外部 CO₂ 管线。', steps: [] }
    ]
  },
  STORE_012: {
    title: 'PTES 充放关系',
    lead: '热库是热泵用户水侧的并列调节支路，当前只展示方案接口和待核边界。',
    lanes: [
      { title: '充热 / 返回枢纽', description: '按连接合同显示去程和返回，不扩写成已验证的储热容量或放热时长。', steps: [
        ['HUB_011', '热泵用户侧'], ['PTES_CHARGE', 'PTES 充热'], ['STORE_012', 'PTES 池式储热'], ['PTES_RETURN', 'PTES 返回枢纽']
      ] }
    ]
  },
  DC_004: { title: '源端候选关系', lead: 'DC1 只提供候选源侧水接口，数据中心自身冷却与项目外部接入仍待核。', lanes: [{ title: '源侧水 · 隔离边界', description: '源水进入热泵枢纽后返回源端；不与用户水或站内 CO₂ 混接。', steps: [['DC_004', 'DC1 数据中心'], ['DC_004_SOURCE', 'DC1 源侧供水'], ['HUB_011', '热泵枢纽'], ['DC_004_SOURCE_RETURN', 'DC1 源侧回水']] }] },
  DC_005: { title: '源端候选关系', lead: 'DC2 只提供候选源侧水接口，数据中心自身冷却与项目外部接入仍待核。', lanes: [{ title: '源侧水 · 隔离边界', description: '源水进入热泵枢纽后返回源端；不与用户水或站内 CO₂ 混接。', steps: [['DC_005', 'DC2 数据中心'], ['DC_005_SOURCE', 'DC2 源侧供水'], ['HUB_011', '热泵枢纽'], ['DC_005_SOURCE_RETURN', 'DC2 源侧回水']] }] },
  DC_006: { title: '源端候选关系', lead: 'DC3 只提供候选源侧水接口，数据中心自身冷却与项目外部接入仍待核。', lanes: [{ title: '源侧水 · 隔离边界', description: '源水进入热泵枢纽后返回源端；不与用户水或站内 CO₂ 混接。', steps: [['DC_006', 'DC3 数据中心'], ['DC_006_SOURCE', 'DC3 源侧供水'], ['HUB_011', '热泵枢纽'], ['DC_006_SOURCE_RETURN', 'DC3 源侧回水']] }] }
};

export function renderEnergyStory(host, network, id, navigate) {
  const story = ENERGY_STORIES[id];
  if (!story) return;
  const section = el('section', '', 'energy-story');
  section.setAttribute('aria-label', '能源解释纵切');
  section.append(el('h3', story.title), el('p', story.lead));
  for (const lane of story.lanes) {
    const laneNode = el('div', '', 'energy-story-lane');
    laneNode.append(el('h4', lane.title), el('p', lane.description));
    const steps = el('div', '', 'energy-story-steps');
    lane.steps.forEach(([targetId, label], index) => {
      const target = network.endpoint(targetId), button = link(network, targetId, navigate);
      button.textContent = label;
      button.setAttribute('aria-label', `能源路径定位 ${targetId} · ${lane.title}`);
      button.dataset.energyStoryTarget = targetId;
      steps.append(button);
      if (index < lane.steps.length - 1) steps.append(el('span', '→', 'energy-story-arrow'));
    });
    laneNode.append(steps);
    section.append(laneNode);
  }
  host.append(section);
}

export function renderNetworkRelations(host, network, id, navigate) {
  const context = network.context(id), section = el('section', '', 'energy-context');
  const related = network.related(id), local = new Set(related.map(route => route.route_id));
  section.append(el('h3', context.title), el('p', context.text));
  const links = el('div', '', 'network-links');
  for (const target of context.links.filter(target => !local.has(target))) links.append(link(network, target, navigate));
  section.append(links); host.append(section);
  for (const route of related) {
    const row = el('div', '', 'network-route-row');
    const button = el('button', `${route.route_id} · ${route.label}`);
    button.dataset.networkTarget = route.route_id; button.setAttribute('aria-label', `查看线路 ${route.route_id}`);
    button.onclick = () => navigate({ id: route.route_id, kind: 'route' }, button);
    row.append(button, el('small', `${route.from.name} → ${route.to.name}`), el('small', route.phase_label)); host.append(row);
  }
  if (!related.length && id !== 'DEMO_013') host.append(el('p', '没有绑定外部候选线路。'));
}
export function renderRouteDetail(host, network, id, navigate) {
  const route = network.describe(id); host.replaceChildren();
  host.append(el('p', route.explanation, 'energy-context'));
  const endpoints = el('div', '', 'route-endpoints');
  endpoints.append(link(network, route.flow_from, navigate, '起点 · '), el('span', '→'), link(network, route.flow_to, navigate, '终点 · ')); host.append(endpoints);
  const table = el('dl');
  for (const [key, value] of [ ['所属系统', route.label], ['阶段', route.phase_label], ['状态', route.status],
    ['方向', `${route.from.name} → ${route.to.name}`], ['显示折线长度', `${route.geometry_length_m.toFixed(1)} m（本段，非施工量）`],
    ['流向依据', `${route.flow_from} → ${route.flow_to}（原表 flow 字段）`], ['端口 / 工况', '外接端口几何、温度、流量、压降均未核'], ['来源', route.source] ]) {
    table.append(el('dt', key), el('dd', value));
  }
  host.append(table);
  const adjacent = network.related(id);
  if (adjacent.length) {
    host.append(el('h3', '分支与汇接'));
    const list = el('div', '', 'network-links');
    for (const edge of adjacent) list.append(link(network, edge.route_id, navigate));
    host.append(list);
  }
  host.append(el('p', '静态箭头仅表示方案流向；无对象级结果，不播放实际流量或源退出/耗尽动画。', 'warning'));
}
