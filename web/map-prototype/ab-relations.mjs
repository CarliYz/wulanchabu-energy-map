export const AB_CIRCUITS = {
  heat: '热水回路',
  control: '控制信号',
};

const MEDIUM = { water: '热水', signal: '控制信号' };

function circuitLabel(id) {
  if (id.endsWith('_CONTROL')) return AB_CIRCUITS.control;
  if (id.endsWith('_HEAT')) return AB_CIRCUITS.heat;
  return id;
}

function circuitKey(id) {
  return id.endsWith('_CONTROL') ? 'control' : 'heat';
}

export function renderABRelations(host, graph, selected, filter, connection, navigate, highlight, changeFilter) {
  host.replaceChildren();
  const note = document.createElement('p');
  note.textContent = 'A/B 末端为候选示意补模；热水与控制信号分开表达，未接入城市干线，也未完成水力验算。';
  host.append(note);

  const parentIds = new Set(graph.parent_facilities.map(item => item.object_id));
  if (parentIds.has(selected)) {
    const children = graph.objects.filter(item => item.parent_id === selected);
    const title = document.createElement('h3'); title.textContent = `${graph.parent_facilities.find(item => item.object_id === selected)?.zone || selected} 末端设备 · ${children.length}`; host.append(title);
    const list = document.createElement('div'); list.className = 'device-list';
    children.forEach(item => {
      const button = document.createElement('button');
      button.textContent = `${item.short_name} ${item.name}`;
      button.dataset.device = item.object_id;
      button.onclick = () => navigate(item.object_id, button);
      list.append(button);
    });
    host.append(list);
  }

  const filters = document.createElement('nav'); filters.className = 'circuit-filters'; filters.setAttribute('aria-label', 'A/B 回路筛选');
  for (const [id, name] of [['all', '全部连接'], ['heat', AB_CIRCUITS.heat], ['control', AB_CIRCUITS.control]]) {
    const button = document.createElement('button'); button.textContent = name; button.dataset.circuit = id;
    button.setAttribute('aria-pressed', String(filter === id)); button.onclick = () => changeFilter(id); filters.append(button);
  }
  host.append(filters);

  const selectedItem = graph.objects.find(item => item.object_id === selected);
  const parentId = selectedItem?.parent_id || (parentIds.has(selected) ? selected : null);
  const edges = graph.connections.filter(edge => {
    const sameParent = !parentId || edge.parent_id === parentId;
    const sameCircuit = filter === 'all' || circuitKey(edge.circuit_id) === filter;
    const touchesSelected = parentIds.has(selected) || edge.from_object_id === selected || edge.to_object_id === selected;
    return sameParent && sameCircuit && touchesSelected;
  });
  const summary = document.createElement('p'); summary.textContent = `${edges.length} 条候选连接 · 供回方向以端口定义为准`;
  summary.id = 'ab-connection-summary'; host.append(summary);

  const names = new Map(graph.objects.map(item => [item.object_id, item.name]));
  for (const edge of edges) {
    const row = document.createElement('div'); row.className = 'connection-row'; row.dataset.edgeRow = edge.connection_id;
    const button = document.createElement('button'); button.dataset.connection = edge.connection_id;
    const role = edge.role === 'return' ? '回流' : edge.role === 'supply' ? '供流' : edge.role === 'control' ? '控制' : '内部';
    button.textContent = `${edge.connection_id} · ${circuitLabel(edge.circuit_id)} · ${role}`;
    button.setAttribute('aria-pressed', String(connection === edge.connection_id));
    button.onclick = () => highlight(connection === edge.connection_id ? null : edge.connection_id); row.append(button);
    const endpoints = document.createElement('div'); endpoints.className = 'connection-endpoints';
    for (const [index, id] of [edge.from_object_id, edge.to_object_id].entries()) {
      if (index) endpoints.append(document.createTextNode(' → '));
      const node = document.createElement('button'); node.textContent = names.get(id) || id;
      node.setAttribute('aria-label', `${edge.connection_id} ${index ? '终点' : '起点'} ${names.get(id) || id}`);
      node.onclick = () => navigate(id, node); endpoints.append(node);
    }
    const ports = document.createElement('small'); ports.textContent = `${edge.from_port_id} → ${edge.to_port_id}`;
    row.append(endpoints, ports); host.append(row);
  }
  if (connection) {
    const clear = document.createElement('button'); clear.textContent = '清除管段高亮'; clear.id = 'clear-connection';
    clear.onclick = () => highlight(null); host.append(clear);
  }
  if (selectedItem && !parentIds.has(selected)) {
    const title = document.createElement('h3'); title.textContent = '设备端口'; host.append(title);
    for (const port of graph.ports.filter(item => item.object_id === selected)) {
      const row = document.createElement('p'); row.dataset.port = port.port_id;
      row.textContent = `${circuitLabel(port.circuit_id)} · ${MEDIUM[port.medium] || port.medium} · ${port.direction === 'in' ? '入口' : '出口'}`;
      const id = document.createElement('small'); id.textContent = port.port_id; row.append(id); host.append(row);
    }
  }
}
