"""Check combined GLB bytes, semantic ownership, coordinates, ports and visible edges."""
import hashlib
import json
import math
import struct
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def matrix(node):
    if 'matrix' in node:
        return [node['matrix'][i::4] for i in range(4)]
    x,y,z,w = node.get('rotation',[0,0,0,1])
    scale = node.get('scale',[1,1,1]); t = node.get('translation',[0,0,0])
    rows = [[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
            [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
            [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]]
    return [[rows[i][j]*scale[j] for j in range(3)]+[t[i]] for i in range(3)]+[[0,0,0,1]]


def mul(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='qc/m11-integrated-v1/model-validation.json')
    args=parser.parse_args()
    folder = ROOT/'web/map-prototype'
    asset = json.loads((folder/'integrated-asset.json').read_text())
    blob = (folder/asset['asset_url']).resolve().read_bytes()
    assert struct.unpack_from('<4sII',blob)==(b'glTF',2,len(blob))
    assert hashlib.sha256(blob).hexdigest()==asset['sha256']
    json_size = struct.unpack_from('<I',blob,12)[0]
    doc = json.loads(blob[20:20+json_size]); nodes = doc['nodes']
    assert struct.unpack_from('<I',blob,24+json_size)[0]==0x004e4942
    binary = blob[28+json_size:]
    graphs = [json.loads((folder/n).read_text()) for n in ['facility-registry.json','c1-runtime.json','ab-terminal-runtime.json','m10-system-runtime.json']]
    entities = {o['object_id']:o for g in graphs for o in g['objects']}
    assert len(entities)==sum(len(g['objects']) for g in graphs)
    assert len(graphs[0]['objects'])==12
    assert set(entities)==set(asset['entity_nodes'])
    parents = {child:i for i,n in enumerate(nodes) for child in n.get('children',[])}
    world = {}
    def transform(i):
        if i not in world:
            world[i]=mul(transform(parents[i]),matrix(nodes[i])) if i in parents else matrix(nodes[i])
        return world[i]
    def origin(i):
        t=transform(i); return [t[0][3],-t[2][3],t[1][3]]
    coordinate_errors = {}
    for id,entity in entities.items():
        idx=asset['entity_nodes'][id]; extras=nodes[idx].get('extras',{})
        assert extras.get('object_id',extras.get('asset_id'))==id,id
        error=math.dist(origin(idx),entity['model_root_xyz']);coordinate_errors[id]=error
        assert error<.002,(id,error)
    mesh_names = {n['name'] for n in nodes if 'mesh' in n}
    duplicate_conversions = [name for name in mesh_names
                            if name.endswith(' | GLB mesh') and name.removesuffix(' | GLB mesh') in mesh_names]
    assert not duplicate_conversions, ('duplicate curve/font surfaces', duplicate_conversions)
    rendered = {id:0 for id in entities}; edge_meshes={}
    vertices = 0
    checked_accessors=set()
    for i,node in enumerate(nodes):
        if 'mesh' not in node: continue
        owner=i
        while owner is not None:
            e=nodes[owner].get('extras',{}); id=e.get('object_id',e.get('asset_id'))
            if id in entities: break
            owner=parents.get(owner)
        assert owner is not None,('unowned mesh',node['name'])
        rendered[id]+=1
        connection=node.get('extras',{}).get('connection_id')
        if connection:edge_meshes[connection]=edge_meshes.get(connection,0)+1
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            assert 0<=primitive['material']<len(doc['materials'])
            ai=primitive['attributes']['POSITION']; accessor=doc['accessors'][ai]
            assert accessor['componentType']==5126 and accessor['type']=='VEC3'
            vertices+=accessor['count']
            if ai in checked_accessors:continue
            checked_accessors.add(ai)
            view=doc['bufferViews'][accessor['bufferView']]
            start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
            stride=view.get('byteStride',12)
            assert start+(accessor['count']-1)*stride+12<=view.get('byteOffset',0)+view['byteLength']<=len(binary)
            for j in range(accessor['count']):
                assert all(math.isfinite(v) for v in struct.unpack_from('<fff',binary,start+j*stride))
    ports={n.get('extras',{}).get('port_id'):i for i,n in enumerate(nodes) if n.get('extras',{}).get('port_id')}
    checked_edges=[]
    port_coordinate_errors=[]
    for graph in graphs[1:]:
        declared={p['port_id']:p for p in graph['ports']}
        assert set(declared)<=set(ports)
        for edge in graph['connections']:
            assert edge['from_port_id'] in declared and edge['to_port_id'] in declared
            assert edge_meshes.get(edge['connection_id'],0)>0,('invisible connection',edge['connection_id'])
            checked_edges.append(edge['connection_id'])
    for port in graphs[3]['ports']:
        root=entities[port['object_id']]['model_root_xyz']
        expected=[a+b for a,b in zip(root,port['position']['xyz_m'])]
        error=math.dist(origin(ports[port['port_id']]),expected)
        assert error<.002,(port['port_id'],error)
        port_coordinate_errors.append(error)
    for id in ['DC_004','DC_005','DC_006','HUB_011','STORE_012','DEMO_013','AGRI_014','AGRI_015','AGRI_016','AGRI_017','AGRI_018','DRY_019']:
        assert rendered[id]>0,id
    for id in ['AGRI_016_HX','AGRI_017_GH1','BOILER_CAND_001']:
        assert rendered[id]>0,id
    expected_semantic = set() if asset['revision']=='m14-sensors-integrated-v1' else {f'AGRI_{i}_SENSOR' for i in ['014','015','016','017']}
    assert set(asset['semantic_only_entities'])==expected_semantic
    if not expected_semantic:
        for i in ['014','015','016','017']:
            assert rendered[f'AGRI_{i}_SENSOR']>=37
    assert {id for id,count in rendered.items() if not count}==set(asset['semantic_only_entities'])
    for source,sha in asset['sources'].items():
        assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==sha,source
    receipt={'status':'pass','glb_sha256':asset['sha256'],'entities':len(entities),'mesh_nodes':sum(rendered.values()),
             'vertices':vertices,'material_count':len(doc['materials']),'port_nodes':len(ports),
             'visible_connections_verified':len(checked_edges),'max_coordinate_difference_m':max(coordinate_errors.values()),
             'duplicate_converted_surfaces':len(duplicate_conversions),
             'max_m10_port_coordinate_difference_m':max(port_coordinate_errors,default=0),
             'rendered_meshes_by_entity':rendered,'visible_connections':edge_meshes,
             'limits':['Geometric/semantic verification only; no hydraulic sizing or independent geographic registration',
                       'Candidate model sockets are not field nozzle locations or commissioned piping'],
             'reviewer':'coordinator_single_agent'}
    (ROOT/args.output).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['rendered_meshes_by_entity','visible_connections','limits']}))


if __name__=='__main__':
    main()
