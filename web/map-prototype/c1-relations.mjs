export const CIRCUITS = { C1_HEAT: '热水回路', C1_NUTRIENT: '营养液回路', C1_CONTROL: '控制信号', USER: '一次侧预留' };
const MEDIUM = { water: '热水', nutrient: '营养液', signal: '信号' };

export function renderC1Relations(host, graph, selected, filter, connection, navigate, highlight, changeFilter) {
  host.replaceChildren();
  const note = document.createElement('p');
  note.textContent = '热水与营养液各自循环；板换两侧只传热不混水。以下为同版模型连接，未进行水力验算；一次侧仅预留，未投运。';
  host.append(note);
  if (selected === graph.parent_id) {
    const title = document.createElement('h3'); title.textContent = 'C1 子设备 · 11'; host.append(title);
    const list = document.createElement('div'); list.className = 'device-list';
    graph.objects.forEach(item => {
      const button = document.createElement('button'); button.textContent = item.name;
      button.dataset.device = item.object_id; button.onclick = () => navigate(item.object_id, button); list.append(button);
    });
    host.append(list);
  }
  const filters = document.createElement('nav'); filters.className = 'circuit-filters'; filters.setAttribute('aria-label', 'C1 回路筛选');
  for (const [id, name] of [['all', '全部连接'], ...Object.entries(CIRCUITS).filter(([id]) => id !== 'USER')]) {
    const button = document.createElement('button'); button.textContent = name; button.dataset.circuit = id;
    button.setAttribute('aria-pressed', String(filter === id)); button.onclick = () => changeFilter(id); filters.append(button);
  }
  host.append(filters);
  const edges = graph.connections.filter(e => (filter === 'all' || e.circuit_id === filter) &&
    (selected === graph.parent_id || e.from_object_id === selected || e.to_object_id === selected));
  const summary = document.createElement('p'); summary.textContent = `${edges.length} 条拟定内部连接 · 供回方向以端口定义为准`;
  summary.id = 'connection-summary'; host.append(summary);
  const names = new Map(graph.objects.map(o => [o.object_id, o.name]));
  for (const edge of edges) {
    const row = document.createElement('div'); row.className = 'connection-row'; row.dataset.edgeRow = edge.connection_id;
    const button = document.createElement('button'); button.dataset.connection = edge.connection_id;
    button.textContent = `${edge.connection_id} · ${CIRCUITS[edge.circuit_id]} · ${edge.medium === 'signal' ? '传输' : edge.role === 'return' ? '回流' : '供流'}`;
    button.setAttribute('aria-pressed', String(connection === edge.connection_id));
    button.onclick = () => highlight(connection === edge.connection_id ? null : edge.connection_id); row.append(button);
    const endpoints = document.createElement('div'); endpoints.className = 'connection-endpoints';
    for (const [i, id] of [edge.from_object_id, edge.to_object_id].entries()) {
      if (i) endpoints.append(document.createTextNode(' → '));
      const node = document.createElement('button'); node.textContent = names.get(id);
      node.setAttribute('aria-label', `${edge.connection_id} ${i ? '终点' : '起点'} ${names.get(id)}`);
      node.onclick = () => navigate(id, node); endpoints.append(node);
    }
    const ports = document.createElement('small'); ports.textContent = `${edge.from_port_id} → ${edge.to_port_id}`;
    row.append(endpoints, ports); host.append(row);
  }
  if (connection) {
    const clear = document.createElement('button'); clear.textContent = '清除管段高亮'; clear.id = 'clear-connection';
    clear.onclick = () => highlight(null); host.append(clear);
  }
  if (selected !== graph.parent_id) {
    const title = document.createElement('h3'); title.textContent = '设备端口'; host.append(title);
    for (const port of graph.ports.filter(p => p.object_id === selected)) {
      const row = document.createElement('p'); row.dataset.port = port.port_id;
      row.textContent = `${CIRCUITS[port.circuit_id]} · ${MEDIUM[port.medium]} · ${port.direction === 'in' ? '入口' : '出口'}${port.circuit_id === 'USER' ? ' · 预留未接' : ''}`;
      const id = document.createElement('small'); id.textContent = port.port_id; row.append(id); host.append(row);
    }
  }
}
