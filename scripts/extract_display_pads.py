"""Read actual GLB pad vertices; do not infer surveyed building footprints."""
import hashlib
import argparse
import json
import struct
from pathlib import Path
from validate_integrated_model import matrix, mul

ROOT = Path(__file__).resolve().parents[1]


def hull(points):
    points = sorted(set(points))
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for target, values in [(lower, points), (upper, reversed(points))]:
        for p in values:
            while len(target) >= 2 and cross(target[-2], target[-1], p) <= 0:
                target.pop()
            target.append(p)
    ring = lower[:-1]+upper[:-1]
    if len(ring) < 3:
        raise ValueError('Degenerate display pad')
    return ring+[ring[0]]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='qc/m13-geographic-review-v1/display-pads.json')
    args=parser.parse_args()
    folder = ROOT/'web/map-prototype'
    binding = json.loads((folder/'integrated-asset.json').read_text())
    asset = (folder/binding['asset_url']).resolve()
    blob = asset.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == binding['sha256'], 'GLB identity changed'
    size = struct.unpack_from('<I', blob, 12)[0]
    doc = json.loads(blob[20:20+size]); binary = blob[28+size:]
    nodes = doc['nodes']; parents = {child:i for i,n in enumerate(nodes) for child in n.get('children', [])}
    world = {}
    def transform(i):
        if i not in world:
            world[i] = mul(transform(parents[i]), matrix(nodes[i])) if i in parents else matrix(nodes[i])
        return world[i]
    objects = json.loads((folder/'facility-registry.json').read_text())['objects']
    pads = []
    for obj in objects:
        oid = obj['object_id']; matches = [(i,n) for i,n in enumerate(nodes) if n.get('name') == oid+' | 场坪']
        assert len(matches) == 1, (oid, 'missing/ambiguous display pad')
        i, node = matches[0]; t = transform(i); points = []
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            acc = doc['accessors'][primitive['attributes']['POSITION']]
            assert acc['componentType'] == 5126 and acc['type'] == 'VEC3'
            view = doc['bufferViews'][acc['bufferView']]; stride = view.get('byteStride', 12)
            start = view.get('byteOffset', 0)+acc.get('byteOffset', 0)
            for j in range(acc['count']):
                p = [*struct.unpack_from('<fff', binary, start+j*stride), 1]
                v = [sum(t[k][l]*p[l] for l in range(4)) for k in range(3)]
                points.append((v[0], -v[2]))
        pads.append({'object_id':oid, 'source_node':node['name'], 'ring_local_xy':hull(points),
                     'geometry_scope':'actual_display_pad_convex_hull_not_surveyed_footprint'})
    output = ROOT/args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'asset_path':str(asset.relative_to(ROOT)), 'asset_sha256':digest, 'pads':pads}, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'pads':len(pads), 'asset_sha256':digest}))


if __name__ == '__main__':
    main()
