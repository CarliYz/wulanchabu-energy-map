const GROUPS = [['dc', '数据中心 · 源区', '源'], ['energy', '能源枢纽', '能'],
  ['a', 'A 区 · 种薯 / 菌房 / 科研', 'A'], ['b', 'B 区 · 番茄 / 草莓', 'B'], ['c', 'C 区 · 水培 / 秋烘', 'C']];

export function createFacilityIndex(registry, onSelect, onGroup) {
  const panel = document.getElementById('index-panel'), host = document.getElementById('index');
  const toggle = document.getElementById('index-toggle'), search = document.getElementById('entity-search');
  const tree = document.getElementById('entity-tree'), rows = new Map(), groups = new Map(), branches = new Map();
  let expanded = false, width = 288, drag = null;
  function setExpanded(value, returnFocus = false) {
    expanded = value; panel.hidden = !value; host.classList.toggle('expanded', value);
    toggle.setAttribute('aria-expanded', String(value)); toggle.textContent = value ? '‹' : '›';
    toggle.setAttribute('aria-label', value ? '收起实体索引' : '展开实体索引');
    if (returnFocus) toggle.focus();
  }
  function filter() {
    const query = search.value.trim().toLocaleLowerCase(); let count = 0;
    const matches = new Set(registry.objects.filter(item =>
      `${item.name} ${item.short_name} ${item.object_id}`.toLocaleLowerCase().includes(query)).map(o => o.object_id));
    for (const item of registry.objects) {
      const match = matches.has(item.object_id) || matches.has(item.parent_id) ||
        registry.objects.some(child => child.parent_id === item.object_id && matches.has(child.object_id));
      rows.get(item.object_id).hidden = !match; if (match) count++;
    }
    for (const [id, branch] of branches) {
      branch.hidden = !registry.objects.some(o => o.parent_id === id && !rows.get(o.object_id).hidden);
      if (query && !branch.hidden) branch.open = true;
    }
    for (const [key, group] of groups) {
      group.hidden = !registry.objects.some(o => o.group === key && !rows.get(o.object_id).hidden);
      if (query && !group.hidden) group.open = true;
    }
    document.getElementById('empty-index').hidden = count !== 0;
    document.getElementById('clear-search').hidden = !query;
  }
  for (const [key, name, glyph] of GROUPS) {
    const group = document.createElement('details'); group.open = true;
    const title = document.createElement('summary'); title.textContent = name; group.append(title);
    function appendRow(item, container) {
      const row = document.createElement('button'); row.dataset.select = item.object_id;
      row.setAttribute('aria-pressed', 'false');
      const text = document.createElement('span'), id = document.createElement('small');
      text.textContent = `${item.short_name} ${item.name}`; id.textContent = item.object_id;
      row.append(text, id); row.onclick = () => onSelect(item.object_id, row);
      container.append(row); rows.set(item.object_id, row);
    }
    for (const item of registry.objects.filter(o => o.group === key && !o.parent_id)) {
      appendRow(item, group);
      const children = registry.objects.filter(o => o.parent_id === item.object_id);
      if (children.length) {
        const branch = document.createElement('details'); branch.className = 'entity-children';
        const summary = document.createElement('summary'); summary.textContent = `${item.short_name} 子设备（${children.length}）`;
        branch.append(summary); children.forEach(child => appendRow(child, branch));
        group.append(branch); branches.set(item.object_id, branch);
      }
    }
    tree.append(group); groups.set(key, group);
    const icon = document.createElement('button'); icon.textContent = glyph;
    icon.title = name; icon.setAttribute('aria-label', `展开${name}`); icon.dataset.group = key;
    icon.onclick = () => {
      setExpanded(true); search.value = ''; filter();
      for (const [id, node] of groups) node.open = id === key;
      onGroup(registry.objects.filter(o => o.group === key && !o.parent_id).map(o => o.object_id));
    };
    document.getElementById('group-icons').append(icon);
  }
  toggle.onclick = () => setExpanded(!expanded);
  search.oninput = filter;
  document.getElementById('clear-search').onclick = () => { search.value = ''; filter(); search.focus(); };
  const handle = document.getElementById('index-resize');
  const applyWidth = value => {
    width = Math.max(220, Math.min(420, value)); panel.style.width = `${width}px`;
    handle.setAttribute('aria-valuenow', String(width));
  };
  const endDrag = cancel => {
    if (!drag) return;
    if (cancel) applyWidth(drag.width);
    if (handle.hasPointerCapture(drag.id)) handle.releasePointerCapture(drag.id);
    drag = null;
  };
  handle.onpointerdown = event => {
    if (event.button !== 0) return;
    drag = { id: event.pointerId, x: event.clientX, width }; handle.setPointerCapture(event.pointerId);
    event.preventDefault();
  };
  handle.onpointermove = event => { if (drag) applyWidth(drag.width + event.clientX - drag.x); };
  handle.onpointerup = () => endDrag(false);
  handle.onpointercancel = () => endDrag(true);
  handle.onlostpointercapture = () => { drag = null; };
  handle.onkeydown = event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      applyWidth(width + (event.key === 'ArrowLeft' ? -10 : 10)); event.preventDefault();
    }
  };
  return {
    get expanded() { return expanded; },
    setExpanded,
    select(id) {
      for (const [key, row] of rows) row.setAttribute('aria-pressed', String(key === id));
      const item = registry.objects.find(o => o.object_id === id);
      if (item) {
        if (search.value && rows.get(id).hidden) { search.value = ''; filter(); }
        let container = rows.get(id).parentElement;
        while (container && container !== tree) { if (container.tagName === 'DETAILS') container.open = true; container = container.parentElement; }
      }
    },
    focus(id) {
      const row = rows.get(id);
      const collapsed = row?.closest('details:not([open])');
      if (expanded && !row?.hidden && !collapsed && row?.getClientRects().length) row.focus();
      else if (expanded && collapsed?.getClientRects().length) collapsed.querySelector('summary').focus();
      else toggle.focus();
    },
    escape() {
      if (drag) { endDrag(true); return true; }
      if (expanded && search.value) { search.value = ''; filter(); search.focus(); return true; }
      if (expanded) { setExpanded(false, true); return true; }
      return false;
    },
    get resizing() { return !!drag; },
  };
}
