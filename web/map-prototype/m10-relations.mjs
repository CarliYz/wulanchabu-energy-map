const circuitLabel = circuit => ({
  DRY_019_HEAT: 'C2 热水候选',
  C2_SECONDARY: 'C2 二次水候选',
  SOURCE: '源侧水候选',
  P1_USER: '一期用户水候选',
  DRY_019_POWER: 'C2 电输入候选',
  DRY_019_CONTROL: 'C2 控制候选',
  PTES_CHARGE: 'PTES 充热候选',
  PTES_DISCHARGE: 'PTES 放热候选',
  PTES_CONTROL: 'PTES 控制候选',
  CONDITIONAL_POWER: '条件绿电候选',
  CO2: '站内 CO₂ 闭环',
  USER: '用户水候选',
  HUB_POWER: '压缩机电输入候选'
}[circuit] || circuit || '候选关系');

export function renderM10Relations(host, runtime, selected, navigateEntity, selectedConnection, highlight) {
  host.replaceChildren();
  const parent = runtime.objects.find(item => item.object_id === selected)?.parent_id;
  const scope = parent || selected;
  const edges = runtime.connections.filter(edge => {
    const from = runtime.objects.find(item => item.object_id === edge.from_object_id);
    const to = runtime.objects.find(item => item.object_id === edge.to_object_id);
    const ids = [edge.from_object_id, edge.to_object_id, from?.parent_id, to?.parent_id];
    return ids.includes(scope) || ids.includes(selected);
  });
  const title = document.createElement('h3');
  title.textContent = 'M10 候选设备与回路';
  host.append(title);
  const note = document.createElement('p');
  note.textContent = '候选端口与可见管段逐一对应；点击管段可高亮，再次点击或 Esc 清除。PTES 默认 IDLE，系统不下发设备指令。';
  host.append(note);
  if (!edges.length) {
    const empty = document.createElement('p');
    empty.textContent = '当前对象暂无 M10 候选关系。';
    host.append(empty);
    return;
  }
  const list = document.createElement('div');
  list.className = 'relation-list';
  for (const edge of edges) {
    const row = document.createElement('article');
    row.className = 'relation-row';
    const from = runtime.objects.find(item => item.object_id === edge.from_object_id);
    const to = runtime.objects.find(item => item.object_id === edge.to_object_id);
    const meta = document.createElement('small');
    const branch = { charge: '充热支路', discharge: '放热支路' }[edge.branch];
    meta.textContent = `${branch || circuitLabel(edge.circuit_id)} · ${edge.medium} · ${edge.role === 'internal' ? '设备内部' : edge.role === 'return' ? '回流' : '候选连接'}`;
    const segment = document.createElement('button');
    segment.textContent = edge.connection_id;
    segment.setAttribute('aria-label', `高亮管段 ${edge.connection_id}`);
    segment.setAttribute('aria-pressed', String(selectedConnection === edge.connection_id));
    segment.dataset.connection = edge.connection_id;
    segment.onclick = () => highlight(selectedConnection === edge.connection_id ? null : edge.connection_id);
    const buttons = document.createElement('div');
    buttons.className = 'relation-buttons';
    const fromButton = document.createElement('button');
    fromButton.textContent = `${from?.short_name || edge.from_object_id} →`;
    fromButton.dataset.networkTarget = edge.from_object_id;
    fromButton.onclick = () => navigateEntity(edge.from_object_id, fromButton);
    const toButton = document.createElement('button');
    toButton.textContent = `→ ${to?.short_name || edge.to_object_id}`;
    toButton.dataset.networkTarget = edge.to_object_id;
    toButton.onclick = () => navigateEntity(edge.to_object_id, toButton);
    buttons.append(fromButton, toButton);
    const ports = document.createElement('small');
    ports.textContent = `${edge.from_port_id} → ${edge.to_port_id}`;
    row.append(meta, segment, buttons, ports);
    list.append(row);
  }
  host.append(list);
  if (selectedConnection) {
    const clear = document.createElement('button'); clear.textContent = '清除管段高亮';
    clear.onclick = () => highlight(null); host.append(clear);
  }
}
