"""Validate actual standalone sensor bytes and keep the accepted map frozen."""
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/m14-agriculture-sensors-v1'
QC = ROOT / 'qc/m14-agriculture-sensors-v1'
IDS = [f'AGRI_{i}_SENSOR' for i in ['014','015','016','017']]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    before_raw = json.loads((QC/'before-modeling.json').read_text())
    text = next(c['text'] for c in before_raw['content'] if c['type']=='text')
    before = json.loads(text[text.index('{'):])['sensors']
    path = OUT/'four-agriculture-sensors.glb'
    blob = path.read_bytes()
    assert struct.unpack_from('<4sII', blob) == (b'glTF',2,len(blob))
    length, kind = struct.unpack_from('<II',blob,12)
    assert kind==0x4E4F534A
    doc=json.loads(blob[20:20+length])
    bin_length, bin_kind=struct.unpack_from('<II',blob,20+length)
    assert bin_kind==0x004E4942
    binary=blob[28+length:]
    assert len(binary)==bin_length
    nodes=doc['nodes']
    roots={n['name']:n for n in nodes if n.get('name') in IDS}
    assert set(roots)==set(IDS)
    assert {n.get('extras',{}).get('object_id') for n in nodes}==set(IDS)
    counts={}
    vertices=0
    for oid,node in roots.items():
        extra=node['extras']
        assert extra['parent_id']==oid.removesuffix('_SENSOR')
        assert extra['model_status']=='schematic_proxy_unconnected'
        assert extra['real_measurements_available'] is False
        assert not any(k in extra for k in ['port_id','connection_id','measured_value'])
        old=before[oid]['matrix_world']
        xyz=node['translation']
        assert math.dist([xyz[0],-xyz[2],xyz[1]],[old[3],old[7],old[11]])<.002
        children=node['children']
        assert len(children)==37 and all('mesh' in nodes[j] for j in children)
        counts[oid]=len(children)
        for j in children:
            child=nodes[j]
            assert child['extras']['object_id']==oid
            assert child['extras']['installation_status']=='candidate_unverified'
            for primitive in doc['meshes'][child['mesh']]['primitives']:
                assert 0<=primitive['material']<len(doc['materials'])
                accessor=doc['accessors'][primitive['attributes']['POSITION']]
                assert accessor['componentType']==5126 and accessor['type']=='VEC3'
                view=doc['bufferViews'][accessor['bufferView']]
                start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
                stride=view.get('byteStride',12)
                count=accessor['count']
                assert start+(count-1)*stride+12<=view.get('byteOffset',0)+view['byteLength']<=len(binary)
                for k in range(count):
                    assert all(math.isfinite(v) for v in struct.unpack_from('<fff',binary,start+k*stride))
                vertices+=count
    assert len(doc['meshes'])==148 and len(doc['materials'])==5
    hashes={str(path.relative_to(ROOT)):digest(path)}
    for oid in IDS:
        png=OUT/(oid+'.png')
        data=png.read_bytes()
        assert data[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack_from('>II',data,16)==(900,600)
        hashes[str(png.relative_to(ROOT))]=digest(png)
    blend=OUT/'乌兰察布_农业测点补模_v1.blend'
    # The connected Blender saves Zstandard-compressed .blend files, including
    # the retained M12 source. Native save + live observation cover the scene;
    # this byte check identifies the container, not a standalone .blend parser.
    assert blend.read_bytes().startswith((b'BLENDER', b'\x28\xb5\x2f\xfd'))
    hashes[str(blend.relative_to(ROOT))]=digest(blend)
    frozen=json.loads((ROOT/'qc/m13-geographic-ui-v1/tested-identity.json').read_text())
    assert all(digest(ROOT/name)==sha for name,sha in frozen['hashes'].items())
    receipt={'status':'pass_for_standalone_model_assets','entities':4,'mesh_nodes':148,
        'vertices':vertices,'materials':5,'meshes_by_entity':counts,
        'source_roots_and_parent_ids':'unchanged','m13_identity_files_unchanged':len(frozen['hashes']),
        'previews':{'count':4,'size':[900,600]},'sha256':hashes,
        'blender_view_observed':'live Blender close-up on AGRI_016_SENSOR; material viewport and rendered image inspected',
        'web_integration':'not_run; preserved accepted M13 runtime',
        'engineering':'candidate display-scale sample; pipe taps, signals, range, vendor and field installation unverified',
        'review_mode':'coordinator_single_agent'}
    (QC/'model-validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='sha256'},ensure_ascii=False))

if __name__=='__main__':
    main()
