"""Check frozen prototype transitions, not runtime product behavior."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'qc/m7-design/figma-readback.json').read_text())
frames = {f['id']: f for f in data['frames']}
checks = []

def require(value, message):
    if not value:
        raise AssertionError(message)
    checks.append(message)

def transition(frame_id, name, target=None, action='NODE', trigger='ON_CLICK'):
    return any(c['name'] == name and c['trigger'] == trigger and
               c['action'] == action and (target is None or c['target'] == target)
               for c in frames[frame_id]['controls'])

require(len(frames) == 25, '25 frozen design frames')
require(not data['dangling'], 'no unresolved page-navigation target')
require(not data['overflow'], 'no unscrollable detail content overflow')
require(data['fonts'] == ['Noto Sans SC'], 'Chinese typeface consistent')
require(all(f'183:{i}' in frames for i in range(3, 11)), 'eight primary screens preserved')
states = {
    'standard': ['183:3', '183:7', '183:8', '193:977', '193:1188'],
    'satellite': ['183:5', '193:558', '206:1266', '206:1535', '206:1794'],
    'data': ['183:6', '193:782', '206:2053', '206:2296', '206:2533'],
}
for view, (home, detail, relations, pump, hub) in states.items():
    require(transition(home, 'map/select/AGRI_018', detail), f'{view}: C1 map opens same facility')
    require(transition(detail, 'detail/relations', relations), f'{view}: relations retain base view')
    require(transition(relations, 'detail/properties', detail), f'{view}: properties retain base view')
    require(transition(detail, 'detail/close', home), f'{view}: facility closes to same base')
    for child in [pump, hub]:
        require(transition(child, 'detail/back', relations), f'{view}: {child} returns to parent relations')
        require(transition(child, frames[child]['name'], relations, trigger='ON_KEY_DOWN'), f'{view}: {child} Escape exits one level')
    require(transition(relations, 'detail/pump', pump), f'{view}: pump has dedicated card')
    require(transition(relations, 'detail/upstream', hub), f'{view}: upstream has dedicated card')
    for other, other_ids in states.items():
        if other == view:
            continue
        require(transition(relations, f'view/{other}', other_ids[2]), f'{view} to {other}: preserve relationship context')
for name in ['audit/close', 'audit/back', 'audit/backdrop']:
    require(transition('183:10', name, action='BACK'), f'{name}: return to actual origin')
for node_id, prefix in [('193:1400', 'layers'), ('193:1424', 'image')]:
    require(transition(node_id, prefix + '/close', action='CLOSE'), f'{prefix}: explicit close')
    require(transition(node_id, 'overlay/backdrop', action='CLOSE'), f'{prefix}: backdrop close')
    require(transition(node_id, frames[node_id]['name'], action='CLOSE', trigger='ON_KEY_DOWN'), f'{prefix}: Escape closes overlay')
manifest = json.loads((ROOT / 'design/m7/manifest.json').read_text())
import hashlib
for path, expected in manifest['files'].items():
    require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected, f'export/source hash: {path}')
require(hashlib.sha256((ROOT/'qc/m7-design/figma-readback.json').read_bytes()).hexdigest()
        == manifest['frozen_baseline']['readback_sha256'], 'frozen readback identity')
map_assets = ROOT / manifest['map']['asset_directory']
for name, expected in manifest['map']['files'].items():
    require(hashlib.sha256((map_assets/name).read_bytes()).hexdigest() == expected,
            f'archived map hash: {name}')
coordinate = json.loads((ROOT/'data/contracts/coordinate-contract.json').read_text())
transform = manifest['map']['transform']
for key in ['origin_utm_egm2008_m','blender_to_glb_matrix_row_major',
            'vertical_reference','independent_registration_status']:
    require(transform[key] == coordinate[key], f'map canonical transform: {key}')
for path, expected in manifest['map']['input_sha256'].items():
    if not path.startswith('outputs/'):
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected,
                f'canonical map input: {path}')
print(json.dumps({'status':'pass','checks':len(checks),'scope':'frozen Figma graph and exports; not runtime QA'}, ensure_ascii=False))
