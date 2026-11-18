"""Validate frozen Figma navigation evidence, not browser behavior."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QC = ROOT / 'qc/m15-figma-runtime-sync-v1'
snapshot = json.loads((QC / 'figma-final-structure.json').read_text())
frames = {f['id']: f for f in snapshot['frames']}
roots = {
    '01': '251:528', '02': '251:657', '03': '251:803', '04': '251:931',
    '05': '251:1063', '06': '251:1210', '07': '251:1357', '08': '251:1495',
    '09': '258:551', '10': '258:702', '11': '258:853', '12': '258:1004',
    '13': '258:1155', '14': '258:1306', '15': '258:1448',
    '16': '266:1106', '17': '266:1297',
}
variants = json.loads((QC / 'variant-nodes.json').read_text())
if isinstance(variants, dict):
    variants = variants.get('variants', variants.get('frames', []))
checks = []


def check(name, passed):
    checks.append({'name': name, 'pass': bool(passed)})


def lookup(screen, mode):
    if screen in ['01', '03', '04']:
        return roots[{'standard': '01', 'satellite': '03', 'data': '04'}[mode]]
    if mode == 'standard':
        return roots[screen]
    return next(v['id'] for v in variants if v['screen'] == screen and v['mode'] == mode)


def actions(frame, name):
    return [a for n in frame['nodes'] if n['name'] == name
            for r in n.get('reactions', []) for a in r['actions']]


def walk(action):
    yield action
    if action['type'] == 'CONDITIONAL':
        for branch in action['branches']:
            for target in branch[1:]:
                yield {'type': 'NODE', 'navigation': 'NAVIGATE', 'destinationId': target}


check('43 frames: 17 main, 22 contextual, 4 overlays', len(frames) == 43 and len(variants) == 22)
for fid, frame in frames.items():
    root = next(n for n in frame['nodes'] if n['id'] == fid)
    check(fid + ' Escape exists', any(r['trigger']['type'] == 'ON_KEY_DOWN'
          and 27 in r['trigger'].get('keyCodes', []) for r in root.get('reactions', [])))
    for node in frame['nodes']:
        check(node['id'] + ' current text/font', node.get('font') != 'MISMATCH'
              and not any(t in node.get('text', '') for t in ['设施模型 · 待补全', '模型缺口   第二温室支管']))
        for reaction in node.get('reactions', []):
            for raw in reaction['actions']:
                for action in walk(raw):
                    if action['type'] == 'NODE':
                        target = action.get('destinationId')
                        check(node['id'] + ' valid destination', target in frames)
                        check(node['id'] + ' no self navigation', action.get('navigation') != 'NAVIGATE' or target != fid)

for screen, mode, fid in ([(s, 'standard', fid) for s, fid in roots.items()
                           if s not in ['03', '04', '08', '15', '17']]
                          + [('01', 'satellite', roots['03']), ('01', 'data', roots['04'])]
                          + [(v['screen'], v['mode'], v['id']) for v in variants]):
    frame = frames[fid]
    for target_mode in ['standard', 'satellite', 'data']:
        navs = [a['destinationId'] for a in actions(frame, 'view/' + target_mode) if a['type'] == 'NODE']
        check(fid + ' view preserves context ' + target_mode,
              navs == ([] if mode == target_mode else [lookup(screen, target_mode)]))

for child, parent in [('09', '10'), ('10', '01'), ('12', '11'), ('15', '17')]:
    frame = frames[roots[child]]
    check(child + ' Escape returns parent', any(a.get('destinationId') == roots[parent]
          for a in actions(frame, frame['name'])))

# The player discarded branches after the first ELSE in one multi-way action.
# Check each possible source, including later sources, against the read-back graph.
origins = ['01', '02', '05', '06', '07', '09', '10', '14']
conditional_nodes = 0
for fid, frame in frames.items():
    mode = next((v['mode'] for v in variants if v['id'] == fid), 'standard')
    for node in frame['nodes']:
        for reaction in node.get('reactions', []):
            conditionals = [a for a in reaction['actions'] if a['type'] == 'CONDITIONAL']
            if not conditionals:
                continue
            conditional_nodes += 1
            check(node['id'] + ' independent conditions with empty ELSE',
                  len(conditionals) == 8 and all(len(a['branches']) == 2
                      and a['branches'][1] == ['ELSE'] for a in conditionals))
            for origin in origins:
                selected = []
                for action in conditionals:
                    branch = next((b for b in action['branches']
                                   if b[0] in [origin, 'ELSE']), [])
                    selected.extend(branch[1:])
                check(node['id'] + ' returns source ' + origin + ' in ' + mode,
                      selected == [lookup(origin, mode)])
check('48 geographic conditional reactors read back', conditional_nodes == 48)

failure_layout = json.loads((QC / 'failure-close-layout.json').read_text())
check('map failure X fits inside header', failure_layout['inside']
      and failure_layout['close']['x'] + failure_layout['close']['width']
      <= failure_layout['head']['width'])

check('failure close does not restore success', not any(a['type'] == 'NODE'
      for a in actions(frames[roots['17']], frames[roots['17']]['name'])))
for fid in ['251:1638', '251:1647', '280:3359', '280:3368']:
    check(fid + ' outside click closes', any(a['type'] == 'CLOSE'
          for a in actions(frames[fid], 'overlay/outside-close')))
    close = 'layers/close' if fid == '251:1638' else 'image/close'
    check(fid + ' X closes', any(a['type'] == 'CLOSE' for a in actions(frames[fid], close)))

identity = json.loads((QC / 'm14-identity-recheck.json').read_text())
check('130 M14 inputs unchanged', identity['count'] == 130 and identity['unchanged'])
runtime = json.loads((QC / 'runtime/receipt.json').read_text())
check('24 runtime reference states pass', runtime['status'] == 'pass'
      and len(runtime['checks']) == 24 and not runtime['errors'])
result = {'status': 'pass' if all(c['pass'] for c in checks) else 'fail',
          'scope': 'Figma frozen structure; not prototype-player clicks or independent QA',
          'checks': checks, 'count': len(checks),
          'snapshot_sha256': hashlib.sha256((QC / 'figma-final-structure.json').read_bytes()).hexdigest()}
(QC / 'design-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'count': len(checks),
                  'failed': [c for c in checks if not c['pass']]}, ensure_ascii=False))
raise SystemExit(0 if result['status'] == 'pass' else 1)
