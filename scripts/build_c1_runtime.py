"""Derive selectable C1 entities, ports and edges from the retained GLB extras."""
import hashlib
import json
import struct
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
asset = BASE / 'web/map-viewer/assets/facilities-v1/facilities.glb'
raw = asset.read_bytes()
glb = json.loads(raw[20:20 + struct.unpack_from('<I', raw, 12)[0]])
nodes = glb['nodes']
parents = {c: i for i, n in enumerate(nodes) for c in n.get('children', [])}
root_index = next(i for i, n in enumerate(nodes) if n.get('extras', {}).get('asset_id') == 'AGRI_018')


def world_position(index):
    result = [0, 0, 0]
    while True:
        n = nodes[index]
        # This asset's semantic roots/ports are translations. Reject a changed
        # transform contract rather than silently discarding scale or rotation.
        assert not n.get('matrix') and not n.get('rotation') and n.get('scale', [1, 1, 1]) == [1, 1, 1]
        result = [a + b for a, b in zip(result, n.get('translation', [0, 0, 0]))]
        if index not in parents:
            return [result[0], -result[2], result[1]]
        index = parents[index]


def in_c1(index):
    while index != root_index:
        if index not in parents:
            return False
        index = parents[index]
    return True


entities, ports, edges = [], [], []
short = {'HX': '板换', 'PUMP': '热水泵', 'VALVE': '调节阀', 'HEADER': '热水集管',
         'GH1': '温室1', 'GH2': '温室2', 'TANK': '营养箱', 'NPUMP': '营养泵',
         'NHEADER': '营养集管', 'SENSOR': '测点', 'CTRL': 'PLC'}
for i, n in enumerate(nodes):
    if not in_c1(i):
        continue
    e = n.get('extras', {})
    if e.get('label') and e.get('parent_id') == 'AGRI_018':
        oid = e['object_id']
        entities.append({'object_id': oid, 'parent_id': 'AGRI_018', 'name': e['label'],
                         'short_name': short[oid.removeprefix('AGRI_018_')], 'group': 'c',
                         'gltf_root_index': i, 'model_root_xyz': world_position(i),
                         'model_revision': e['m8_revision'], 'installation_status': '候选规划 · 未验收投运',
                         'planning_area': None, 'model_footprint_m2': None,
                         'description': 'C1同版示意子设备；型号、容量、工况与工程尺寸待核。',
                         'gaps': ['非厂家施工模型', '无实测温度、流量或泵扬程'],
                         'preview_url': f'../map-viewer/assets/c1-devices-v1/{oid}.png'})
    if e.get('port_id'):
        ports.append({k: e[k] for k in ['port_id', 'object_id', 'circuit_id', 'direction', 'medium']}
                     | {'model_xyz': world_position(i), 'gltf_node_index': i})
    if e.get('connection_id'):
        edges.append({k: e[k] for k in ['connection_id', 'from_port_id', 'to_port_id', 'circuit_id', 'design_status']}
                     | {'gltf_node_index': i, 'status': 'schematic_not_commissioned'})

assert len(entities) == 11 and len(ports) == 38 and len(edges) == 19
by_port = {p['port_id']: p for p in ports}
assert len(by_port) == len(ports)
for edge in edges:
    a, b = by_port[edge['from_port_id']], by_port[edge['to_port_id']]
    assert a['direction'] == 'out' and b['direction'] == 'in'
    assert a['medium'] == b['medium'] and a['circuit_id'] == b['circuit_id'] == edge['circuit_id']
    edge.update({'from_object_id': a['object_id'], 'to_object_id': b['object_id'], 'medium': a['medium'],
                 'role': 'return' if ('_return' in a['port_id'] or edge['connection_id'] in ['EDGE_017', 'EDGE_024']) else 'supply'})
for entity in entities:
    entity['circuits'] = sorted({p['circuit_id'] for p in ports if p['object_id'] == entity['object_id']})

result = {'revision': 'c1-runtime-v1', 'parent_id': 'AGRI_018',
          'asset_sha256': hashlib.sha256(raw).hexdigest(), 'model_revision': 'c1-dual-loop-v1',
          'objects': entities, 'ports': ports, 'connections': edges,
          'external_status': 'reserved_not_operating', 'hydraulic_validation': 'not_run'}
out = BASE / 'web/map-prototype/c1-runtime.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'entities': len(entities), 'ports': len(ports), 'connections': len(edges), 'output': str(out)}))
