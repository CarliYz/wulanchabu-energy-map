"""Complete a live-MCP raw receipt with identities derived from the actual export bytes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def finalize(raw, glb):
    data = glb.read_bytes()
    assert struct.unpack_from('<4sII', data) == (b'glTF', 2, len(data)), 'Invalid GLB framing'
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(data[20:20 + size])
    assert len(doc['scenes']) == 1, 'Expected one exported scene'
    nodes = doc['nodes']
    roots = {}
    for i, node in enumerate(nodes):
        fid = node.get('extras', {}).get('asset_id')
        if fid:
            assert fid not in roots, f'Duplicate facility {fid}'
            roots[fid] = i
    ids = [o['object_id'] for o in raw['objects']]
    assert len(ids) == len(set(ids)) == len(roots) == 12 and set(ids) == set(roots)
    owned = set()
    for item in raw['objects']:
        fid = item['object_id']
        item['gltf_root_index'] = roots[fid]
        pending = [roots[fid]]
        descendants = []
        while pending:
            i = pending.pop()
            assert i not in owned, f'Overlapping/cyclic ownership {fid}/{i}'
            owned.add(i)
            descendants.append(i)
            pending.extend(nodes[i].get('children', []))
        assert any('mesh' in nodes[i] for i in descendants), f'No geometry {fid}'
        assert len(descendants) == item['included_objects'], f'Export object count changed {fid}'
    raw['sha256'] = hashlib.sha256(data).hexdigest()
    raw['bytes'] = len(data)
    raw['source_sha256'] = hashlib.sha256(Path(raw['source_blend']).read_bytes()).hexdigest()
    return raw


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-receipt', required=True, type=Path)
    parser.add_argument('--glb', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = finalize(json.loads(args.raw_receipt.read_text()), args.glb)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'objects': len(result['objects']), 'sha256': result['sha256'], 'output': str(args.output)}))
